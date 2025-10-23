from flask import render_template, request, redirect, session, url_for, jsonify
from index import app, db
from models import User, Admin, SECO_MANAGER, Evaluation, SECO_process, Question, DeveloperQuestionnaire, SECO_dimension, SECOType, Guideline, DX_factor
from functions import isLogged, isAdmin
from datetime import datetime
import random as rd
import requests
import os
from sqlalchemy.exc import IntegrityError
from secrets import token_urlsafe
from flask import session

# Credenciais do administrador (ideal substituir por um sistema de autenticação mais seguro)
credenciais_admin = {
    "email": os.getenv('ADMIN_EMAIL'),
    "password": os.getenv('ADMIN_PASSWORD')
}

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

    # DEBUG: Check table columns in real-time
    from sqlalchemy import inspect, text

    print("\n" + "="*60)
    print("DEBUG: CHECKING DATABASE TABLE STRUCTURE")
    print("="*60)

    # Method 1: Check via SQLAlchemy inspector
    try:
        inspector = inspect(db.engine)
        columns = inspector.get_columns('evaluation')
        column_names = [col['name'] for col in columns]
        print(f"Columns in 'evaluation' table (via inspector): {column_names}")
        print(f"Has 'manager_objective'? {'manager_objective' in column_names}")
    except Exception as e:
        print(f"Error inspecting table: {e}")

    # Method 2: Direct SQL query
    try:
        result = db.session.execute(text("SHOW COLUMNS FROM evaluation"))
        columns = [row[0] for row in result]
        print(f"Columns via SHOW COLUMNS: {columns}")
        print(f"Has 'manager_objective'? {'manager_objective' in columns}")
    except Exception as e:
        print(f"Error with SHOW COLUMNS: {e}")

    # Method 3: Check the model mapping
    try:
        mapper = inspect(Evaluation)
        model_columns = [column.key for column in mapper.columns]
        print(f"Columns in Evaluation model: {model_columns}")
        print(f"Model has 'manager_objective'? {'manager_objective' in model_columns}")
    except Exception as e:
        print(f"Error inspecting model: {e}")

    print("="*60 + "\n")

    evaluations = user.evaluations
    return render_template('evaluations.html', evaluations=evaluations)

@app.route('/evaluations/create_evaluation', methods=['GET'])
def create_evaluation():
    email = session.get('user_signed_in')
    user = User.query.filter_by(email=email).first() if email else None
    seco_processes = SECO_process.query.all()

    token = token_urlsafe(16)
    session['eval_form_token'] = token

    return render_template(
        'create_evaluation.html',
        user=user,
        seco_processes=seco_processes,
        form_token=token,
        seco_types=SECOType 
    )



@app.route('/evaluations/create_evaluation/add_evaluation', methods=['POST'])
def add_evaluation():
    # local imports for this handler
    from sqlalchemy.exc import IntegrityError
    import random as rd
    import requests

    # DEBUG: Check if Evaluation model has manager_objective attribute
    print("\n" + "="*60)
    print("DEBUG: CHECKING EVALUATION MODEL")
    print("="*60)
    print(f"Evaluation model attributes: {dir(Evaluation)}")
    print(f"Has manager_objective? {'manager_objective' in dir(Evaluation)}")

    # Try to check the column directly
    try:
        from sqlalchemy import inspect
        mapper = inspect(Evaluation)
        columns = [column.key for column in mapper.columns]
        print(f"Database columns for Evaluation: {columns}")
        print(f"manager_objective in columns? {'manager_objective' in columns}")
    except Exception as e:
        print(f"Could not inspect model: {e}")
    print("="*60 + "\n")

    # one-time form token check
    token = request.form.get('form_token')
    saved = session.pop('eval_form_token', None)
    if not token or token != saved:
        return redirect(url_for('evaluations'))

    # read form data
    name = request.form.get('name', '').strip()
    seco_portal = request.form.get('seco_portal', '').strip()
    seco_portal_url = request.form.get('seco_portal_url', '').strip()
    seco_process_ids = request.form.getlist('seco_process_ids')
    seco_type_str = request.form.get('seco_type')
    manager_objective = request.form.get('manager_objective', '').strip()

    # DEBUG: Print all form data received
    print("\n" + "="*60)
    print("DEBUG: FORM DATA RECEIVED")
    print("="*60)
    print(f"Name: '{name}'")
    print(f"SECO Portal: '{seco_portal}'")
    print(f"SECO Portal URL: '{seco_portal_url}'")
    print(f"SECO Type: '{seco_type_str}'")
    print(f"Manager Objective: '{manager_objective}'")
    print(f"Manager Objective Length: {len(manager_objective)} characters")
    print(f"Process IDs: {seco_process_ids}")
    print("\nAll form fields:")
    for key, value in request.form.items():
        print(f"  {key}: {value}")
    print("="*60 + "\n")

    seco_type = SECOType(seco_type_str)

    # must select at least one process
    if not seco_process_ids:
        values = {
            "name": name,
            "seco_portal": seco_portal,
            "seco_portal_url": seco_portal_url,
            "seco_type": seco_type_str,
            "manager_objective": manager_objective
        }
        error_msg = "Please select at least one process"
        seco_processes = SECO_process.query.all()
        return render_template(
            "create_evaluation.html",
            user=user,
            seco_processes=seco_processes,
            values=values,
            error_msg=error_msg,
            form_token=token,  # pass the token again
            seco_types=SECOType
        )


    # resolve user
    email = session.get('user_signed_in')
    if not email:
        return redirect(url_for('signin'))
    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('signin'))

    # prevent duplicate by content
    existing = Evaluation.query.filter_by(
        name=name,
        seco_portal=seco_portal,
        seco_portal_url=seco_portal_url,
        user_id=user.user_id
    ).first()
    if existing:
        return redirect(url_for('evaluations'))

    # generate evaluation_id via UXT API, fallback to unique 6-digit
    evaluation_id = None
    access_token = session.get('uxt_access_token')

    print(f"=== LOG: Iniciando geração de código de avaliação ===")
    print(f"LOG: Access token disponível: {bool(access_token)}")
    if access_token:
        print(f"LOG: Access token: {access_token[:20]}...")  # Mostra só os primeiros caracteres por segurança

    if access_token:
        try:
            print(f"LOG: Fazendo chamada para API UXT...")
            r = requests.post(
                'https://uxt-stage.liis.com.br/generate-code?horas=730',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            print(f"LOG: Resposta da API UXT - Status: {r.status_code}")
            print(f"LOG: Resposta da API UXT - Conteúdo: {r.text}")

            if r.status_code == 201:
                data = r.json() or {}
                evaluation_id = data.get('cod')
                print(f"LOG: Código gerado pela API UXT: {evaluation_id}")
            else:
                print(f"LOG: API UXT não retornou status 201. Status: {r.status_code}")
        except Exception as e:
            print(f"LOG: ERRO ao chamar API UXT: {str(e)}")
            evaluation_id = None
    else:
        print(f"LOG: Sem access token disponível, usando fallback")

    if not evaluation_id:
        print(f"LOG: Usando geração aleatória de código (fallback)")
        while True:
            if Evaluation.query.filter_by(evaluation_id=evaluation_id).first() is None:
                break

    if r and r.status_code == 201 and evaluation_id:

        # map selected processes
        seco_processes = []
        if seco_process_ids:
            seco_processes = SECO_process.query.filter(
                SECO_process.seco_process_id.in_(seco_process_ids)
            ).all()

        # create and save
        print("\n" + "="*60)
        print("DEBUG: CREATING EVALUATION OBJECT")
        print("="*60)
        print(f"evaluation_id: {evaluation_id}")
        print(f"name: {name}")
        print(f"user_id: {user.user_id}")
        print(f"seco_portal: {seco_portal}")
        print(f"seco_portal_url: {seco_portal_url}")
        print(f"seco_type: {seco_type}")
        print(f"manager_objective: '{manager_objective}'")
        print(f"manager_objective is empty? {not manager_objective}")
        print(f"Number of processes: {len(seco_processes)}")

        new_evaluation = Evaluation(
            evaluation_id=evaluation_id,
            name=name,
            user_id=user.user_id,
            seco_processes=seco_processes,
            seco_portal=seco_portal,
            seco_portal_url=seco_portal_url,
            seco_type=seco_type,
            manager_objective=manager_objective
        )

        print("\nDEBUG: Evaluation object created")
        print(f"Object manager_objective: '{new_evaluation.manager_objective}'")

        try:
            print("\nDEBUG: Adding to session...")
            db.session.add(new_evaluation)

            print("DEBUG: Committing to database...")
            db.session.commit()

            print("DEBUG: SUCCESS! Evaluation saved to database")
            print(f"Saved evaluation ID: {new_evaluation.evaluation_id}")

            # Verify it was saved correctly
            saved_eval = Evaluation.query.filter_by(evaluation_id=evaluation_id).first()
            if saved_eval:
                print(f"\nDEBUG: VERIFICATION - Evaluation found in database")
                print(f"  - ID: {saved_eval.evaluation_id}")
                print(f"  - Name: {saved_eval.name}")
                print(f"  - Manager Objective: '{saved_eval.manager_objective}'")
                print(f"  - Manager Objective is None? {saved_eval.manager_objective is None}")
                print(f"  - Manager Objective is empty string? {saved_eval.manager_objective == ''}")
            else:
                print("\nDEBUG: WARNING - Could not find evaluation in database after save!")

        except IntegrityError as e:
            print(f"\nDEBUG: ERROR - IntegrityError occurred: {str(e)}")
            db.session.rollback()
            return redirect(url_for('evaluations'))
        except Exception as e:
            print(f"\nDEBUG: ERROR - Unexpected error: {type(e).__name__}: {str(e)}")
            db.session.rollback()
            return redirect(url_for('evaluations'))

        print("="*60 + "\n")

    return redirect(url_for('evaluations'))


@app.route('/evaluations/<int:id>/edit')
def edit_evaluation(id):
    email = session['user_signed_in']
    user = User.query.filter_by(email=email).first()
    evaluation = Evaluation.query.get_or_404(id)
    seco_processes = SECO_process.query.all()
    return render_template('edit_evaluation.html', evaluation=evaluation, user=user, seco_processes=seco_processes, seco_types=SECOType)

@app.route('/evaluations/<int:id>/update', methods=['POST'])
def update_evaluation(id):
    # getting the form data
    name = request.form.get('name')
    seco_portal = request.form.get('seco_portal')
    seco_portal_url = request.form.get('seco_portal_url')
    seco_type_str = request.form.get('seco_type')
    manager_objective = request.form.get('manager_objective', '')

    try:
        seco_type = SECOType(seco_type_str)
    except Exception:
        seco_type = None
    
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
    evaluation.seco_type = seco_type
    evaluation.manager_objective = manager_objective 
    
    # committing the changes to the database
    db.session.commit()

    # redirecting to the evaluations page
    return redirect(url_for('evaluation', id=id))

@app.route('/evaluations/<int:id>/delete')
def delete_evaluation(id):
    evaluation = Evaluation.query.get_or_404(id)
    
    # Delete all related objects tied to this evaluation's collected data
    for c in evaluation.collected_data:
        # Answers are linked to CollectedData (not PerformedTask)
        for a in c.answers:
            db.session.delete(a)

        # Delete navigation events tied to this CollectedData
        for n in c.navigation:
            db.session.delete(n)

        # Delete performed tasks tied to this CollectedData
        for p in c.performed_tasks:
            db.session.delete(p)

        # Delete developer questionnaire if present
        if getattr(c, 'developer_questionnaire', None):
            db.session.delete(c.developer_questionnaire)

        # Finally, delete the collected data record itself
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
    
    # Build procedure-organized data structure
    procedures_data = []
    all_guidelines = []
    all_tasks = []
    
    for process in seco_processes:
        # Get guideline for this process (1:1 relationship)
        guideline = process.guidelines[0] if process.guidelines else None
        
        # Get tasks for this process
        process_tasks = process.tasks
        
        # Build procedure data structure
        procedure_data = {
            'process': process,
            'guideline': guideline,
            'tasks': process_tasks
        }
        procedures_data.append(procedure_data)
        
        # Collect all guidelines and tasks for backward compatibility
        if guideline and guideline not in all_guidelines:
            all_guidelines.append(guideline)
        for task in process_tasks:
            if task not in all_tasks:
                all_tasks.append(task)
    
    # Renumber collected data per evaluation
    collected_data_renumbered = []
    for i, data in enumerate(collected_data, 1):
        collected_data_renumbered.append({
            'display_name': f'Collect {i}',
            'original_id': data.collected_data_id,
            'data': data
        })
                
    count_collected_data = len(collected_data)

    return render_template('eval.html', 
                         evaluation=evaluation, 
                         user=user, 
                         seco_processes=seco_processes, 
                         count_collected_data=count_collected_data, 
                         guidelines=all_guidelines, 
                         tasks=all_tasks, 
                         collected_data=collected_data_renumbered, 
                         questions=questions,
                         procedures_data=procedures_data)

@app.route('/eval_dashboard/<int:id>')
def eval_dashboard(id):
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
    
    # CORREÇÃO: construir lista de dimensões corretamente (adiciona cada dimensão, não a lista inteira)
    g_dimensions = []
    for g in guidelines:
        for d in g.seco_dimensions:
            if d not in g_dimensions:
                g_dimensions.append(d)
                
    # agora g_dimensions já é flat
    g_dimensions_flat = g_dimensions
    
    
    eName = evaluation.name
    eId = evaluation.evaluation_id
    ePortal = evaluation.seco_portal
    ePortalUrl = evaluation.seco_portal_url
    
    dimensions = SECO_dimension.query.all()
    
    # Criar lista de IDs dos collected_data desta avaliação
    evaluation_collected_data_ids = [cd.collected_data_id for cd in collected_data]
    
    # Helper: parseia resposta para 0..1 (numeric) ou None
    def parse_answer_to_fraction(ans):
        """
        Aceita int, float, '50', '50.0', '50%', '0.5', 'yes', 'partial', 'no'
        Retorna float entre 0.0 e 1.0 ou None se inválido.
        """
        if ans is None:
            return None

        # se já é número
        if isinstance(ans, (int, float)):
            v = float(ans)
            if 0.0 <= v <= 1.0:
                return v
            if 0.0 <= v <= 100.0:
                return v / 100.0
            return None

        # string: tenta interpretar
        if isinstance(ans, str):
            s = ans.strip().lower()
            # antigos tokens
            if s in ('yes', 'y', 'sim'):
                return 1.0
            if s in ('partial', 'parcial'):
                return 0.5
            if s in ('no', 'n', 'não', 'nao'):
                return 0.0
            # remove '%' e tenta converter
            s_clean = s.rstrip('%')
            try:
                v = float(s_clean)
            except ValueError:
                return None
            if 0.0 <= v <= 1.0:
                return v
            if 0.0 <= v <= 100.0:
                return v / 100.0
            return None

        # fallback
        try:
            v = float(ans)
            if 0.0 <= v <= 1.0:
                return v
            if 0.0 <= v <= 100.0:
                return v / 100.0
        except Exception:
            return None

        return None

    # Processar pontuação dos ksc e guidelines
    result = []

    for g in guidelines:
        g_data = {
            'title': g.title,
            'description': g.description,
            'key_success_criteria': [],
            'average_score': None,
            'status': None
        }

        ksc_scores = []

        for ksc in g.key_success_criteria:
            total_score = 0.0
            total_answers = 0

            ksc_data = {
                'title': ksc.title,
                'description': ksc.description,
                'questions': [],
                'porcentagem': None,
                'score': None,
                'status': None,
                'examples': []
            }

            for question in ksc.questions:
                question_data = {
                    'question': question.question,
                    'answers': []
                }

                # Filtrar apenas respostas desta avaliação
                for answer in question.answers:
                    # Verificar se a resposta pertence a esta avaliação
                    if answer.collected_data_id not in evaluation_collected_data_ids:
                        continue  # Pular respostas de outras avaliações

                    parsed = parse_answer_to_fraction(answer.answer)
                    if parsed is None:
                        continue  # ignora respostas inválidas

                    score = parsed  # 0..1
                    display_value = f"{round(score * 100)} / 100"

                    total_score += score
                    total_answers += 1
                    question_data['answers'].append(display_value)

                ksc_data['questions'].append(question_data)

            # Score individual do KSC
            if total_answers > 0:
                final_score = total_score / total_answers
                ksc_data['score'] = round(final_score, 2)
                ksc_scores.append(final_score)
                ksc_data['porcentagem'] = round(final_score * 100, 2)

                if final_score >= 0.75:
                    ksc_data['status'] = "Fulfilled"
                elif final_score >= 0.5:
                    ksc_data['status'] = "Partially Fulfilled"
                else:
                    ksc_data['status'] = "Not Fulfilled"
            else:
                ksc_data['score'] = None
                ksc_data['status'] = "No Answers"

            # Adicionar exemplos para KSC "Not Fulfilled" e "Partially Fulfilled"
            if ksc_data['status'] in ["Not Fulfilled", "Partially Fulfilled"]:
                for example in ksc.examples:
                    ksc_data['examples'].append({
                        'description': example.description
                    })

            g_data['key_success_criteria'].append(ksc_data)

        # Score médio da guideline
        if ksc_scores:
            avg = sum(ksc_scores) / len(ksc_scores)
            g_data['average_score'] = round(avg * 100, 2)
            if avg >= 0.75:
                g_data['status'] = "Fulfilled"
            elif avg >= 0.5:
                g_data['status'] = "Partially Fulfilled"
            else:
                g_data['status'] = "Not Fulfilled"
        else:
            g_data['status'] = "No Answers"

        result.append(g_data)

    scores_guideline = []
    
    for i in result:
        # Excluir guidelines sem respostas (None) do cálculo
        if i['average_score'] is not None:
            scores_guideline.append(i['average_score'])
    
    # Calcular score_geral apenas se houver scores válidos    
    if scores_guideline:
        score_geral = round(sum(scores_guideline) / len(scores_guideline))
    else:
        score_geral = 0  # ou None, dependendo de como você quer tratar quando não há dados

    # Processamento das tasks para facilitar o jinja
    # Reunir tasks únicas
    task_map = {}  # task_id → { title, comments[], avg_time, completion_rate }

    for data in collected_data:
        for pt in data.performed_tasks:
            task_id = pt.task_id
            task_title = pt.task.title

            # tempo em segundos (proteção básica)
            try:
                exec_time = (pt.final_timestamp - pt.initial_timestamp).total_seconds()
            except Exception:
                exec_time = 0

            if task_id not in task_map:
                task_map[task_id] = {
                    "title": task_title,
                    "comments": [],
                    "times": [],
                    "solved_count": 0,
                    "total_count": 0,
                }

            task_info = task_map[task_id]
            if getattr(pt, "comments", None):
                task_info["comments"].append(pt.comments)

            task_info["times"].append(exec_time)
            task_info["total_count"] += 1
            # proteção contra pt.status ser None
            if getattr(pt, "status", None) and getattr(pt.status, "name", None) == "SOLVED":
                task_info["solved_count"] += 1

    # Processar média de tempo e taxa de completude
    processed_tasks = []
    for task_id, info in task_map.items():
        avg_time = round(sum(info["times"]) / len(info["times"]), 2) if info["times"] else 0
        completion_rate = round((info["solved_count"] / info["total_count"]) * 100, 1) if info["total_count"] > 0 else 0

        processed_tasks.append({
            "task_id": task_id,
            "title": info["title"],
            "comments": info["comments"],
            "avg_time": avg_time,
            "completion_rate": completion_rate
        })

    # Agrupar tasks por SECO process (para desktop layout mais informativo)
    # Mapa de task_id -> lista de process_ids
    task_to_process = {}
    for p in evaluation.seco_processes:
        for t in p.tasks:
            task_to_process.setdefault(t.task_id, []).append(p.seco_process_id)

    # Índice rápido de processed_tasks por id
    processed_by_id = {t["task_id"]: t for t in processed_tasks}

    tasks_by_process = []
    seen_in_process = set()
    for p in evaluation.seco_processes:
        section_tasks = []
        for t in p.tasks:
            pt = processed_by_id.get(t.task_id)
            if pt:
                section_tasks.append(pt)
                seen_in_process.add(pt["task_id"])
        tasks_by_process.append({
            "process_id": p.seco_process_id,
            "process_title": p.description,
            "tasks": section_tasks,
        })

    # Qualquer task realizada que não esteja associada a um processo da avaliação
    uncategorized = [pt for pt in processed_tasks if pt["task_id"] not in seen_in_process]
    if uncategorized:
        tasks_by_process.append({
            "process_id": 0,
            "process_title": "Other Tasks",
            "tasks": uncategorized,
        })
        
    dimension_scores = []
        
    for d in g_dimensions_flat:
        
        dim_data = {
            'id': d.seco_dimension_id,
            'name': d.name,
            'guidelines': [],
            'average_score': None,
        }
        
        scores = []
        
        for g in d.guidelines:
            g_result = next((item for item in result if item['title'] == g.title), None)
            if g_result and g_result['average_score'] is not None:
                dim_data['guidelines'].append(g_result)
                scores.append(g_result['average_score'])
                
        if scores:
            dim_data['average_score'] = round(sum(scores) / len(scores))
            
        dimension_scores.append(dim_data)
    
    # DX_factor ID to category mapping (same as evaluation details)
    dx_factor_categories = {
        # Common Technological Platform
        1: 'common_technological_platform',   # Desired technical resources for development
        2: 'common_technological_platform',   # Easy to configure platform
        5: 'common_technological_platform',   # Platform transparency
        6: 'common_technological_platform',   # Documentation quality
        7: 'common_technological_platform',   # Existence of communication channels
        8: 'common_technological_platform',   # Platform openness level
        26: 'common_technological_platform',  # Qualities and characteristics of platform

        # Projects and Applications
        9: 'projects_and_applications',       # More clients/users for applications
        10: 'projects_and_applications',     # Application distribution methods
        11: 'projects_and_applications',     # Application interface and appearance standards
        12: 'projects_and_applications',     # Requirements for developing applications
        13: 'projects_and_applications',     # Ease of learning about technology
        14: 'projects_and_applications',     # Low barriers to entry into applications market

        # Community Interaction
        15: 'community_interaction',         # Obtaining community recognition
        16: 'community_interaction',         # Commitment to the community
        17: 'community_interaction',         # A good relationship with the community
        18: 'community_interaction',         # Knowledge exchange between community developers
        19: 'community_interaction',         # A good developer relations program
        20: 'community_interaction',         # Community size and scalability

        # Expectations and Value
        3: 'expectations_and_value',         # Financial costs for using the platform
        21: 'expectations_and_value',        # Emergence of new market and job opportunities
        22: 'expectations_and_value',        # More financial gains
        23: 'expectations_and_value',        # Fun while developing
        24: 'expectations_and_value',        # Improvement of developer skills and intellect
        25: 'expectations_and_value',        # Autonomy and self-control of workflow
        27: 'expectations_and_value'         # Engagement and rewards for work
    }

    # Calcular pontuações para Developer Experience Categories
    dx_categories = {
        'common_technological_platform': {
            'name': 'Common Technological Platform',
            'guidelines': [],
            'score': None
        },
        'projects_and_applications': {
            'name': 'Projects and Applications', 
            'guidelines': [],
            'score': None
        },
        'community_interaction': {
            'name': 'Community Interaction',
            'guidelines': [],
            'score': None
        },
        'expectations_and_value': {
            'name': 'Expectations and Value of Contribution',
            'guidelines': [],
            'score': None
        }
    }
    
    # Distribuir guidelines entre categorias DX usando mapeamento baseado em DX_factors
    for g_result in result:
        if g_result['average_score'] is not None:
            # Buscar a guideline completa para obter seus DX_factors
            guideline_obj = next((g for g in guidelines if g.title == g_result['title']), None)

            if guideline_obj:
                # Coletar categorias únicas para esta guideline
                guideline_categories = set()
                for dx_factor in guideline_obj.dx_factors:
                    category = dx_factor_categories.get(dx_factor.dx_factor_id)
                    if category:
                        guideline_categories.add(category)

                # Adicionar score apenas uma vez para cada categoria única
                for category in guideline_categories:
                    dx_categories[category]['guidelines'].append(g_result['average_score'])
            else:
                # Fallback: distribuição equilibrada als niet kan mappen
                hash_value = hash(g_result['title']) % 4
                category_keys = list(dx_categories.keys())
                dx_categories[category_keys[hash_value]]['guidelines'].append(g_result['average_score'])
    
    # Calcular média para cada categoria DX
    for category in dx_categories.values():
        if category['guidelines']:
            category['score'] = round(sum(category['guidelines']) / len(category['guidelines']))
        else:
            category['score'] = 0

    # Função helper para determinar badge de transparência
    def get_transparency_badge(score):
        if score is None or score == 0:
            return "No Procedures"
        elif score >= 75:
            return "Good Transparency"
        elif score >= 50:
            return "Moderate Transparency"
        else:
            return "Bad Transparency"

    # Adicionar badges de transparência
    transparency_badge_overall = get_transparency_badge(score_geral)

    for dim in dimension_scores:
        dim['transparency_badge'] = get_transparency_badge(dim['average_score'])

    for category in dx_categories.values():
        category['transparency_badge'] = get_transparency_badge(category['score'])

    # Calcular scores por procedure para cada dimensão
    for dim in dimension_scores:
        dim['procedure_scores'] = {}
        for process in seco_processes:
            process_id = process.seco_process_id
            process_guidelines_scores = []

            for g in process.guidelines:
                if any(d.seco_dimension_id == dim['id'] for d in g.seco_dimensions):
                    g_result = next((item for item in result if item['title'] == g.title), None)
                    if g_result and g_result['average_score'] is not None:
                        process_guidelines_scores.append(g_result['average_score'])

            if process_guidelines_scores:
                dim['procedure_scores'][f'P{process_id}'] = round(sum(process_guidelines_scores) / len(process_guidelines_scores))
            else:
                dim['procedure_scores'][f'P{process_id}'] = 0

    # Calcular scores por procedure para categorias DX usando mapeamento gebaseerd op DX_factors
    for category_key, category in dx_categories.items():
        category['procedure_scores'] = {}

        for process in seco_processes:
            process_id = process.seco_process_id
            process_guidelines_scores = []

            # Mapear guidelines van dit proces naar de DX categorie
            for g in process.guidelines:
                g_result = next((item for item in result if item['title'] == g.title), None)
                if g_result and g_result['average_score'] is not None:
                    # Controleren of een DX_factor van deze guideline tot de categorie behoort
                    guideline_belongs_to_category = False
                    for dx_factor in g.dx_factors:
                        if dx_factor_categories.get(dx_factor.dx_factor_id) == category_key:
                            guideline_belongs_to_category = True
                            break

                    if guideline_belongs_to_category:
                        process_guidelines_scores.append(g_result['average_score'])

            if process_guidelines_scores:
                category['procedure_scores'][f'P{process_id}'] = round(sum(process_guidelines_scores) / len(process_guidelines_scores))
            else:
                category['procedure_scores'][f'P{process_id}'] = 0

    return render_template('dashboard.html',
                            evaluation=evaluation,
                            user=user,
                            seco_processes=seco_processes,
                            count_collected_data=count_collected_data,
                            guidelines=guidelines,
                            tasks=tasks,
                            collected_data=collected_data,
                            questions=questions,
                            eName=eName,
                            eId=eId,
                            ePortal=ePortal,
                            ePortalUrl=ePortalUrl,
                            dimensions=dimensions,
                            processed_tasks=processed_tasks,
                            tasks_by_process=tasks_by_process,
                            result=result,
                            score_geral=score_geral,
                            transparency_badge_overall=transparency_badge_overall,
                            g_dimensions=g_dimensions_flat,
                            dimension_scores=dimension_scores,
                            dx_categories=dx_categories)
    

@app.route('/view_heatmap/<int:id>')
def view_heatmap(id):
    email = session['user_signed_in']
    user = User.query.filter_by(email=email).first()
    evaluation = Evaluation.query.get_or_404(id)
    
    return render_template('heatmaps.html', evaluation=evaluation, user=user, id=id)
    
    # # Obter Token de administrador para mudar a role
    # uxt_admin_login_url = 'https://uxt-stage.liis.com.br/auth/login'

    # resposta_admin = requests.post(uxt_admin_login_url, json=credenciais_admin)
    # if resposta_admin.status_code == 200:
    #     token = resposta_admin.json().get("access_token")
        
    #     url_gethm = 'https://uxt-stage.liis.com.br/view/heatmap/code/{id}'
    
    #     headers_admin = {
    #                 'Authorization': f'Bearer {token}'
    #             }
        
    #     resposta_heatmap = requests.get(url_gethm.format(id=evaluation.evaluation_id), headers=headers_admin)
        
    #     if resposta_heatmap.status_code == 200:
    #         heatmap_data = resposta_heatmap.json()
    #         # print(f"[UXT] Heatmap data for evaluation {evaluation.evaluation_id}: {type(jsonhm)}")

    #         heat_maps = []
    #         # print(type(jsonhm))

    #         # Se heatmap_data for um dicionário com a chave "page_images"
    #         for item in heatmap_data:
    #             page_images = item.get("page_images", [])
    #             for i in page_images:
    #                 if isinstance(i, dict):
    #                     heat_maps.append({
    #                         "height": i.get("height"),
    #                         "image": i.get("image"),
    #                         "points": i.get("points"),
    #                         "scroll_positions": i.get("scroll_positions"),
    #                         "url": i.get("url"),
    #                         "width": i.get("width")
    #                     })
    #                     print(f"Heatmap data: {i['height']}, {i['width']}, {i['points']}, {i['scroll_positions']}, {i['url']}")
    #             else:
    #                 heat_maps.append(i)
                
    #             print('teste')
            
    #         return render_template('heatmaps.html',heat_maps=heat_maps)
    #     else:
    #         print(f"[UXT] Error fetching heatmap data: {resposta_heatmap.text}")
    #         return jsonify({"error": "Failed to fetch heatmap data"}), 500
