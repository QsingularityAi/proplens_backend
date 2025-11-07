from django.contrib import admin
from .models import Campaign, CampaignLead, CampaignMessage, CampaignConversation


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign_project_name', 'channel', 'leads_count', 'created_at']
    list_filter = ['campaign_project_name', 'channel', 'created_at']
    search_fields = ['name']


@admin.register(CampaignLead)
class CampaignLeadAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'lead', 'goal_achieved', 'message_sent_at']
    list_filter = ['goal_achieved', 'campaign']


@admin.register(CampaignMessage)
class CampaignMessageAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'lead', 'sent_at', 'status']
    list_filter = ['status', 'campaign']


@admin.register(CampaignConversation)
class CampaignConversationAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'lead', 'intent_detected', 'created_at']
    list_filter = ['intent_detected', 'campaign']



