from models import User
from app import db
from flask import session

def isAdmin(email):
    if email is not None:
        user = User.query.filter_by(email = email).first()
        return user.type == 'AMDIN'

def isLogged():
    if 'user_signed_in' in session and session['user_signed_in'] is not None:
        return True