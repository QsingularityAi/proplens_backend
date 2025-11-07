import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from agents.services.gemini_service import GeminiEmbeddings
from django.conf import settings
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Disable ChromaDB telemetry to prevent errors
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
os.environ.setdefault('CHROMA_TELEMETRY_DISABLED', 'True')


class DocumentRAGService:
    """Document RAG service for brochure queries"""
    
    def __init__(self):
        # Configure ChromaDB settings with telemetry disabled
        chroma_settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_DB_PATH),
            settings=chroma_settings
        )
        self.collection_name = "brochure_documents"
        
        # Initialize embeddings - using Google Gemini embeddings
        try:
            if settings.GEMINI_API_KEY:
                self.embeddings = GeminiEmbeddings(model_name=settings.GEMINI_EMBEDDING_MODEL)
            else:
                # Fallback to HuggingFace embeddings
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
        except Exception as e:
            logger.warning(f"Could not initialize Gemini embeddings, using HuggingFace: {str(e)}")
            # Fallback to HuggingFace embeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
        except:
            self.collection = self.chroma_client.create_collection(name=self.collection_name)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def ingest_document(self, file_path: str, project_name: str = None) -> int:
        """Ingest a PDF document into ChromaDB"""
        try:
            import pypdf
            
            # Read PDF
            with open(file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
            
            # Split into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Generate embeddings and store
            documents = []
            metadatas = []
            ids = []
            embeddings = []
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{Path(file_path).stem}_{i}"
                documents.append(chunk)
                metadatas.append({
                    "source": file_path,
                    "project_name": project_name or Path(file_path).stem,
                    "chunk_index": i,
                })
                ids.append(doc_id)
                # Generate embedding for this chunk
                embedding = self.embeddings.embed_query(chunk)
                embeddings.append(embedding)
            
            # Add to collection with embeddings
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings,
            )
            
            logger.info(f"Ingested {len(chunks)} chunks from {file_path}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error ingesting document {file_path}: {str(e)}")
            raise
    
    def query_by_project(self, project_name: str, query_text: str, n_results: int = 10) -> str:
        """Query the document collection filtered by project name"""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query_text)
            
            # Search in ChromaDB with project name filter
            # ChromaDB where clause format: {"metadata_field": "value"}
            where_clause = {"project_name": project_name} if project_name else None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
            )
            
            # Combine results
            if results['documents'] and len(results['documents'][0]) > 0:
                combined_text = "\n\n".join(results['documents'][0])
                return combined_text
            else:
                # Fallback to regular query if project filter returns no results
                return self.query(query_text, n_results)
                
        except Exception as e:
            logger.error(f"Error querying documents by project: {str(e)}")
            # Fallback to regular query if project filter fails
            return self.query(query_text, n_results)
    
    def query(self, query_text: str, n_results: int = 5) -> str:
        """Query the document collection"""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query_text)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
            )
            
            # Combine results
            if results['documents'] and len(results['documents'][0]) > 0:
                combined_text = "\n\n".join(results['documents'][0])
                return combined_text
            else:
                return "No relevant information found in the documents."
                
        except Exception as e:
            logger.error(f"Error querying documents: {str(e)}")
            return f"Error retrieving information: {str(e)}"

