from flask import render_template, request, redirect, session, url_for, jsonify
from app import app, db
from functions import isLogged, isAdmin
from models import User, Guideline, SECO_process, SECO_dimension, Conditioning_factor_transp, Key_success_criterion, DX_factor

@app.route('/doc')
def doc():
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin()
        return render_template('doc.html', is_admin = is_admin)
    
    return render_template('doc.html')

@app.route('/about')
def about():
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin()
        return render_template('about.html', is_admin = is_admin)
    
    return render_template('about.html')

@app.route('/guidelines')
def guidelines():
    guidelines = Guideline.query.all()
    processes = SECO_process.query.all()
    dimensions = SECO_dimension.query.all()
    conditioning_factors = Conditioning_factor_transp.query.all()
    criteria = Key_success_criterion.query.all()
    factors = DX_factor.query.all()
    
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin()
        return render_template('guidelines.html', 
                                is_admin = is_admin,
                                guidelines = guidelines, processes = processes, dimensions = dimensions, conditioning_factors = conditioning_factors, criteria = criteria, factors = factors)

    return render_template('guidelines.html', 
                            guidelines = guidelines, processes = processes, dimensions = dimensions, conditioning_factors = conditioning_factors, criteria = criteria, factors = factors)

@app.route('/seco_dashboard')
def seco_dashboard():
    if isLogged():
        email = session['user_signed_in']
        is_admin = isAdmin()
        if not is_admin:
            return render_template('dashboard.html', is_admin=is_admin)
        else:
            return redirect(url_for('index'))
    else:
        return redirect(url_for('signin'))

@app.route('/api/ping')
def ping():
    return jsonify({"status": "ok", "message": "API server is running"})

@app.route('/api/evaluation-data')
def get_evaluation_data():
    # Hier kun je echte gegevens uit je database halen
    # Voor nu een eenvoudig voorbeeld
    data = {
        "taskCompletionTimes": [
            {"task_id": 1, "task_name": "Translate the page", "avg_time_seconds": 45}
        ],
        "interactionTypes": [
            {"type": "click", "count": 150}
        ],
        "heatmapData": [
            {"x": 100, "y": 150, "value": 10},
            {"x": 200, "y": 100, "value": 5}
        ]
    }
    return jsonify(data)

@app.route('/api/check-tables')
def check_tables():
    # Controleer of tabellen bestaan
    return jsonify({"tables_exist": True})

@app.route('/dashboardv2')
def dashboard_v2():
    dimensions = SECO_dimension.query.all()
        
    return render_template('dashboardv2.html', dimensions=dimensions)