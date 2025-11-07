from django.core.management.base import BaseCommand
from agents.services.document_rag import DocumentRAGService
from agents.models import Document
from django.conf import settings
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Ingest brochure PDFs from Project_brochure_dataset directory'

    def handle(self, *args, **options):
        # Find the brochure dataset directory
        # BASE_DIR is backend/, so parent is the project root
        base_dir = Path(settings.BASE_DIR).parent
        brochure_dir = base_dir / 'Project_brochure_dataset'
        
        if not brochure_dir.exists():
            self.stdout.write(self.style.ERROR(f'Directory not found: {brochure_dir}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Ingesting PDFs from {brochure_dir}...'))
        
        rag_service = DocumentRAGService()
        count = 0
        
        for filename in os.listdir(brochure_dir):
            if filename.lower().endswith('.pdf'):
                file_path = brochure_dir / filename
                
                try:
                    # Extract project name from filename
                    doc_project_name = None
                    filename_lower = filename.lower()
                    
                    project_mapping = {
                        'altura': 'Altura',
                        'beachgate': 'Beachgate by Address',
                        'damac': 'Damac Bay by Cavalli',
                        'dlf': 'DLF West Park',
                        'godrej': 'Godrej Vistas',
                        'lumina': 'Lumina Grand',
                        'sobha crest': 'Sobha Crest',
                        'sobha waves': 'Sobha Waves',
                    }
                    
                    for key, value in project_mapping.items():
                        if key in filename_lower:
                            doc_project_name = value
                            break
                    
                    chunks_count = rag_service.ingest_document(str(file_path), doc_project_name)
                    
                    # Save document record
                    Document.objects.create(
                        name=filename,
                        project_name=doc_project_name,
                        file_path=str(file_path),
                        file_size=file_path.stat().st_size,
                        file_type='pdf',
                        chunks_count=chunks_count,
                    )
                    
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Ingested: {filename} ({chunks_count} chunks)'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error ingesting {filename}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully ingested {count} documents'))

