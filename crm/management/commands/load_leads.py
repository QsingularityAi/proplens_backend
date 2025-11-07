import csv
import os
from django.core.management.base import BaseCommand
from crm.models import Lead
from django.utils import timezone


class Command(BaseCommand):
    help = 'Load leads from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loading leads from {csv_file}...'))
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            errors = 0
            
            for row in reader:
                try:
                    # Parse budget values
                    min_budget = Lead.parse_budget(row.get('Min. Budget', ''))
                    max_budget = Lead.parse_budget(row.get('Max Budget', ''))
                    
                    # Parse date
                    last_conversation_date = Lead.parse_date(row.get('Last conversation date', ''))
                    
                    # Create or update lead
                    lead, created = Lead.objects.update_or_create(
                        lead_id=row['Lead ID'],
                        defaults={
                            'lead_name': row['Lead name'],
                            'email': row['Email'],
                            'country_code': row['Country code'],
                            'phone': row['Phone'],
                            'project_name': row.get('Project name') or None,
                            'unit_type': row.get('Unit type') or None,
                            'min_budget': min_budget,
                            'max_budget': max_budget,
                            'lead_status': row.get('Lead status', 'not_connected').replace(' ', '_').lower(),
                            'last_conversation_date': last_conversation_date,
                            'last_conversation_summary': row.get('Last conversation summary', ''),
                        }
                    )
                    
                    if created:
                        count += 1
                    else:
                        self.stdout.write(f'Updated: {lead.lead_id}')
                        
                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f'Error processing row {row.get("Lead ID", "unknown")}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} leads. Errors: {errors}'))



