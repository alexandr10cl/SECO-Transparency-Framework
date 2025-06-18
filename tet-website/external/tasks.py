from flask import render_template, request, redirect, session, url_for, jsonify
from app import app, db
from datetime import datetime
from models import (
    User, Task, Evaluation, CollectedData, Guideline, SECO_process,
    PerformedTask, DeveloperQuestionnaire, Navigation, Answer, Question
)
from models.enums import (
    PerformedTaskStatus, NavigationType, AcademicLevel,
    SegmentType, PreviousExperience
)
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
def submit_tasks():
    data = request.get_json(force=True)
    print("Dados recebidos:", data)

    # Busca a avaliação pelo código
    evaluation = Evaluation.query.filter_by(evaluation_id=data.get("evaluation_code")).first()
    if not evaluation:
        return jsonify({"error": "Evaluation not found"}), 404


    # Cria o objeto CollectedData
    collected = CollectedData(
        start_time    = datetime.fromisoformat(data.get("startTime")),
        end_time      = datetime.fromisoformat(data.get("endTime")),
        evaluation_id = evaluation.evaluation_id,
        cod = data.get("uxt_cod"),
        sessionId = data.get("uxt_sessionId")
    )
    db.session.add(collected)
    db.session.flush()  # para gerar collected_data_id

    # Salva cada tarefa executada
    for item in data.get("performed_tasks", []):
        if item.get("type") == "task_review":
            initial_ts = item.get("initialTimestamp") or data.get("startTime")
            final_ts   = item.get("finalTimestamp")   or data.get("endTime")
            status = item.get("status")
            

            performed = PerformedTask(
                initial_timestamp    = datetime.fromisoformat(initial_ts),
                final_timestamp      = datetime.fromisoformat(final_ts),
                status               = status,
                task_id              = item.get("task_id"),
                collected_data_id    = collected.collected_data_id,
                comments             = item.get("answer")
            )
            db.session.add(performed)

        elif item.get("type") == "process_review":
            answer = Answer(
                answer              = item.get("answer"),
                question_id         = item.get("question_id"),
                collected_data_id   = collected.collected_data_id
            )
            db.session.add(answer)

    # Salva o questionário do desenvolvedor
    prof = data.get("profile_questionnaire", {})
    fin  = data.get("final_questionnaire", {})

    dev_q = DeveloperQuestionnaire(
        academic_level      = AcademicLevel(prof.get("academic_level")),
        segment             = SegmentType(prof.get("segment")),
        previus_xp          = PreviousExperience(prof.get("previus_experience")),
        experience          = int(prof.get("years_of_experience")) if prof.get("years_of_experience") else None,
        emotion             = int(fin.get("emotion", 0)),
        comments            = fin.get("comments", ""),
        collected_data_id   = collected.collected_data_id
    )
    db.session.add(dev_q)

    # Salva a navegação (caso exista)
    for nav in data.get("navigation", []):
        nav_entry = Navigation(
            action              = NavigationType(nav.get("action")),
            title               = nav.get("title"),
            url                 = nav.get("url"),
            timestamp           = datetime.fromisoformat(nav.get("timestamp")),
            task_id             = nav.get("taskId"),
            collected_data_id   = collected.collected_data_id
        )
        db.session.add(nav_entry)

    db.session.commit()
    return jsonify({"message": "Dados recebidos e salvos com sucesso"}), 200


@app.route('/get_data/<evaluation_id>', methods=['GET'])
def get_data(evaluation_id):
    evaluation = Evaluation.query.filter_by(evaluation_id=evaluation_id).first()
    if not evaluation:
        return jsonify({"error": "Evaluation not found"}), 404

    # Busca todos os registros CollectedData vinculados a essa avaliação
    collected_list = CollectedData.query.filter_by(evaluation_id=evaluation_id).all()

    result = []
    for col in collected_list:
        collected_dict = {
            "collected_data_id": col.collected_data_id,
            "start_time": col.start_time.isoformat(),
            "end_time": col.end_time.isoformat(),
            "performed_tasks": [],
            "process_answers": [],
            "developer_questionnaire": None,
            # "navigation": []  
        }

        # Tarefas executadas
        tasks = PerformedTask.query.filter_by(collected_data_id=col.collected_data_id).all()
        for t in tasks:
            collected_dict["performed_tasks"].append({
                "task_id": t.task_id,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "initial_timestamp": t.initial_timestamp.isoformat(),
                "final_timestamp": t.final_timestamp.isoformat(),
                "comments": t.comments
            })

        # Respostas do processo
        answers = Answer.query.filter_by(collected_data_id=col.collected_data_id).all()
        for a in answers:
            collected_dict["process_answers"].append({
                "question_id": a.question_id,
                "answer": a.answer
            })

        # Questionário do desenvolvedor
        devq = DeveloperQuestionnaire.query.filter_by(collected_data_id=col.collected_data_id).first()
        if devq:
            collected_dict["developer_questionnaire"] = {
                "academic_level": devq.academic_level.value if hasattr(devq.academic_level, "value") else devq.academic_level,
                "segment": devq.segment.value if hasattr(devq.segment, "value") else devq.segment,
                "previus_xp": devq.previus_xp.value if hasattr(devq.previus_xp, "value") else devq.previus_xp,
                "experience": devq.experience,
                "emotion": devq.emotion,
                "comments": devq.comments
            }

        # Navegação
        # navs = Navigation.query.filter_by(collected_data_id=col.collected_data_id).all()
        # collected_dict["navigation"] = [{
        #     "action": n.action.value if hasattr(n.action, "value") else n.action,
        #     "url": n.url,
        #     "title": n.title,
        #     "timestamp": n.timestamp.isoformat(),
        #     "task_id": n.task_id
        # } for n in navs]

        result.append(collected_dict)

    return jsonify(result), 200





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