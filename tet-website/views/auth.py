from flask import render_template, request, redirect, session, url_for
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

    return redirect(url_for('signin'))

@app.route('/logout')
def logout():
    if isLogged():
        session['user_signed_in'] = None
        session['user_type'] = None
        return redirect(url_for('index'))