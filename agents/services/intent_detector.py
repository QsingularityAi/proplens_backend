from agents.services.gemini_service import GeminiLLM
from django.conf import settings
import re


class IntentDetector:
    """Detect customer intent from messages"""
    
    def __init__(self):
        self.llm = GeminiLLM(
            model_name=settings.GEMINI_MODEL,
            temperature=0,
        )
    
    def detect_intent(self, message: str) -> str:
        """Detect intent from customer message"""
        message_lower = message.lower()
        
        # Simple keyword-based detection
        visit_keywords = ['visit', 'viewing', 'tour', 'see', 'view', 'schedule visit']
        call_keywords = ['call', 'phone', 'speak', 'talk', 'discuss', 'schedule call']
        info_keywords = ['what', 'tell me', 'information', 'features', 'amenities', 'details']
        
        if any(keyword in message_lower for keyword in visit_keywords):
            return 'schedule_visit'
        elif any(keyword in message_lower for keyword in call_keywords):
            return 'schedule_call'
        elif any(keyword in message_lower for keyword in info_keywords):
            return 'request_info'
        else:
            # Use LLM for more complex detection
            try:
                prompt = f"""
                Classify the intent of this customer message into one of these categories:
                - schedule_visit: Customer wants to schedule a property viewing
                - schedule_call: Customer wants to schedule a call with sales
                - request_info: Customer is asking for information about the property
                - general_inquiry: General question or comment
                
                Message: {message}
                
                Respond with only the category name.
                """
                response = self.llm.invoke(prompt)
                return response.content.strip().lower()
            except:
                return 'general_inquiry'

