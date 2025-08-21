from flask import render_template, request, redirect, session, url_for, flash
from index import app, db
from models import Guideline, Key_success_criterion, Conditioning_factor_transp, DX_factor, SECO_process, SECO_dimension, Task, Question, Example
from functions import isLogged, isAdmin

# Messages
admin_message = ''
message_type = 'info'

# Routes
@app.route('/admin/guidelines')
def admin_guidelines():
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin()
        admin_message = ''
        message_type = 'info'
        guidelines = Guideline.query.all()
        key_success_criteria = Key_success_criterion.query.all()
        conditioning_factors = Conditioning_factor_transp.query.all()
        dx_factors = DX_factor.query.all()
        seco_processes = SECO_process.query.all()
        seco_dimensions = SECO_dimension.query.all()
        tasks = Task.query.all()
        questions = Question.query.all()
        examples = Example.query.all()
        
        return render_template('admin_guidelines.html', 
                            guidelines=guidelines,
                            key_success_criteria=key_success_criteria,
                            conditioning_factors=conditioning_factors,
                            dx_factors=dx_factors,
                            seco_processes=seco_processes,
                            seco_dimensions=seco_dimensions,
                            message=admin_message, 
                            message_type=message_type,
                            is_admin=is_admin,
                            tasks=tasks,
                            questions=questions,
                            examples=examples)
    else:
        return redirect(url_for('signin'))

# Route to add a new guideline
@app.route('/admin/add_guideline', methods=['POST'])
def add_guideline():
    global admin_message
    global message_type

    guidelines = Guideline.query.all()

    if not guidelines:
        cont_guideline = 1
    else:
        cont_guideline = guidelines[-1].guidelineID + 1

    title = request.form.get('title')
    description = request.form.get('description')
    conditioning_factor_transp_ids = request.form.getlist('conditioning_factor_transp_ids')
    dx_factor_ids = request.form.getlist('dx_factor_ids')
    seco_process_ids = request.form.getlist('seco_process_ids')
    seco_dimension_ids = request.form.getlist('seco_dimension_ids')
    notes = request.form.get('notes', '')  # Optional field, default to empty string
    # Buscar os objetos relacionados
    conditioning_factors = Conditioning_factor_transp.query.filter(Conditioning_factor_transp.conditioning_factor_transp_id.in_(conditioning_factor_transp_ids)).all() if conditioning_factor_transp_ids else []
    dx_factors = DX_factor.query.filter(DX_factor.dx_factor_id.in_(dx_factor_ids)).all() if dx_factor_ids else []
    seco_processes = SECO_process.query.filter(SECO_process.seco_process_id.in_(seco_process_ids)).all() if seco_process_ids else []
    seco_dimensions = SECO_dimension.query.filter(SECO_dimension.seco_dimension_id.in_(seco_dimension_ids)).all() if seco_dimension_ids else []
    # Create a new guideline
    new_guideline = Guideline(
        guidelineID=cont_guideline,
        title=title,
        description=description,
        conditioning_factors=conditioning_factors,
        dx_factors=dx_factors,
        seco_processes=seco_processes,
        seco_dimensions=seco_dimensions,
        notes=notes
    )
    
    try:
        db.session.add(new_guideline)
        db.session.commit()
        admin_message = 'Guideline added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding guideline: {str(e)}'
        message_type = 'danger'
    
    # Obtain the last id of criterion to increment
    key_success_criteria = Key_success_criterion.query.all()
    if not key_success_criteria:
        cont_key_success_criterion = 1
    else:
        cont_key_success_criterion = Key_success_criterion.query.order_by(Key_success_criterion.key_success_criterion_id.desc()).first().key_success_criterion_id + 1
    
    # Coletar todos os possíveis critérios (com base no padrão de nomes)
    criterion_titles = {}
    criterion_descriptions = {}
    
    for key, value in request.form.items():
        if key.startswith('title') and key != 'title':
            number = key[5:]  # Get the number after 'title'
            criterion_titles[number] = value
        elif key.startswith('description') and key != 'description':
            number = key[11:]  # Get the number after 'description'
            criterion_descriptions[number] = value
    
    # Add criteria
    for num in criterion_titles.keys():
        if num in criterion_descriptions:
            criterion_title = criterion_titles[num]
            criterion_description = criterion_descriptions[num]
            
            if criterion_title and criterion_description:  # Check if they are not empty
                new_criterion = Key_success_criterion(
                    key_success_criterion_id=cont_key_success_criterion, 
                    title=criterion_title, 
                    description=criterion_description, 
                    guideline_id=new_guideline.guidelineID  # Use the ID of the newly created guideline
                )
                try:
                    db.session.add(new_criterion)
                    db.session.commit()
                    cont_key_success_criterion += 1
                except Exception as e:
                    db.session.rollback()
                    admin_message = f'Error adding success criterion: {str(e)}'
                    message_type = 'danger'

    return redirect(url_for('admin_guidelines'))

# Route to edit a guideline (form page)
@app.route('/admin/edit_guideline/<int:id>')
def edit_guideline(id):
    guideline = Guideline.query.get_or_404(id)
    key_success_criteria = Key_success_criterion.query.all()
    conditioning_factors = Conditioning_factor_transp.query.all()
    dx_factors = DX_factor.query.all()
    seco_processes = SECO_process.query.all()
    seco_dimensions = SECO_dimension.query.all()
    return render_template('admin_edit_guideline.html', 
                          guideline_edit=guideline,
                          key_success_criteria=key_success_criteria,
                          conditioning_factors=conditioning_factors,
                          dx_factors=dx_factors,
                          seco_processes=seco_processes,
                          seco_dimensions=seco_dimensions,
                          message=admin_message,
                          message_type=message_type)

# Route to update a guideline (form processing)
@app.route('/admin/update_guideline/<int:id>', methods=['POST'])
def update_guideline(id):
    global admin_message
    global message_type
    
    guideline = Guideline.query.get_or_404(id)
    
    title = request.form.get('title')
    description = request.form.get('description')
    key_success_criterion_ids = request.form.getlist('key_success_criterion_ids')
    conditioning_factor_transp_ids = request.form.getlist('conditioning_factor_transp_ids')
    dx_factor_ids = request.form.getlist('dx_factor_ids')
    seco_process_ids = request.form.getlist('seco_process_ids')
    seco_dimension_ids = request.form.getlist('seco_dimension_ids')
    # Buscar os objetos relacionados
    key_success_criteria = Key_success_criterion.query.filter(Key_success_criterion.key_success_criterion_id.in_(key_success_criterion_ids)).all() if key_success_criterion_ids else []
    conditioning_factors = Conditioning_factor_transp.query.filter(Conditioning_factor_transp.conditioning_factor_transp_id.in_(conditioning_factor_transp_ids)).all() if conditioning_factor_transp_ids else []
    dx_factors = DX_factor.query.filter(DX_factor.dx_factor_id.in_(dx_factor_ids)).all() if dx_factor_ids else []
    seco_processes = SECO_process.query.filter(SECO_process.seco_process_id.in_(seco_process_ids)).all() if seco_process_ids else []
    seco_dimensions = SECO_dimension.query.filter(SECO_dimension.seco_dimension_id.in_(seco_dimension_ids)).all() if seco_dimension_ids else []
    try:
        guideline.title = title
        guideline.description = description
        guideline.key_success_criteria = key_success_criteria
        guideline.conditioning_factors = conditioning_factors
        guideline.dx_factors = dx_factors
        guideline.seco_processes = seco_processes
        guideline.seco_dimensions = seco_dimensions
        db.session.commit()
        admin_message = 'Guideline updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating guideline: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to delete a guideline
@app.route('/admin/delete_guideline/<int:id>')
def delete_guideline(id):
    global admin_message
    global message_type
    
    guideline = Guideline.query.get_or_404(id)
    
    try:
        # First remove all associated key success criteria
        Key_success_criterion.query.filter_by(guideline_id=id).delete()
        
        # Now you can delete the guideline
        db.session.delete(guideline)
        db.session.commit()
        
        flash('Guideline deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        # Detailed error log
        import traceback
        print(traceback.format_exc())
        flash(f'Erro ao excluir guideline: {str(e)}', 'danger')
    
    return redirect(url_for('admin_guidelines'))

# Route to add a new SECO process
@app.route('/admin/add_seco_process', methods=['POST'])
def add_seco_process():
    global admin_message
    global message_type
    
    seco_processes = SECO_process.query.all()

    if not seco_processes:
        cont_seco_process = 1
    else:
        cont_seco_process = seco_processes[-1].seco_process_id + 1   

    description = request.form.get('description')
    
    try:
        new_process = SECO_process(seco_process_id=cont_seco_process, description=description)
        db.session.add(new_process)
        db.session.commit()
        admin_message = 'SECO process added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding process: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to edit a SECO process
@app.route('/admin/edit_seco_process/<int:id>')
def edit_seco_process(id):
    seco_process = SECO_process.query.get_or_404(id)
    return render_template('edit_seco_process.html',
                            seco_process=seco_process,
                            message=admin_message,
                            message_type=message_type)

# Route to update a SECO process
@app.route('/admin/update_seco_process/<int:id>', methods=['POST'])
def update_seco_process(id):
    global admin_message
    global message_type
    
    seco_process = SECO_process.query.get_or_404(id)
    description = request.form.get('description')
    
    try:
        seco_process.description = description
        db.session.commit()
        admin_message = 'SECO process updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating process: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to delete a SECO process
@app.route('/admin/delete_seco_process/<int:id>')
def delete_seco_process(id):
    global admin_message
    global message_type
    
    seco_process = SECO_process.query.get_or_404(id)
    
    try:
        db.session.delete(seco_process)
        db.session.commit()
        admin_message = 'SECO process successfully deleted!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting process: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to add a new SECO dimension
@app.route('/admin/add_seco_dimension', methods=['POST'])
def add_seco_dimension():
    global admin_message
    global message_type
    
    seco_dimensions = SECO_dimension.query.all()

    if not seco_dimensions:
        cont_seco_dimension = 1
    else:
        cont_seco_dimension = seco_dimensions[-1].seco_dimension_id + 1

    name = request.form.get('name')
    
    try:
        new_dimension = SECO_dimension(seco_dimension_id=cont_seco_dimension, name=name)
        db.session.add(new_dimension)
        db.session.commit()
        admin_message = 'SECO dimension added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding dimension: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to edit a SECO dimension
@app.route('/admin/edit_seco_dimension/<int:id>')
def edit_seco_dimension(id):
    seco_dimension = SECO_dimension.query.get_or_404(id)
    return render_template('edit_dimension.html',
                            seco_dimension=seco_dimension,
                            message=admin_message,
                            message_type=message_type)

# Route to update a SECO dimension
@app.route('/admin/update_seco_dimension/<int:id>', methods=['POST'])   
def update_seco_dimension(id):
    global admin_message
    global message_type
    
    seco_dimension = SECO_dimension.query.get_or_404(id)
    name = request.form.get('name')
    
    try:
        seco_dimension.name = name
        db.session.commit()
        admin_message = 'SECO dimension updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating dimension: {str(e)}'
        message_type = 'danger'

    return redirect(url_for('admin_guidelines'))

# Route to delete a SECO dimension
@app.route('/admin/delete_seco_dimension/<int:id>')
def delete_seco_dimension(id):
    global admin_message
    global message_type
    
    seco_dimension = SECO_dimension.query.get_or_404(id)
    
    try:
        db.session.delete(seco_dimension)
        db.session.commit()
        admin_message = 'SECO dimension deleted successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting dimension: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to add a new conditioning factor
@app.route('/admin/add_conditioning_factor', methods=['POST'])
def add_conditioning_factor():
    global admin_message
    global message_type
    
    conditioning_factors = Conditioning_factor_transp.query.all()

    if not conditioning_factors:
        cont_conditioning_factor = 1
    else:
        cont_conditioning_factor = conditioning_factors[-1].conditioning_factor_transp_id + 1

    description = request.form.get('description')
    
    try:
        new_factor = Conditioning_factor_transp(conditioning_factor_transp_id=cont_conditioning_factor, description=description)
        db.session.add(new_factor)
        db.session.commit()
        admin_message = 'Conditioning factor added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding conditioning factor: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to edit a conditioning factor
@app.route('/admin/edit_conditioning_factor/<int:id>')
def edit_conditioning_factor(id):
    conditioning_factor = Conditioning_factor_transp.query.get_or_404(id)
    return render_template('edit_conditioning_factor.html',
                            factor=conditioning_factor,
                            message=admin_message,
                            message_type=message_type)

# Route to update a conditioning factor
@app.route('/admin/update_conditioning_factor/<int:id>', methods=['POST'])
def update_conditioning_factor(id):
    global admin_message
    global message_type
    
    conditioning_factor = Conditioning_factor_transp.query.get_or_404(id)
    description = request.form.get('description')
    
    try:
        conditioning_factor.description = description
        db.session.commit()
        admin_message = 'Conditioning factor updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating conditioning factor: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to delete a conditioning factor
@app.route('/admin/delete_conditioning_factor/<int:id>')
def delete_conditioning_factor(id):
    global admin_message
    global message_type
    
    conditioning_factor = Conditioning_factor_transp.query.get_or_404(id)
    
    try:
        db.session.delete(conditioning_factor)
        db.session.commit()
        admin_message = 'Conditioning factor deleted successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting conditioning factor: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to add a new DX factor
@app.route('/admin/add_dx_factor', methods=['POST'])
def add_dx_factor():
    global admin_message
    global message_type
    
    dx_factors = DX_factor.query.all()

    if not dx_factors:
        cont_dx_factor = 1
    else:
        cont_dx_factor = dx_factors[-1].dx_factor_id + 1

    description = request.form.get('description')
    
    try:
        new_factor = DX_factor(dx_factor_id=cont_dx_factor, description=description)
        db.session.add(new_factor)
        db.session.commit()
        admin_message = 'DX factor added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding DX factor: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to edit a DX factor
@app.route('/admin/edit_dx_factor/<int:id>')
def edit_dx_factor(id):
    dx_factor = DX_factor.query.get_or_404(id)
    return render_template('edit_dx_factor.html',
                            dx_factor=dx_factor,
                            message=admin_message,
                            message_type=message_type)

# Route to update a DX factor
@app.route('/admin/update_dx_factor/<int:id>', methods=['POST'])
def update_dx_factor(id):
    global admin_message
    global message_type
    
    dx_factor = DX_factor.query.get_or_404(id)
    description = request.form.get('description')
    
    try:
        dx_factor.description = description
        db.session.commit()
        admin_message = 'DX factor updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating DX factor: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to delete a DX factor
@app.route('/admin/delete_dx_factor/<int:id>')
def delete_dx_factor(id):
    global admin_message
    global message_type
    
    dx_factor = DX_factor.query.get_or_404(id)
    
    try:
        db.session.delete(dx_factor)
        db.session.commit()
        admin_message = 'DX factor deleted successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting DX factor: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to add a new key success criterion
@app.route('/admin/add_key_success_criterion', methods=['POST'])
def add_key_success_criterion():
    global admin_message
    global message_type
    
    key_success_criteria = Key_success_criterion.query.all()

    if not key_success_criteria:
        cont_key_success_criterion = 1
    else:
        cont_key_success_criterion = key_success_criteria[-1].key_success_criterion_id + 1

    title = request.form.get('title')
    description = request.form.get('description')
    guideline_id = request.form.get('guideline_id')

    try:
        new_criterion = Key_success_criterion(key_success_criterion_id=cont_key_success_criterion, title=title, description=description, guideline_id=guideline_id)
        db.session.add(new_criterion)
        db.session.commit()
        admin_message = 'Success criterion added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding success criterion: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to edit a key success criterion
@app.route('/admin/edit_key_success_criterion/<int:id>')
def edit_key_success_criterion(id):
    key_success_criterion = Key_success_criterion.query.get_or_404(id)
    return render_template('edit_key_success_criterion.html',
                            criterion=key_success_criterion,
                            message=admin_message,
                            message_type=message_type)

# Route to update a key success criterion
@app.route('/admin/update_key_success_criterion/<int:id>', methods=['POST'])
def update_key_success_criterion(id):
    global admin_message
    global message_type
    
    key_success_criterion = Key_success_criterion.query.get_or_404(id)
    title = request.form.get('title')
    description = request.form.get('description')
    
    try:
        key_success_criterion.title = title
        key_success_criterion.description = description
        db.session.commit()
        admin_message = 'Success criterion updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating success criterion: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

# Route to delete a key success criterion
@app.route('/admin/delete_key_success_criterion/<int:id>')
def delete_key_success_criterion(id):
    global admin_message
    global message_type

    key_success_criterion = Key_success_criterion.query.get_or_404(id)
    
    try:
        
        examples = Example.query.filter_by(key_success_criterion_id=id).all()
        
        for ex in examples:
            db.session.delete(ex)
        
        db.session.delete(key_success_criterion)
        db.session.commit()
        admin_message = 'Success criterion deleted successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting success criterion: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/add_task', methods=['POST'])
def add_task():
    
    global admin_message
    global message_type

    # Get task ID
    tasks = Task.query.all()
    if not tasks:
        task_id = 1
    else:
        task_id = tasks[-1].task_id + 1

    # Get form data
    task_title = request.form.get('title')
    task_description = request.form.get('description')
    
    process_ids = request.form.getlist('process_ids')

    if process_ids:
        processes = SECO_process.query.filter(SECO_process.seco_process_id.in_(process_ids)).all()

    try:
        # Create a new task
        new_task = Task(title=task_title, description=task_description, task_id=task_id, seco_processes=processes)
        # Add the task to the session and commit
        db.session.add(new_task)
        db.session.commit()
        print('Task added successfully!')
        admin_message = 'Task added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        print('Error adding task:', str(e))
        admin_message = f'Error adding task: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/edit_task/<int:id>')
def edit_task(id):
    task = Task.query.get_or_404(id)
    guidelines = Guideline.query.all()
    guideline_ids = [guideline.guidelineID for guideline in task.guidelines]
    return render_template('edit_task.html', task=task, guidelines=guidelines, message=admin_message, message_type=message_type, guideline_ids=guideline_ids)

@app.route('/admin/update_task/<int:id>', methods=['POST'])
def update_task(id):
    global admin_message
    global message_type
    
    task = Task.query.get_or_404(id)
    task_title = request.form.get('title')
    task_description = request.form.get('description')
    
    guidelines_ids = request.form.getlist('guideline_ids')

    if guidelines_ids:
        guidelines = Guideline.query.filter(Guideline.guidelineID.in_(guidelines_ids)).all()

    try:
        task.title = task_title
        task.description = task_description
        task.guidelines = guidelines
        db.session.commit()
        admin_message = 'Task updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating task: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/delete_task/<int:id>')
def delete_task(id):
    global admin_message
    global message_type
    
    task = Task.query.get_or_404(id)
    tasks = Task.query.all()
    
    try:
        
        questions = Question.query.filter_by(task_id=id).all()
        
        for q in questions:
            db.session.delete(q)
        
        db.session.delete(task)
        db.session.commit()
        
        print('deleted')
        
        admin_message = 'Task deleted successfully!'
        message_type = 'success'
        
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting task: {str(e)}'
        message_type = 'danger'
        
        print(e)
        print('error')
        
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/add_question', methods=['POST'])  # Removido o parêntese extra
def add_question():
    global admin_message
    global message_type

    # Get all questions
    questions = Question.query.all()
    if not questions:
        question_id = 1
    else:
        question_id = questions[-1].question_id + 1

    # Get form data
    question = request.form.get('question')
    ksc_id = request.form.get('ksc_id')
    print('saved data')

    try:
        # Create a new question
        new_question = Question(question_id=question_id, question=question, key_success_criterion_id=ksc_id)  # Corrigido para usar Question
        # Add the question to the session and commit
        db.session.add(new_question)
        db.session.commit()
        print('Question added successfully!')
        admin_message = 'Question added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        print('Error adding question:', str(e))
        admin_message = f'Error adding question: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/edit_question/<int:id>')
def edit_question(id):
    question = Question.query.get_or_404(id)
    tasks = Task.query.all()
    return render_template('edit_question.html', question=question, tasks=tasks, message=admin_message, message_type=message_type)

@app.route('/admin/update_question/<int:id>', methods=['POST'])
def update_question(id):
    global admin_message
    global message_type
    
    question = Question.query.get_or_404(id)
    question_text = request.form.get('question')
    task_id = request.form.get('task_id')
    
    try:
        question.question = question_text
        question.task_id = task_id
        db.session.commit()
        admin_message = 'Question updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating question: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/delete_question/<int:id>')
def delete_question(id):
    global admin_message
    global message_type
    
    question = Question.query.get_or_404(id)
    
    try:
        db.session.delete(question)
        db.session.commit()
        admin_message = 'Question deleted successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting question: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/add_example', methods=['POST'])
def add_example():
    global admin_message
    global message_type

    # Get form data
    description = request.form.get('example')
    key_success_criterion_id = request.form.get('key_success_criterion_id')

    # get example id
    examples = Example.query.all()
    if not examples:
        example_id = 1
    else:
        example_id = examples[-1].example_id + 1

    try:
        # Create a new example (assuming you have an Example model)
        new_example = Example(description=description, example_id=example_id, key_success_criterion_id=key_success_criterion_id)
        
        # Add the example to the session and commit
        db.session.add(new_example)
        db.session.commit()
        admin_message = 'Example added successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error adding example: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/edit_example/<int:id>')
def edit_example(id):
    example = Example.query.get_or_404(id)
    key_success_criteria = Key_success_criterion.query.all()
    return render_template('edit_example.html', example=example, key_success_criteria=key_success_criteria, message=admin_message, message_type=message_type)

@app.route('/admin/update_example/<int:id>', methods=['POST'])
def update_example(id):
    global admin_message
    global message_type
    
    example = Example.query.get_or_404(id)
    description = request.form.get('example')
    
    try:
        example.description = description
        db.session.commit()
        admin_message = 'Example updated successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error updating example: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))

@app.route('/admin/delete_example/<int:id>')
def delete_example(id):
    global admin_message
    global message_type
    
    example = Example.query.get_or_404(id)
    
    try:
        db.session.delete(example)
        db.session.commit()
        admin_message = 'Example deleted successfully!'
        message_type = 'success'
    except Exception as e:
        db.session.rollback()
        admin_message = f'Error deleting example: {str(e)}'
        message_type = 'danger'
    
    return redirect(url_for('admin_guidelines'))