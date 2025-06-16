from flask import render_template, request, redirect, session, url_for, jsonify
from app import app, db
from models import User, Task, Evaluation, CollectedData, Guideline, SECO_process, PerformedTask, DeveloperQuestionnaire, Navigation, Answer, Question
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
    
    #Inserir no banco a coleta
    collected_data = CollectedData.query.all()
    if not collected_data:
        collected_data_id = 1
    else:
        collected_data_id = collected_data[-1].collected_data_id + 1 #pega o último id e soma 1

    # Pega o informações do JSON
    evaluation_code = data.get("evaluation_code") 
    collected_data_starttime = data.get("startTime")
    collected_data_endtime = data.get("endTime")

    performedtasksList = []
    # PerformedTasks
    performed_tasks = data.get("performed_tasks")
    for task in performed_tasks:
        #task_id = task.get("id")
        task_start_time = task.get("initial_timestamp")
        task_end_time = task.get("final_timestamp")
        status = data.get("status")

        answersList = []

        for a in task.get("answers"):
            # Pega as perguntas e respostas
            task_question = a.get("question")
            task_answer = a.get("answer")

            answers = Answer.query.all()
            if not answers:
                id = 1
            else:
                id = answers[-1].answer_id + 1 #pega o último id e soma 1

            new_answer = Answer(
                answer_id=id,
                answer=task_answer,
                question_id=task_question
            )         
            db.session.add(new_answer) # Adiciona a nova resposta ao banco de dados
            db.session.commit() #envia de fato pro servidor       
            answersList.append(new_answer.answer_id) # Adiciona o id da resposta à lista de respostas

        performedtasks = PerformedTask.query.all()
        if not performedtasks:
            id = 1
        else:
            id = performedtasks[-1].performed_task_id + 1 #pega o último id e soma 1

        # Inserir no banco a coleta
        new_performed_task = PerformedTask(
            performed_task_id=id,
            collected_data_id=collected_data_id,
            initial_timestamp=task_start_time,
            final_timestamp=task_end_time,
            answers=answersList,
            status=status,
            #task_id=task_id
            )
        db.session.add(new_performed_task) # Adiciona a nova coleta ao banco de dados
        db.session.commit() #envia de fato pro servidor
        performedtasksList.append(new_performed_task.performed_task_id) # Adiciona o id da resposta à lista de respostas

    new_collected_data = CollectedData( # os nomes da esquerda são como está no db
        collected_data_id=collected_data_id,
        start_time=collected_data_starttime,
        end_time=collected_data_endtime,
        evaluation_id=evaluation_code,
        performed_tasks=performedtasksList
        #developer_questionnaire=questionnaire_id,
        #navigation=navigation_id
        )



    return jsonify({"message": "Dados recebidos com sucesso"}), 200



@app.route('/load_tasks', methods=['POST'])
def load_tasks():
    data = request.json # JSON RECEBIDO DA EXTENSÃO
    evaluation_code = data.get("code") # Pega o código do JSON
    print("Código da avaliação:", evaluation_code)
    # Query no db para verificar se o código existe
    evaluation = Evaluation.query.filter_by(evaluation_id=evaluation_code).first()

    if evaluation:
        result = []
        for process in evaluation.seco_processes:
            process_obj = {
                "process_id": process.seco_process_id,
                "process_title": process.description,
                "process_tasks": [],
                "process_review": []
            }
            # Adiciona tasks associadas ao processo
            for task in process.tasks:
                process_obj["process_tasks"].append({
                    "task_id": task.task_id,
                    "task_title": task.title,
                    "task_description": task.description
                })
            # Adiciona perguntas de review (questions dos Key Success Criteria das guidelines do processo)
            review_questions = set()
            for guideline in process.guidelines:
                for ksc in guideline.key_success_criteria:
                    for question in ksc.questions:
                        review_questions.add((question.question, question.question_id))
            # Adiciona ao objeto, evitando duplicatas
            for q_text, q_id in review_questions:
                process_obj["process_review"].append({
                    "process_review_question_text": q_text,
                    "process_review_question_id": q_id
                })
            result.append(process_obj)
        
        print("Resultado:", result)
        return jsonify(result), 200
    else:
        print("Código de avaliação inválido:", evaluation_code)
        return jsonify({"message": "Invalid"}), 401


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