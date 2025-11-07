import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from campaigns.models import Campaign, CampaignLead, CampaignConversation
from crm.models import Lead


class Command(BaseCommand):
    help = 'Populate dummy data for Property Visit/Call Scheduled and AI Agent Follow-ups'

    def add_arguments(self, parser):
        parser.add_argument(
            '--campaign-id',
            type=int,
            help='Specific campaign ID to populate (optional, will use first campaign if not provided)',
        )
        parser.add_argument(
            '--goals-count',
            type=int,
            default=5,
            help='Number of goals to create (default: 5)',
        )
        parser.add_argument(
            '--conversations-count',
            type=int,
            default=8,
            help='Number of conversations to create (default: 8)',
        )

    def handle(self, *args, **options):
        campaign_id = options.get('campaign_id')
        goals_count = options.get('goals_count', 5)
        conversations_count = options.get('conversations_count', 8)

        # Get campaign
        if campaign_id:
            try:
                campaign = Campaign.objects.get(id=campaign_id)
            except Campaign.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Campaign with ID {campaign_id} not found'))
                return
        else:
            campaigns = Campaign.objects.all()
            if not campaigns.exists():
                self.stdout.write(self.style.ERROR('No campaigns found. Please create a campaign first.'))
                return
            campaign = campaigns.first()
            self.stdout.write(self.style.SUCCESS(f'Using campaign: {campaign.name} (ID: {campaign.id})'))

        # Get leads from campaign
        campaign_leads = CampaignLead.objects.filter(campaign=campaign).select_related('lead')
        if not campaign_leads.exists():
            self.stdout.write(self.style.ERROR('No leads found in this campaign. Please add leads to the campaign first.'))
            return

        leads_list = list(campaign_leads)
        if len(leads_list) < max(goals_count, conversations_count):
            self.stdout.write(self.style.WARNING(f'Campaign has only {len(leads_list)} leads. Adjusting counts...'))
            goals_count = min(goals_count, len(leads_list))
            conversations_count = min(conversations_count, len(leads_list))

        self.stdout.write(self.style.SUCCESS(f'Populating dummy data for campaign: {campaign.name}'))
        
        # Sample customer messages and agent responses
        customer_messages = [
            "What are the facilities and amenities in this property?",
            "I'm interested in scheduling a property visit. When can we arrange this?",
            "Can you tell me more about the unit types available?",
            "I'd like to schedule a call with a sales advisor to discuss financing options.",
            "What are the payment plans available?",
            "Is there a gym and swimming pool in the building?",
            "I'm very interested! Can we schedule a viewing this week?",
            "What's the price range for 2-bedroom units?",
            "I want to schedule a property visit for next week.",
            "Are there any special offers or discounts available?",
        ]

        agent_responses = [
            "Thank you for your interest! {campaign_project} features world-class amenities including a state-of-the-art fitness center, swimming pool, landscaped gardens, children's play area, and 24/7 security. The property also offers concierge services, covered parking, and easy access to major highways. Would you like to schedule a visit to see these amenities in person?",
            "Absolutely! I'd be happy to arrange a property visit for you. Based on your preferences for {unit_type} units, I can schedule a viewing at your convenience. Would you prefer a weekday or weekend visit? Please let me know your preferred dates and times.",
            "We have a variety of unit types available at {campaign_project}, including studios, 1-bedroom, 2-bedroom, 2-bedroom with study, 3-bedroom, 4-bedroom, duplexes, and penthouses. Each unit is designed with modern finishes and maximizes natural light. Given your interest in {unit_type} units, I'd recommend scheduling a visit to see our available options. Would you like to arrange a viewing?",
            "I'd be delighted to connect you with one of our sales advisors to discuss financing options. They can provide detailed information about our flexible payment plans, mortgage assistance programs, and any special financing offers currently available. Would you like to schedule a call this week?",
            "We offer flexible payment plans including post-handover payment plans, construction-linked plans, and early bird discounts. Our sales team can provide detailed information tailored to your budget of {budget_range}. Would you like to schedule a call to discuss these options in detail?",
            "Yes! {campaign_project} features a fully equipped gym with modern fitness equipment and a beautiful swimming pool with a pool deck. Additionally, residents enjoy access to a spa, sauna, children's play area, and landscaped gardens. Would you like to schedule a visit to see these facilities?",
            "That's wonderful to hear! I can arrange a viewing for you this week. We have several time slots available. Would you prefer a morning or afternoon visit? Please let me know your preferred date and time, and I'll confirm the appointment.",
            "Our 2-bedroom units at {campaign_project} range from {budget_range}, offering excellent value for money. These units feature modern layouts, high-quality finishes, and beautiful views. Given your budget preferences, I believe we have options that would be perfect for you. Would you like to schedule a viewing?",
            "Perfect! I can schedule a property visit for you next week. We have availability on multiple days. Please let me know your preferred date and time, and I'll confirm the appointment. I'll also send you a calendar invitation with all the details.",
            "We currently have special offers including early bird discounts, flexible payment plans, and complimentary parking spaces. These offers are available for a limited time. Would you like to schedule a visit to learn more about these opportunities and see the property?",
        ]

        # Create goals (Property Visit/Call Scheduled)
        self.stdout.write(self.style.SUCCESS(f'\nCreating {goals_count} goals (Property Visit/Call Scheduled)...'))
        goal_types = ['visit', 'call']
        
        # Ensure we don't try to sample more than available
        goals_to_create = min(goals_count, len(leads_list))
        selected_leads_for_goals = random.sample(leads_list, goals_to_create)
        
        for i, campaign_lead in enumerate(selected_leads_for_goals):
            goal_type = random.choice(goal_types)
            # Schedule dates in the future (next 1-4 weeks)
            days_ahead = random.randint(1, 28)
            scheduled_date = timezone.now() + timedelta(days=days_ahead)
            # Set time (9 AM to 6 PM)
            hour = random.randint(9, 17)
            scheduled_date = scheduled_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            campaign_lead.goal_achieved = True
            campaign_lead.goal_type = goal_type
            campaign_lead.goal_scheduled_date = scheduled_date
            campaign_lead.save()
            
            # Create a conversation for this goal
            if goal_type == 'visit':
                customer_msg = random.choice([
                    "I'm interested in scheduling a property visit. When can we arrange this?",
                    "I'd like to schedule a viewing for next week.",
                    "Can we schedule a property visit?",
                ])
                agent_msg = f"Absolutely! I've scheduled a property visit for you on {scheduled_date.strftime('%B %d, %Y at %I:%M %p')}. Our sales team will meet you at the property and give you a comprehensive tour. Please confirm if this time works for you, or let me know if you'd prefer a different date or time."
            else:
                customer_msg = random.choice([
                    "I'd like to schedule a call with a sales advisor to discuss financing options.",
                    "Can we schedule a call to discuss the property details?",
                    "I want to schedule a sales call.",
                ])
                agent_msg = f"Perfect! I've scheduled a sales call for you on {scheduled_date.strftime('%B %d, %Y at %I:%M %p')}. One of our sales advisors will call you to discuss {campaign.campaign_project_name} in detail, including financing options and payment plans. Please confirm if this time works for you."
            
            CampaignConversation.objects.create(
                campaign=campaign,
                lead=campaign_lead.lead,
                customer_message=customer_msg,
                agent_response=agent_msg,
                intent_detected='schedule_visit' if goal_type == 'visit' else 'schedule_call',
                created_at=timezone.now() - timedelta(days=random.randint(1, 7)),
            )
            
            self.stdout.write(f'  ✓ Created goal for {campaign_lead.lead.lead_name} - {goal_type} scheduled for {scheduled_date.strftime("%B %d, %Y at %I:%M %p")}')

        # Create additional conversations (AI Agent Follow-ups)
        self.stdout.write(self.style.SUCCESS(f'\nCreating {conversations_count} conversations (AI Agent Follow-ups)...'))
        
        # Get leads that don't have goals yet (or use all leads)
        leads_without_goals = [cl for cl in leads_list if not cl.goal_achieved]
        if len(leads_without_goals) < conversations_count:
            # Use all leads if needed (some may already have conversations)
            leads_without_goals = leads_list
        
        # Ensure we don't try to sample more than available
        conversations_to_create = min(conversations_count, len(leads_without_goals))
        selected_leads_for_conversations = random.sample(leads_without_goals, conversations_to_create)
        
        intents = ['general_inquiry', 'question', 'information_request', 'schedule_visit', 'schedule_call']
        
        for i, campaign_lead in enumerate(selected_leads_for_conversations):
            lead = campaign_lead.lead
            
            # Select appropriate customer message and agent response
            msg_index = i % len(customer_messages)
            customer_msg = customer_messages[msg_index]
            agent_template = agent_responses[msg_index]
            
            # Fill in template variables
            agent_msg = agent_template.format(
                campaign_project=campaign.campaign_project_name,
                unit_type=lead.unit_type or 'various',
                budget_range=f"AED {lead.min_budget:,.0f} - {lead.max_budget:,.0f}" if lead.min_budget and lead.max_budget else "various price ranges",
            )
            
            # Detect intent based on message
            intent = 'general_inquiry'
            if 'schedule' in customer_msg.lower() or 'visit' in customer_msg.lower() or 'call' in customer_msg.lower():
                intent = random.choice(['schedule_visit', 'schedule_call'])
            elif '?' in customer_msg:
                intent = random.choice(['question', 'information_request'])
            
            # Create conversation with random timestamp (last 1-14 days)
            days_ago = random.randint(1, 14)
            created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            CampaignConversation.objects.create(
                campaign=campaign,
                lead=lead,
                customer_message=customer_msg,
                agent_response=agent_msg,
                intent_detected=intent,
                created_at=created_at,
            )
            
            self.stdout.write(f'  ✓ Created conversation for {lead.lead_name} - Intent: {intent}')

        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully populated dummy data!'))
        self.stdout.write(f'   - Goals created: {goals_to_create}')
        self.stdout.write(f'   - Conversations created: {conversations_to_create}')

