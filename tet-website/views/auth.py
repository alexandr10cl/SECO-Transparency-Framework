from flask import render_template, request, redirect, session, url_for, flash
import requests
from app import app, db
from models import User
from functions import isLogged, isAdmin

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
    user = User.query.filter_by(email = request.form.get('email')).first()
    if user:
        if request.form.get('passw') == user.passw:
            global message
            global messageEA
            global messageReg

            session['user_signed_in'] = user.email
            session['user_type'] = user.type.value

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
    email = request.form.get('email')
    name = request.form.get('name')
    passw = request.form.get('passw')

    account = User.query.filter_by(email=email).first()
    if account:
        global message
        global messageReg
        global messageEA
        message = ''
        messageReg = ''
        messageEA = 'This email is already registered, sign in'
        return redirect(url_for('signin'))
    
    users = User.query.all()
    if not users:
        cont = 1
    else:
        cont = users[-1].user_id + 1
    
    # Define the default user type as UserType.SECO_MANAGER
    new_account = User(email=email, username=name, passw=passw, type='seco_manager', user_id=cont)
    db.session.add(new_account)
    db.session.commit()

    message = ''
    messageReg = 'Account created successfully'
    messageEA = ''

    uxt_url = 'https://uxt-stage.liis.com.br/auth/register'

    uxt_dados = {
        "email": email,
        "username": name,
        "password": passw,
        "role": 1
    }

    try:
        resposta = requests.post(uxt_url, json=uxt_dados)
        if resposta.status_code == 201:
            print(f"[UXT] Conta registrada com sucesso na API UXT para '{email}'.")

            # Conta criada com sucesso. Agora, é necessário mudar a role padrão 1 para 2 (SECO Manager)
            # PEGAR O TOKEN RETORNADO DO NOVO USUÁRIO
            access_token = resposta.json().get('access_token')

            if access_token:
                # FAZER REQUISIÇÃO AUTENTICADA PARA /auth/me
                headers = {
                    'Authorization': f'Bearer {access_token}'
                }

                me_url = 'https://uxt-stage.liis.com.br/auth/me'
                me_resp = requests.get(me_url, headers=headers)

                if me_resp.status_code == 200:
                    me_data = me_resp.json()
                    print(f"[UXT] Dados do usuário logado: {me_data}")
                else:
                    print(f"[UXT] Falha ao acessar /auth/me: {me_resp.status_code}")
                    print(f"[UXT] Resposta: {me_resp.text}")
            else:
                print("[UXT] Nenhum token de acesso retornado.")

            # Obter Token de administrador para mudar a role
            uxt_admin_login_url = 'https://uxt-stage.liis.com.br/auth/login'

            # Credenciais do administrador (ideal substituir por um sistema de autenticação mais seguro)
            credenciais_admin = {
                "email": "vasco@gmail.com",
                "password": "vasco123"
            }

            resposta_admin = requests.post(uxt_admin_login_url, json=credenciais_admin)
            if resposta_admin.status_code == 200:
                token = resposta_admin.json().get("access_token")
                managerId = me_data.get("idUser")

                # Atualizar a role do usuário para SECO Manager (role 2)
                uxt_changeRole_url = 'https://uxt-stage.liis.com.br/auth/change-role'
                dados_changeRole = {
                    "userId": managerId,
                    "newRole": 2 # SECO Manager
                }

                headers_admin = {
                    'Authorization': f'Bearer {token}'
                }

                resposta_changeRole = requests.post(uxt_changeRole_url, json=dados_changeRole, headers=headers_admin)
                if resposta_changeRole.status_code == 200:
                    print(f"[UXT] Role do usuário '{email}' alterada para SECO Manager com sucesso.")
                    message = 'Account created and registered in UXT successfully'
                    messageReg = ''
                    messageEA = ''
                else:
                    print(f"[UXT] Erro ao alterar a role do usuário: {resposta_changeRole.text}")
                    message = 'Error changing user role in UXT'
                    messageReg = ''
                    messageEA = ''
                    return redirect(url_for('signin'))

            else:
                print(f"[UXT] Erro ao obter token de administrador: {resposta_admin.text}")
                message = 'Error obtaining admin token for UXT'
                messageReg = ''
                messageEA = ''
                return redirect(url_for('signin'))

        else:
            print(f"[UXT] Erro ao registrar na API UXT (status {resposta.status_code}).")
            print(f"[UXT] Resposta: {resposta.text}")
            message = 'Local account created, but UXT registration failed. This user already exists.'
            messageReg = ''
            messageEA = ''
    except requests.exceptions.RequestException as e:
        print(f"[UXT] Erro de conexão com a API UXT: {str(e)}")
        message = 'Error connecting to UXT'
        messageReg = ''
        messageEA = ''

    return redirect(url_for('signin'))

@app.route('/logout')
def logout():
    if isLogged():
        session['user_signed_in'] = None
        session['user_type'] = None
        return redirect(url_for('index'))