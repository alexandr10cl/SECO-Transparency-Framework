from flask import render_template, request, redirect, session, url_for, jsonify
from index import app, db
from datetime import datetime
from models import (
    User, Task, Evaluation, CollectedData, Guideline, SECO_process,
    PerformedTask, DeveloperQuestionnaire, Navigation, Answer, Question
)
from models.task import task_seco_type
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

    # Idempotency guard: ignore replays of the SAME run (not new runs)
    session_raw = data.get("uxt_sessionId")
    try:
        session_id = int(session_raw) if session_raw is not None else None
    except (TypeError, ValueError):
        session_id = None

    # Use combination of (evaluation, session or cod, start_time, end_time)
    # to detect duplicates of the same evaluation run.
    start_time_iso = data.get("startTime")
    end_time_iso = data.get("endTime")
    existing = None
    if session_id is not None:
        existing = CollectedData.query.filter(
            CollectedData.evaluation_id == evaluation.evaluation_id,
            CollectedData.sessionId == session_id,
            CollectedData.start_time == datetime.fromisoformat(start_time_iso),
            CollectedData.end_time == datetime.fromisoformat(end_time_iso)
        ).first()
    else:
        # Fallback to cod when sessionId is unavailable
        existing = CollectedData.query.filter(
            CollectedData.evaluation_id == evaluation.evaluation_id,
            CollectedData.cod == data.get("uxt_cod"),
            CollectedData.start_time == datetime.fromisoformat(start_time_iso),
            CollectedData.end_time == datetime.fromisoformat(end_time_iso)
        ).first()

    if existing:
        return jsonify({
            "message": "Already submitted. Duplicate ignored.",
            "collected_data_id": existing.collected_data_id
        }), 200


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
            # Converte string para Enum
            if status:
                try:
                    status_enum = PerformedTaskStatus(status)
                except ValueError:
                    status_enum = PerformedTaskStatus.SOLVED  # fallback ou trate como preferir
            else:
                status_enum = PerformedTaskStatus.SOLVED
            

            performed = PerformedTask(
                initial_timestamp    = datetime.fromisoformat(initial_ts),
                final_timestamp      = datetime.fromisoformat(final_ts),
                status               = status_enum,
                task_id              = item.get("task_id"),
                collected_data_id    = collected.collected_data_id,
                comments             = item.get("answer")
            )
            db.session.add(performed)

        elif item.get("type") == "process_review":
            # Convert answer to integer for 0-100 scale
            answer_value = item.get("answer")
            if isinstance(answer_value, str):
                # For backward compatibility, convert old string values
                if answer_value == "yes":
                    answer_value = 100
                elif answer_value == "partial":
                    answer_value = 50
                elif answer_value == "no":
                    answer_value = 0
                else:
                    try:
                        answer_value = int(answer_value)
                    except ValueError:
                        answer_value = 50  # default value
            elif answer_value is None:
                answer_value = 50  # default value
            
            # Persist answer for the selected question_id and any other question rows
            # that share the exact same text (deduplicated display, but full DB coverage)
            qid = item.get("question_id")
            question_row = Question.query.get(qid) if qid is not None else None

            if question_row is None:
                # Fallback: save only for provided question_id
                answer = Answer(
                    answer            = int(answer_value),
                    question_id       = qid,
                    collected_data_id = collected.collected_data_id
                )
                db.session.add(answer)
            else:
                # Find all questions with identical text and save the same answer to each
                same_text_questions = Question.query.filter_by(question=question_row.question).all()
                for q2 in same_text_questions:
                    # Avoid duplicate Answer rows for the same (collected_data, question)
                    existing_ans = Answer.query.filter_by(
                        collected_data_id=collected.collected_data_id,
                        question_id=q2.question_id
                    ).first()
                    if existing_ans is None:
                        db.session.add(Answer(
                            answer            = int(answer_value),
                            question_id       = q2.question_id,
                            collected_data_id = collected.collected_data_id
                        ))

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
    #for nav in data.get("navigation", []):
        #nav_entry = Navigation(
          #  action              = NavigationType(nav.get("action")),
          #  title               = nav.get("title"),
          #  url                 = nav.get("url"),
          #  timestamp           = datetime.fromisoformat(nav.get("timestamp")),
           # task_id             = nav.get("taskId"),
          #  collected_data_id   = collected.collected_data_id
       # )
      #  db.session.add(nav_entry)

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
        evaluation_seco_type = evaluation.seco_type  # Obtém o seco_type da avaliação
        
        seen_question_texts = set()
        for process in evaluation.seco_processes:
            process_obj = {
                "process_id": process.seco_process_id,
                "process_title": process.description,
                "process_tasks": [],
                "process_review": []
            }
            # Filtra tasks associadas ao processo que pertencem ao seco_type da avaliação
            for task in process.tasks:
                # Verifica se a task pertence ao seco_type da avaliação
                task_seco_types = db.session.execute(
                    db.select(task_seco_type.c.seco_type)
                    .where(task_seco_type.c.task_id == task.task_id)
                ).fetchall()
                
                # Se a task tem seco_types definidos, verifica se inclui o da avaliação
                if task_seco_types:
                    task_types = [row[0] for row in task_seco_types]
                    if evaluation_seco_type in task_types:
                        process_obj["process_tasks"].append({
                            "task_id": task.task_id,
                            "task_title": task.title,
                            "task_description": task.description
                        })
                else:
                    # Se a task não tem seco_types definidos, inclui por compatibilidade
                    process_obj["process_tasks"].append({
                        "task_id": task.task_id,
                        "task_title": task.title,
                        "task_description": task.description
                    })
            # Adiciona perguntas de review (questions dos Key Success Criteria das guidelines do processo)
            # Evita duplicatas entre processos por texto de pergunta
            local_seen_texts = set()
            for guideline in process.guidelines:
                for ksc in guideline.key_success_criteria:
                    for question in ksc.questions:
                        if question.question in local_seen_texts:
                            continue
                        local_seen_texts.add(question.question)

                        if question.question in seen_question_texts:
                            # Já exibida em processo anterior nesta avaliação
                            continue

                        seen_question_texts.add(question.question)
                        process_obj["process_review"].append({
                            "process_review_question_text": question.question,
                            "process_review_question_id": question.question_id
                        })
            result.append(process_obj)
        
        print("Resultado:", result)
        return jsonify(result), 200
    else:
        print("Invalid evaluation code:", evaluation_code)
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
