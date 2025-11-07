from ninja import Router, File
from ninja.security import HttpBearer
from ninja.files import UploadedFile
from typing import Optional
from pydantic import BaseModel
from agents.services.langgraph_agent import LangGraphAgent
from agents.services.document_rag import DocumentRAGService
from agents.models import Document
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
import os
from pathlib import Path

from agents.services.campaign_suggestions import CampaignSuggestionService

router = Router()


class TokenAuth(HttpBearer):
    def authenticate(self, request, token):
        from rest_framework_simplejwt.authentication import JWTAuthentication
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user
        except:
            return None


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str
    task_type: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    message: str
    document_id: int
    chunks_count: int


class CampaignSuggestionsResponse(BaseModel):
    campaign_names: list
    sales_offers: list  # Changed to list for multiple suggestions


@router.get("/campaigns/suggestions/{project_name}", response=CampaignSuggestionsResponse, auth=TokenAuth())
def get_campaign_suggestions(request, project_name: str):
    """Get AI-generated campaign name and sales offer suggestions based on project brochure"""
    try:
        suggestion_service = CampaignSuggestionService()
        campaign_names = suggestion_service.generate_campaign_name_suggestions(project_name)
        sales_offers = suggestion_service.generate_sales_offer_suggestions(project_name)
        
        return CampaignSuggestionsResponse(
            campaign_names=campaign_names,
            sales_offers=sales_offers
        )
    except Exception as e:
        return {"error": str(e)}, 500


@router.post("/query", response=QueryResponse, auth=TokenAuth())
def query_agent(request, data: QueryRequest):
    """Query the LangGraph agent"""
    agent = LangGraphAgent()
    response = agent.query(data.query)
    
    # Determine task type from response
    task_type = "rag" if "brochure" in data.query.lower() or "property" in data.query.lower() else "t2sql"
    
    return QueryResponse(response=response, task_type=task_type)


@router.post("/documents/upload", response=DocumentUploadResponse, auth=TokenAuth())
def upload_document(request, file: UploadedFile = File(...), project_name: Optional[str] = None):
    """Upload and ingest a brochure document"""
    try:
        # Save uploaded file
        file_path = default_storage.save(f"brochures/{file.name}", file)
        full_path = default_storage.path(file_path)
        
        # Ingest document
        rag_service = DocumentRAGService()
        chunks_count = rag_service.ingest_document(full_path, project_name)
        
        # Save document record
        document = Document.objects.create(
            name=file.name,
            project_name=project_name,
            file_path=file_path,
            file_size=file.size,
            file_type=Path(file.name).suffix[1:] if Path(file.name).suffix else 'pdf',
            chunks_count=chunks_count,
        )
        
        return DocumentUploadResponse(
            message="Document uploaded and ingested successfully",
            document_id=document.id,
            chunks_count=chunks_count,
        )
    except Exception as e:
        return {"error": str(e)}, 500


@router.post("/campaigns/{campaign_id}/respond", auth=TokenAuth())
def respond_to_customer(request, campaign_id: int, lead_id: str, customer_message: str):
    """AI agent responds to customer message"""
    from campaigns.models import Campaign, CampaignConversation, CampaignLead, Lead
    from agents.services.intent_detector import IntentDetector
    
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        lead = Lead.objects.get(lead_id=lead_id)
    except (Campaign.DoesNotExist, Lead.DoesNotExist):
        return {"error": "Campaign or Lead not found"}, 404
    
    # Detect intent
    intent_detector = IntentDetector()
    intent = intent_detector.detect_intent(customer_message)
    
    # Generate response using agent
    agent = LangGraphAgent()
    
    # Build context-aware query
    context_query = f"""
    Customer message: {customer_message}
    Campaign project: {campaign.campaign_project_name}
    Lead preferences: {lead.last_conversation_summary}
    
    Respond to the customer's message. If they're asking about property features, use brochure information.
    If they want to schedule a visit or call, acknowledge and indicate that scheduling will be arranged.
    """
    
    agent_response = agent.query(context_query)
    
    # If intent is to schedule visit/call, mark goal as achieved
    if intent in ['schedule_visit', 'schedule_call']:
        try:
            campaign_lead = CampaignLead.objects.get(campaign=campaign, lead=lead)
            campaign_lead.goal_achieved = True
            campaign_lead.goal_type = 'visit' if intent == 'schedule_visit' else 'call'
            # Set scheduled date (default to 7 days from now if not specified)
            if not campaign_lead.goal_scheduled_date:
                from datetime import timedelta
                campaign_lead.goal_scheduled_date = timezone.now() + timedelta(days=7)
            campaign_lead.save()
        except CampaignLead.DoesNotExist:
            pass
    
    # Save conversation
    conversation = CampaignConversation.objects.create(
        campaign=campaign,
        lead=lead,
        customer_message=customer_message,
        agent_response=agent_response,
        intent_detected=intent,
    )
    
    return {
        "response": agent_response,
        "intent": intent,
        "goal_achieved": intent in ['schedule_visit', 'schedule_call'],
    }

