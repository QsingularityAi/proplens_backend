"""
Google Gemini service wrapper for LangChain compatibility
"""
import google.generativeai as genai
from django.conf import settings
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class GeminiLLM:
    """Wrapper for Google Gemini LLM to work with LangChain-style interface"""
    
    def __init__(self, model_name: str = None, temperature: float = 0.7):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in settings")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model_name or settings.GEMINI_MODEL
        self.temperature = temperature
        self.model = genai.GenerativeModel(self.model_name)
    
    def invoke(self, prompt: str) -> 'GeminiResponse':
        """Invoke the model with a prompt"""
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=self.temperature,
            )
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            return GeminiResponse(response.text)
        except Exception as e:
            logger.error(f"Error invoking Gemini: {str(e)}")
            raise


class GeminiResponse:
    """Response wrapper to match LangChain interface"""
    
    def __init__(self, content: str):
        self.content = content


class GeminiEmbeddings:
    """Google Gemini Embeddings wrapper"""
    
    def __init__(self, model_name: str = None):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set in settings")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query"""
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_query",
            )
            # Handle different response formats
            if isinstance(result, dict) and 'embedding' in result:
                return result['embedding']
            elif isinstance(result, list):
                return result
            else:
                return result
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents"""
        try:
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document",
                )
                # Handle different response formats
                if isinstance(result, dict) and 'embedding' in result:
                    embeddings.append(result['embedding'])
                elif isinstance(result, list):
                    embeddings.append(result)
                else:
                    embeddings.append(result)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating document embeddings: {str(e)}")
            raise

