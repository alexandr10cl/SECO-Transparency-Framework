from flask import render_template, request, redirect, session, url_for, flash
from index import app, db
from models import User, UserType, Evaluation
from functions import isLogged, isAdmin, send_verification_email, send_password_reset_email
import secrets
import os
from services.heatmap_prefetch import schedule_heatmap_prefetch
from services import uxt_service
from services.uxt_service import (
    clear_session_uxt_token,
    get_uxt_token,
)

from config_flags import DEV_MODE, UXT_INTEGRATION

messageType = ''
message = '' # Error sign in message
messageReg = '' # Success sign up message
messageEA = '' # Existent account message

@app.route('/signin')
def signin():
    global message
    global messageEA
    global messageReg
    global messageType
    print(f'Message of successful registration: "{messageReg}"')
    print(f'Message of existent account: "{messageEA}"')
    print(f'Message of sign in: "{message}"')
    return render_template('sign_in.html', message = message, messageEA = messageEA, messageReg = messageReg, messageType=messageType)

@app.route('/auth', methods=['POST',])
def auth():
    global message
    global messageEA
    global messageReg
    global messageType
    
    user = User.query.filter_by(email = request.form.get('email')).first()
    if user:
        if user.check_password(request.form.get('passw')):
            # Check if user is verified
            if not user.is_verified and not DEV_MODE:
                message = 'Please verify your email address before signing in. Check your inbox for a verification link.'
                messageReg = ''
                messageEA = ''
                return redirect(url_for('signin'))

            # Fix #1: Make session permanent so timeout works
            session.permanent = True
            session['user_signed_in'] = user.email
            session['user_type'] = user.type.value

            # Fix #2: UXT API fallback - don't block login if UXT is down
            # Try to get UXT token, but allow login even if it fails
            if UXT_INTEGRATION:
                uxt_service.login(user.email, request.form.get('passw'))
            else:
                clear_session_uxt_token()

            # Always allow login regardless of UXT status
            message = ''
            messageReg = ''
            messageEA = ''
            messageType = ''

            # Prefetch heatmaps in the background for faster dashboard loading
            if UXT_INTEGRATION:
                token_for_prefetch = get_uxt_token()
                evaluation_ids = [
                    evaluation.evaluation_id
                    for evaluation in Evaluation.query
                        .filter_by(user_id=user.user_id)
                        .order_by(Evaluation.created_at.desc(), Evaluation.evaluation_id.desc())
                        .limit(5)
                ]
                schedule_heatmap_prefetch(evaluation_ids, token_for_prefetch)

            return redirect(url_for('index'))
        else:
            messageType = 'error'
            message = 'Email or password are incorrect'
            messageReg = ''
            messageEA = ''
            return redirect(url_for('signin'))
    else:
        messageType = 'error'
        message = 'Email or password are incorrect'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))

@app.route('/signup')
def signup():
    if not isLogged():
        return render_template('sign_up.html', message = message, messageEA = messageEA, messageReg = messageReg, messageType = messageType)
    else:
        return redirect(url_for('index'))

@app.route('/register', methods=['POST',])
def register():
    global message
    global messageReg
    global messageEA
    global messageType
    
    email = request.form.get('email')
    name = request.form.get('name')
    passw = request.form.get('passw')

    account = User.query.filter_by(email=email).first()
    if account:
        messageType = 'error'
        message = ''
        messageReg = ''
        messageEA = 'This email is already registered, please sign in.'
        return redirect(url_for('signin'))

    # First, try to register the user in the UXTracking API
    # (skipped entirely when UXT_INTEGRATION is disabled - local account only)
    if UXT_INTEGRATION:
        result = uxt_service.register(email, name, passw)
        if not result["ok"]:
            reason = result["reason"]
            if reason == "register_http":
                status_code = result["status_code"]
                # Provide specific error messages based on status code
                if status_code == 502:
                    messageType = 'error'
                    message = 'UXTracking service is temporarily unavailable. Please try again in a few minutes.'
                elif status_code == 409:
                    messageType = 'error'
                    message = 'This email or username is already registered in our tracking system. Please use a different email address.'
                elif status_code == 400:
                    messageType = 'error'
                    message = 'Invalid registration data. Please check your information and try again.'
                elif status_code == 500:
                    messageType = 'error'
                    message = 'UX-Tracking service is experiencing technical difficulties. Please try again later.'
                elif status_code >= 500:
                    messageType = 'error'
                    message = 'UX-Tracking service is temporarily unavailable. Please try again in a few minutes.'
                else:
                    messageType = 'error'
                    message = f'Registration failed (Error {status_code}). Please try again later.'
            elif reason == "role_assignment":
                messageType = 'error'
                message = 'Account created but role assignment failed. Please contact support.'
            elif reason == "connection":
                messageType = 'error'
                message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
            elif reason == "timeout":
                messageType = 'error'
                message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
            else:  # request
                messageType = 'error'
                message = 'UXTracking service is temporarily unavailable. Please try again later.'

            messageReg = ''
            messageEA = ''
            return redirect(url_for('signin'))
    else:
        print(f"[UXT] Integration disabled - creating local-only account for '{email}'.")

    # Create the local account (runs in both UXT modes once the block above
    # passed or was skipped). Email verification follows DEV_MODE.
    if DEV_MODE:
        new_account = User(
            email=email,
            username=name,
            type=UserType.SECO_MANAGER,
            is_verified=True,
            verification_token=None
        )
        new_account.set_password(passw)
        db.session.add(new_account)
        db.session.commit()

        messageType = 'success'
        message = 'Account created successfully. You can sign in now (DEV_MODE: email verification skipped).'
        messageReg = ''
        messageEA = ''
    else:
        verification_token = secrets.token_urlsafe(32)
        new_account = User( # Changed from SECO_MANAGER to User
            email=email,
            username=name,
            type=UserType.SECO_MANAGER,
            is_verified=False,
            verification_token=verification_token
        )
        new_account.set_password(passw)
        db.session.add(new_account)
        db.session.commit()

        # Send verification email
        verification_url = url_for('verify_email', token=verification_token, _external=True)
        if send_verification_email(email, name, verification_url):
            messageType = 'success'
            message = 'Account created successfully. Please check your email to verify your account.'
            messageReg = ''
            messageEA = ''
        else:
            messageType = 'error'
            message = 'Account created but verification email could not be sent. Please contact support.'
            messageReg = ''
            messageEA = ''

    return redirect(url_for('signin'))

@app.route('/verify/<token>')
def verify_email(token):
    global message
    global messageReg
    global messageEA
    global messageType
    
    user = User.query.filter_by(verification_token=token).first()
    
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        
        messageType = 'success'
        message = 'Your email has been verified successfully! You can now sign in.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))
    else:
        messageType = 'error'
        message = 'Invalid or expired verification link.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))

@app.route('/logout')
def logout():
    if isLogged():
        session['user_signed_in'] = None
        session['user_type'] = None
        clear_session_uxt_token()
        return redirect(url_for('index')) 
    
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    global message
    global messageType

    if not UXT_INTEGRATION:
        messageType = 'error'
        message = 'Password reset is unavailable: UX-Tracking integration is disabled.'
        return redirect(url_for('signin'))

    if request.method == 'GET':
        if not isLogged():
            message = ''
            return render_template('forgot_password.html', message=message, messageType=messageType)
        else:
            return redirect(url_for('index'))
    
    elif request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            result = uxt_service.request_password_reset(email)
            if result["ok"]:
                messageType = 'success'
                message = 'If an account with that email exists, a password reset code has been sent.'
                return redirect(url_for('reset_password', id=user.user_id))
            else:
                reason = result["reason"]
                if reason == "connection":
                    message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
                elif reason == "timeout":
                    message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
                else:  # http or request
                    message = 'Error sending password reset email. Please try again later.'
                messageType = 'error'
                return render_template('forgot_password.html', message=message, messageType=messageType)
        else:
            messageType = 'success'
            message = 'If an account with that email exists, a password reset code has been sent.'
            return redirect(url_for('reset_password', id=0))

@app.route('/reset-password/<int:id>', methods=['GET', 'POST'])
def reset_password(id):
    global message
    global messageType

    if not UXT_INTEGRATION:
        messageType = 'error'
        message = 'Password reset is unavailable: UX-Tracking integration is disabled.'
        return redirect(url_for('signin'))

    if request.method == 'GET':
        if not isLogged():
            return render_template('reset_password.html', message=message, id=id, messageType=messageType)
        else:
            return redirect(url_for('index'))
        
    elif request.method == 'POST':
        print(f"[UXT] Resetting password for user ID: {id}")
        if id == 0:
            messageType = 'error'
            message = 'Invalid user ID. Please try again later.'
            return render_template('reset_password.html', message=message, id=id, messageType=messageType)
        user = User.query.get_or_404(id)
        newPassword = request.form.get('password')
        code = request.form.get('code')
        print(f"[UXT] New password: {newPassword}, Code: {code}")
        print(f"[UXT] User: {user.email if user else 'None'}")
        
        if user and newPassword and code:
            result = uxt_service.reset_password(user.email, code, newPassword)
            if result["ok"]:
                user.set_password(newPassword)
                db.session.commit()
                messageType = 'success'
                message = 'Your password has been reset successfully. You can now sign in.'
                return redirect(url_for('signin'))
            else:
                reason = result["reason"]
                if reason == "http":
                    messageType = 'error'
                    message = 'Error resetting password. Please check the code and try again.'
                    return render_template('reset_password.html', message=message, id=id)
                elif reason == "connection":
                    messageType = 'error'
                    message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
                    return render_template('reset_password.html', message=message, id=id)
                elif reason == "timeout":
                    messageType = 'error'
                    message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
                    return render_template('reset_password.html', message=message, id=id)
                else:  # request
                    messageType = 'error'
                    message = 'Error resetting password. Please try again later.'
                    return render_template('reset_password.html', message=message, id=id, messageType=messageType)
        else:
            messageType = 'error'
            message = 'Invalid request. Please try again.'
            print("Reset password: Missing user, new password, or code.")
            return render_template('reset_password.html', message=message, id=id)