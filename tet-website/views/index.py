from flask import render_template, request, redirect, session, url_for, jsonify
from index import app, db
from models import User, Admin, SECO_MANAGER, Evaluation, SECO_process, Question, DeveloperQuestionnaire, SECO_dimension
from functions import isLogged, isAdmin
from datetime import datetime
import random as rd
import requests
import os

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
                'status': None
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
            "title": info["title"],
            "comments": info["comments"],
            "avg_time": avg_time,
            "completion_rate": completion_rate
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
    
    # Distribuir guidelines entre categorias DX (mantive sua lógica atual)
    for idx, g_result in enumerate(result):
        if g_result['average_score'] is not None:
            if idx % 4 == 0:
                dx_categories['common_technological_platform']['guidelines'].append(g_result['average_score'])
            elif idx % 4 == 1:
                dx_categories['projects_and_applications']['guidelines'].append(g_result['average_score'])
            elif idx % 4 == 2:
                dx_categories['community_interaction']['guidelines'].append(g_result['average_score'])
            else:
                dx_categories['expectations_and_value']['guidelines'].append(g_result['average_score'])
    
    # Calcular média para cada categoria DX
    for category in dx_categories.values():
        if category['guidelines']:
            category['score'] = round(sum(category['guidelines']) / len(category['guidelines']))
        else:
            category['score'] = 0

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
                            result=result,
                            score_geral=score_geral,
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