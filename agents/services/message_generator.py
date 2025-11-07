from typing import Optional
import re
from crm.models import Lead
from agents.services.document_rag import DocumentRAGService
from agents.services.gemini_service import GeminiLLM
from django.conf import settings
import os


class MessageGenerator:
    """Generate hyper-personalized messages for leads"""
    
    def __init__(self):
        self.llm = GeminiLLM(
            model_name=settings.GEMINI_MODEL,
            temperature=0.7,
        )
        self.rag_service = DocumentRAGService()
    
    def generate_subject(self, lead: Lead, campaign_project: str) -> str:
        """Generate personalized email subject line"""
        prompt = f"""
Generate a SINGLE, concise email subject line for a follow-up email to {lead.lead_name} about {campaign_project}.

Lead Information:
- Name: {lead.lead_name}
- Unit Type Preference: {lead.unit_type or 'Not specified'}
- Previous Project Interest: {lead.project_name or 'None'}

CRITICAL REQUIREMENTS:
- Generate ONLY ONE subject line (not multiple options)
- Maximum 60 characters
- Single line only (no line breaks, no bullet points, no asterisks)
- Make it personal and engaging
- Reference the project name: {campaign_project}
- Include the lead's first name: {lead.lead_name.split()[0]}
- Create interest/urgency
- Do NOT include "Subject:" prefix
- Do NOT include multiple options separated by asterisks (*) or bullets
- Do NOT include explanatory text like "Here are a few options" or "playing with different angles"
- Output ONLY the subject line text, nothing else

Good examples:
- "{lead.lead_name.split()[0]}, {campaign_project}: Your Dream Home Awaits"
- "{campaign_project}: Exclusive Update for {lead.lead_name.split()[0]}"
- "{lead.lead_name.split()[0]}, Don't Miss {campaign_project} Opportunity"

Bad examples (DO NOT generate these):
- "Here are a few options: * Option 1 * Option 2"
- Multiple lines or bullet points
- Explanatory text before the subject
"""
        try:
            response = self.llm.invoke(prompt)
            subject = response.content.strip()
            
            # Remove "Subject:" if LLM added it
            if subject.startswith("Subject:"):
                subject = subject.replace("Subject:", "").strip()
            
            # Remove quotes if present
            subject = subject.strip('"').strip("'")
            
            # Remove any explanatory text before the actual subject
            if "Here are" in subject or "options" in subject.lower() or "playing with" in subject.lower():
                # Try to extract just the subject line after colons or before asterisks
                if ":" in subject:
                    # Take everything after the last colon
                    parts = subject.split(":")
                    if len(parts) > 1:
                        # Get the last part and clean it
                        subject = parts[-1].strip()
            
            # Remove asterisks, bullet points, and multiple options
            # Split by asterisks or bullets and take the first clean option
            if "*" in subject or "•" in subject or "- " in subject:
                # Split by common separators
                parts = re.split(r'[*•]', subject)
                if parts:
                    # Take the first non-empty part
                    subject = parts[0].strip()
                    # Clean up any remaining markers
                    subject = re.sub(r'^\s*[-*•]\s*', '', subject)
            
            # Remove any line breaks and keep only first line
            subject = subject.split('\n')[0].strip()
            
            # Remove any remaining explanatory text patterns
            subject = re.sub(r'^.*?(?:options|angles|here are|playing with).*?:', '', subject, flags=re.IGNORECASE)
            subject = subject.strip()
            
            # Ensure it's not empty and has reasonable length
            if not subject or len(subject) > 100:
                # Fallback to a simple, clean subject
                first_name = lead.lead_name.split()[0]
                return f"{first_name}, {campaign_project}: Your Opportunity Awaits"
            
            # Final cleanup: remove any leading/trailing punctuation issues
            subject = subject.strip(' *•-')
            
            return subject
        except Exception as e:
            # Fallback subject
            first_name = lead.lead_name.split()[0]
            return f"{first_name}, {campaign_project}: Your Opportunity Awaits"
    
    def generate_message(self, lead: Lead, campaign_project: str, sales_offer: Optional[str] = None) -> str:
        """Generate personalized message for a lead"""
        
        # Get project information from RAG
        project_info = self.rag_service.query(f"What are the key features and amenities of {campaign_project}?")
        
        # Build context
        context = f"""
Lead Information:
- Name: {lead.lead_name}
- Previous Project Interest: {lead.project_name or 'None'}
- Unit Type Preference: {lead.unit_type or 'Not specified'}
- Budget Range: {lead.min_budget or 'N/A'} - {lead.max_budget or 'N/A'}
- Last Conversation Summary: {lead.last_conversation_summary or 'No previous conversation'}
- Lead Status: {lead.lead_status}

Campaign Project: {campaign_project}
Project Information: {project_info}

Sales Offer: {sales_offer or 'No special offer'}
"""
        
        prompt = f"""
You are a professional real estate sales associate writing a personalized follow-up email to a lead.

Context:
{context}

Task:
Write a warm, personalized email that:
1. Acknowledges their previous interest and preferences
2. Highlights how {campaign_project} matches their needs based on their preferences
3. Mentions specific features/amenities they showed interest in
4. Creates urgency and interest
5. Includes a clear call-to-action to schedule a property viewing or call
{f"6. Mentions the special offer: {sales_offer}" if sales_offer else ""}

Keep the tone professional but friendly. The email should be around 200-300 words.

CRITICAL REQUIREMENTS: 
- Write ONLY the email body content (no introductory text like "Of course. Here is a personalized follow-up email...")
- Start directly with "Dear [Name]," 
- End with ONLY "Best regards," - DO NOT include any signature, name, contact information, or placeholder text like [Your Name], [Your Agency], [Your Contact Number], etc.
- Do NOT include any explanatory text before or after the email
- Do NOT include placeholder brackets like [Your Name], [Your Agency], [Your Contact Number], [Your Email Address]
- The signature will be added automatically, so just end with "Best regards,"
"""
        
        try:
            response = self.llm.invoke(prompt)
            message_content = response.content.strip()
            
            # Remove any introductory text if LLM added it
            if "Of course" in message_content or "Here is" in message_content or "personalized follow-up email" in message_content.lower():
                # Try to find where the actual email starts
                if "Dear" in message_content:
                    message_content = message_content[message_content.find("Dear"):]
                elif "Subject:" in message_content:
                    # Extract everything after Subject line
                    parts = message_content.split("Subject:", 1)
                    if len(parts) > 1:
                        subject_and_body = parts[1].strip()
                        if "Dear" in subject_and_body:
                            message_content = subject_and_body[subject_and_body.find("Dear"):]
            
            # Remove any placeholder signatures or placeholder text
            # Remove placeholder patterns like [Your Name], [Your Agency], etc.
            placeholder_patterns = [
                r'\[Your Name\]',
                r'\[Your Agency\]',
                r'\[Your Agency Name\]',
                r'\[Your Contact Number\]',
                r'\[Your Phone Number\]',
                r'\[Your Email Address\]',
                r'\[Your Email\]',
            ]
            for pattern in placeholder_patterns:
                message_content = re.sub(pattern, '', message_content, flags=re.IGNORECASE)
            
            # Find the last "Best regards," and remove everything after it (including placeholder signatures)
            lines = message_content.split('\n')
            best_regards_index = -1
            
            # Find the last occurrence of "Best regards,"
            for i in range(len(lines) - 1, -1, -1):
                if 'best regards' in lines[i].lower():
                    best_regards_index = i
                    break
            
            # If we found "Best regards,", keep only up to that line
            if best_regards_index >= 0:
                message_content = '\n'.join(lines[:best_regards_index + 1]).strip()
                # Ensure it ends with "Best regards,"
                if not message_content.endswith('Best regards,'):
                    message_content = message_content.rstrip() + '\n\nBest regards,'
            else:
                # No "Best regards," found, add it
                message_content = message_content.rstrip() + '\n\nBest regards,'
            
            # Clean up multiple blank lines
            message_content = re.sub(r'\n{3,}', '\n\n', message_content)
            
            # Add our signature block
            signature = """

Joao Silva
Real Estate Sales Associate
Head of AI Team at Proplens.ai
+65-XXXXXXXXX
info@proplens.ai"""
            
            # Ensure signature is added (replace any existing signature)
            if "Joao Silva" not in message_content:
                message_content += signature
            
            return message_content
        except Exception as e:
            # Fallback message
            return self._generate_fallback_message(lead, campaign_project, sales_offer)
    
    def _generate_fallback_message(self, lead: Lead, campaign_project: str, sales_offer: Optional[str]) -> str:
        """Generate a simple fallback message"""
        message = f"""Dear {lead.lead_name},

We hope this message finds you well. We noticed your interest in {lead.project_name or 'real estate properties'} and wanted to share an exciting opportunity with you.

We're excited to introduce {campaign_project}, which we believe aligns perfectly with your preferences for {lead.unit_type or 'property'} units.

{f'Special Offer: {sales_offer}' if sales_offer else ''}

We'd love to schedule a personalized viewing or call to discuss how {campaign_project} can meet your needs.

Best regards,

Joao Silva
Real Estate Sales Associate
Head of AI Team at Proplens.ai
+65-XXXXXXXXX
info@proplens.ai"""
        return message

