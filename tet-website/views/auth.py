from flask import render_template, request, redirect, session, url_for, flash
import requests
from index import app, db
from models import User, UserType
from functions import isLogged, isAdmin, send_verification_email, send_password_reset_email
import secrets
import os

DEV_MODE = os.getenv('DEV_MODE', 'False') == 'True'
admin_credentials = {
    "email": os.getenv("ADMIN_EMAIL"),
    "password": os.getenv("ADMIN_PASSWORD")
}

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
            uxt_url = 'https://uxt-stage.liis.com.br/auth/login'
            uxt_dados = {
                "email": user.email,
                "password": request.form.get('passw')
            }

            try:
                # Set timeout to prevent hanging
                resposta = requests.post(uxt_url, json=uxt_dados, timeout=5)
                
                if resposta.status_code == 200:
                    access_token = resposta.json().get('access_token')
                    if access_token:
                        session['uxt_access_token'] = access_token
                        print(f"[UXT] Token de acesso obtido com sucesso para '{user.email}'.")
                    else:
                        print("[UXT] Nenhum token de acesso retornado.")
                        # Continue login without UXT token
                        session['uxt_access_token'] = None
                else:
                    print(f"[UXT] Erro ao autenticar na API UXT (status {resposta.status_code}).")
                    print(f"[UXT] Resposta: {resposta.text}")
                    # Continue login without UXT token
                    session['uxt_access_token'] = None
                    
            except requests.exceptions.Timeout:
                # UXT API timeout - allow login anyway
                print("[UXT] Timeout ao conectar com API UXT. Continuando login sem UXT token.")
                session['uxt_access_token'] = None
                
            except requests.exceptions.ConnectionError:
                # UXT API not reachable - allow login anyway
                print("[UXT] Erro de conexão com API UXT. Continuando login sem UXT token.")
                session['uxt_access_token'] = None
                
            except requests.exceptions.RequestException as e:
                # Any other request error - allow login anyway
                print(f"[UXT] Erro ao conectar com API UXT: {str(e)}. Continuando login sem UXT token.")
                session['uxt_access_token'] = None

            # Always allow login regardless of UXT status
            message = ''
            messageReg = ''
            messageEA = ''
            messageType = ''
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
    uxt_url = 'https://uxt-stage.liis.com.br/auth/register'
    uxt_dados = {
        "email": email,
        "username": name,
        "password": passw,
        "role": 1
    }
    try:
        resposta = requests.post(uxt_url, json=uxt_dados)
        if resposta.status_code != 201:
            print(f"[UXT] Registration failed at UXT API (status {resposta.status_code}).")
            print(f"[UXT] Response: {resposta.text}")
            
            # Provide specific error messages based on status code
            if resposta.status_code == 502:
                messageType = 'error'
                message = 'UXTracking service is temporarily unavailable. Please try again in a few minutes.'
            elif resposta.status_code == 409:
                messageType = 'error'
                message = 'This email or username is already registered in our tracking system. Please use a different email address.'
            elif resposta.status_code == 400:
                messageType = 'error'
                message = 'Invalid registration data. Please check your information and try again.'
            elif resposta.status_code == 500:
                messageType = 'error'
                message = 'UX-Tracking service is experiencing technical difficulties. Please try again later.'
            elif resposta.status_code >= 500:
                messageType = 'error'
                message = 'UX-Tracking service is temporarily unavailable. Please try again in a few minutes.'
            else:
                messageType = 'error'
                message = f'Registration failed (Error {resposta.status_code}). Please try again later.'
            
            messageReg = ''
            messageEA = ''
            return redirect(url_for('signin'))
        print(f"[UXT] Account successfully registered at UXT API for '{email}'.")
        access_token = resposta.json().get('access_token')
        me_data = None
        if access_token:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            me_url = 'https://uxt-stage.liis.com.br/auth/me'
            me_resp = requests.get(me_url, headers=headers)
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                print(f"[UXT] Logged in user data: {me_data}")
            else:
                print(f"[UXT] Failed to access /auth/me: {me_resp.status_code}")
                print(f"[UXT] Response: {me_resp.text}")
        else:
            print("[UXT] No access token returned.")
        # Get admin token to change role
        uxt_admin_login_url = 'https://uxt-stage.liis.com.br/auth/login'
        resposta_admin = requests.post(uxt_admin_login_url, json=admin_credentials)
        if resposta_admin.status_code == 200 and me_data:
            token = resposta_admin.json().get("access_token")
            managerId = me_data.get("idUser")
            uxt_changeRole_url = 'https://uxt-stage.liis.com.br/auth/change-role'
            changeRole_data = {
                "userId": managerId,
                "newRole": 2 # SECO Manager
            }
            headers_admin = {
                'Authorization': f'Bearer {token}'
            }
            resposta_changeRole = requests.post(uxt_changeRole_url, json=changeRole_data, headers=headers_admin)
            if resposta_changeRole.status_code == 200:
                print(f"[UXT] User role for '{email}' changed to SECO Manager successfully.")
            else:
                print(f"[UXT] Error changing user role: {resposta_changeRole.text}")
                messageType = 'error'
                message = 'Account created but role assignment failed. Please contact support.'
                messageReg = ''
                messageEA = ''
                return redirect(url_for('signin'))
        else:
            print(f"[UXT] Error obtaining admin token or user data: {resposta_admin.text if resposta_admin.status_code != 200 else 'No user data'}")
            messageType = 'error'
            message = 'Account created but role assignment failed. Please contact support.'
            messageReg = ''
            messageEA = ''
            return redirect(url_for('signin'))
    except requests.exceptions.ConnectionError:
        print("[UXT] Connection error: Could not connect to UXTracking API")
        messageType = 'error'
        message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))
    except requests.exceptions.Timeout:
        print("[UXT] Timeout error: UXTracking API request timed out")
        messageType = 'error'
        message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))
    except requests.exceptions.RequestException as e:
        print(f"[UXT] Request error with UXT API: {str(e)}")
        messageType = 'error'
        message = 'UXTracking service is temporarily unavailable. Please try again later.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))

    # Only create the local account if everything above succeeded
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
        return redirect(url_for('index')) 
    
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    global message
    global messageType
    
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
            
            uxt_url = 'https://uxt-stage.liis.com.br/auth/forgot-password'
            
            uxt_dados = {
                "email": email
            }
            
            try:
                resposta = requests.post(uxt_url, json=uxt_dados)
                if resposta.status_code == 200:
                    print(f"[UXT] Password reset email sent successfully to '{email}'.")
                    messageType = 'success'
                    message = 'If an account with that email exists, a password reset code has been sent.'
                    return redirect(url_for('reset_password', id=user.user_id))
                else:
                    print(f"[UXT] Error sending password reset email (status {resposta.status_code}).")
                    messageType = 'error'
                    message = 'Error sending password reset email. Please try again later.'
                    return render_template('forgt_password.html', message=message, messageType=messageType)
            except requests.exceptions.ConnectionError:
                print("[UXT] Connection error: Could not connect to UXTracking API")
                messageType = 'error'
                message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
                return render_template('forgt_password.html', message=message, messageType=messageType)
            except requests.exceptions.Timeout:
                print("[UXT] Timeout error: UXTracking API request timed out")
                messageType = 'error'
                message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
                return render_template('forgt_password.html', message=message, messageType=messageType)
            except requests.exceptions.RequestException as e:
                print(f"[UXT] Error sending password reset email: {str(e)}")
                messageType = 'error'
                message = 'Error sending password reset email. Please try again later.'
                return render_template('forgt_password.html', message=message, messageType=messageType)
        else:
            messageType = 'success'
            message = 'If an account with that email exists, a password reset code has been sent.'
            return redirect(url_for('reset_password', id=0))

@app.route('/reset-password/<int:id>', methods=['GET', 'POST'])
def reset_password(id):
    global message
    global messageType
    
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
            uxt_url = 'https://uxt-stage.liis.com.br/auth/reset-password'
            
            uxt_dados = {
                "email": user.email,
                "code": code,
                "newPassword":newPassword,
                "confirmNewPassword": newPassword
            }
            
            try:
                resposta = requests.post(uxt_url, json=uxt_dados)
                if resposta.status_code == 200:
                    print(f"[UXT] Password reset successfully for '{user.email}'.")
                    user.set_password(newPassword)
                    db.session.commit()
                    messageType = 'success'
                    message = 'Your password has been reset successfully. You can now sign in.'
                    return redirect(url_for('signin'))
                else:
                    print(f"[UXT] Error resetting password (status {resposta.status_code}).")
                    messageType = 'error'
                    message = 'Error resetting password. Please check the code and try again.'
                    return render_template('reset_password.html', message=message, id=id)
            except requests.exceptions.ConnectionError:
                print("[UXT] Connection error: Could not connect to UXTracking API")
                messageType = 'error'
                message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
                return render_template('reset_password.html', message=message, id=id)
            except requests.exceptions.Timeout:
                print("[UXT] Timeout error: UXTracking API request timed out")
                messageType = 'error'
                message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
                return render_template('reset_password.html', message=message, id=id)
            except requests.exceptions.RequestException as e:
                print(f"[UXT] Error resetting password: {str(e)}")
                messageType = 'error'
                message = 'Error resetting password. Please try again later.'
                return render_template('reset_password.html', message=message, id=id, messageType=messageType)
        else:
            messageType = 'error'
            message = 'Invalid request. Please try again.'
            print("Reset password: Missing user, new password, or code.")
            return render_template('reset_password.html', message=message, id=id)