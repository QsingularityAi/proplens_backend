from django.db import models
from crm.models import Lead


class Campaign(models.Model):
    """Campaign model for lead nurturing"""
    
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
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    name = models.CharField(max_length=255)
    campaign_project_name = models.CharField(max_length=100, choices=PROJECT_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    sales_offer_details = models.TextField(null=True, blank=True)
    
    # Filter criteria
    filter_project_name = models.CharField(max_length=100, null=True, blank=True)
    filter_unit_types = models.JSONField(default=list, blank=True)
    filter_min_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    filter_max_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    filter_lead_status = models.CharField(max_length=50, null=True, blank=True)
    filter_date_from = models.DateField(null=True, blank=True)
    filter_date_to = models.DateField(null=True, blank=True)
    
    leads = models.ManyToManyField(Lead, through='CampaignLead', related_name='campaigns')
    
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def leads_count(self):
        return self.leads.count()
    
    @property
    def messages_sent_count(self):
        return CampaignMessage.objects.filter(campaign=self).count()
    
    @property
    def responses_count(self):
        # SQLite doesn't support distinct('field'), so we use values().distinct() instead
        return CampaignConversation.objects.filter(
            campaign=self
        ).exclude(
            customer_message=''
        ).values('lead').distinct().count()
    
    @property
    def goals_achieved_count(self):
        return CampaignLead.objects.filter(campaign=self, goal_achieved=True).count()


class CampaignLead(models.Model):
    """Through model for Campaign-Lead relationship"""
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    personalized_message = models.TextField(null=True, blank=True)
    email_subject = models.CharField(max_length=255, null=True, blank=True)
    message_sent_at = models.DateTimeField(null=True, blank=True)
    goal_achieved = models.BooleanField(default=False)
    goal_type = models.CharField(max_length=50, null=True, blank=True)  # 'visit' or 'call'
    goal_scheduled_date = models.DateTimeField(null=True, blank=True)
    goal_confirmed = models.BooleanField(default=False)
    goal_confirmed_at = models.DateTimeField(null=True, blank=True)
    sales_associate_notified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'campaign_leads'
        unique_together = ['campaign', 'lead']


class CampaignMessage(models.Model):
    """Track messages sent in campaigns"""
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='messages')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='campaign_messages')
    message_content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')  # sent, failed, bounced
    
    class Meta:
        db_table = 'campaign_messages'
        ordering = ['-sent_at']


class CampaignConversation(models.Model):
    """Track conversations between AI agent and leads"""
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='conversations')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='conversations')
    customer_message = models.TextField()
    agent_response = models.TextField()
    intent_detected = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'campaign_conversations'
        ordering = ['created_at']

