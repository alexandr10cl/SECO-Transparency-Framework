import os
from functools import wraps

from dotenv import load_dotenv
from flask import session, redirect, url_for, flash

from index import db
from models import User
from services.email_service import email_service

load_dotenv()

def isAdmin():
    if 'user_type' in session and session['user_type'] == 'admin':
        return True

def isLogged():
    if 'user_signed_in' in session and session['user_signed_in'] is not None:
        return True

# Fix #3: Add login_required decorator for route protection
def login_required(f):
    """
    Decorator to protect routes that require authentication.
    Redirects to signin page if user is not logged in.
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "This is protected"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not isLogged():
            # Flash message to inform user why they were redirected
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('signin'))
        return f(*args, **kwargs)
    return decorated_function

def send_verification_email(email, username, verification_url):
    """
    Send verification email to user.
    Delegates to EmailService.
    """
    return email_service.send_verification_email(email, username, verification_url)


def send_password_reset_email(email, username, reset_url):
    """
    Send password reset email to user.
    Delegates to EmailService.
    """
    return email_service.send_password_reset_email(email, username, reset_url)