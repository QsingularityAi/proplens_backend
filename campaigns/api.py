from ninja import Router
from typing import List, Optional
from datetime import datetime
from django.utils import timezone
from campaigns.models import Campaign, CampaignLead, CampaignMessage, CampaignConversation
from crm.models import Lead
from pydantic import BaseModel
from agents.services.message_generator import MessageGenerator
from agents.services.email_service import EmailService
from agents.auth import TokenAuth

router = Router()


class CampaignCreateSchema(BaseModel):
    name: str
    campaign_project_name: str
    channel: str = "email"
    sales_offer_details: Optional[str] = None
    filter_project_name: Optional[str] = None
    filter_unit_types: Optional[List[str]] = None
    filter_min_budget: Optional[float] = None
    filter_max_budget: Optional[float] = None
    filter_lead_status: Optional[str] = None
    filter_date_from: Optional[str] = None
    filter_date_to: Optional[str] = None
    lead_ids: List[str]


class CampaignResponse(BaseModel):
    id: int
    name: str
    campaign_project_name: str
    channel: str
    sales_offer_details: Optional[str]
    leads_count: int
    messages_sent_count: int
    responses_count: int
    goals_achieved_count: int
    created_at: str
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    lead_id: str
    lead_name: str
    customer_message: str
    agent_response: str
    intent_detected: Optional[str]
    created_at: str


@router.post("/create", response=CampaignResponse, auth=TokenAuth())
def create_campaign(request, data: CampaignCreateSchema):
    """Create a new campaign"""
    # Get authenticated user from request.auth (set by TokenAuth)
    # request.auth is the user object returned by TokenAuth.authenticate()
    user = request.auth if hasattr(request, 'auth') and request.auth else None
    
    campaign = Campaign.objects.create(
        name=data.name,
        campaign_project_name=data.campaign_project_name,
        channel=data.channel,
        sales_offer_details=data.sales_offer_details,
        filter_project_name=data.filter_project_name,
        filter_unit_types=data.filter_unit_types or [],
        filter_min_budget=data.filter_min_budget,
        filter_max_budget=data.filter_max_budget,
        filter_lead_status=data.filter_lead_status,
        filter_date_from=datetime.strptime(data.filter_date_from, '%Y-%m-%d').date() if data.filter_date_from else None,
        filter_date_to=datetime.strptime(data.filter_date_to, '%Y-%m-%d').date() if data.filter_date_to else None,
        created_by=user,
    )
    
    # Add leads to campaign
    leads = Lead.objects.filter(lead_id__in=data.lead_ids)
    for lead in leads:
        CampaignLead.objects.create(campaign=campaign, lead=lead)
    
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        campaign_project_name=campaign.campaign_project_name,
        channel=campaign.channel,
        sales_offer_details=campaign.sales_offer_details,
        leads_count=campaign.leads_count,
        messages_sent_count=0,
        responses_count=0,
        goals_achieved_count=0,
        created_at=campaign.created_at.isoformat(),
    )


class EmailSendResult(BaseModel):
    lead_id: str
    lead_name: str
    email: str
    status: str  # 'sent' or 'failed'
    error: Optional[str] = None


class SendMessagesResponse(BaseModel):
    message: str
    sent_count: int
    failed_count: int
    results: List[EmailSendResult]


@router.post("/{campaign_id}/send-messages", response=SendMessagesResponse, auth=TokenAuth())
def send_campaign_messages(request, campaign_id: int):
    """Send personalized messages to all leads in campaign (uses stored/edited messages)"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    message_generator = MessageGenerator()
    email_service = EmailService()
    
    campaign_leads = CampaignLead.objects.filter(campaign=campaign).select_related('lead')
    sent_count = 0
    failed_count = 0
    results = []
    
    for campaign_lead in campaign_leads:
        # Skip if already sent
        if campaign_lead.message_sent_at:
            continue
        
        # Use stored message if available, otherwise generate new one
        if campaign_lead.personalized_message:
            personalized_message = campaign_lead.personalized_message
            email_subject = campaign_lead.email_subject or f"Exclusive Opportunity: {campaign.campaign_project_name}"
        else:
            personalized_message = message_generator.generate_message(
                lead=campaign_lead.lead,
                campaign_project=campaign.campaign_project_name,
                sales_offer=campaign.sales_offer_details,
            )
            email_subject = message_generator.generate_subject(
                lead=campaign_lead.lead,
                campaign_project=campaign.campaign_project_name,
            )
            campaign_lead.personalized_message = personalized_message
            campaign_lead.email_subject = email_subject
            campaign_lead.save()
        
        # Send email
        try:
            email_service.send_email(
                to_email=campaign_lead.lead.email,
                subject=email_subject,
                body=personalized_message,
            )
            
            # Save message
            CampaignMessage.objects.create(
                campaign=campaign,
                lead=campaign_lead.lead,
                message_content=personalized_message,
                status='sent',
            )
            
            campaign_lead.message_sent_at = timezone.now()
            campaign_lead.save()
            
            sent_count += 1
            results.append(EmailSendResult(
                lead_id=campaign_lead.lead.lead_id,
                lead_name=campaign_lead.lead.lead_name,
                email=campaign_lead.lead.email,
                status='sent',
            ))
        except Exception as e:
            CampaignMessage.objects.create(
                campaign=campaign,
                lead=campaign_lead.lead,
                message_content=personalized_message,
                status='failed',
            )
            failed_count += 1
            results.append(EmailSendResult(
                lead_id=campaign_lead.lead.lead_id,
                lead_name=campaign_lead.lead.lead_name,
                email=campaign_lead.lead.email,
                status='failed',
                error=str(e),
            ))
    
    return SendMessagesResponse(
        message=f"Sent {sent_count} messages successfully, {failed_count} failed",
        sent_count=sent_count,
        failed_count=failed_count,
        results=results,
    )


@router.get("/", response=List[CampaignResponse])
def list_campaigns(request):
    """List all campaigns"""
    campaigns = Campaign.objects.all()
    return [
        CampaignResponse(
            id=c.id,
            name=c.name,
            campaign_project_name=c.campaign_project_name,
            channel=c.channel,
            sales_offer_details=c.sales_offer_details,
            leads_count=c.leads_count,
            messages_sent_count=c.messages_sent_count,
            responses_count=c.responses_count,
            goals_achieved_count=c.goals_achieved_count,
            created_at=c.created_at.isoformat(),
        )
        for c in campaigns
    ]


@router.get("/{campaign_id}", response=CampaignResponse)
def get_campaign(request, campaign_id: int):
    """Get campaign details"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        return CampaignResponse(
            id=campaign.id,
            name=campaign.name,
            campaign_project_name=campaign.campaign_project_name,
            channel=campaign.channel,
            sales_offer_details=campaign.sales_offer_details,
            leads_count=campaign.leads_count,
            messages_sent_count=campaign.messages_sent_count,
            responses_count=campaign.responses_count,
            goals_achieved_count=campaign.goals_achieved_count,
            created_at=campaign.created_at.isoformat(),
        )
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404


@router.get("/{campaign_id}/conversations", response=List[ConversationResponse])
def get_campaign_conversations(request, campaign_id: int):
    """Get all conversations for a campaign"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    conversations = CampaignConversation.objects.filter(campaign=campaign).order_by('created_at')
    return [
        ConversationResponse(
            id=conv.id,
            lead_id=conv.lead.lead_id,
            lead_name=conv.lead.lead_name,
            customer_message=conv.customer_message,
            agent_response=conv.agent_response,
            intent_detected=conv.intent_detected,
            created_at=conv.created_at.isoformat(),
        )
        for conv in conversations
    ]


@router.post("/{campaign_id}/goals/{lead_id}/confirm")
def confirm_goal(request, campaign_id: int, lead_id: str):
    """Confirm a scheduled visit or call"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        lead = Lead.objects.get(lead_id=lead_id)
        campaign_lead = CampaignLead.objects.get(campaign=campaign, lead=lead)
        
        if campaign_lead.goal_achieved:
            campaign_lead.goal_confirmed = True
            campaign_lead.goal_confirmed_at = timezone.now()
            campaign_lead.save()
            return {"message": "Goal confirmed successfully"}
        else:
            return {"error": "Goal not yet achieved"}, 400
    except (Campaign.DoesNotExist, Lead.DoesNotExist, CampaignLead.DoesNotExist):
        return {"error": "Campaign, Lead, or CampaignLead not found"}, 404


@router.post("/{campaign_id}/goals/{lead_id}/reschedule")
def reschedule_goal(request, campaign_id: int, lead_id: str, new_date: str):
    """Reschedule a visit or call"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        lead = Lead.objects.get(lead_id=lead_id)
        campaign_lead = CampaignLead.objects.get(campaign=campaign, lead=lead)
        
        if campaign_lead.goal_achieved:
            new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()
            campaign_lead.goal_scheduled_date = timezone.make_aware(datetime.combine(new_date_obj, datetime.min.time()))
            campaign_lead.goal_confirmed = False
            campaign_lead.goal_confirmed_at = None
            campaign_lead.save()
            return {"message": "Goal rescheduled successfully", "new_date": new_date}
        else:
            return {"error": "Goal not yet achieved"}, 400
    except (Campaign.DoesNotExist, Lead.DoesNotExist, CampaignLead.DoesNotExist):
        return {"error": "Campaign, Lead, or CampaignLead not found"}, 404
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}, 400


@router.get("/{campaign_id}/goals", response=List[dict])
def get_campaign_goals(request, campaign_id: int):
    """Get all leads with achieved goals"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    campaign_leads = CampaignLead.objects.filter(campaign=campaign, goal_achieved=True)
    result = []
    for cl in campaign_leads:
        # Get last conversation summary - prefer campaign conversation, fallback to lead's summary
        last_conv = CampaignConversation.objects.filter(
            campaign=campaign, lead=cl.lead
        ).order_by('-created_at').first()
        
        last_conversation_summary = None
        if last_conv:
            # Use agent response as summary (it contains the context)
            last_conversation_summary = last_conv.agent_response[:200] if len(last_conv.agent_response) > 200 else last_conv.agent_response
        elif cl.lead.last_conversation_summary:
            last_conversation_summary = cl.lead.last_conversation_summary
        
        result.append({
            "lead_id": cl.lead.lead_id,
            "lead_name": cl.lead.lead_name,
            "email": cl.lead.email,
            "phone": cl.lead.phone,
            "goal_type": cl.goal_type,
            "goal_scheduled_date": cl.goal_scheduled_date.isoformat() if cl.goal_scheduled_date else None,
            "last_conversation_summary": last_conversation_summary,
        })
    return result


class LeadMessagePreview(BaseModel):
    lead_id: str
    lead_name: str
    email: str
    phone: Optional[str]
    subject: Optional[str] = None
    message: str
    message_sent: bool
    message_sent_at: Optional[str] = None


class UpdateMessageSchema(BaseModel):
    message: str
    subject: Optional[str] = None


class SendSelectedSchema(BaseModel):
    lead_ids: List[str]


@router.post("/{campaign_id}/generate-messages", response=List[LeadMessagePreview])
def generate_campaign_messages(request, campaign_id: int):
    """Generate/preview messages for all leads without sending"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    message_generator = MessageGenerator()
    campaign_leads = CampaignLead.objects.filter(campaign=campaign).select_related('lead')
    
    result = []
    for campaign_lead in campaign_leads:
        # Use existing message if available, otherwise generate new one
        if campaign_lead.personalized_message:
            message = campaign_lead.personalized_message
            subject = campaign_lead.email_subject
        else:
            message = message_generator.generate_message(
                lead=campaign_lead.lead,
                campaign_project=campaign.campaign_project_name,
                sales_offer=campaign.sales_offer_details,
            )
            subject = message_generator.generate_subject(
                lead=campaign_lead.lead,
                campaign_project=campaign.campaign_project_name,
            )
            # Save generated message and subject (not sent yet)
            campaign_lead.personalized_message = message
            campaign_lead.email_subject = subject
            campaign_lead.save()
        
        result.append(LeadMessagePreview(
            lead_id=campaign_lead.lead.lead_id,
            lead_name=campaign_lead.lead.lead_name,
            email=campaign_lead.lead.email,
            phone=campaign_lead.lead.phone,
            subject=subject,
            message=message,
            message_sent=bool(campaign_lead.message_sent_at),
            message_sent_at=campaign_lead.message_sent_at.isoformat() if campaign_lead.message_sent_at else None,
        ))
    
    return result


@router.delete("/{campaign_id}/messages/clear", auth=TokenAuth())
def clear_campaign_messages(request, campaign_id: int):
    """Clear all generated messages for a campaign (only unsent messages)"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    # Clear messages only for leads that haven't been sent yet
    campaign_leads = CampaignLead.objects.filter(
        campaign=campaign,
        message_sent_at__isnull=True  # Only clear unsent messages
    )
    
    cleared_count = 0
    for campaign_lead in campaign_leads:
        campaign_lead.personalized_message = None
        campaign_lead.email_subject = None
        campaign_lead.save()
        cleared_count += 1
    
    return {
        "message": f"Cleared {cleared_count} unsent messages",
        "cleared_count": cleared_count
    }


@router.get("/{campaign_id}/messages", response=List[LeadMessagePreview])
def get_campaign_messages(request, campaign_id: int):
    """Get all leads with their messages for editing"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    campaign_leads = CampaignLead.objects.filter(campaign=campaign).select_related('lead')
    
    result = []
    for campaign_lead in campaign_leads:
        result.append(LeadMessagePreview(
            lead_id=campaign_lead.lead.lead_id,
            lead_name=campaign_lead.lead.lead_name,
            email=campaign_lead.lead.email,
            phone=campaign_lead.lead.phone,
            subject=campaign_lead.email_subject,
            message=campaign_lead.personalized_message or "",
            message_sent=bool(campaign_lead.message_sent_at),
            message_sent_at=campaign_lead.message_sent_at.isoformat() if campaign_lead.message_sent_at else None,
        ))
    
    return result


@router.put("/{campaign_id}/messages/{lead_id}", auth=TokenAuth())
def update_lead_message(request, campaign_id: int, lead_id: str, data: UpdateMessageSchema):
    """Update message for a specific lead"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        lead = Lead.objects.get(lead_id=lead_id)
        campaign_lead = CampaignLead.objects.get(campaign=campaign, lead=lead)
        
        # Don't allow editing if already sent
        if campaign_lead.message_sent_at:
            return {"error": "Cannot edit message that has already been sent"}, 400
        
        campaign_lead.personalized_message = data.message
        if data.subject:
            campaign_lead.email_subject = data.subject
        campaign_lead.save()
        
        return {"message": "Message updated successfully"}
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    except Lead.DoesNotExist:
        return {"error": "Lead not found"}, 404
    except CampaignLead.DoesNotExist:
        return {"error": "Campaign lead not found"}, 404


@router.post("/{campaign_id}/send-message/{lead_id}", auth=TokenAuth())
def send_single_message(request, campaign_id: int, lead_id: str):
    """Send message to a single lead"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        lead = Lead.objects.get(lead_id=lead_id)
        campaign_lead = CampaignLead.objects.get(campaign=campaign, lead=lead)
        
        if not campaign_lead.personalized_message:
            return {"error": "No message generated for this lead"}, 400
        
        if campaign_lead.message_sent_at:
            return {"error": "Message already sent"}, 400
        
        email_service = EmailService()
        email_subject = campaign_lead.email_subject or f"Exclusive Opportunity: {campaign.campaign_project_name}"
        
        try:
            email_service.send_email(
                to_email=lead.email,
                subject=email_subject,
                body=campaign_lead.personalized_message,
            )
            
            # Save message
            CampaignMessage.objects.create(
                campaign=campaign,
                lead=lead,
                message_content=campaign_lead.personalized_message,
                status='sent',
            )
            
            campaign_lead.message_sent_at = timezone.now()
            campaign_lead.save()
            
            return {"message": "Message sent successfully", "status": "sent"}
        except Exception as e:
            CampaignMessage.objects.create(
                campaign=campaign,
                lead=lead,
                message_content=campaign_lead.personalized_message,
                status='failed',
            )
            return {"error": str(e), "status": "failed"}, 500
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    except Lead.DoesNotExist:
        return {"error": "Lead not found"}, 404
    except CampaignLead.DoesNotExist:
        return {"error": "Campaign lead not found"}, 404


@router.post("/{campaign_id}/send-selected", response=SendMessagesResponse, auth=TokenAuth())
def send_selected_messages(request, campaign_id: int, data: SendSelectedSchema):
    """Send messages to selected leads"""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"error": "Campaign not found"}, 404
    
    email_service = EmailService()
    campaign_leads = CampaignLead.objects.filter(
        campaign=campaign,
        lead__lead_id__in=data.lead_ids
    ).select_related('lead')
    
    sent_count = 0
    failed_count = 0
    results = []
    
    for campaign_lead in campaign_leads:
        if not campaign_lead.personalized_message:
            failed_count += 1
            results.append(EmailSendResult(
                lead_id=campaign_lead.lead.lead_id,
                lead_name=campaign_lead.lead.lead_name,
                email=campaign_lead.lead.email,
                status='failed',
                error='No message generated',
            ))
            continue
        
        if campaign_lead.message_sent_at:
            # Skip already sent messages
            continue
        
        email_subject = campaign_lead.email_subject or f"Exclusive Opportunity: {campaign.campaign_project_name}"
        
        try:
            email_service.send_email(
                to_email=campaign_lead.lead.email,
                subject=email_subject,
                body=campaign_lead.personalized_message,
            )
            
            CampaignMessage.objects.create(
                campaign=campaign,
                lead=campaign_lead.lead,
                message_content=campaign_lead.personalized_message,
                status='sent',
            )
            
            campaign_lead.message_sent_at = timezone.now()
            campaign_lead.save()
            
            sent_count += 1
            results.append(EmailSendResult(
                lead_id=campaign_lead.lead.lead_id,
                lead_name=campaign_lead.lead.lead_name,
                email=campaign_lead.lead.email,
                status='sent',
            ))
        except Exception as e:
            CampaignMessage.objects.create(
                campaign=campaign,
                lead=campaign_lead.lead,
                message_content=campaign_lead.personalized_message,
                status='failed',
            )
            failed_count += 1
            results.append(EmailSendResult(
                lead_id=campaign_lead.lead.lead_id,
                lead_name=campaign_lead.lead.lead_name,
                email=campaign_lead.lead.email,
                status='failed',
                error=str(e),
            ))
    
    return SendMessagesResponse(
        message=f"Sent {sent_count} messages successfully, {failed_count} failed",
        sent_count=sent_count,
        failed_count=failed_count,
        results=results,
    )

