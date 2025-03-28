from flask import render_template, request, redirect, session, url_for, jsonify
from app import app, db
from models import User, Task
from flask_cors import CORS

CORS(app)

tasks_data = []

# @app.route('/tasks_dashboard')
# def tasks_dashboard():
#     # Importação tardia para evitar importação circular
#     from views.utils import check_admin
    
#     is_admin = check_admin()
#     return render_template('dash.html', tasks=tasks_data, is_admin=is_admin)

@app.route('/submit_tasks', methods=['POST'])
def dashboard():
    data = request.json  # Obtém os dados JSON enviados pela extensão
    tasks_data.extend(data)
    print("Dados recebidos:", data) 
    return jsonify({"message": "Dados recebidos com sucesso"}), 200

@app.route('/getguidelines', methods=['GET'])
def get_guidelines():
    guidelines = {
        "Nome": "Access Capability",
        "Description": "Software ecosystem portals must be accessible, stable, and functional, with consistent and uninterrupted access."
    }
    return jsonify(guidelines) 

@app.route('/gettasks', methods=['GET'])
def get_tasks():
    selected_tasks = [{
        "id": 1,
        "title": "Task 1",
        "description": "Translate the page into Portuguese.",
        "questions": [
        { "text": "Could you solve the task? If not, could you explain why?" },
        { "text": "In your opinion, is the portal's translation system effective?" },
        { "text": "What do you think about the page design?" }
        ]
    },
    {
        "id": 2,
        "title": "Task 2",
        "description": "Find the language documentation.",
        "questions": [
        { "text": "Could you solve the task? If not, could you explain why?" },
        { "text": "Q2?" }
        ]
    },{
        "id": 3,
        "title": "Task 3",
        "description": "Task description.",
        "questions": [
        { "text": "Q1?" },
        { "text": "Q2?" }
        ]
    }]
    return jsonify(selected_tasks)