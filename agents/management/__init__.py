import os
from django.core.management.base import BaseCommand
from agents.services.document_rag import DocumentRAGService
from agents.models import Document
from django.conf import settings


class Command(BaseCommand):
    help = 'Ingest brochure PDFs from directory'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Path to directory containing PDFs')
        parser.add_argument('--project-name', type=str, help='Project name for all documents')

    def handle(self, *args, **options):
        directory = options['directory']
        project_name = options.get('project_name')
        
        if not os.path.exists(directory):
            self.stdout.write(self.style.ERROR(f'Directory not found: {directory}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Ingesting PDFs from {directory}...'))
        
        rag_service = DocumentRAGService()
        count = 0
        
        for filename in os.listdir(directory):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(directory, filename)
                
                try:
                    # Extract project name from filename if not provided
                    doc_project_name = project_name
                    if not doc_project_name:
                        # Try to extract from filename
                        for proj in ['Altura', 'Beachgate', 'Damac', 'DLF', 'Godrej', 'Lumina', 'Sobha']:
                            if proj.lower() in filename.lower():
                                doc_project_name = proj
                                break
                    
                    chunks_count = rag_service.ingest_document(file_path, doc_project_name)
                    
                    # Save document record
                    Document.objects.create(
                        name=filename,
                        project_name=doc_project_name,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        file_type='pdf',
                        chunks_count=chunks_count,
                    )
                    
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Ingested: {filename} ({chunks_count} chunks)'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error ingesting {filename}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully ingested {count} documents'))



