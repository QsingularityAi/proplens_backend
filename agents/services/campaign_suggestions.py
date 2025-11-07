from agents.services.document_rag import DocumentRAGService
from agents.services.gemini_service import GeminiLLM
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CampaignSuggestionService:
    """Service to generate campaign name and sales offer suggestions"""
    
    def __init__(self):
        self.rag_service = DocumentRAGService()
        self.llm = GeminiLLM(model_name=settings.GEMINI_MODEL, temperature=0.7)
    
    def get_project_brochure_info(self, project_name: str) -> str:
        """Retrieve brochure information for a specific project"""
        try:
            # Query brochure data for the specific project
            query = f"Tell me about {project_name} project features, amenities, location, pricing, and unique selling points"
            
            # Query with project name filter
            brochure_info = self.rag_service.query_by_project(project_name, query, n_results=10)
            return brochure_info
        except Exception as e:
            logger.error(f"Error retrieving brochure info for {project_name}: {str(e)}")
            return ""
    
    def generate_campaign_name_suggestions(self, project_name: str) -> list:
        """Generate campaign name suggestions based on project brochure"""
        try:
            brochure_info = self.get_project_brochure_info(project_name)
            
            if not brochure_info or "No relevant information" in brochure_info:
                # Fallback suggestions if no brochure data
                return [
                    f"{project_name} Exclusive Offer",
                    f"Discover {project_name}",
                    f"{project_name} Special Promotion",
                ]
            
            prompt = f"""Based on the following information about {project_name}, generate 3 creative and compelling campaign name suggestions for a lead nurturing campaign.

Project Information:
{brochure_info}

Requirements:
- Each campaign name should be 3-6 words
- Should highlight unique selling points or key features
- Should create urgency or interest
- Should be professional and appealing to real estate buyers

Return ONLY a JSON array of exactly 3 campaign name strings, no other text. Format: ["Campaign Name 1", "Campaign Name 2", "Campaign Name 3"]
"""
            
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Try to extract JSON array
            import json
            import re
            
            # Find JSON array in response
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                if isinstance(suggestions, list) and len(suggestions) > 0:
                    return suggestions[:3]  # Return max 3
            
            # Fallback parsing
            lines = [line.strip().strip('"').strip("'") for line in content.split('\n') if line.strip()]
            suggestions = [line for line in lines if line and not line.startswith('#')]
            if suggestions:
                return suggestions[:3]
            
            # Final fallback
            return [
                f"{project_name} Exclusive Offer",
                f"Discover {project_name}",
                f"{project_name} Special Promotion",
            ]
            
        except Exception as e:
            logger.error(f"Error generating campaign name suggestions: {str(e)}")
            return [
                f"{project_name} Exclusive Offer",
                f"Discover {project_name}",
                f"{project_name} Special Promotion",
            ]
    
    def generate_sales_offer_suggestions(self, project_name: str) -> list:
        """Generate sales offer details suggestions (max 3) based on project brochure"""
        try:
            brochure_info = self.get_project_brochure_info(project_name)
            
            if not brochure_info or "No relevant information" in brochure_info:
                # Fallback suggestions if no brochure data
                return [
                    f"Exclusive opportunity to own a premium property at {project_name}. Limited units available. Contact us for special pricing and flexible payment plans.",
                    f"Discover {project_name} - a perfect blend of luxury and comfort. Early bird pricing available for limited time. Schedule your private viewing today.",
                    f"Secure your future at {project_name}. Premium amenities, strategic location, and flexible payment options. Don't miss this exclusive opportunity.",
                ]
            
            prompt = f"""Based on the following information about {project_name}, generate 3 compelling sales offer details for a lead nurturing campaign.

Project Information:
{brochure_info}

Requirements:
- Each sales offer should be 2-4 sentences
- Highlight different key features, amenities, or unique selling points in each offer
- Include urgency or exclusivity elements
- Mention pricing benefits or special offers if available
- Keep it professional and appealing to real estate buyers
- Do NOT include specific prices unless mentioned in the brochure
- Each offer should have a slightly different angle or focus

Return ONLY a JSON array of exactly 3 sales offer strings, no other text. Format: ["Sales Offer 1", "Sales Offer 2", "Sales Offer 3"]
"""
            
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Try to extract JSON array
            import json
            import re
            
            # Find JSON array in response
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                if isinstance(suggestions, list) and len(suggestions) > 0:
                    return suggestions[:3]  # Return max 3
            
            # Fallback parsing - split by newlines or common separators
            lines = [line.strip().strip('"').strip("'").strip('-').strip('•').strip() 
                    for line in content.split('\n') if line.strip()]
            suggestions = [line for line in lines if line and not line.startswith('#') and len(line) > 20]
            if suggestions:
                return suggestions[:3]
            
            # Final fallback
            return [
                f"Exclusive opportunity to own a premium property at {project_name}. Limited units available. Contact us for special pricing and flexible payment plans.",
                f"Discover {project_name} - a perfect blend of luxury and comfort. Early bird pricing available for limited time. Schedule your private viewing today.",
                f"Secure your future at {project_name}. Premium amenities, strategic location, and flexible payment options. Don't miss this exclusive opportunity.",
            ]
            
        except Exception as e:
            logger.error(f"Error generating sales offer suggestions: {str(e)}")
            return [
                f"Exclusive opportunity to own a premium property at {project_name}. Limited units available. Contact us for special pricing and flexible payment plans.",
                f"Discover {project_name} - a perfect blend of luxury and comfort. Early bird pricing available for limited time. Schedule your private viewing today.",
                f"Secure your future at {project_name}. Premium amenities, strategic location, and flexible payment options. Don't miss this exclusive opportunity.",
            ]

