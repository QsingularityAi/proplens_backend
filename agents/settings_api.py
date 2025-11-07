from ninja import Router
from pydantic import BaseModel
from typing import Optional
from agents.auth import TokenAuth

router = Router()


class AgentSettingsSchema(BaseModel):
    max_followups: int = 5
    messaging_focus: str = "Property Features & Benefits"
    response_style: str = "Professional & Formal"
    urgency_level: str = "Medium - Moderate urgency"
    custom_instructions: Optional[str] = None


class AgentSettingsResponse(BaseModel):
    max_followups: int
    messaging_focus: str
    response_style: str
    urgency_level: str
    custom_instructions: Optional[str]
    message: str


# In-memory storage for settings (in production, use database)
_agent_settings = {
    "max_followups": 5,
    "messaging_focus": "Property Features & Benefits",
    "response_style": "Professional & Formal",
    "urgency_level": "Medium - Moderate urgency",
    "custom_instructions": "",
}


@router.get("/settings", response=AgentSettingsResponse, auth=TokenAuth())
def get_agent_settings(request):
    """Get AI agent settings"""
    return AgentSettingsResponse(
        max_followups=_agent_settings["max_followups"],
        messaging_focus=_agent_settings["messaging_focus"],
        response_style=_agent_settings["response_style"],
        urgency_level=_agent_settings["urgency_level"],
        custom_instructions=_agent_settings["custom_instructions"],
        message="Settings retrieved successfully"
    )


@router.post("/settings", response=AgentSettingsResponse, auth=TokenAuth())
def save_agent_settings(request, settings: AgentSettingsSchema):
    """Save AI agent settings"""
    _agent_settings["max_followups"] = settings.max_followups
    _agent_settings["messaging_focus"] = settings.messaging_focus
    _agent_settings["response_style"] = settings.response_style
    _agent_settings["urgency_level"] = settings.urgency_level
    _agent_settings["custom_instructions"] = settings.custom_instructions or ""
    
    return AgentSettingsResponse(
        max_followups=_agent_settings["max_followups"],
        messaging_focus=_agent_settings["messaging_focus"],
        response_style=_agent_settings["response_style"],
        urgency_level=_agent_settings["urgency_level"],
        custom_instructions=_agent_settings["custom_instructions"],
        message="Settings saved successfully"
    )



