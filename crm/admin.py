from django.contrib import admin
from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['lead_id', 'lead_name', 'email', 'project_name', 'unit_type', 'lead_status', 'last_conversation_date']
    list_filter = ['lead_status', 'project_name', 'unit_type']
    search_fields = ['lead_id', 'lead_name', 'email']
    readonly_fields = ['created_at', 'updated_at']



