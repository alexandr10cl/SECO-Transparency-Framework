from flask import render_template, request, redirect, session, url_for, jsonify
from app import app, db
from models import User, Task, Evaluation, CollectedData
from flask_cors import CORS

CORS(app)

collections_data = []

# @app.route('/tasks_dashboard')
# def tasks_dashboard():
#     # Importação tardia para evitar importação circular
#     from views.utils import check_admin
    
#     is_admin = check_admin()
#     return render_template('dash.html', tasks=tasks_data, is_admin=is_admin)

@app.route('/data_collected')
def data_collected():

    code = '123456'
    
    #jeito 1 
    evaluation = Evaluation.query.filter_by(evaluation_id=code).first()
    #if evaluation: se achou é true

    #jeito 2
    #if Evaluation.query.filter_by(evaluation_id=code).first():

    #Inserir coisa no banco uma coleta
    collected_data = CollectedData.query.all()
    if not collected_data:
        collected_data_id = 1
    else:
        collected_data_id = collected_data[-1].collected_data_id + 1 #pega o último id e soma 1
        
    collected_data_starttime = '2023-10-01 12:00:00'
    collected_data_endtime = '2023-10-01 12:00:00'
    evaluation_code = 34307

    new_collected_data = CollectedData( # os nomes da esquerda são como está no db
        collected_data_id=collected_data_id,
        start_time=collected_data_starttime,
        end_time=collected_data_endtime,
        evaluation_id=evaluation_code)

    #db.session.add(new_collected_data) # Adiciona a nova coleta ao banco de dados
    #db.session.commit() #envia de fato pro servidor

    return render_template('data_collected.html', collections=collections_data)


@app.route('/submit_tasks', methods=['POST'])
def dashboard():
    data = request.json  # Obtém os dados JSON enviados pela extensão
    collections_data.append(data)
    print("Dados recebidos:", data) 
    return jsonify({"message": "Dados recebidos com sucesso"}), 200


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
        "description": "Find the portal's official documentation.",
        "questions": [
        { "text": "Could you solve the task? If not, could you explain why?" },
        { "text": "Was it easy to identify where the documentation is located and how to access it? If not, what could be improved?" }
        ]
    },{
        "id": 3,
        "title": "Task 3",
        "description": "Explore the portal's updates and news section and find a recent piece of information.",
        "questions": [
        { "text": "Were you able to easily identify where news and updates are published?" },
        { "text": "Are the presented information clear and organized in a way that facilitates tracking changes?" }
        ]
    }]
    return jsonify(selected_tasks)

@app.route('/auth_evaluation', methods=['POST'])
def auth_evaluation():
    data = request.json  # JSON RECEBIDO DA EXTENSÃO
    evaluation_code = data.get("code") # Pega o código do JSON

    # Query no db para verificar se o código existe
    evaluation = Evaluation.query.filter_by(evaluation_id=evaluation_code).first()

    if evaluation: 
        return jsonify({"message": "Valid"}), 200
    else:
        return jsonify({"message": "Invalid"}), 401