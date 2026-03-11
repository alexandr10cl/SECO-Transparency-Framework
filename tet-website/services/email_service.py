import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()


class EmailService:
    """
    Unified email service for sending emails.
    Consolidates duplicate email sending logic.
    """

    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')

    def _send_email(self, to_email, subject, body):
        """
        Private method to send email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            if not self.sender_email or not self.sender_password:
                print("Email configuration not found in environment variables")
                return False

            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            text = msg.as_string()
            server.sendmail(self.sender_email, to_email, text)
            server.quit()

            print(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def send_verification_email(self, email, username, verification_url):
        """
        Send account verification email to user.

        Args:
            email: User's email address
            username: User's username
            verification_url: URL for email verification

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = "Verify your SECO-TransP account"
        body = f"""
        Hello {username},

        Thank you for registering with SECO-TransP!

        Please click the following link to verify your email address:
        {verification_url}

        If you did not create this account, please ignore this email.

        Best regards,
        The SECO-TransP Team
        """

        return self._send_email(email, subject, body)

    def send_password_reset_email(self, email, username, reset_url):
        """
        Send password reset email to user.

        Args:
            email: User's email address
            username: User's username
            reset_url: URL for password reset

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = "Reset your SECO-TransP password"
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

        return self._send_email(email, subject, body)


# Create a singleton instance for easy import
email_service = EmailService()
