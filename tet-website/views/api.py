from app import app
from flask import jsonify
from models import *
import os
import requests
import json

credenciais_admin = {
    "email": os.getenv('ADMIN_EMAIL'),
    "password": os.getenv('ADMIN_PASSWORD')
}

@app.route('/api/guideline/<int:id>')
def api_get_guideline(id):
    guideline = Guideline.query.get_or_404(id)
    print(guideline.notes)
    return jsonify({
        "guidelineID": guideline.guidelineID,
        "title": guideline.title,
        "description": guideline.description,
        "seco_processes": [{"description": p.description} for p in guideline.seco_processes],
        "seco_dimensions": [{"name": d.name} for d in guideline.seco_dimensions],
        "conditioning_factors": [{"description": cf.description} for cf in guideline.conditioning_factors],
        "dx_factors": [{"description": f.description} for f in guideline.dx_factors],
        "key_success_criteria": [
            {
                "title": k.title,
                "description": k.description,
                "examples": [{"description": e.description} for e in k.examples]
            }
            for k in guideline.key_success_criteria
        ],
        "notes": guideline.notes
    })
    
@app.route('/api/experience-data/<int:id>')
def api_experience_data(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data
    
    t0a1 = 0
    t2a3 = 0
    t4a5 = 0
    t6a10 = 0
    t10m = 0
    
    for d in col_data:
        v = d.developer_questionnaire.experience
        if v == 0 or v == 1:
            t0a1 += 1
        elif v < 4:
            t2a3 += 1
        elif v < 6:
            t4a5 += 1
        elif v < 10:
            t6a10 += 1
        else:
            t10m += 1
        
        
    values = [t0a1,t2a3,t4a5,t6a10,t10m]

    data = {
        "values": values
    }
    
    return jsonify(data)

@app.route('/api/grau-academico/<int:id>')
def api_grau_academico(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data
    
    hs = 0
    grad = 0
    mest = 0
    dout = 0
    
    for d in col_data:
        v = d.developer_questionnaire.academic_level.value
        if v == 'high_school':
            hs += 1
        elif v == 'bachelor':
            grad += 1
        elif v == 'master':
            mest += 1
        elif v == 'doctorate':
            dout += 1
            
    values = [hs,grad,mest,dout]
    
    data = {
        "values": values
    }
    
    return jsonify(data)

@app.route('/api/satisfaction/<int:id>')
def api_satisfaction(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data
    
    mi = 0
    i = 0
    n = 0
    s = 0
    ms = 0
    
    for d in col_data:
        v = d.developer_questionnaire.emotion
        match v:
            case 1:
                mi += 1
            case 2:
                i += 1
            case 3:
                n += 1
            case 4:
                s += 1
            case 5:
                ms += 1
                
    values = [mi,i,n,s,ms]
    
    data = {
        "values": values
    }
    
    return jsonify(data)

@app.route('/api/wordcloud/<int:id>')
def api_wordcloud(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data
    
    comments = []
    
    for d in col_data:
        for pt in d.performed_tasks:
            comments.append(pt.comments)
            
        
        comments.append(d.developer_questionnaire.comments)
        
        
    texto_total = " ".join(comments)
    
    import re
    palavras = re.findall(r'\b\w+\b', texto_total.lower())
    
    palavras_filtradas = [p for p in palavras if len(p) > 2]
    
    from collections import Counter
    
    frequencia = Counter(p for p in palavras_filtradas)
    
    lista = [[pa, con] for pa, con in frequencia.items()]
    
    
    return jsonify(lista)
    
@app.route('/api/view_heatmap/<int:id>')
def api_view_heatmap(id):
    print(f"\n--- 1. Rota /api/view_heatmap chamada com ID: {id} ---")
    evaluation = Evaluation.query.get_or_404(id)
    
    # Obter token de administrador uxt
    uxt_admin_login_url = 'https://uxt-stage.liis.com.br/auth/login'
    
    print("--- 2. Tentando autenticar na API externa... ---")
    resposta_admin = requests.post(uxt_admin_login_url, json=credenciais_admin)
    
    if resposta_admin.status_code == 200:
        token = resposta_admin.json().get('access_token')
        print("--- 3. Autenticação bem-sucedida! ---")
        
        url_get_heatmap = f'https://uxt-stage.liis.com.br/view/heatmap/code/{id}'
        headers_admin = {'Authorization': f'Bearer {token}'}
        
        print(f"--- 4. Buscando dados do heatmap na URL: {url_get_heatmap} ---")
        resposta_heatmap = requests.get(url_get_heatmap, headers=headers_admin)
        
        if resposta_heatmap.status_code == 200:
            print("--- 5. SUCESSO! Dados do heatmap recebidos. ---")
            heatmap_data = resposta_heatmap.json()
            
            
            heatmaps = []
            
            if not isinstance(heatmap_data, list):
                print("\n>>> ATENÇÃO: O dado recebido NÃO é uma lista! A lógica de loop pode falhar. <<<\n")

            
            print("--- 7. Iniciando processamento dos dados recebidos... ---")
            for item in heatmap_data:
                page_images = item.get('page_images', [])
                for i in page_images:
                    if isinstance(i, dict):
                        heatmaps.append({
                            "height": i.get("height"),
                            "image": i.get("image"),
                            "points": i.get("points"),
                            "scroll_positions": i.get("scroll_positions"),
                            "url": i.get("url"),
                            "width": i.get("width")
                        })

            return jsonify(heatmaps)
        else:
            print(f"--- ERRO [A]: Falha ao buscar dados do heatmap. Status: {resposta_heatmap.status_code} ---")
            print(f"Resposta de erro da API: {resposta_heatmap.text}")
            return jsonify({"error": "Failed to retrieve heatmap data"}), resposta_heatmap.status_code
    else:
        print(f"--- ERRO [B]: Falha na autenticação. Status: {resposta_admin.status_code} ---")
        print(f"Resposta de erro da API: {resposta_admin.text}")
        return jsonify({"error": "Authentication failed"}), resposta_admin.status_code