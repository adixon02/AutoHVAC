import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """SendGrid email service for magic links and notifications"""
    
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "no-reply@autohvac.ai")
        self.client = None
        
        if self.api_key:
            self.client = SendGridAPIClient(api_key=self.api_key)
        else:
            logger.warning("SENDGRID_API_KEY not set - email functionality disabled")
    
    async def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification magic link"""
        if not self.client:
            logger.error("SendGrid client not initialized")
            return False
        
        # Build verification URL
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verification_url = f"{base_url}/verify?token={verification_token}"
        
        # Email content
        subject = "Verify your email for AutoHVAC"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">AutoHVAC</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">HVAC Load Calculation & Analysis</p>
            </div>
            
            <div style="padding: 40px 30px; background: white;">
                <h2 style="color: #333; margin-bottom: 20px;">Verify Your Email Address</h2>
                
                <p style="color: #666; line-height: 1.6; margin-bottom: 30px;">
                    Welcome to AutoHVAC! To get started with your free blueprint analysis, 
                    please verify your email address by clicking the button below.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              font-weight: bold; 
                              display: inline-block;
                              transition: transform 0.2s;">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="color: #999; font-size: 14px; line-height: 1.6;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{verification_url}" style="color: #667eea; word-break: break-all;">
                        {verification_url}
                    </a>
                </p>
                
                <p style="color: #999; font-size: 14px; margin-top: 30px;">
                    This link will expire in 24 hours. If you didn't request this verification, 
                    you can safely ignore this email.
                </p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                <p style="color: #999; margin: 0; font-size: 14px;">
                    AutoHVAC - Professional HVAC Load Calculations<br>
                    This email was sent to {to_email}
                </p>
            </div>
        </div>
        """
        
        text_content = f"""
        AutoHVAC - Verify Your Email Address
        
        Welcome to AutoHVAC! To get started with your free blueprint analysis, 
        please verify your email address by clicking the link below:
        
        {verification_url}
        
        This link will expire in 24 hours. If you didn't request this verification, 
        you can safely ignore this email.
        
        AutoHVAC - Professional HVAC Load Calculations
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
                plain_text_content=text_content
            )
            
            response = self.client.send(message)
            
            if response.status_code == 202:
                logger.info(f"Verification email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending verification email to {to_email}: {str(e)}")
            return False
    
    async def send_report_ready_email(self, to_email: str, project_label: str, download_url: str) -> bool:
        """Send notification when HVAC report is ready"""
        if not self.client:
            logger.error("SendGrid client not initialized")
            return False
        
        # Email content
        subject = f"Your HVAC report is ready: {project_label}"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px;">AutoHVAC</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">HVAC Load Calculation & Analysis</p>
            </div>
            
            <div style="padding: 40px 30px; background: white;">
                <h2 style="color: #333; margin-bottom: 20px;">🎉 Your Report is Ready!</h2>
                
                <p style="color: #666; line-height: 1.6; margin-bottom: 20px;">
                    Great news! Your HVAC load calculation for <strong>{project_label}</strong> 
                    has been completed and is ready for download.
                </p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #333; margin: 0 0 10px 0;">Project: {project_label}</h3>
                    <p style="color: #666; margin: 0;">Complete Manual J calculation with equipment recommendations</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{download_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              font-weight: bold; 
                              display: inline-block;">
                        Download Report (PDF)
                    </a>
                </div>
                
                <p style="color: #999; font-size: 14px; line-height: 1.6;">
                    You can also access this report anytime from your 
                    <a href="{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/dashboard" style="color: #667eea;">
                        dashboard
                    </a>.
                </p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                <p style="color: #999; margin: 0; font-size: 14px;">
                    AutoHVAC - Professional HVAC Load Calculations<br>
                    This email was sent to {to_email}
                </p>
            </div>
        </div>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            
            if response.status_code == 202:
                logger.info(f"Report ready email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending report ready email to {to_email}: {str(e)}")
            return False

# Global instance
email_service = EmailService()