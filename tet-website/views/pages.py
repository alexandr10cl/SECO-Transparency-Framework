from flask import render_template, request, redirect, session, url_for
from app import app, db
from functions import isLogged, isAdmin
from models import User

@app.route('/doc')
def doc():
    if isLogged():
        email = session['user_signed_in']
    return render_template('doc.html')

@app.route('/about')
def about():
    if isLogged():
        email = session['user_signed_in']
    return render_template('about.html')

@app.route('/guidelines')
def guidelines():
    if isLogged():
        email = session['user_signed_in']
    return render_template('guidelines.html')