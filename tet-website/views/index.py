from flask import render_template, request, redirect, session, url_for
from app import app, db
from models import User, Admin, SECO_MANAGER, Evaluation, SECO_process
from functions import isLogged, isAdmin
from datetime import datetime
import random as rd

@app.route('/')
def index():
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin(email)
        user = User.query.filter_by(email=email).first()
        admins = Admin.query.all()

        return render_template('index.html', email=email, username=user.username, is_admin=is_admin, admins=admins)
    
    admins = Admin.query.all()
    return render_template('index.html', admins=admins)

@app.route('/evaluations')
def evaluations():
    email = session['user_signed_in']
    user = SECO_MANAGER.query.filter_by(email=email).first()
    evaluations = user.evaluations
    return render_template('evaluations.html', evaluations=evaluations)

@app.route('/evaluations/create_evaluation')
def create_evaluation():
    email = session['user_signed_in']
    user = User.query.filter_by(email=email).first()
    seco_processes = SECO_process.query.all()
    return render_template('create_evaluation.html', user=user, seco_processes=seco_processes)

@app.route('/evaluations/create_evaluation/add_evaluation', methods=['POST'])
def add_evaluation():

    # getting the form data
    name = request.form.get('name')
    email = session['user_signed_in']
    user = SECO_MANAGER.query.filter_by(email=email).first()
    user_id = user.user_id

    # setting the evaluation_id
    while True:
        evaluation_id = ''.join(rd.choices('0123456789', k=6))
        if Evaluation.query.filter_by(evaluation_id=evaluation_id).first() is None:
            break



    # getting the selected SECO_process IDs
    seco_process_ids = request.form.getlist('seco_process_ids')

    # getting the selected SECO_process objects
    if seco_process_ids:
        seco_processes = SECO_process.query.filter(SECO_process.seco_process_id.in_(seco_process_ids)).all()

    # creating the new evaluation object
    new_evaluation = Evaluation(evaluation_id=evaluation_id,
                                name=name, 
                                user_id=user_id, 
                                seco_processes=seco_processes)
    
    # adding the new evaluation to the database
    db.session.add(new_evaluation)
    db.session.commit()

    # redirecting to the evaluations page
    return redirect(url_for('evaluations'))