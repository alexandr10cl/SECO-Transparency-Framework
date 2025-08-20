from models import User
from index import db
from flask import session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def isAdmin():
    if 'user_type' in session and session['user_type'] == 'admin':
        return True

def isLogged():
    if 'user_signed_in' in session and session['user_signed_in'] is not None:
        return True

def send_verification_email(email, username, verification_url):
    """
    Send verification email to user
    """
    try:
        # Email configuration
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        
        if not sender_email or not sender_password:
            print("Email configuration not found in environment variables")
            return False
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = "Verify your SECO-TransP account"
        
        # Email body
        body = f"""
        Hello {username},
        
        Thank you for registering with SECO-TransP!
        
        Please click the following link to verify your email address:
        {verification_url}
        
        If you did not create this account, please ignore this email.
        
        Best regards,
        The SECO-TransP Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        
        print(f"Verification email sent to {email}")
        return True
        
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False
    
def send_password_reset_email(email, username, reset_url):
    """
    Send password reset email to user
    """
    
    try:
        # Email configuration
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        
        if not sender_email or not sender_password:
            print("Email configuration not found in environment variables")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = "Reset your SECO-TransP password"
        
        # Email body
        body = f"""
        Hello {username},
        
        We received a request to reset your SECO-TransP password.
        
        Please click the following link to reset your password:
        {reset_url}
        
        Please check your inbox to get the Reset Password Code sent by UX-Tracking.
        
        If you did not request this, please ignore this email.
        
        Best regards,
        The SECO-TransP Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        
        print(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        print(f"Error preparing password reset email: {str(e)}")
        return False