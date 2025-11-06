from index import app
from flask import jsonify, session, request
from models import *
from functions import isLogged
import os
import requests
import json
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any, Optional
import traceback

def normalize_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Função utilitária para normalizar timestamps de diferentes formatos para UTC
    
    Args:
        timestamp_str: String do timestamp em vários formatos possíveis
        
    Returns:
        datetime object normalizado para UTC ou None se falhar
    """
    if not timestamp_str:
        return None
        
    try:
        timestamp_str = str(timestamp_str).strip()
        
        # Formato ISO com Z (UTC)
        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.astimezone(pytz.UTC)
            
        # Formato ISO com timezone explícito
        elif '+' in timestamp_str[-6:] or timestamp_str[-6:-3] == '-':
            dt = datetime.fromisoformat(timestamp_str)
            return dt.astimezone(pytz.UTC)
            
        # Formato ISO sem timezone - assumir UTC
        else:
            dt = datetime.fromisoformat(timestamp_str)
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            return dt.astimezone(pytz.UTC)
            
    except (ValueError, AttributeError, TypeError) as e:
        print(f"⚠️ Erro ao normalizar timestamp '{timestamp_str}': {e}")
        return None

def build_task_interval_map(performed_tasks: List) -> Dict[str, Dict]:
    """
    Constrói um mapa otimizado de intervalos de tarefas para busca eficiente
    
    Args:
        performed_tasks: Lista de PerformedTask objects
        
    Returns:
        Dict mapeando performed_task_id para informações da tarefa e intervalos normalizados
    """
    task_map = {}
    
    for pt in performed_tasks:
        try:
            # Normalizar timestamps da performed_task
            initial_ts = normalize_timestamp(str(pt.initial_timestamp))
            final_ts = normalize_timestamp(str(pt.final_timestamp))
            
            if initial_ts and final_ts:
                task_map[pt.performed_task_id] = {
                    'task_id': pt.task_id,
                    'title': pt.task.title,
                    'description': getattr(pt.task, 'description', ''),
                    'performed_task_id': pt.performed_task_id,
                    'initial_timestamp': initial_ts,
                    'final_timestamp': final_ts,
                    'status': pt.status.value if hasattr(pt.status, 'value') else str(pt.status)
                }
                
        except Exception as e:
            print(f"⚠️ Erro ao processar performed_task {pt.performed_task_id}: {e}")
            
    return task_map

def find_active_task_optimized(point_timestamp: datetime, task_intervals: Dict[str, Dict]) -> Optional[Dict]:
    """
    Encontra a tarefa ativa no momento do ponto usando busca otimizada
    
    Args:
        point_timestamp: Timestamp normalizado do ponto
        task_intervals: Mapa de intervalos de tarefas
        
    Returns:
        Dict com informações da tarefa ativa ou None
    """
    for task_info in task_intervals.values():
        if task_info['initial_timestamp'] <= point_timestamp <= task_info['final_timestamp']:
            return {
                'task_id': task_info['task_id'],
                'title': task_info['title'],
                'description': task_info['description'],
                'performed_task_id': task_info['performed_task_id'],
                'status': task_info['status']
            }
    
    return None

def build_navigation_task_map(performed_tasks: List, navigation_data: List) -> Dict[str, Dict]:
    """
    Constrói um mapa de URLs visitadas por tarefa usando dados de navegação
    Versão melhorada com fallback e data quality monitoring
    
    Args:
        performed_tasks: Lista de PerformedTask objects
        navigation_data: Lista de dados de navegação
        
    Returns:
        Dict com task_id como chave e informações da tarefa + URLs como valor
    """
    print(f"🔍 Building navigation task map...")
    print(f"📊 Performed tasks: {len(performed_tasks)}")
    print(f"🧭 Navigation data points: {len(navigation_data)}")
    
    task_url_map = {}
    data_quality_stats = {
        'tasks_with_timestamps': 0,
        'navigation_points_mapped': 0,
        'navigation_points_unmapped': 0,
        'tasks_with_navigation': 0
    }
    
    # Criar mapa de intervalos de tempo das tarefas
    task_intervals = {}
    for pt in performed_tasks:
        initial_ts = normalize_timestamp(str(pt.initial_timestamp))
        final_ts = normalize_timestamp(str(pt.final_timestamp))
        
        if initial_ts and final_ts:
            task_intervals[pt.task_id] = {
                'initial_timestamp': initial_ts,
                'final_timestamp': final_ts,
                'title': pt.task.title,
                'description': getattr(pt.task, 'description', ''),
                'duration_minutes': (final_ts - initial_ts).total_seconds() / 60
            }
            task_url_map[pt.task_id] = {
                'title': pt.task.title,
                'description': getattr(pt.task, 'description', ''),
                'duration_minutes': (final_ts - initial_ts).total_seconds() / 60,
                'navigation_count': 0,
                'url_diversity': set(),
                'urls': set(),
                'initial_timestamp': initial_ts,
                'final_timestamp': final_ts,
                'url_details_map': {}
            }
            data_quality_stats['tasks_with_timestamps'] += 1
        else:
            print(f"⚠️ Task {pt.task_id} has invalid timestamps: {pt.initial_timestamp} -> {pt.final_timestamp}")
    
    print(f"✅ Tasks with valid timestamps: {data_quality_stats['tasks_with_timestamps']}")
    
    # Mapear URLs por tarefa baseado na navegação
    for nav in navigation_data:
        nav_timestamp = normalize_timestamp(nav.get('timestamp'))
        nav_task_id = nav.get('task_id')
        if not nav_timestamp or nav_task_id not in task_url_map:
            data_quality_stats['navigation_points_unmapped'] += 1
            if nav_task_id not in task_url_map:
                print(f"⚠️ Navigation point task_id não encontrado: {nav_task_id}")
            continue
        
        task_data = task_url_map[nav_task_id]
        task_data['urls'].add(nav.get('url'))
        task_data['navigation_count'] += 1
        task_data['url_diversity'].add(nav.get('url'))
        
        url_key = nav.get('url') or 'unknown'
        url_stats = task_data['url_details_map'].setdefault(url_key, {
            'first_seen': nav_timestamp,
            'last_seen': nav_timestamp,
            'count': 0
        })
        url_stats['count'] += 1
        if nav_timestamp < url_stats['first_seen']:
            url_stats['first_seen'] = nav_timestamp
        if nav_timestamp > url_stats['last_seen']:
            url_stats['last_seen'] = nav_timestamp
        
        data_quality_stats['navigation_points_mapped'] += 1
    
    # Converter sets para listas e calcular estatísticas
    for task_id, task_data in task_url_map.items():
        url_details_list = []
        for url, stats in sorted(task_data['url_details_map'].items(), key=lambda item: item[1]['first_seen']):
            url_details_list.append({
                'url': url,
                'first_seen': stats['first_seen'].isoformat() if stats['first_seen'] else None,
                'last_seen': stats['last_seen'].isoformat() if stats['last_seen'] else None,
                'count': stats['count']
            })
        task_data['url_details'] = url_details_list
        task_data['urls'] = [detail['url'] for detail in url_details_list]
        task_data['url_diversity'] = len(task_data['url_diversity'])
        data_quality_stats['tasks_with_navigation'] += 1 if task_data['navigation_count'] > 0 else 0
    
    # Log data quality
    print(f"📈 Data Quality Stats:")
    print(f"   - Tasks with timestamps: {data_quality_stats['tasks_with_timestamps']}")
    print(f"   - Navigation points mapped: {data_quality_stats['navigation_points_mapped']}")
    print(f"   - Navigation points unmapped: {data_quality_stats['navigation_points_unmapped']}")
    print(f"   - Tasks with navigation data: {data_quality_stats['tasks_with_navigation']}")
    
    # Add quality assessment
    quality_score = 0
    if data_quality_stats['tasks_with_timestamps'] > 0:
        quality_score += 40
    if data_quality_stats['navigation_points_mapped'] > 0:
        quality_score += 30
    if data_quality_stats['tasks_with_navigation'] > 0:
        quality_score += 30
    
    print(f"🎯 Navigation tracking quality score: {quality_score}/100")
    
    return task_url_map

def segment_heatmaps_by_tasks(heatmap_data: List, task_url_map: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Segmenta heatmaps por tarefa combinando URLs visitadas e intervalos de tempo
    """
    print("🎯 Segmenting heatmaps by tasks...")
    print(f"📊 Heatmap data items: {len(heatmap_data)}")
    print(f"🧭 Tasks with navigation: {len(task_url_map)}")
    
    segmented_heatmaps = {}
    segmentation_stats = {
        'heatmaps_processed': 0,
        'heatmaps_matched': 0,
        'heatmaps_unmatched': 0,
        'tasks_with_heatmaps': 0
    }
    
    for task_id, task_data in task_url_map.items():
        segmented_heatmaps[task_id] = {
            'task_info': {
                'task_id': task_id,
                'title': task_data['title'],
                'description': task_data['description'],
                'duration_minutes': task_data.get('duration_minutes', 0),
                'navigation_count': task_data.get('navigation_count', 0),
                'url_diversity': task_data.get('url_diversity', 0),
                'urls_visited': task_data['urls'],
                'url_details': task_data.get('url_details', []),
                'initial_timestamp': task_data.get('initial_timestamp'),
                'final_timestamp': task_data.get('final_timestamp')
            },
            'heatmaps': []
        }
    
    def _ranges_overlap(a_start: Optional[datetime], a_end: Optional[datetime], b_start: Optional[datetime], b_end: Optional[datetime]) -> bool:
        if not a_start or not a_end or not b_start or not b_end:
            return False
        return max(a_start, b_start) <= min(a_end, b_end)
    
    for item in heatmap_data:
        if not isinstance(item, dict):
            continue
        page_images = item.get('heatmap_images', [])
        if not isinstance(page_images, list):
            continue
        total_interactions = item.get('total_interactions', len(page_images))
        time_range = item.get('time_range', {})
        heatmap_start = normalize_timestamp(time_range.get('start')) if isinstance(time_range, dict) else None
        heatmap_end = normalize_timestamp(time_range.get('end')) if isinstance(time_range, dict) else None
        
        for page_image in page_images:
            if not isinstance(page_image, dict):
                continue
            page_url = page_image.get('url')
            if not page_url:
                continue
            segmentation_stats['heatmaps_processed'] += 1
            point_timestamps = [normalize_timestamp(p.get('timestamp')) for p in page_image.get('points', []) if p.get('timestamp')]

            candidate_matches = []
            for task_id, task_data in task_url_map.items():
                url_details = task_data.get('url_details_map', {}).get(page_url)
                if not url_details:
                    continue
                range_match = _ranges_overlap(
                    task_data.get('initial_timestamp'),
                    task_data.get('final_timestamp'),
                    heatmap_start or url_details['first_seen'],
                    heatmap_end or url_details['last_seen']
                )
                points_match = False
                if point_timestamps:
                    points_match = any(task_data.get('initial_timestamp') <= ts <= task_data.get('final_timestamp') for ts in point_timestamps if ts)
                if range_match or points_match:
                    confidence = 0
                    if page_url in task_data['urls']:
                        confidence += 0.4
                    if range_match:
                        confidence += 0.3
                    if points_match:
                        confidence += 0.3
                    candidate_matches.append((task_id, confidence, range_match, points_match))

            if not candidate_matches:
                segmentation_stats['heatmaps_unmatched'] += 1
                print(f"⚠️ Heatmap unmatched: {page_url}")
                continue

            candidate_matches.sort(key=lambda x: x[1], reverse=True)
            segmentation_stats['heatmaps_matched'] += 1

            for task_id, confidence_score, range_match, points_match in candidate_matches:
                if confidence_score < 0.5:
                    continue
                match_strategy = 'points+url' if points_match else ('url+range' if range_match else 'url')
                nav_window = task_url_map[task_id].get('url_details_map', {}).get(page_url, {})
                heatmap_item = {
                    'height': page_image.get('height'),
                    'image': page_image.get('image'),
                    'points': page_image.get('points', []),
                    'scroll_positions': page_image.get('scroll_positions'),
                    'url': page_url,
                    'width': page_image.get('width'),
                    'metadata': {
                        'total_points': len(page_image.get('points', [])),
                        'task_id': task_id,
                        'task_title': task_url_map[task_id]['title'],
                        'matched_strategy': match_strategy,
                        'confidence': round(confidence_score, 2),
                        'heatmap_time_range': {
                            'start': heatmap_start.isoformat() if heatmap_start else None,
                            'end': heatmap_end.isoformat() if heatmap_end else None
                        },
                        'navigation_window': {
                            'count': nav_window.get('count'),
                            'first_seen': nav_window.get('first_seen').isoformat() if nav_window.get('first_seen') else None,
                            'last_seen': nav_window.get('last_seen').isoformat() if nav_window.get('last_seen') else None
                        }
                    }
                }
                segmented_heatmaps[task_id]['heatmaps'].append(heatmap_item)
            
            if all(confidence < 0.5 for _, confidence, _, _ in candidate_matches):
                print(f"⚠️ Heatmap candidates below threshold for {page_url}")
                segmentation_stats['heatmaps_unmatched'] += 1

    for task_id, task_data in segmented_heatmaps.items():
        if len(task_data['heatmaps']) > 0:
            segmentation_stats['tasks_with_heatmaps'] += 1

    print(f"📈 Segmentation Stats:")
    print(f"   - Heatmaps processed: {segmentation_stats['heatmaps_processed']}")
    print(f"   - Heatmaps matched: {segmentation_stats['heatmaps_matched']}")
    print(f"   - Heatmaps unmatched: {segmentation_stats['heatmaps_unmatched']}")
    print(f"   - Tasks with heatmaps: {segmentation_stats['tasks_with_heatmaps']}")
    if segmentation_stats['heatmaps_processed'] > 0:
        success_rate = (segmentation_stats['heatmaps_matched'] / segmentation_stats['heatmaps_processed']) * 100
        print(f"🎯 Segmentation success rate: {success_rate:.1f}%")

    return segmented_heatmaps

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

@app.route('/api/portal-familiarity/<int:id>')
def api_portal_familiarity(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data

    never = 0
    rarely = 0
    often = 0
    always = 0

    for d in col_data:
        v = d.developer_questionnaire.previus_xp.value
        if v == 'never':
            never += 1
        elif v == 'rarely':
            rarely += 1
        elif v == 'often':
            often += 1
        elif v == 'aways':  # Note: typo in the enum 'aways' instead of 'always'
            always += 1

    values = [never, rarely, often, always]

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

@app.route('/api/wordcloud/task/<int:evaluation_id>/<int:task_id>')
def api_wordcloud_task(evaluation_id, task_id):
    evaluation = Evaluation.query.get_or_404(evaluation_id)
    comments = []

    # Buscar apenas comentários da task específica
    for d in evaluation.collected_data:
        for pt in d.performed_tasks:
            if pt.task_id == task_id and pt.comments:
                comments.append(pt.comments)

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
            
            # UFPA API returns 'heatmap_images' not 'page_images'
            page_images = item.get('heatmap_images', [])
            print(f"--- Heatmap_images encontradas: {len(page_images)} ---")
            
            if not isinstance(page_images, list):
                print(f"--- ERRO: heatmap_images não é uma lista! Tipo: {type(page_images)} ---")
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

@app.route('/api/heatmap-tasks/<int:evaluation_id>')
def api_heatmap_tasks(evaluation_id):
    """
    API para mapear heatmaps com tarefas executadas durante uma avaliação
    Retorna dados de heatmap enriquecidos com informações das tarefas ativas
    Versão otimizada com melhor tratamento de timestamps e algoritmo eficiente
    """
    print(f"\n🔥 === HEATMAP TASKS API - VERSÃO OTIMIZADA ===")
    print(f"📊 Avaliação ID: {evaluation_id}")
    print(f"⏰ Iniciado em: {datetime.now(pytz.UTC).isoformat()}")
    
    # Verificar autenticação
    if not isLogged():
        print("❌ Usuário não autenticado")
        return jsonify({"error": "User not authenticated", "details": "Login required"}), 401
    
    token = session.get('uxt_access_token')
    if not token:
        print("❌ Token UXT não encontrado")
        return jsonify({"error": "UXT authentication token not found", "details": "Session expired"}), 401
    
    try:
        evaluation = Evaluation.query.get_or_404(evaluation_id)
        print(f"✅ Avaliação encontrada: ID {evaluation.evaluation_id}")
        
        print(f"🔑 Token (primeiros 20 chars): {token[:20]}...")
        
        url_get_heatmap = f'https://uxt-stage.liis.com.br/view/heatmap/code/{evaluation_id}'
        headers_user = {'Authorization': f'Bearer {token}'}
        
        print(f"🌐 Requisitando heatmap: {url_get_heatmap}")
        print(f"🔐 Headers configurados com token")
        
        # Buscar dados do heatmap
        resposta_heatmap = requests.get(url_get_heatmap, headers=headers_user, timeout=60)
        print(f"📡 Status: {resposta_heatmap.status_code} | Content-Type: {resposta_heatmap.headers.get('content-type', 'N/A')}")
        print(f"📦 Tamanho: {len(resposta_heatmap.content)} bytes")
        
        if resposta_heatmap.status_code != 200:
            print(f"❌ Falha no heatmap - Status: {resposta_heatmap.status_code}")
            print(f"📋 Headers: {dict(resposta_heatmap.headers)}")
            print(f"📄 Resposta: {resposta_heatmap.text[:500]}...")
            return jsonify({
                "error": "Failed to retrieve heatmap data", 
                "status_code": resposta_heatmap.status_code,
                "details": resposta_heatmap.text[:200]
            }), resposta_heatmap.status_code
        
        print("✅ Dados do heatmap recebidos com sucesso")
        
        # Parse do JSON
        try:
            heatmap_data = resposta_heatmap.json()
            print("✅ JSON parseado com sucesso")
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao parsear JSON: {e}")
            print(f"📄 Resposta: {resposta_heatmap.text[:300]}...")
            traceback.print_exc()
            return jsonify({"error": "Invalid JSON response", "details": str(e)}), 500
        
        print(f"📊 Tipo dos dados: {type(heatmap_data)} | É lista: {isinstance(heatmap_data, list)}")
        
        # Normalizar dados para lista
        if not isinstance(heatmap_data, list):
            print("🔄 Convertendo dados para lista")
            heatmap_data = [heatmap_data]
        
        # Coletar performed_tasks e dados de navegação
        performed_tasks = []
        navigation_data = []
        for col_data in evaluation.collected_data:
            performed_tasks.extend(col_data.performed_tasks)
            # Coletar dados de navegação
            for nav in col_data.navigation:
                navigation_data.append({
                    'action': nav.action.value if hasattr(nav.action, 'value') else str(nav.action),
                    'url': nav.url,
                    'title': nav.title,
                    'timestamp': nav.timestamp.isoformat(),
                    'task_id': nav.task_id
                })
        
        print(f"📋 Total de performed_tasks encontradas: {len(performed_tasks)}")
        print(f"🧭 Total de dados de navegação encontrados: {len(navigation_data)}")
        
        if not performed_tasks:
            print("⚠️ Nenhuma performed_task encontrada para esta avaliação")
            return jsonify({
                "heatmaps": [],
                "available_tasks": [],
                "message": "No performed tasks found for this evaluation"
            })
        
        # Construir mapa de URLs por tarefa usando dados de navegação
        print("🔧 Construindo mapa de URLs por tarefa usando navegação...")
        task_url_map = build_navigation_task_map(performed_tasks, navigation_data)
        print(f"✅ Mapa construído com {len(task_url_map)} tarefas com URLs mapeadas")
        
        # Criar lista de tarefas únicas para filtros
        unique_tasks = {}
        for pt in performed_tasks:
            if pt.task_id not in unique_tasks:
                unique_tasks[pt.task_id] = {
                    'task_id': pt.task_id,
                    'title': pt.task.title,
                    'description': getattr(pt.task, 'description', '')
                }
        
        print(f"📋 Tarefas únicas criadas: {len(unique_tasks)}")
        
        # Segmentar heatmaps por tarefa usando navegação
        print(f"🔄 Segmentando heatmaps por tarefa usando dados de navegação...")
        segmented_heatmaps = segment_heatmaps_by_tasks(heatmap_data, task_url_map)
        
        # Se não há dados de navegação, usar fallback: mostrar todos os heatmaps
        if not task_url_map and len(performed_tasks) > 0:
            print("⚠️ Nenhum dado de navegação encontrado, usando fallback...")
            print("🔍 Possíveis causas:")
            print("   - Navigation tracking não estava ativo durante a avaliação")
            print("   - Extension não estava instalada ou funcionando")
            print("   - Dados de navegação foram perdidos")
            print("   - Problemas de sincronização entre extensions")
            
            segmented_heatmaps = {
                "all_heatmaps": {
                    "task_info": {
                        "task_id": "all",
                        "title": "All Heatmaps (No Navigation Data)",
                        "description": "Heatmaps without task-specific navigation data. Navigation tracking may not have been active during this evaluation.",
                        "duration_minutes": 0,
                        "navigation_count": 0,
                        "url_diversity": 0,
                        "urls_visited": [],
                        "data_quality_warning": True,
                        "fallback_reason": "No navigation data available"
                    },
                    "heatmaps": []
                }
            }
            
            # Adicionar todos os heatmaps à categoria geral
            for item in heatmap_data:
                if not isinstance(item, dict):
                    continue
                page_images = item.get('heatmap_images', [])
                if not isinstance(page_images, list):
                    continue
                for page_image in page_images:
                    if not isinstance(page_image, dict):
                        continue
                    heatmap_item = {
                        "height": page_image.get("height"),
                        "image": page_image.get("image"),
                        "points": page_image.get("points", []),
                        "scroll_positions": page_image.get("scroll_positions"),
                        "url": page_image.get("url", "Unknown"),
                        "width": page_image.get("width"),
                        "metadata": {
                            "total_points": len(page_image.get("points", [])),
                            "task_id": "all",
                            "task_title": "All Heatmaps"
                        }
                    }
                    segmented_heatmaps["all_heatmaps"]["heatmaps"].append(heatmap_item)
        
        # Calcular estatísticas
        total_heatmaps = sum(len(task_data['heatmaps']) for task_data in segmented_heatmaps.values())
        total_points = sum(
            sum(hm.get('metadata', {}).get('total_points', 0) for hm in task_data['heatmaps'])
            for task_data in segmented_heatmaps.values()
        )
        
        print(f"\n✅ === SEGMENTAÇÃO CONCLUÍDA ===")
        print(f"📊 Total de tarefas com heatmaps: {len(segmented_heatmaps)}")
        print(f"📊 Total de heatmaps segmentados: {total_heatmaps}")
        print(f"🎯 Total de pontos processados: {total_points}")
        print(f"⏰ Processamento finalizado em: {datetime.now(pytz.UTC).isoformat()}")
        print("🔥 === FIM HEATMAP TASKS API ===\n")
        
        # Calcular data quality score
        data_quality_score = 0
        data_quality_warnings = []
        
        if len(navigation_data) > 0:
            data_quality_score += 40
        else:
            data_quality_warnings.append("No navigation data available")
            
        if len(task_url_map) > 0:
            data_quality_score += 30
        else:
            data_quality_warnings.append("No task-URL mapping possible")
            
        if total_heatmaps > 0:
            data_quality_score += 30
        else:
            data_quality_warnings.append("No heatmaps found")
        
        # Resposta final com heatmaps segmentados por tarefa
        metadata = {
            'total_tasks_with_heatmaps': len(segmented_heatmaps),
            'total_heatmaps': total_heatmaps,
            'total_points_processed': total_points,
            'navigation_data_count': len(navigation_data),
            'processed_at': datetime.now(pytz.UTC).isoformat(),
            'evaluation_id': evaluation_id,
            'segmentation_method': 'navigation_and_timestamp' if len(task_url_map) > 0 else 'fallback',
            'data_quality_score': data_quality_score,
            'data_quality_warnings': data_quality_warnings,
            'fallback_used': len(task_url_map) == 0 and len(performed_tasks) > 0
        }
        segmentation_metadata = {
            'heatmaps_processed': total_heatmaps,
            'tasks_with_heatmaps': metadata['total_tasks_with_heatmaps'],
            'navigation_points': len(navigation_data)
        }
        response_data = {
            'segmented_heatmaps': segmented_heatmaps,
            'available_tasks': list(unique_tasks.values()),
            'metadata': metadata,
            'segmentation_metadata': segmentation_metadata
        }
        
        return jsonify(response_data)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição do heatmap: {e}")
        traceback.print_exc()
        return jsonify({"error": "Heatmap request failed", "details": str(e)}), 500
        
    except Exception as e:
        print(f"❌ ERRO GERAL no processamento: {e}")
        traceback.print_exc()
        return jsonify({
            "error": "Processing error", 
            "details": str(e),
            "traceback": traceback.format_exc() if app.debug else None
        }), 500

@app.route('/api/debug-ufpa/<int:evaluation_id>')
def debug_ufpa_raw(evaluation_id):
    """
    Debug endpoint - Retorna RAW data da UFPA sem processamento
    """
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    token = session.get('uxt_access_token')
    if not token:
        return jsonify({"error": "Token not found"}), 401
    
    try:
        evaluation = Evaluation.query.get_or_404(evaluation_id)
        
        url = f'https://uxt-stage.liis.com.br/view/heatmap/code/{evaluation_id}'
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(url, headers=headers, timeout=60)
        
        debug_info = {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type'),
            "content_length": len(response.content),
            "raw_data": response.json() if response.status_code == 200 else response.text[:1000]
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/api/debug-all-navigation')
def debug_all_navigation():
    """
    Debug endpoint - Retorna todos os dados de navegação do sistema
    """
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        # Query all navigation records
        all_navigation = Navigation.query.order_by(Navigation.timestamp.desc()).limit(20).all()
        
        navigation_data = []
        for nav in all_navigation:
            navigation_data.append({
                "action": nav.action.value if hasattr(nav.action, "value") else nav.action,
                "url": nav.url,
                "title": nav.title,
                "timestamp": nav.timestamp.isoformat(),
                "task_id": nav.task_id,
                "collected_data_id": nav.collected_data_id
            })
        
        return jsonify({
            "total_navigation_records": len(navigation_data),
            "navigation_data": navigation_data,
            "message": f"Found {len(navigation_data)} navigation records in system"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/create-test-evaluation')
def create_test_evaluation():
    """
    Create a test evaluation for testing navigation tracking
    """
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        # Create test evaluation
        test_evaluation = Evaluation(
            evaluation_id=999999,
            portal_name="Test Portal",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(hours=1),
            status="active"
        )
        
        # Check if already exists
        existing = Evaluation.query.filter_by(evaluation_id=999999).first()
        if existing:
            return jsonify({
                "message": "Test evaluation already exists",
                "evaluation_id": 999999,
                "status": "ready"
            })
        
        db.session.add(test_evaluation)
        db.session.commit()
        
        return jsonify({
            "message": "Test evaluation created successfully",
            "evaluation_id": 999999,
            "status": "created"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug-evaluation/<int:evaluation_id>')
def debug_evaluation_data(evaluation_id):
    """
    Debug endpoint - Toont alle data van een evaluatie inclusief navigatie
    """
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        evaluation = Evaluation.query.get_or_404(evaluation_id)
        
        # Verzamel alle data
        collected_data = []
        for col_data in evaluation.collected_data:
            col_dict = {
                "collected_data_id": col_data.collected_data_id,
                "start_time": col_data.start_time.isoformat() if col_data.start_time else None,
                "end_time": col_data.end_time.isoformat() if col_data.end_time else None,
                "performed_tasks": [],
                "navigation": []
            }
            
            # Performed tasks
            for pt in col_data.performed_tasks:
                col_dict["performed_tasks"].append({
                    "performed_task_id": pt.performed_task_id,
                    "task_id": pt.task_id,
                    "task_title": pt.task.title,
                    "status": pt.status.value if hasattr(pt.status, 'value') else str(pt.status),
                    "initial_timestamp": pt.initial_timestamp.isoformat() if pt.initial_timestamp else None,
                    "final_timestamp": pt.final_timestamp.isoformat() if pt.final_timestamp else None
                })
            
            # Navigation data
            for nav in col_data.navigation:
                col_dict["navigation"].append({
                    "action": nav.action.value if hasattr(nav.action, 'value') else str(nav.action),
                    "url": nav.url,
                    "title": nav.title,
                    "timestamp": nav.timestamp.isoformat(),
                    "task_id": nav.task_id
                })
            
            collected_data.append(col_dict)
        
        debug_info = {
            "evaluation_id": evaluation_id,
            "evaluation_found": True,
            "collected_data_count": len(collected_data),
            "total_performed_tasks": sum(len(cd["performed_tasks"]) for cd in collected_data),
            "total_navigation_events": sum(len(cd["navigation"]) for cd in collected_data),
            "collected_data": collected_data
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "error": str(e), 
            "traceback": traceback.format_exc(),
            "evaluation_found": False
        }), 500
        
@app.route('/api/get_pksc')
def get_pksc():
    """
    API endpoint to get the KSC based on selected SECO procedures
    """
    
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return jsonify({"error": "No procedure IDs provided"}), 400
    
    ids = [int(i) for i in ids_str.split(',') if i.isdigit()]
    
    # encontrando a guideline de cada processo e depois os ksc de cada guideline
    pksc = []
    for p in ids:
        process = SECO_process.query.get(p)
        if process:
            guideline = process.guidelines[0] if process.guidelines else None
            if guideline:
                for ksc in guideline.key_success_criteria:
                    pksc.append({
                        "process_id": process.seco_process_id,
                        "process_description": process.description,
                        "ksc_id": ksc.key_success_criterion_id,
                        "ksc_title": ksc.title,
                        "ksc_description": ksc.description
                    })
    
    grouped = {}
    for item in pksc:
        pid = str(item['process_id'])
        if pid not in grouped:
            grouped[pid] = {
                "process_description": item["process_description"],
                "ksc_list": []
            }
        grouped[pid]["ksc_list"].append({
            "id": item["ksc_id"],
            "title": item["ksc_title"],
            "description": item["ksc_description"]
        })
        
    return jsonify(grouped)