from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send an email"""
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False



