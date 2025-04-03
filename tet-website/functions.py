from models import User
from app import db
from flask import session

def isAdmin():
    if 'user_type' in session and session['user_type'] == 'admin':
        return True

def isLogged():
    if 'user_signed_in' in session and session['user_signed_in'] is not None:
        return True