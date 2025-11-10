from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytz
import requests
from flask import jsonify, session, request

from functions import isLogged
from index import app, db
from models import (
    Evaluation,
    SECO_process,
    Guideline,
    Navigation,
)
from services.heatmap_cache import get_cached_payload, set_cached_payload, get_cache_stats
from services.heatmap_service import (
    build_scenarios_payload,
    build_navigation_task_map,
    segment_heatmaps_by_tasks,
    aggregate_heatmaps_by_url,
    normalize_timestamp,
)

from collections import Counter


# spaCy lazy loading - carrega apenas quando necessário
_nlp_model = None


def get_nlp_model():
    """Lazy load spaCy model para economizar memória"""
    global _nlp_model
    if _nlp_model is None:
        try:
            import spacy

            _nlp_model = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        except Exception:
            app.logger.warning("spaCy not installed. Falling back to basic stopwords.")
            _nlp_model = "fallback"
    return _nlp_model


@app.route('/api/heatmap-scenarios/<int:evaluation_id>')
def api_heatmap_scenarios(evaluation_id: int):
    """Return aggregated heatmap insights by URL (hotspots)."""
    if not isLogged():
        return jsonify({"error": "User not authenticated", "details": "Login required"}), 401

    # 1) Try cache first (prefetch or previous requests)
    cached_payload = get_cached_payload(evaluation_id, 'scenarios')
    if cached_payload:
        payload = dict(cached_payload)
        metadata = payload.setdefault('metadata', {})
        metadata['cached'] = True
        metadata.setdefault('processed_at', datetime.now(pytz.UTC).isoformat())
        return jsonify(payload)

    # 2) No cache available - fetch from UX Tracking API now
    token = session.get('uxt_access_token')
    if not token:
        return jsonify({"error": "UXT authentication token not found", "details": "Session expired"}), 401

    try:
        payload = build_scenarios_payload(evaluation_id, token)
        payload['metadata']['cached'] = False
        set_cached_payload(evaluation_id, 'scenarios', payload)
        return jsonify(payload)
    except requests.exceptions.Timeout:
        app.logger.warning("Timeout while fetching heatmaps for evaluation %s", evaluation_id)
        return jsonify({
            "error": "Request timeout",
            "details": "The UX Tracking API took too long to respond. This may happen with large heatmap datasets.",
            "suggestion": "Try again in a few moments. If the issue persists, contact the UX Tracking team.",
            "timeout_seconds": 120,
        }), 504
    except requests.HTTPError as exc:
        response = exc.response
        status_code = response.status_code if response is not None else 500
        details = response.text[:200] if response is not None else str(exc)
        return jsonify({
            "error": "Failed to retrieve heatmap data",
            "status_code": status_code,
            "details": details,
        }), status_code
    except Exception as exc:  # noqa: BLE001 - broad exception for API safety
        app.logger.exception("Unexpected error while generating heatmap scenarios for %s", evaluation_id)
        return jsonify({
            "error": "Processing error",
            "details": str(exc),
        }), 500


@app.route('/api/guideline/<int:id>')
def api_get_guideline(id):
    guideline = Guideline.query.get_or_404(id)
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
                "examples": [{"description": e.description} for e in k.examples],
            }
            for k in guideline.key_success_criteria
        ],
        "notes": guideline.notes,
    })
    
    
@app.route('/api/experience-data/<int:id>')
def api_experience_data(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data
    
    t0a1 = t2a3 = t4a5 = t6a10 = t10m = 0
    
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
        
    return jsonify({"values": [t0a1, t2a3, t4a5, t6a10, t10m]})


@app.route('/api/grau-academico/<int:id>')
def api_grau_academico(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data

    counts = {
        'high_school': 0,
        'bachelor': 0,
        'master': 0,
        'doctorate': 0,
    }

    for d in col_data:
        level = d.developer_questionnaire.academic_level.value
        if level in counts:
            counts[level] += 1

    return jsonify({"values": [counts['high_school'], counts['bachelor'], counts['master'], counts['doctorate']]})


@app.route('/api/portal-familiarity/<int:id>')
def api_portal_familiarity(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data

    counts = {
        'never': 0,
        'rarely': 0,
        'often': 0,
        'aways': 0,  # note: typo kept for backwards compatibility
    }

    for d in col_data:
        xp = d.developer_questionnaire.previus_xp.value
        if xp in counts:
            counts[xp] += 1

    return jsonify({"values": [counts['never'], counts['rarely'], counts['often'], counts['aways']]} )


@app.route('/api/satisfaction/<int:id>')
def api_satisfaction(id):
    evaluation = Evaluation.query.get_or_404(id)
    col_data = evaluation.collected_data
    
    counts = [0, 0, 0, 0, 0]
    for d in col_data:
        emotion = d.developer_questionnaire.emotion
        if 1 <= emotion <= 5:
            counts[emotion - 1] += 1

    return jsonify({"values": counts})


def process_text_for_wordcloud(text: str, max_words: int = 100) -> List[List[Any]]:
    if not text or text.strip() == "":
        return []

    nlp = get_nlp_model()

    if nlp != "fallback":
        doc = nlp(text.lower())
        filtered = [
            token.text
            for token in doc
            if not token.is_stop
            and not token.is_punct
            and not token.is_space
            and token.is_alpha
            and len(token.text) > 2
        ]
    else:
        import re

        STOPWORDS = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with',
            'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
            'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up',
            'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time',
            'no', 'just', 'him', 'know', 'take', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
            'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'also', 'back',
            'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want',
            'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'was', 'are', 'were', 'been',
            'has', 'had', 'did', 'does', 'de', 'het', 'een', 'van', 'en', 'op', 'dat', 'die', 'voor',
            'met', 'te', 'zijn', 'er', 'aan', 'wordt', 'als', 'ook', 'maar', 'door', 'bij', 'naar', 'om',
            'tot', 'uit', 'werd', 'dan', 'kan', 'heeft', 'niet', 'meer', 'dit', 'deze', 'ze', 'al', 'nog',
            'wel', 'hij', 'over', 'moet', 'twee', 'geen', 'zoals', 'worden', 'alle', 'veel', 'o', 'a', 'e',
            'que', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por',
            'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou',
            'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela',
            'até', 'isso', 'ela', 'entre', 'era'
        }
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        filtered = [word for word in words if len(word) > 2 and word not in STOPWORDS]

    frequency = Counter(filtered)
    return [[word, freq] for word, freq in frequency.most_common(max_words)]


@app.route('/api/wordcloud/<int:id>')
def api_wordcloud(id):
    evaluation = Evaluation.query.get_or_404(id)
    comments: List[str] = []

    for d in evaluation.collected_data:
        comments.extend(pt.comments for pt in d.performed_tasks if pt.comments)
        if d.developer_questionnaire and d.developer_questionnaire.comments:
            comments.append(d.developer_questionnaire.comments)
    
    texto_total = " ".join(comments)
    return jsonify(process_text_for_wordcloud(texto_total, max_words=100))


@app.route('/api/wordcloud/task/<int:evaluation_id>/<int:task_id>')
def api_wordcloud_task(evaluation_id, task_id):
    evaluation = Evaluation.query.get_or_404(evaluation_id)
    comments: List[str] = []

    for d in evaluation.collected_data:
        for pt in d.performed_tasks:
            if pt.task_id == task_id and pt.comments:
                comments.append(pt.comments)

    texto_total = " ".join(comments)
    return jsonify(process_text_for_wordcloud(texto_total, max_words=75))


@app.route('/api/view_heatmap/<int:id>')
def api_view_heatmap(id):
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    token = session.get('uxt_access_token')
    if not token:
        return jsonify({"error": "UXT authentication token not found"}), 401
    
    evaluation = Evaluation.query.get_or_404(id)
    try:
        data = requests.get(
            f'https://uxt-stage.liis.com.br/view/heatmap/code/{id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=120,
        )
        data.raise_for_status()
        payload = data.json()
        heatmap_data = payload if isinstance(payload, list) else [payload]
        return jsonify(heatmap_data)
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timeout"}), 504
    except requests.exceptions.RequestException as exc:
        return jsonify({"error": str(exc)}), 500


@app.route('/api/heatmap-tasks/<int:evaluation_id>')
def api_heatmap_tasks(evaluation_id):
    if not isLogged():
        return jsonify({"error": "User not authenticated", "details": "Login required"}), 401
    
    token = session.get('uxt_access_token')
    if not token:
        return jsonify({"error": "UXT authentication token not found", "details": "Session expired"}), 401
    
    try:
        evaluation = Evaluation.query.get_or_404(evaluation_id)
        response = requests.get(
            f'https://uxt-stage.liis.com.br/view/heatmap/code/{evaluation_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        heatmap_data = payload if isinstance(payload, list) else [payload]

        performed_tasks: List[Any] = []
        navigation_data: List[Dict[str, Any]] = []
        for col_data in evaluation.collected_data:
            performed_tasks.extend(col_data.performed_tasks)
            for nav in col_data.navigation:
                navigation_data.append({
                    'action': nav.action.value if hasattr(nav.action, 'value') else str(nav.action),
                    'url': nav.url,
                    'title': nav.title,
                    'timestamp': nav.timestamp.isoformat(),
                    'task_id': nav.task_id,
                    'collected_data_id': nav.collected_data_id,
                })
        
        if not performed_tasks:
            return jsonify({
                "heatmaps": [],
                "available_tasks": [],
                "message": "No performed tasks found for this evaluation",
            })
        
        task_url_map = build_navigation_task_map(performed_tasks, navigation_data)
        unique_tasks = {
            pt.task_id: {
                    'task_id': pt.task_id,
                    'title': pt.task.title,
                'description': getattr(pt.task, 'description', ''),
            }
            for pt in performed_tasks
                }
        
        segmented_heatmaps = segment_heatmaps_by_tasks(heatmap_data, task_url_map)
        
        if not task_url_map and performed_tasks:
            fallback = {
                "all_heatmaps": {
                    "task_info": {
                        "task_id": "all",
                        "title": "All Heatmaps (No Navigation Data)",
                        "description": "Heatmaps without task-specific navigation data.",
                        "duration_minutes": 0,
                        "navigation_count": 0,
                        "url_diversity": 0,
                        "urls_visited": [],
                        "data_quality_warning": True,
                        "fallback_reason": "No navigation data available",
                    },
                    "heatmaps": [],
                }
            }
            for item in heatmap_data:
                for page_image in item.get('heatmap_images', []):
                    fallback['all_heatmaps']['heatmaps'].append({
                        "height": page_image.get("height"),
                        "image": page_image.get("image"),
                        "points": page_image.get("points", []),
                        "scroll_positions": page_image.get("scroll_positions"),
                        "url": page_image.get("url", "Unknown"),
                        "width": page_image.get("width"),
                        "metadata": {
                            "total_points": len(page_image.get("points", [])),
                            "task_id": "all",
                            "task_title": "All Heatmaps",
                        },
                    })
            segmented_heatmaps = fallback

        total_heatmaps = sum(len(task_data['heatmaps']) for task_data in segmented_heatmaps.values())
        total_points = sum(
            sum(hm.get('metadata', {}).get('total_points', 0) for hm in task_data['heatmaps'])
            for task_data in segmented_heatmaps.values()
        )
        
        metadata = {
            'total_tasks_with_heatmaps': len(segmented_heatmaps),
            'total_heatmaps': total_heatmaps,
            'total_points_processed': total_points,
            'navigation_data_count': len(navigation_data),
            'processed_at': datetime.now(pytz.UTC).isoformat(),
            'evaluation_id': evaluation_id,
        }
        segmentation_metadata = {
            'heatmaps_processed': total_heatmaps,
            'tasks_with_heatmaps': metadata['total_tasks_with_heatmaps'],
            'navigation_points': len(navigation_data),
        }

        return jsonify({
            'segmented_heatmaps': segmented_heatmaps,
            'available_tasks': list(unique_tasks.values()),
            'metadata': metadata,
            'segmentation_metadata': segmentation_metadata,
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Request timeout",
            "details": "The UX Tracking API took too long to respond.",
            "timeout_seconds": 120,
        }), 504
    except requests.exceptions.RequestException as exc:
        return jsonify({
            "error": "Heatmap request failed",
            "details": str(exc),
        }), 500
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("Unexpected error while processing heatmap tasks for %s", evaluation_id)
        return jsonify({
            "error": "Processing error", 
            "details": str(exc),
        }), 500


@app.route('/api/debug-ufpa/<int:evaluation_id>')
def debug_ufpa_raw(evaluation_id):
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    token = session.get('uxt_access_token')
    if not token:
        return jsonify({"error": "Token not found"}), 401
    
    try:
        response = requests.get(
            f'https://uxt-stage.liis.com.br/view/heatmap/code/{evaluation_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=120,
        )
        response.raise_for_status()
        debug_info = {
            "url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type'),
            "content_length": len(response.content),
            "raw_data": response.json(),
        }
        return jsonify(debug_info)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500
        

@app.route('/api/debug-all-navigation')
def debug_all_navigation():
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        all_navigation = Navigation.query.order_by(Navigation.timestamp.desc()).limit(20).all()
        navigation_data: List[Dict[str, Any]] = []
        for nav in all_navigation:
            navigation_data.append({
                "action": nav.action.value if hasattr(nav.action, "value") else nav.action,
                "url": nav.url,
                "title": nav.title,
                "timestamp": nav.timestamp.isoformat(),
                "task_id": nav.task_id,
                "collected_data_id": nav.collected_data_id,
            })
        return jsonify({
            "total_navigation_records": len(navigation_data),
            "navigation_data": navigation_data,
            "message": f"Found {len(navigation_data)} navigation records in system",
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500
        

@app.route('/api/create-test-evaluation')
def create_test_evaluation():
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        test_evaluation = Evaluation(
            evaluation_id=999999,
            portal_name="Test Portal",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(hours=1),
            status="active",
        )
        existing = Evaluation.query.filter_by(evaluation_id=999999).first()
        if existing:
            return jsonify({
                "message": "Test evaluation already exists",
                "evaluation_id": 999999,
                "status": "ready",
            })
        db.session.add(test_evaluation)
        db.session.commit()
        return jsonify({
            "message": "Test evaluation created successfully",
            "evaluation_id": 999999,
            "status": "created",
        })
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500
        

@app.route('/api/debug-evaluation/<int:evaluation_id>')
def debug_evaluation_data(evaluation_id):
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        evaluation = Evaluation.query.get_or_404(evaluation_id)
        collected_data_dump: List[Dict[str, Any]] = []
        for col_data in evaluation.collected_data:
            col_dict: Dict[str, Any] = {
                "collected_data_id": col_data.collected_data_id,
                "start_time": col_data.start_time.isoformat() if col_data.start_time else None,
                "end_time": col_data.end_time.isoformat() if col_data.end_time else None,
                "performed_tasks": [],
                "navigation": [],
            }
            for pt in col_data.performed_tasks:
                col_dict["performed_tasks"].append({
                    "performed_task_id": pt.performed_task_id,
                    "task_id": pt.task_id,
                    "task_title": pt.task.title,
                    "status": pt.status.value if hasattr(pt.status, 'value') else str(pt.status),
                    "initial_timestamp": pt.initial_timestamp.isoformat() if pt.initial_timestamp else None,
                    "final_timestamp": pt.final_timestamp.isoformat() if pt.final_timestamp else None,
                })
            for nav in col_data.navigation:
                col_dict["navigation"].append({
                    "action": nav.action.value if hasattr(nav.action, 'value') else str(nav.action),
                    "url": nav.url,
                    "title": nav.title,
                    "timestamp": nav.timestamp.isoformat(),
                    "task_id": nav.task_id,
                })
            collected_data_dump.append(col_dict)
            
        return jsonify({
            "evaluation_id": evaluation_id,
            "evaluation_found": True,
            "collected_data_count": len(collected_data_dump),
            "total_performed_tasks": sum(len(cd["performed_tasks"]) for cd in collected_data_dump),
            "total_navigation_events": sum(len(cd["navigation"]) for cd in collected_data_dump),
            "collected_data": collected_data_dump,
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({
            "error": str(exc),
            "evaluation_found": False,
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
    
    grouped = {}
    for p in ids:
        process = SECO_process.query.get(p)
        if not process:
            continue

        guideline = process.guidelines[0] if process.guidelines else None
        task = process.tasks[0] if process.tasks else None

        pid = str(process.seco_process_id)
        process_label = f"P{process.seco_process_id} — {process.description}"

        grouped.setdefault(pid, {
            "process_id": process.seco_process_id,
            "process_description": process_label,
            "raw_process_description": process.description,
            "task_id": task.task_id if task else None,
            "task_title": task.title if task else None,
            "task_summary": task.summary if task else None,
            "ksc_list": []
        })

        if not guideline:
            continue

        for ksc in guideline.key_success_criteria:
            grouped[pid]["ksc_list"].append({
                "id": ksc.key_success_criterion_id,
                "title": ksc.title,
                "description": ksc.description
            })

    # Remove groups without KSC entries to avoid empty UI sections
    grouped = {
        pid: data for pid, data in grouped.items()
        if data["ksc_list"]
    }

    return jsonify(grouped)


@app.route('/api/cache/stats')
def api_cache_stats():
    """
    API endpoint to monitor cache health and performance.
    Useful for production monitoring and debugging memory issues.
    """
    if not isLogged():
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        stats = get_cache_stats()
        return jsonify({
            "status": "healthy" if stats['utilization_percent'] < 90 else "warning",
            "cache_stats": stats,
            "recommendations": _get_cache_recommendations(stats),
        })
    except Exception as exc:  # noqa: BLE001
        return jsonify({
            "error": "Failed to retrieve cache stats",
            "details": str(exc),
        }), 500


def _get_cache_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate actionable recommendations based on cache statistics."""
    recommendations = []
    
    utilization = stats.get('utilization_percent', 0)
    if utilization > 90:
        recommendations.append("Cache is near capacity - consider increasing MAX_CACHE_SIZE or implementing Redis")
    
    expired = stats.get('expired_entries', 0)
    if expired > 5:
        recommendations.append(f"{expired} expired entries detected - cleanup will happen on next insertion")
    
    active = stats.get('active_entries', 0)
    if active < 10:
        recommendations.append("Low cache utilization - prefetch may need adjustment")
    
    if not recommendations:
        recommendations.append("Cache is operating optimally")
    
    return recommendations