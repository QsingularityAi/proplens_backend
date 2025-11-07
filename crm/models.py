from django.db import models
from django.core.validators import EmailValidator
import re


class Lead(models.Model):
    """CRM Lead model"""
    
    LEAD_STATUS_CHOICES = [
        ('not_connected', 'Not Connected'),
        ('connected', 'Connected'),
        ('visit_scheduled', 'Visit scheduled'),
        ('visit_done_not_purchased', 'Visit done not purchased'),
        ('purchased', 'Purchased'),
        ('not_interested', 'Not interested'),
    ]
    
    UNIT_TYPE_CHOICES = [
        ('studio', 'Studio'),
        ('1 bed', '1 Bed'),
        ('2 bed', '2 Bed'),
        ('2 bed w study', '2 bed w study'),
        ('3 bed', '3 bed'),
        ('4 bed', '4 bed'),
        ('Duplex', 'Duplex'),
        ('Penthouse', 'Penthouse'),
    ]
    
    PROJECT_CHOICES = [
        ('Altura', 'Altura'),
        ('Beachgate by Address', 'Beachgate by Address'),
        ('Damac Bay by Cavalli', 'Damac Bay by Cavalli'),
        ('DLF West Park', 'DLF West Park'),
        ('Godrej Vistas', 'Godrej Vistas'),
        ('Lumina Grand', 'Lumina Grand'),
        ('Sobha Crest', 'Sobha Crest'),
        ('Sobha Waves', 'Sobha Waves'),
    ]
    
    lead_id = models.CharField(max_length=50, unique=True, db_index=True)
    lead_name = models.CharField(max_length=255)
    email = models.EmailField(validators=[EmailValidator()])
    country_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    project_name = models.CharField(max_length=100, choices=PROJECT_CHOICES, null=True, blank=True)
    unit_type = models.CharField(max_length=50, choices=UNIT_TYPE_CHOICES, null=True, blank=True)
    min_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    max_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    lead_status = models.CharField(max_length=50, choices=LEAD_STATUS_CHOICES, default='not_connected')
    last_conversation_date = models.DateField(null=True, blank=True)
    last_conversation_summary = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_leads'
        ordering = ['-last_conversation_date', '-created_at']
        indexes = [
            models.Index(fields=['lead_status']),
            models.Index(fields=['project_name']),
            models.Index(fields=['unit_type']),
            models.Index(fields=['last_conversation_date']),
        ]
    
    def __str__(self):
        return f"{self.lead_id} - {self.lead_name}"
    
    @staticmethod
    def parse_budget(budget_str):
        """Parse budget string with commas to decimal"""
        if not budget_str or budget_str.strip() == '':
            return None
        try:
            # Remove commas and convert to float
            cleaned = budget_str.replace(',', '').strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def parse_date(date_str):
        """Parse date string in DD-MM-YYYY format"""
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.strptime(date_str, '%d-%m-%Y').date()
        except (ValueError, AttributeError):
            return None



