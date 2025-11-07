from django.db import models


class Document(models.Model):
    """Model to track uploaded brochure documents"""
    
    name = models.CharField(max_length=255)
    project_name = models.CharField(max_length=100, null=True, blank=True)
    file_path = models.CharField(max_length=500)
    file_size = models.IntegerField()
    file_type = models.CharField(max_length=50, default='pdf')
    chunks_count = models.IntegerField(default=0)
    ingested_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-ingested_at']
    
    def __str__(self):
        return self.name



