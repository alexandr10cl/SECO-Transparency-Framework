from flask import render_template, request, redirect, session, url_for, flash
import requests
from app import app, db
from models import User
from functions import isLogged, isAdmin, send_verification_email
import secrets

message = '' # Error sign in message
messageReg = '' # Success sign up message
messageEA = '' # Existent account message

@app.route('/signin')
def signin():
    if not isLogged():
        return render_template('sign_in.html', message = message, messageEA = messageEA, messageReg = messageReg)
    else:
        return redirect(url_for('index'))

@app.route('/auth', methods=['POST',])
def auth():
    global message
    global messageEA
    global messageReg
    
    user = User.query.filter_by(email = request.form.get('email')).first()
    if user:
        if user.check_password(request.form.get('passw')):
            # Check if user is verified
            if not user.is_verified:
                message = 'Please verify your email address before signing in. Check your inbox for a verification link.'
                messageReg = ''
                messageEA = ''
                return redirect(url_for('signin'))

            session['user_signed_in'] = user.email
            session['user_type'] = user.type.value

            # Pegar token de autenticação do UXT
            uxt_url = 'https://uxt-stage.liis.com.br/auth/login'

            uxt_dados = {
                "email": user.email,
                "password": request.form.get('passw')
            }

            resposta = requests.post(uxt_url, json=uxt_dados)
            if resposta.status_code == 200:
                access_token = resposta.json().get('access_token')
                if access_token:
                    session['uxt_access_token'] = access_token
                    print(f"[UXT] Token de acesso obtido com sucesso para '{user.email}'.")
                else:
                    print("[UXT] Nenhum token de acesso retornado.")
            else:
                print(f"[UXT] Erro ao autenticar na API UXT (status {resposta.status_code}).")
                print(f"[UXT] Resposta: {resposta.text}")
                return redirect(url_for('signin'))

            message = ''
            messageReg = ''
            messageEA = ''
            return redirect(url_for('index'))
        else:
            message = 'Email or password are incorrect'
            messageReg = ''
            messageEA = ''
            return redirect(url_for('signin'))
    else:
        message = 'Email or password are incorrect'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))

@app.route('/signup')
def signup():
    if not isLogged():
        return render_template('sign_up.html', message = message, messageEA = messageEA, messageReg = messageReg)
    else:
        return redirect(url_for('index'))

@app.route('/register', methods=['POST',])
def register():
    global message
    global messageReg
    global messageEA
    
    email = request.form.get('email')
    name = request.form.get('name')
    passw = request.form.get('passw')

    account = User.query.filter_by(email=email).first()
    if account:
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
                message = 'UXTracking service is temporarily unavailable. Please try again in a few minutes.'
            elif resposta.status_code == 409:
                message = 'This email is already registered in our tracking system. Please use a different email address.'
            elif resposta.status_code == 400:
                message = 'Invalid registration data. Please check your information and try again.'
            elif resposta.status_code == 500:
                message = 'UX-Tracking service is experiencing technical difficulties. Please try again later.'
            elif resposta.status_code >= 500:
                message = 'UX-Tracking service is temporarily unavailable. Please try again in a few minutes.'
            else:
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
        admin_credentials = {
            "email": "vasco@gmail.com",
            "password": "vasco123"
        }
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
                message = 'Account created but role assignment failed. Please contact support.'
                messageReg = ''
                messageEA = ''
                return redirect(url_for('signin'))
        else:
            print(f"[UXT] Error obtaining admin token or user data: {resposta_admin.text if resposta_admin.status_code != 200 else 'No user data'}")
            message = 'Account created but role assignment failed. Please contact support.'
            messageReg = ''
            messageEA = ''
            return redirect(url_for('signin'))
    except requests.exceptions.ConnectionError:
        print("[UXT] Connection error: Could not connect to UXTracking API")
        message = 'Unable to connect to UXTracking service. Please check your internet connection and try again.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))
    except requests.exceptions.Timeout:
        print("[UXT] Timeout error: UXTracking API request timed out")
        message = 'UXTracking service is taking too long to respond. Please try again in a few minutes.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))
    except requests.exceptions.RequestException as e:
        print(f"[UXT] Request error with UXT API: {str(e)}")
        message = 'UXTracking service is temporarily unavailable. Please try again later.'
        messageReg = ''
        messageEA = ''
        return redirect(url_for('signin'))

    # Only create the local account if everything above succeeded
    users = User.query.all()
    cont = 1 if not users else users[-1].user_id + 1
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    
    new_account = User(
        email=email, 
        username=name, 
        type='seco_manager', 
        user_id=cont,
        is_verified=False,
        verification_token=verification_token
    )
    new_account.set_password(passw)
    db.session.add(new_account)
    db.session.commit()
    
    # Send verification email
    verification_url = url_for('verify_email', token=verification_token, _external=True)
    if send_verification_email(email, name, verification_url):
        message = ''
        messageReg = 'Account created successfully. Please check your email to verify your account.'
        messageEA = ''
    else:
        message = 'Account created but verification email could not be sent. Please contact support.'
        messageReg = ''
        messageEA = ''
    
    return redirect(url_for('signin'))

@app.route('/verify/<token>')
def verify_email(token):
    global message
    global messageReg
    global messageEA
    
    user = User.query.filter_by(verification_token=token).first()
    
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        
        message = ''
        messageReg = 'Your email has been verified successfully! You can now sign in.'
        messageEA = ''
        return redirect(url_for('signin'))
    else:
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