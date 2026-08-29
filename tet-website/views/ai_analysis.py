"""Endpoints da camada analitica de IA (Findings e Action Plan do dashboard).

Duas rotas so: uma que le o estado e outra que agenda a geracao. Toda a logica esta em
`services/ai/pipeline.py` — aqui e traducao para HTTP.

Autenticacao segue a convencao do `views/api.py`: `login_required` redireciona com flash,
o que nao serve para JSON, entao a checagem e inline e devolve 401.
"""
from flask import jsonify, request

from config_flags import AI_ANALYSIS, AI_ALLOW_REGENERATE
from functions import isLogged
from index import app
from models import Evaluation
from services.ai import pipeline
from services.ai.provider import available_models

AI_DISABLED_MESSAGE = (
    "Camada analitica de IA desativada. Defina AI_ANALYSIS=True no .env para habilitar."
)


def _guard(evaluation_id: int):
    """Checagens comuns. Devolve uma resposta de erro, ou None quando esta tudo certo."""
    if not isLogged():
        return jsonify({"error": "User not authenticated", "details": "Login required"}), 401
    if not AI_ANALYSIS:
        return jsonify({"error": "AI analysis disabled", "details": AI_DISABLED_MESSAGE}), 404
    if Evaluation.query.get(evaluation_id) is None:
        return jsonify({"error": "Evaluation not found", "evaluation_id": evaluation_id}), 404
    return None


@app.route('/api/ai-analysis/<int:evaluation_id>')
def api_ai_analysis(evaluation_id: int):
    """Estado da analise mais os cards, quando existirem.

    Durante uma regeneracao devolve `status=RUNNING` junto com o resultado anterior, para
    a tela manter os cards atuais em vez de piscar vazia.
    """
    error = _guard(evaluation_id)
    if error:
        return error

    try:
        payload = pipeline.get_status(evaluation_id)
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("ai-analysis: falha lendo a avaliacao %s", evaluation_id)
        return jsonify({"error": "Processing error", "details": str(exc)}), 500

    payload["can_regenerate"] = bool(AI_ALLOW_REGENERATE)
    payload["available_models"] = available_models() if AI_ALLOW_REGENERATE else []
    return jsonify(payload)


@app.route('/api/ai-analysis/<int:evaluation_id>/generate', methods=['POST'])
def api_ai_analysis_generate(evaluation_id: int):
    """Agenda a analise numa thread. 202 quando agendou, 409 quando ja havia uma rodando.

    Regenerar (quando ja existe resultado) exige AI_ALLOW_REGENERATE — e o que impede o
    gestor de queimar chamadas de API em producao clicando no botao.
    """
    error = _guard(evaluation_id)
    if error:
        return error

    try:
        current = pipeline.get_status(evaluation_id)
        is_regeneration = current["status"] not in ("NONE", "ERROR")
        if is_regeneration and not AI_ALLOW_REGENERATE:
            return jsonify({
                "error": "Regeneration disabled",
                "details": "Defina AI_ALLOW_REGENERATE=True no .env para regerar a analise.",
            }), 403

        body = request.get_json(silent=True) or {}
        result = pipeline.schedule(evaluation_id, model=body.get("model"))
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("ai-analysis: falha agendando a avaliacao %s", evaluation_id)
        return jsonify({"error": "Processing error", "details": str(exc)}), 500

    return jsonify(result), 409 if result["already_running"] else 202


@app.route('/api/ai-analysis/<int:evaluation_id>/actions/<int:action_id>', methods=['PATCH'])
def api_ai_action_update(evaluation_id: int, action_id: int):
    """Edita titulo/descricao/where e/ou decisao (aprovar/descartar/resetar) de uma action.

    Campos omitidos no body ficam como estavam. `decision` aceita os valores do enum
    AIReviewStatus (NEW/ACCEPTED/DISMISSED).
    """
    error = _guard(evaluation_id)
    if error:
        return error

    body = request.get_json(silent=True) or {}
    try:
        payload = pipeline.update_action(
            evaluation_id,
            action_id,
            title=body.get("title"),
            description=body.get("description"),
            where=body.get("where"),
            decision=body.get("decision"),
        )
    except pipeline.ActionNotFound as exc:
        return jsonify({"error": "Action not found", "details": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": "Invalid payload", "details": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("ai-analysis: falha editando a action %s", action_id)
        return jsonify({"error": "Processing error", "details": str(exc)}), 500

    return jsonify(payload)


@app.route('/api/ai-analysis/<int:evaluation_id>/actions/<int:action_id>/move', methods=['POST'])
def api_ai_action_move(evaluation_id: int, action_id: int):
    """Troca a posicao da action com a vizinha (setas ▲▼ da UI)."""
    error = _guard(evaluation_id)
    if error:
        return error

    body = request.get_json(silent=True) or {}
    direction = body.get("direction")
    try:
        payload = pipeline.move_action(evaluation_id, action_id, direction)
    except pipeline.ActionNotFound as exc:
        return jsonify({"error": "Action not found", "details": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": "Invalid payload", "details": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("ai-analysis: falha movendo a action %s", action_id)
        return jsonify({"error": "Processing error", "details": str(exc)}), 500

    return jsonify(payload)
