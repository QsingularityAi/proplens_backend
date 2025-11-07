from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_name', 'chunks_count', 'ingested_at']
    list_filter = ['project_name', 'file_type']
    search_fields = ['name', 'project_name']



