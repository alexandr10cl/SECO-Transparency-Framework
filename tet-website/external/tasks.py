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

    if oi == 0:
        # Gerar um novo ID para CollectedData usando o último registro disponível
        last_collected = db.session.query(CollectedData).order_by(CollectedData.collected_data_id.desc()).first()
        collected_data_id = last_collected.collected_data_id + 1 if last_collected else 1

        # Obter os dados principais da coleta do JSON
        evaluation_code = data.get("evaluation_code") 
        collected_data_starttime = data.get("startTime")
        collected_data_endtime = data.get("endTime")

        # Criar e persistir o registro de CollectedData primeiro
        new_collected_data = CollectedData(
            collected_data_id=collected_data_id,
            start_time=collected_data_starttime,
            end_time=collected_data_endtime,
            evaluation_id=evaluation_code
        )
        db.session.add(new_collected_data)
        db.session.flush()  # Garante que o registro já esteja presente no banco

        performedtasksList = []
        performed_tasks = data.get("performed_tasks", [])

        for task in performed_tasks:
            # Gerar novo ID para PerformedTask
            last_performed = db.session.query(PerformedTask).order_by(PerformedTask.performed_task_id.desc()).first()
            performed_id = last_performed.performed_task_id + 1 if last_performed else 1

            task_id = task.get("id")
            task_start_time = task.get("initial_timestamp")
            task_end_time = task.get("final_timestamp")
            status = task.get("status")

            # Criar a PerformedTask referenciando o CollectedData já persistido
            new_performed_task = PerformedTask(
                performed_task_id=performed_id,
                collected_data_id=collected_data_id,
                initial_timestamp=task_start_time,
                final_timestamp=task_end_time,
                status=status,
                task_id=task_id
            )
            db.session.add(new_performed_task)
            db.session.flush()  # Garante que PerformedTask seja inserida antes de adicionar Answers

            # Processar e inserir cada Answer associada à tarefa
            answers = task.get("answers", [])
            for a in answers:
                task_question = a.get("question_id")
                task_answer = a.get("answer")

                last_answer = db.session.query(Answer).order_by(Answer.answer_id.desc()).first()
                answer_id = last_answer.answer_id + 1 if last_answer else 1

                new_answer = Answer(
                    answer_id=answer_id,
                    answer=task_answer,
                    question_id=task_question,
                    performed_task_id=performed_id  # Agora a PerformedTask já existe no banco
                )
                db.session.add(new_answer)

            performedtasksList.append(performed_id)

        # Commitar todas as PerformedTask e Answers
        db.session.commit()

        # Inserir o DeveloperQuestionnaire
        last_dev = db.session.query(DeveloperQuestionnaire).order_by(DeveloperQuestionnaire.developer_questionnaire_id.desc()).first()
        developer_questionnaire_id = last_dev.developer_questionnaire_id + 1 if last_dev else 1

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
            experience=profile.get("years_of_experience")
        )
        db.session.add(new_developer_questionnaire)
        db.session.commit()

        # Inserir todos os registros de Navigation
        # Navigation
        last_nav = db.session.query(Navigation).order_by(Navigation.navigation_id.desc()).first()
        navigation_id = last_nav.navigation_id + 1 if last_nav else 1

        for nav in data.get("navigation", []):
            new_navigation = Navigation(
                navigation_id=navigation_id,
                action=nav.get("action"),
                title=nav.get("title"),
                url=nav.get("url"),
                timestamp=nav.get("timestamp"),
                task_id=nav.get("taskId"),
                collected_data_id=collected_data_id
            )
            db.session.add(new_navigation)
            navigation_id += 1  # Incrementa para o próximo registro

        db.session.commit()  # Salva todos de uma vez só após o loop

        # Se for necessário atualizar o registro de CollectedData com os IDs das entidades relacionadas,
        # isso pode ser feito, por exemplo, se estes campos forem utilizados para relacionamento manual.
        #new_collected_data.performed_tasks = performedtasksList
        #new_collected_data.developer_questionnaire = developer_questionnaire_id
        # Para navigation, se o campo armazenar apenas um ID ou uma lista, ajuste conforme o modelo

        db.session.add(new_collected_data)
        db.session.commit()

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