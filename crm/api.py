from ninja import Router
from typing import List, Optional
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from crm.models import Lead
from pydantic import BaseModel, EmailStr, Field

router = Router()


class LeadFilterSchema(BaseModel):
    project_name: Optional[str] = None
    unit_types: Optional[List[str]] = Field(default_factory=list)
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    lead_status: Optional[str] = None  # Legacy single select
    lead_statuses: Optional[List[str]] = Field(default_factory=list)  # Multi-select support
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class LeadResponse(BaseModel):
    lead_id: str
    lead_name: str
    email: str
    phone: str
    project_name: Optional[str]
    unit_type: Optional[str]
    min_budget: Optional[float]
    max_budget: Optional[float]
    lead_status: str
    last_conversation_date: Optional[str]
    last_conversation_summary: Optional[str]
    
    class Config:
        from_attributes = True


class ShortlistResponse(BaseModel):
    count: int
    leads: List[LeadResponse]


@router.post("/shortlist", response=ShortlistResponse)
def shortlist_leads(request, filters: LeadFilterSchema):
    """
    Shortlist leads based on filter criteria.
    Requires at least 2 filter criteria to be specified.
    """
    # Map frontend status values to backend database values
    STATUS_MAPPING = {
        'Not Connected': 'not_connected',
        'Connected': 'connected',
        'Visit scheduled': 'visit_scheduled',
        'Visit done not purchased': 'visit_done_not_purchased',
        'Purchased': 'purchased',
        'Not interested': 'not_interested',
    }
    
    # Filter out empty arrays - convert to None
    if filters.unit_types == []:
        filters.unit_types = None
    if filters.lead_statuses == []:
        filters.lead_statuses = None
    
    # Count non-empty filters
    filter_count = sum([
        bool(filters.project_name),
        bool(filters.unit_types),
        bool(filters.min_budget is not None),
        bool(filters.max_budget is not None),
        bool(filters.lead_status),
        bool(filters.lead_statuses),
        bool(filters.date_from),
        bool(filters.date_to),
    ])
    
    if filter_count < 2:
        return {"error": "At least 2 filter criteria must be specified"}, 400
    
    # Build query
    query = Q()
    
    if filters.project_name:
        query &= Q(project_name=filters.project_name)
    
    if filters.unit_types:
        query &= Q(unit_type__in=filters.unit_types)
    
    # Fix budget filter logic: A lead matches if its budget range overlaps with filter range
    if filters.min_budget is not None:
        # Lead matches if: lead.max_budget >= filter.min_budget (lead's max overlaps filter min)
        # OR lead has no max_budget but min_budget >= filter.min_budget
        query &= Q(
            Q(max_budget__gte=filters.min_budget) | 
            Q(max_budget__isnull=True, min_budget__gte=filters.min_budget)
        )
    
    if filters.max_budget is not None:
        # Lead matches if: lead.min_budget <= filter.max_budget (lead's min overlaps filter max)
        # OR lead has no min_budget but max_budget <= filter.max_budget
        query &= Q(
            Q(min_budget__lte=filters.max_budget) | 
            Q(min_budget__isnull=True, max_budget__lte=filters.max_budget)
        )
    
    # Support both single and multi-select lead status
    if filters.lead_statuses:
        # Map frontend status values to backend values
        mapped_statuses = [STATUS_MAPPING.get(s, s.replace(' ', '_').lower()) for s in filters.lead_statuses]
        query &= Q(lead_status__in=mapped_statuses)
    elif filters.lead_status:
        mapped_status = STATUS_MAPPING.get(filters.lead_status, filters.lead_status.replace(' ', '_').lower())
        query &= Q(lead_status=mapped_status)
    
    if filters.date_from:
        try:
            date_from = datetime.strptime(filters.date_from, '%Y-%m-%d').date()
            query &= Q(last_conversation_date__gte=date_from)
        except ValueError:
            pass
    
    if filters.date_to:
        try:
            date_to = datetime.strptime(filters.date_to, '%Y-%m-%d').date()
            query &= Q(last_conversation_date__lte=date_to)
        except ValueError:
            pass
    
    # Execute query
    leads = Lead.objects.filter(query)
    
    # Convert to response format
    lead_responses = []
    for lead in leads:
        # Get display name for status
        status_display = lead.get_lead_status_display()
        
        lead_responses.append(LeadResponse(
            lead_id=lead.lead_id,
            lead_name=lead.lead_name,
            email=lead.email,
            phone=lead.phone,
            project_name=lead.project_name,
            unit_type=lead.unit_type,
            min_budget=float(lead.min_budget) if lead.min_budget else None,
            max_budget=float(lead.max_budget) if lead.max_budget else None,
            lead_status=status_display,
            last_conversation_date=lead.last_conversation_date.isoformat() if lead.last_conversation_date else None,
            last_conversation_summary=lead.last_conversation_summary,
        ))
    
    return ShortlistResponse(count=len(lead_responses), leads=lead_responses)


@router.get("/leads", response=List[LeadResponse])
def list_leads(request, limit: int = 100, offset: int = 0):
    """List all leads with pagination"""
    leads = Lead.objects.all()[offset:offset+limit]
    return [
        LeadResponse(
            lead_id=lead.lead_id,
            lead_name=lead.lead_name,
            email=lead.email,
            phone=lead.phone,
            project_name=lead.project_name,
            unit_type=lead.unit_type,
            min_budget=float(lead.min_budget) if lead.min_budget else None,
            max_budget=float(lead.max_budget) if lead.max_budget else None,
            lead_status=lead.lead_status,
            last_conversation_date=lead.last_conversation_date.isoformat() if lead.last_conversation_date else None,
            last_conversation_summary=lead.last_conversation_summary,
        )
        for lead in leads
    ]


@router.get("/leads/{lead_id}", response=LeadResponse)
def get_lead(request, lead_id: str):
    """Get a specific lead by ID"""
    try:
        lead = Lead.objects.get(lead_id=lead_id)
        return LeadResponse(
            lead_id=lead.lead_id,
            lead_name=lead.lead_name,
            email=lead.email,
            phone=lead.phone,
            project_name=lead.project_name,
            unit_type=lead.unit_type,
            min_budget=float(lead.min_budget) if lead.min_budget else None,
            max_budget=float(lead.max_budget) if lead.max_budget else None,
            lead_status=lead.lead_status,
            last_conversation_date=lead.last_conversation_date.isoformat() if lead.last_conversation_date else None,
            last_conversation_summary=lead.last_conversation_summary,
        )
    except Lead.DoesNotExist:
        return {"error": "Lead not found"}, 404

