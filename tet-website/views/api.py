from index import app
from flask import jsonify, session
from models import *
from functions import isLogged
import os
import requests
import json

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
    print(f"\n=== INICIO DEBUG BACKEND HEATMAPS ===")
    print(f"--- 1. Rota /api/view_heatmap chamada com ID: {id} ---")
    print(f"--- Timestamp: {json.dumps(str(__import__('datetime').datetime.now()))} ---")
    
    # Verificar se o usuário está logado
    if not isLogged():
        print("--- ERRO: Usuário não está logado ---")
        return jsonify({"error": "User not authenticated"}), 401
    
    # Obter token da sessão do usuário logado
    token = session.get('uxt_access_token')
    if not token:
        print("--- ERRO: Token UXT não encontrado na sessão ---")
        return jsonify({"error": "UXT authentication token not found"}), 401
    
    evaluation = Evaluation.query.get_or_404(id)
    print(f"--- Avaliação encontrada: {evaluation} ---")
    
    print("--- 2. Usando token da sessão do usuário logado ---")
    print(f"--- Token da sessão (primeiros 20 chars): {token[:20] if token else 'N/A'}... ---")
        
    url_get_heatmap = f'https://uxt-stage.liis.com.br/view/heatmap/code/{id}'
    headers_user = {'Authorization': f'Bearer {token}'}
    
    print(f"--- 3. Buscando dados do heatmap na URL: {url_get_heatmap} ---")
    print(f"--- Headers: Authorization: Bearer {token[:20] if token else 'N/A'}... ---")
    
    try:
        resposta_heatmap = requests.get(url_get_heatmap, headers=headers_user, timeout=60)
        print(f"--- Status da requisição heatmap: {resposta_heatmap.status_code} ---")
        print(f"--- Content-Type da resposta: {resposta_heatmap.headers.get('content-type', 'N/A')} ---")
        print(f"--- Tamanho da resposta: {len(resposta_heatmap.content)} bytes ---")
    except requests.exceptions.RequestException as e:
        print(f"--- ERRO na requisição do heatmap: {e} ---")
        return jsonify({"error": "Heatmap request failed"}), 500
    
    if resposta_heatmap.status_code == 200:
        print("--- 4. SUCESSO! Dados do heatmap recebidos. ---")
        
        try:
            heatmap_data = resposta_heatmap.json()
            print("--- 5. Dados JSON parseados com sucesso ---")
        except json.JSONDecodeError as e:
            print(f"--- ERRO ao parsear JSON: {e} ---")
            print(f"--- Primeiros 500 chars da resposta: {resposta_heatmap.text[:500]} ---")
            return jsonify({"error": "Invalid JSON response"}), 500
        
        print(f"--- Tipo dos dados recebidos: {type(heatmap_data)} ---")
        print(f"--- É lista?: {isinstance(heatmap_data, list)} ---")
        
        if isinstance(heatmap_data, list):
            print(f"--- Quantidade de items na lista: {len(heatmap_data)} ---")
            for idx, item in enumerate(heatmap_data[:3]):  # Mostra só os primeiros 3
                print(f"--- Item {idx}: tipo = {type(item)}, keys = {list(item.keys()) if isinstance(item, dict) else 'N/A'} ---")
        else:
            print(f"--- Dados não são lista. Keys disponíveis: {list(heatmap_data.keys()) if isinstance(heatmap_data, dict) else 'N/A'} ---")
        
        heatmaps = []
        
        if not isinstance(heatmap_data, list):
            print("\n>>> ATENÇÃO: O dado recebido NÃO é uma lista! A lógica de loop pode falhar. <<<")
            print(">>> Convertendo para lista... <<<\n")
            heatmap_data = [heatmap_data]

        print("--- 6. Iniciando processamento dos dados recebidos... ---")
        for idx, item in enumerate(heatmap_data):
            print(f"--- Processando item {idx + 1} de {len(heatmap_data)} ---")
            print(f"--- Tipo do item: {type(item)} ---")
            
            if not isinstance(item, dict):
                print(f"--- AVISO: Item {idx + 1} não é um dicionário! ---")
                continue
            
            print(f"--- Keys do item {idx + 1}: {list(item.keys())} ---")
            
            page_images = item.get('page_images', [])
            print(f"--- Page_images encontradas: {len(page_images)} ---")
            
            if not isinstance(page_images, list):
                print(f"--- ERRO: page_images não é uma lista! Tipo: {type(page_images)} ---")
                continue
            
            for page_idx, i in enumerate(page_images):
                print(f"--- Processando page_image {page_idx + 1} de {len(page_images)} ---")
                
                if isinstance(i, dict):
                    print(f"--- Keys da page_image {page_idx + 1}: {list(i.keys())} ---")
                    
                    # Validações detalhadas
                    width = i.get("width")
                    height = i.get("height")
                    points = i.get("points")
                    image = i.get("image")
                    url = i.get("url")
                    scroll_positions = i.get("scroll_positions")
                    
                    print(f"--- Dimensões: {width}x{height} ---")
                    print(f"--- Pontos: {len(points) if isinstance(points, list) else 'N/A'} ---")
                    print(f"--- Imagem: {len(image) if isinstance(image, str) else 'N/A'} chars ---")
                    print(f"--- URL: {url} ---")
                    print(f"--- Scroll positions: {scroll_positions} ---")
                    
                    # Validação dos pontos
                    if isinstance(points, list) and len(points) > 0:
                        print(f"--- Primeiro ponto: {points[0]} ---")
                        if len(points) > 1:
                            print(f"--- Segundo ponto: {points[1]} ---")
                    
                    heatmap_item = {
                        "height": height,
                        "image": image,
                        "points": points,
                        "scroll_positions": scroll_positions,
                        "url": url,
                        "width": width
                    }
                    
                    heatmaps.append(heatmap_item)
                    print(f"--- Page_image {page_idx + 1} adicionada aos heatmaps ---")
                else:
                    print(f"--- ERRO: page_image {page_idx + 1} não é um dicionário! Tipo: {type(i)} ---")

        print(f"--- 7. Processamento concluído! Total de heatmaps: {len(heatmaps)} ---")
        
        # Log da estrutura final
        for idx, heatmap in enumerate(heatmaps[:2]):  # Mostra só os primeiros 2
            print(f"--- Heatmap final {idx + 1}: {list(heatmap.keys())} ---")
        
        print("--- 8. Retornando dados para o frontend ---")
        print(f"--- Estrutura JSON final: array com {len(heatmaps)} items ---")
        print("=== FIM DEBUG BACKEND HEATMAPS ===\n")

        return jsonify(heatmaps)
    else:
        print(f"--- ERRO: Falha ao buscar dados do heatmap. Status: {resposta_heatmap.status_code} ---")
        print(f"--- Headers da resposta de erro: {dict(resposta_heatmap.headers)} ---")
        print(f"--- Resposta de erro da API: {resposta_heatmap.text[:1000]} ---")  # Primeiros 1000 chars
        return jsonify({"error": "Failed to retrieve heatmap data"}), resposta_heatmap.status_code