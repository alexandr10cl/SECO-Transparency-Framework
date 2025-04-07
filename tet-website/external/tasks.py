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
    oi = 0

    if oi == 1:
        # Criar id para coleta
        collected_data = CollectedData.query.all()
        if not collected_data:
            collected_data_id = 1
        else:
            collected_data_id = collected_data[-1].collected_data_id + 1 #pega o último id e soma 1

        # Pega as informações da COLETA do JSON
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
            status = task.get("status")

            answersList = []

            for a in task.get("answers"):
                # Pega as perguntas e respostas
                task_question = a.get("question_id")
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
                    #de acordo com o db deveria ter aqui o chave estrangeira da perrformed task
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
            #db.session.add(new_performed_task) # Adiciona a nova coleta ao banco de dados
            #db.session.commit() #envia de fato pro servidor
            performedtasksList.append(new_performed_task.performed_task_id) # Adiciona o id da resposta à lista de respostas

        # DeveloperQuestionnaire
        devquestions = DeveloperQuestionnaire.query.all()
        if not devquestions:
            developer_questionnaire_id = 1
        else:
            developer_questionnaire_id = devquestions[-1].developer_questionnaire_id + 1 #pega o último id e soma 1

        profile = data.get("profile_questionnaire", {})
        final = data.get("final_questionnaire", {})
        
        new_developer_questionnaire = DeveloperQuestionnaire(
        developer_questionnaire_id=developer_questionnaire_id,
        academic_level=profile.get("academic_level"),
        previus_xp=profile.get("previus_experience"),
        emotion=final.get("emotion"),
        comments=final.get("comments"),
        segment=profile.get("segment"),
        collected_data_id=collected_data_id,
        # years_of_experience=profile.get("years_of_experience") 
        )

        #db.session.add(new_developer_questionnaire)
        #db.session.commit()

        # Navigation    
        navigation = Navigation.query.all()
        if not navigation:
            navigation_id = 1
        else:
            navigation_id = navigation[-1].navigation_id + 1

        new_navigation = Navigation(
            navigation_id=navigation_id,
            action=data.get("action"),
            title=data.get("title"),
            url=data.get("url"),
            timestamp=data.get("timestamp"),
            task_id=data.get("taskId"),
            collected_data_id=collected_data_id
        )
        #db.session.add(new_navigation) # Adiciona a nova coleta ao banco de dados
        #db.session.commit() #envia de fato pro servidor


        new_collected_data = CollectedData( # os nomes da esquerda são como está no db
            collected_data_id=collected_data_id,
            start_time=collected_data_starttime,
            end_time=collected_data_endtime,
            evaluation_id=evaluation_code,
            performed_tasks=performedtasksList,
            developer_questionnaire=developer_questionnaire_id,
            navigation=navigation_id
            )
        
        #db.session.add(new_collected_data) # Adiciona a nova coleta ao banco de dados
        #db.session.commit() #envia de fato pro servidor

    return jsonify({"message": "Dados recebidos com sucesso"}), 200



@app.route('/load_tasks', methods=['POST'])
def load_tasks():
    data = request.json # JSON RECEBIDO DA EXTENSÃO
    evaluation_code = data.get("code") # Pega o código do JSON

    # Query no db para verificar se o código existe
    evaluation = Evaluation.query.filter_by(evaluation_id=evaluation_code).first()

    if evaluation:
        guidelines = []
        processes = evaluation.seco_processes
        for p in processes:
            for g in p.guidelines:
                if g not in guidelines: # para nao repetir
                    # Se o guideline não estiver na lista, adicione-o
                    guidelines.append(g)

        tasks = []
        for g in guidelines:
            for t in g.related_tasks:
                if t not in tasks:
                    # Se a tarefa não estiver na lista, adicione-a
                    tasks.append(t)
            
        tasks_data = [
            {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "questions": [
                {
                "text": question.question,
                "question_id": question.question_id
                } for question in task.questions
            ]
            } for task in tasks]
        #print(tasks_data)
        return jsonify(tasks_data), 200
    else:
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