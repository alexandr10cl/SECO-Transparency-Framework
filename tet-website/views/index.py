from flask import render_template, request, redirect, session, url_for, jsonify, abort, flash, current_app
from index import app, db
from models import (
    User, Admin, SECO_MANAGER, Evaluation, SECO_process, Question, 
    DeveloperQuestionnaire, SECO_dimension, SECOType, Guideline, DX_factor, 
    EvaluationCriterionWheight, CollectedData, PerformedTask, Answer, 
    Navigation, Task
)
from functions import isLogged, isAdmin, login_required  # Fix #3: Import login_required decorator
from datetime import datetime
import random as rd
import requests
import os
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from secrets import token_urlsafe
from services.heatmap_prefetch import schedule_heatmap_prefetch

# Performance: Import eager loading for optimized queries
from sqlalchemy.orm import joinedload, selectinload, contains_eager
from functools import lru_cache

# Credenciais do administrador (ideal substituir por um sistema de autenticação mais seguro)
credenciais_admin = {
    "email": os.getenv('ADMIN_EMAIL'),
    "password": os.getenv('ADMIN_PASSWORD')
}

# PERFORMANCE: Cache for static/rarely-changing data
@lru_cache(maxsize=1)
def get_all_seco_processes():
    """Cache SECO processes - they rarely change"""
    return SECO_process.query.options(
        selectinload(SECO_process.guidelines),
        selectinload(SECO_process.tasks)
    ).all()

@lru_cache(maxsize=1)
def get_all_dimensions():
    """Cache dimensions - they rarely change"""
    return SECO_dimension.query.all()

# Helper to clear cache when data is updated
def clear_static_caches():
    """Call this after updating processes or dimensions"""
    get_all_seco_processes.cache_clear()
    get_all_dimensions.cache_clear()

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
@login_required  # Fix #3: Protect route from unauthenticated access
def evaluations():
    # Fix #3: Safe access to session variable (decorator ensures user is logged in)
    email = session.get('user_signed_in')
    user = SECO_MANAGER.query.filter_by(email=email).first()

    # Fix #27, #28, #29: Pagination, Search, and Sorting
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Fix #27: 10 evaluations per page
    search_query = request.args.get('search', '', type=str).strip()
    sort_by = request.args.get('sort', 'newest', type=str)  # Fix #29: Sorting options
    
    # PERFORMANCE: Start with user's evaluations query with eager loading for processes
    query = Evaluation.query.options(
        selectinload(Evaluation.seco_processes)
    ).filter_by(user_id=user.user_id)
    
    # Fix #28: Apply search filter if provided
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Evaluation.name.ilike(search_pattern),
                Evaluation.seco_portal.ilike(search_pattern),
                Evaluation.evaluation_id.cast(db.String).like(search_pattern)
            )
        )

    # Fix #29: Apply sorting (using created_at for chronological order)
    # Note: MySQL doesn't support NULLS LAST/FIRST, so we use simple sorting
    # NULL values will naturally sort to the end/beginning depending on ASC/DESC
    if sort_by == 'newest':
        # Sort by creation date (newest first), fallback to evaluation_id
        query = query.order_by(
            Evaluation.created_at.desc(), 
            Evaluation.evaluation_id.desc()
        )
    elif sort_by == 'oldest':
        # Sort by creation date (oldest first), fallback to evaluation_id
        query = query.order_by(
            Evaluation.created_at.asc(), 
            Evaluation.evaluation_id.asc()
        )
    elif sort_by == 'name_asc':
        query = query.order_by(Evaluation.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Evaluation.name.desc())
    else:
        # Default to newest
        query = query.order_by(
            Evaluation.created_at.desc(), 
            Evaluation.evaluation_id.desc()
        )
    
    # Fix #27: Paginate results (FAST)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    evaluations = pagination.items

    # Schedule background heatmap prefetch for fast dashboard loading
    token = session.get('uxt_access_token')
    prefetch_ids = [evaluation.evaluation_id for evaluation in evaluations[:5]]
    schedule_heatmap_prefetch(prefetch_ids, token)
    
    return render_template('evaluations.html', 
                         evaluations=evaluations,
                         pagination=pagination,
                         search_query=search_query,
                         sort_by=sort_by)

@app.route('/evaluations/create_evaluation', methods=['GET'])
@login_required  # Fix #3: Protect evaluation creation from unauthenticated access
def create_evaluation():
    email = session.get('user_signed_in')
    user = User.query.filter_by(email=email).first() if email else None
    # PERFORMANCE: Use cached version of processes
    seco_processes = get_all_seco_processes()

    # Fix #7: Generate CSRF token for form protection
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
@login_required  # Fix #3: Protect POST endpoint
def add_evaluation():
    # local imports for this handler
    from sqlalchemy.exc import IntegrityError
    import random as rd
    import requests
    import re

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

    # Fix #7: CSRF token validation - Validate form token to prevent CSRF attacks
    token = request.form.get('form_token')
    saved = session.pop('eval_form_token', None)
    if not token or token != saved:
        abort(403, description="Invalid or expired form token. Please try again.")

    # read form data
    name = request.form.get('name', '').strip()
    seco_portal = request.form.get('seco_portal', '').strip()
    seco_portal_url = request.form.get('seco_portal_url', '').strip()
    seco_process_ids = request.form.getlist('seco_process_ids')
    seco_type_str = request.form.get('seco_type')
    manager_objective = request.form.get('manager_objective', '').strip()
    
    # Fix #6: Validate manager objective length (max 2000 characters)
    # Prevents database overflow and SQL errors
    MAX_MANAGER_OBJECTIVE_LENGTH = 2000
    if len(manager_objective) > MAX_MANAGER_OBJECTIVE_LENGTH:
        abort(400, description=f"Manager objective too long. Maximum {MAX_MANAGER_OBJECTIVE_LENGTH} characters allowed.")
    
    # Fix #8: Input validation and sanitization for all required fields
    # Prevents empty/invalid data from entering database
    if not name or len(name) > 255:
        abort(400, description="Evaluation name is required and must be less than 255 characters.")
    
    if not seco_portal or len(seco_portal) > 255:
        abort(400, description="SECO portal name is required and must be less than 255 characters.")
    
    # Fix #8: Validate URL format (lenient - accepts with or without protocol)
    # Just check it's not empty and not too long - frontend handles format validation
    if not seco_portal_url:
        abort(400, description="Portal URL is required.")
    
    if len(seco_portal_url) > 500:
        abort(400, description="Portal URL is too long. Maximum 500 characters allowed.")
    
    # Optional: Auto-add http:// if no protocol specified (makes it more user-friendly)
    if not re.match(r'^https?://', seco_portal_url):
        seco_portal_url = 'https://' + seco_portal_url
    
    # Fix #8: Validate SECO type is valid enum value
    try:
        seco_type = SECOType(seco_type_str)
    except (ValueError, AttributeError):
        abort(400, description="Invalid SECO type selected.")
    
    # Fix #8: Validate process IDs are integers (prevents SQL injection via form manipulation)
    # SQLAlchemy uses parameterized queries but we validate early for safety
    try:
        seco_process_ids_int = [int(pid) for pid in seco_process_ids]
        if not seco_process_ids_int:
            abort(400, description="At least one process must be selected.")
    except (ValueError, TypeError):
        abort(400, description="Invalid process IDs provided.")

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

    # Resolve user early (needed for re-render)
    email = session.get('user_signed_in')
    if not email:
        return redirect(url_for('signin'))
    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('signin'))

    # Parse posted KSC weights (ksc_points_<process>_<ksc>)
    ksc_weights_raw = {
        key[len('ksc_points_'):]: value
        for key, value in request.form.items()
        if key.startswith('ksc_points_')
    }

    ksc_weights = {}
    ksc_weights_map = {}
    for suffix, raw_value in ksc_weights_raw.items():
        try:
            process_str, ksc_str = suffix.split('_', 1)
            process_id = int(process_str)
            ksc_id = int(ksc_str)
        except ValueError:
            continue

        try:
            weight = int(raw_value)
        except (ValueError, TypeError):
            weight = 0

        ksc_weights.setdefault(process_id, []).append((ksc_id, weight))
        ksc_weights_map[f"{process_id}_{ksc_id}"] = weight

    form_values = {
        "name": name,
        "seco_portal": seco_portal,
        "seco_portal_url": seco_portal_url,
        "seco_type": seco_type_str,
        "manager_objective": manager_objective,
        "selected_process_ids": seco_process_ids,
        "ksc_weights": ksc_weights_map
    }

    # Note: seco_type and seco_process_ids_int already validated above
    # No need to re-validate here

    # Fix #8: Validate KSC weights for each selected process
    # Ensure all weights are integers between 0-10 (prevents injection/manipulation)
    validation_errors = []
    selected_process_ids_int = seco_process_ids_int  # Already validated above

    for pid in selected_process_ids_int:
        weights = ksc_weights.get(pid, [])
        total = sum(weight for _, weight in weights)
        if total != 10:
            validation_errors.append(f"Procedure P{pid}: total must equal 10 (got {total}).")
        for ksc_id, weight in weights:
            if weight < 0 or weight > 10:
                validation_errors.append(f"Procedure P{pid}, KSC {ksc_id}: weight must be between 0 and 10.")

    missing_processes = [pid for pid in selected_process_ids_int if pid not in ksc_weights]
    for pid in missing_processes:
        validation_errors.append(f"Procedure P{pid}: distribute the 10 points before continuing.")

    if validation_errors:
        error_msg = " ".join(validation_errors)
        seco_processes = SECO_process.query.all()
        return render_template(
            "create_evaluation.html",
            user=user,
            seco_processes=seco_processes,
            values=form_values,
            error_msg=error_msg,
            form_token=token,
            seco_types=SECOType
        )

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
    r = None

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

    # Fix #5: Generate unique evaluation_id with race condition protection
    if not evaluation_id:
        print(f"LOG: Usando geração aleatória de código (fallback)")
        # Generate random 7-digit code, checking for collisions
        import random
        max_attempts = 10
        for attempt in range(max_attempts):
            # Generate random 7-digit number
            evaluation_id = random.randint(1000000, 9999999)
            # Check if already exists
            if Evaluation.query.filter_by(evaluation_id=evaluation_id).first() is None:
                print(f"LOG: Código gerado com sucesso: {evaluation_id}")
                break
            else:
                print(f"LOG: Código {evaluation_id} já existe, tentando novamente...")
                evaluation_id = None
        
        if not evaluation_id:
            # Extremely unlikely, but handle it
            abort(500, description="Failed to generate unique evaluation code. Please try again.")

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
        
        ksc_weights = {}
        for key, value in request.form.items():
            if not key.startswith('ksc_points_'):
                continue
            parts = key.split('_')
            if len(parts) < 4:
                continue
            try:
                pid = parts[2]
                ksc_id = int(parts[3])
                weight = int(value) if value.strip() != '' else 0
            except ValueError:
                print(f"⚠️ Invalid KSC weight value for {key}: {value}")
                return redirect(url_for('create_evaluation'))

            ksc_weights.setdefault(pid, []).append((ksc_id, weight))

        # Validate distribution totals (must sum to 10 per process group)
        for pid, items in ksc_weights.items():
            total = sum(weight for _, weight in items)
            if total != 10:
                print(f"⚠️ Process {pid} has invalid KSC distribution total: {total}")
                error_msg = f"KSC weights for procedure P{pid} must sum to 10."
                values = {
                    "name": name,
                    "seco_portal": seco_portal,
                    "seco_portal_url": seco_portal_url,
                    "seco_type": seco_type_str,
                    "manager_objective": manager_objective
                }
                seco_processes = SECO_process.query.all()
                return render_template(
                    "create_evaluation.html",
                    user=user,
                    seco_processes=seco_processes,
                    values=values,
                    error_msg=error_msg,
                    form_token=token,
                    seco_types=SECOType
                )

        # Persist KSC weights
        last_weight = EvaluationCriterionWheight.query.order_by(EvaluationCriterionWheight.id.desc()).first()
        next_id = (last_weight.id + 1) if last_weight else 1
        for pid, items in ksc_weights.items():
            for ksc_id, weight in items:
                new_weight = EvaluationCriterionWheight(
                    id=next_id,
                    ksc_id=ksc_id,
                    evaluation_id=new_evaluation.evaluation_id,
                    weight=weight
                )
                next_id += 1
                db.session.add(new_weight)
                print(f"✅ KSC weight added for process {pid}, ksc {ksc_id}: {weight}")
                
        try:
            print("\nDEBUG: Adding to session...")
            db.session.add(new_evaluation)

            for process_id, items in ksc_weights.items():
                for ksc_id, weight in items:
                    db.session.add(EvaluationCriterionWheight(
                        weight=weight,
                        ksc_id=ksc_id,
                        evaluation_id=evaluation_id
                    ))

            print("DEBUG: Committing to database...")
            db.session.commit()
            
            print("✅ KSC weights committed successfully")
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
            # Fix #5: Handle race condition/duplicate evaluation gracefully
            print(f"\nDEBUG: ERROR - IntegrityError occurred: {str(e)}")
            print("⚠️ Error committing evaluation - likely duplicate or constraint violation")
            db.session.rollback()
            
            # Check if it's a duplicate evaluation_id (race condition)
            if 'PRIMARY' in str(e) or 'evaluation_id' in str(e):
                abort(409, description="Evaluation code already exists. Please try creating the evaluation again.")
            else:
                # Other integrity errors (e.g., duplicate name+portal combo)
                abort(400, description="An evaluation with these details already exists.")
                
        except Exception as e:
            # Fix #4: Catch any other database errors
            print(f"\nDEBUG: ERROR - Unexpected error: {type(e).__name__}: {str(e)}")
            print("⚠️ Error committing evaluation")
            db.session.rollback()
            abort(500, description="Failed to save evaluation. Please try again.")

    # Fix #26: Add success flash message
    flash('Evaluation created successfully! Share the evaluation code with participants.', 'success')
    return redirect(url_for('evaluations'))


@app.route('/evaluations/<int:id>/edit')
@login_required  # Fix #3: Protect edit route
def edit_evaluation(id):
    email = session.get('user_signed_in')
    user = User.query.filter_by(email=email).first()
    evaluation = Evaluation.query.get_or_404(id)
    seco_processes = SECO_process.query.all()
    return render_template('edit_evaluation.html', evaluation=evaluation, user=user, seco_processes=seco_processes, seco_types=SECOType)

@app.route('/evaluations/<int:id>/update', methods=['POST'])
@login_required  # Fix #3: Protect update route
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

@app.route('/evaluations/<int:id>/delete', methods=['POST'])
@login_required
def delete_evaluation(id):
    evaluation = Evaluation.query.get_or_404(id)
    evaluation_name = evaluation.name

    try:
        db.session.delete(evaluation)
        db.session.commit()
        flash(f'Evaluation "{evaluation_name}" deleted successfully.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete evaluation %s", id)
        flash('Failed to delete evaluation. Please try again.', 'error')

    return redirect(url_for('evaluations'))

@app.route('/evaluations/<int:id>')
def evaluation(id):
    email = session['user_signed_in']
    user = User.query.filter_by(email=email).first()
    
    # PERFORMANCE: Eager load all relationships to avoid N+1 queries
    # This reduces 20+ queries to just 1-2 queries
    evaluation = Evaluation.query.options(
        selectinload(Evaluation.seco_processes)
            .selectinload(SECO_process.guidelines)
            .selectinload(Guideline.seco_dimensions),
        selectinload(Evaluation.seco_processes)
            .selectinload(SECO_process.tasks),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.performed_tasks)
            .selectinload(PerformedTask.task),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.answers)
            .selectinload(Answer.question),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.developer_questionnaire),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.navigation)
    ).get_or_404(id)
    
    seco_processes = evaluation.seco_processes  # Already loaded
    collected_data = evaluation.collected_data  # Already loaded
    
    # PERFORMANCE: Only load questions that are actually used in this evaluation
    question_ids = set()
    for cd in collected_data:
        for answer in cd.answers:
            question_ids.add(answer.question_id)
    
    questions = Question.query.filter(
        Question.question_id.in_(question_ids)
    ).all() if question_ids else []
    
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
    
    # PERFORMANCE: Eager load all relationships (reduces 30+ queries to 2-3)
    evaluation = Evaluation.query.options(
        selectinload(Evaluation.seco_processes)
            .selectinload(SECO_process.guidelines)
            .selectinload(Guideline.seco_dimensions),
        selectinload(Evaluation.seco_processes)
            .selectinload(SECO_process.tasks),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.performed_tasks),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.answers)
            .selectinload(Answer.question),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.developer_questionnaire),
        selectinload(Evaluation.collected_data)
            .selectinload(CollectedData.navigation)
    ).get_or_404(id)
    
    seco_processes = evaluation.seco_processes  # Already loaded
    collected_data = evaluation.collected_data  # Already loaded
    
    # PERFORMANCE: Collect unique tasks and guidelines (already loaded, no extra queries)
    guidelines = []
    tasks = []
    for p in seco_processes:
        for t in p.tasks:
            if t not in tasks:
                tasks.append(t)
        for g in p.guidelines:
            if g not in guidelines:
                guidelines.append(g)
    
    # PERFORMANCE: Only load questions that are actually answered
    question_ids = set()
    for cd in collected_data:
        for answer in cd.answers:
            question_ids.add(answer.question_id)
    
    questions = Question.query.filter(
        Question.question_id.in_(question_ids)
    ).all() if question_ids else []
                
    count_collected_data = len(collected_data)
    
    # Scenario summaries sourced from Rodrigo's spreadsheet (Scenario Context column)
    scenario_context_lookup = {
        "Exploring Resources to Start Development": "Represents developers’ first interaction with the ecosystem portal. Clear and accessible documentation here directly impacts onboarding speed and confidence.",
        "Exploring Repository History and Code Evolution": "Represents how developers explore repositories to understand the platform’s evolution. Traceable and well-documented code changes increase trust and ease of contribution.",
        "Exploring Communication Channels with the Keystone": "Represents how developers connect with ecosystem actors to clarify doubts or propose changes. Transparent and responsive communication fosters collaboration and knowledge flow.",
        "Exploring Participation Rules and Contribution Guidelines": "Represents how developers learn the rules, processes, and compliance requirements for contributing. Clear guidance reduces cognitive effort and prevents frustration or missteps.",
        "Exploring the Flow of Requirements and Roadmap Decisions": "Represents how developers track how new ideas, feature requests, and improvements are evaluated and prioritized. Visible decision flows increase predictability and engagement.",
        "Exploring Data Collection and Sharing Practices": "Represents how developers seek clarity about what data is collected, processed, and shared within the platform. Transparent practices build reliability and ethical trust.",
        "Exploring the Architecture and Structure of the Ecosystem": "Represents how developers understand the overall architecture of the ecosystem. Clear technical maps and dependencies reduce mental load and improve comprehension of how components interact."
    }

    scenario_cards = []
    for index, task in enumerate(tasks, start=1):
        summary = getattr(task, 'summary', None) or scenario_context_lookup.get(task.title)
        if not summary:
            # Fallback: use first sentence or truncated description
            description = (task.description or '').strip()
            summary = description.split('. ')[0] + ('...' if len(description) > 120 else '')
        scenario_cards.append({
            'index': index,
            'title': task.title,
            'summary': summary,
            'description': task.description,
            'task_id': task.task_id
        })
                
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
                'examples': [],
                'weight': 0,
                'insight': None
            }

            # Buscar weight do KSC para esta avaliação
            weight_obj = next(
                (w for w in evaluation.ksc_weights
                 if w.ksc_id == ksc.key_success_criterion_id),
                None
            )
            ksc_data['weight'] = weight_obj.weight if weight_obj else 0

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
                    ksc_data['insight'] = "Criterion fully meets expectations."
                elif final_score >= 0.5:
                    ksc_data['status'] = "Partially Fulfilled"
                    ksc_data['insight'] = "Criterion shows some gaps, needs attention."
                else:
                    ksc_data['status'] = "Not Fulfilled"
                    ksc_data['insight'] = "Criterion far below target, requires major review."
            else:
                ksc_data['score'] = None
                ksc_data['status'] = "No Answers"
                ksc_data['insight'] = "No data available for this criterion."

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

            # Priority Logic - baseado no gap do target (75)
            gap_from_target = 75 - g_data['average_score']

            if gap_from_target <= 0:
                g_data['priority'] = "Low Priority"
                g_data['priority_insight'] = "Target reached or exceeded."
            elif gap_from_target <= 10:
                g_data['priority'] = "Medium Priority"
                g_data['priority_insight'] = "Minor improvement needed."
            elif gap_from_target <= 20:
                g_data['priority'] = "High Priority"
                g_data['priority_insight'] = "Significant improvement required."
            else:
                g_data['priority'] = "Critical Priority"
                g_data['priority_insight'] = "Major transparency issue, immediate action recommended."

            # Status logic
            if avg >= 0.75:
                g_data['status'] = "Fulfilled"
            elif avg >= 0.5:
                g_data['status'] = "Partially Fulfilled"
            else:
                g_data['status'] = "Not Fulfilled"
        else:
            g_data['status'] = "No Answers"
            g_data['priority'] = "No Priority"
            g_data['priority_insight'] = "No data available to calculate priority."

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
             "summary": summary, 
            "comments": info["comments"],
            "avg_time": avg_time,
            "completion_rate": completion_rate
        })
    # Para cada task processada, buscar guidelines relacionadas
    for task_data in processed_tasks:
        task_id_current = task_data['task_id']

        # Encontrar o objeto Task correspondente
        task_obj = next((t for t in tasks if t.task_id == task_id_current), None)
        if not task_obj:
            task_data['guidelines'] = []
            continue

        # Buscar guidelines através dos SECO_processes
        task_guidelines = []
        for process in seco_processes:
            if task_obj in process.tasks:
                for guideline in process.guidelines:
                    if guideline not in task_guidelines:
                        task_guidelines.append(guideline)

        task_data['guidelines'] = task_guidelines

    # Prepare improvement actions for each task
    # Improvement actions show KSCs with status "Partially Fulfilled" or "Not Fulfilled", ordered by weight
    for task_data in processed_tasks:
        improvement_actions = []
        
        # Get all KSCs from this task's guidelines
        for guideline in task_data.get('guidelines', []):
            # Find the guideline result data
            g_result = next((item for item in result if item['title'] == guideline.title), None)
            if not g_result:
                continue
            
            # Get all KSCs for this guideline that need improvement
            for ksc in g_result['key_success_criteria']:
                # Only include KSCs with status "Partially Fulfilled" or "Not Fulfilled"
                if ksc['status'] in ["Partially Fulfilled", "Not Fulfilled"]:
                    # Only include if there are examples
                    if ksc.get('examples') and len(ksc['examples']) > 0:
                        # Get the first example (there should typically be one per KSC)
                        example_description = ksc['examples'][0]['description']
                        
                        improvement_actions.append({
                            'title': ksc['title'],
                            'weight': ksc['weight'],
                            'description': example_description,
                            'status': ksc['status']
                        })
        
        # Sort by weight (descending) - higher weights first
        improvement_actions.sort(key=lambda x: x['weight'], reverse=True)
        
        task_data['improvement_actions'] = improvement_actions

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
            'has_guidelines': len(d.guidelines) > 0,
            'has_data': False
        }

        scores = []

        for g in d.guidelines:
            g_result = next((item for item in result if item['title'] == g.title), None)
            if g_result and g_result['average_score'] is not None:
                dim_data['guidelines'].append(g_result)
                scores.append(g_result['average_score'])

        if scores:
            dim_data['average_score'] = round(sum(scores) / len(scores))
            dim_data['has_data'] = True

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
            'score': None,
            'has_data': False
        },
        'projects_and_applications': {
            'name': 'Projects and Applications',
            'guidelines': [],
            'score': None,
            'has_data': False
        },
        'community_interaction': {
            'name': 'Community Interaction',
            'guidelines': [],
            'score': None,
            'has_data': False
        },
        'expectations_and_value': {
            'name': 'Expectations and Value of Contribution',
            'guidelines': [],
            'score': None,
            'has_data': False
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
            category['has_data'] = True
        else:
            category['score'] = 0
            category['has_data'] = False

    # Função helper para determinar badge de transparência
    def get_transparency_badge(score, has_data=False):
        if score is None or score == 0:
            if not has_data:
                return "Awaiting Data"
            return "No Data"
        elif score >= 75:
            return "Good Transparency"
        elif score >= 50:
            return "Moderate Transparency"
        else:
            return "Bad Transparency"

    # Adicionar badges de transparência
    transparency_badge_overall = get_transparency_badge(score_geral, count_collected_data > 0)

    for dim in dimension_scores:
        dim['transparency_badge'] = get_transparency_badge(dim['average_score'], dim['has_data'])

    for category in dx_categories.values():
        category['transparency_badge'] = get_transparency_badge(category['score'], category['has_data'])

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

    # PERFORMANCE: Immediately prefetch heatmap for THIS evaluation (priority)
    # This ensures the heatmap is ready when user clicks the Hotspots tab
    token = session.get('uxt_access_token')
    if token:
        # Priority prefetch - load THIS evaluation's heatmap immediately (parallel)
        schedule_heatmap_prefetch([id], token, priority=True)

    return render_template('dashboard.html',
                            evaluation=evaluation,
                            user=user,
                            seco_processes=seco_processes,
                            count_collected_data=count_collected_data,
                            guidelines=guidelines,
                            tasks=tasks,
                            scenario_cards=scenario_cards,
                            collected_data=collected_data,
                            questions=questions,
                            eName=eName,
                            eId=eId,
                            ePortal=ePortal,
                            ePortalUrl=ePortalUrl,
                            eManagerObjective=evaluation.manager_objective,
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
