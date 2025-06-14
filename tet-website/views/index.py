from flask import render_template, request, redirect, session, url_for
from app import app, db
from models import User, Admin, SECO_MANAGER, Evaluation, SECO_process, Question, DeveloperQuestionnaire
from functions import isLogged, isAdmin
from datetime import datetime
import random as rd
import requests

@app.route('/')
def index():
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin()
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
    seco_portal = request.form.get('seco_portal')
    seco_portal_url = request.form.get('seco_portal_url')
    email = session['user_signed_in']
    user = SECO_MANAGER.query.filter_by(email=email).first()
    user_id = user.user_id

    # setting the evaluation_id

    # Gerar código de Avaliação Único usando API
    uxt_url_generate = 'https://uxt-stage.liis.com.br/generate-code?horas=730' # 730 horas = 30 dias

    access_token = session.get('uxt_access_token')

    if not access_token:
        print("[UXT] No access token found in session. Please log in again.")
        return redirect(url_for('signin'))

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    resposta_generatecode = requests.post(uxt_url_generate, headers=headers)
    if resposta_generatecode.status_code == 201:
        evaluation_id = resposta_generatecode.json().get('cod')
        print("Generated evaluation ID from API:", evaluation_id)
    else:
        # If the API call fails, we can still use the random ID
        print("Failed to generate evaluation ID from API, using random ID instead.")
        print("Response from API:", resposta_generatecode.status_code, resposta_generatecode.text)
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
                                seco_processes=seco_processes,
                                seco_portal=seco_portal,
                                seco_portal_url=seco_portal_url)
    
    # adding the new evaluation to the database
    db.session.add(new_evaluation)
    db.session.commit()

    # redirecting to the evaluations page
    return redirect(url_for('evaluations'))

@app.route('/evaluations/<int:id>/edit')
def edit_evaluation(id):
    email = session['user_signed_in']
    user = User.query.filter_by(email=email).first()
    evaluation = Evaluation.query.get_or_404(id)
    seco_processes = SECO_process.query.all()
    return render_template('edit_evaluation.html', evaluation=evaluation, user=user, seco_processes=seco_processes)

@app.route('/evaluations/<int:id>/update', methods=['POST'])
def update_evaluation(id):
    # getting the form data
    name = request.form.get('name')
    seco_portal = request.form.get('seco_portal')
    seco_portal_url = request.form.get('seco_portal_url')
    
    # getting the selected SECO_process IDs
    seco_process_ids = request.form.getlist('seco_process_ids')

    # getting the selected SECO_process objects
    if seco_process_ids:
        seco_processes = SECO_process.query.filter(SECO_process.seco_process_id.in_(seco_process_ids)).all()

    # updating the evaluation object
    evaluation = Evaluation.query.get_or_404(id)
    evaluation.name = name
    evaluation.seco_portal = seco_portal
    evaluation.seco_portal_url = seco_portal_url
    evaluation.seco_processes = seco_processes
    
    # committing the changes to the database
    db.session.commit()

    # redirecting to the evaluations page
    return redirect(url_for('evaluation', id=id))

@app.route('/evaluations/<int:id>/delete')
def delete_evaluation(id):
    evaluation = Evaluation.query.get_or_404(id)
    
    for c in evaluation.collected_data:
        for p in c.performed_tasks:
            for a in p.answers:
                db.session.delete(a)
            db.session.delete(p)
        
        db.session.delete(c.developer_questionnaire)
        db.session.delete(c)
    
    db.session.delete(evaluation)
    db.session.commit()
    return redirect(url_for('evaluations'))

@app.route('/evaluations/<int:id>')
def evaluation(id):
    email = session['user_signed_in']
    user = User.query.filter_by(email=email).first()
    evaluation = Evaluation.query.get_or_404(id)
    seco_processes = evaluation.seco_processes
    collected_data = evaluation.collected_data
    questions = Question.query.all()
    guidelines = []
    tasks = []
    for p in seco_processes:
        for t in p.tasks:
            if t not in tasks:
                tasks.append(t)
        for g in p.guidelines:
            if g not in guidelines:
                guidelines.append(g)
                
    count_collected_data = len(collected_data)

    return render_template('eval.html', evaluation=evaluation, user=user, seco_processes=seco_processes, count_collected_data=count_collected_data, guidelines=guidelines, tasks=tasks, collected_data=collected_data, questions=questions)