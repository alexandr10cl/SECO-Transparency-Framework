"""Endpoints da aprovacao de cenarios personalizados (RF18-RF21, RNF07).

Uma rota de leitura (estado + conteudo, ja em linguagem legivel - nunca JSON
cru na tela) e tres de escrita: aprovar, rejeitar (regenera do zero, decisao
travada em CLAUDE.md) e reprocessar (quando a geracao deu ERROR tecnico, sem
nada para o gestor ter revisado).

Autenticacao: `isLogged()` igual as demais rotas de API, MAIS uma checagem de
posse que nenhuma outra rota de avaliacao neste arquivo faz hoje - RNF03 exige
que o log de origem (e por extensao a aprovacao, mesma tela) fique restrito ao
gestor dono do portal.
"""
from datetime import datetime

from flask import abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.orm import selectinload

from functions import isLogged
from index import app, db
from models import (
    Evaluation, PersonalizedScenario, PortalCollection, SECO_process,
    ScenarioApprovalDecision, ScenarioApprovalLog, StatusScenario, User,
)
from services.scenario_personalization.pipeline import schedule_scenario


def _current_user():
    email = session.get('user_signed_in')
    if not email:
        return None
    return User.query.filter_by(email=email).first()


def _guard(evaluation_id: int):
    """Checagens comuns. Devolve `(evaluation, None)` ou `(None, resposta_de_erro)`."""
    user = _current_user()
    if user is None:
        return None, (jsonify({"error": "User not authenticated", "details": "Login required"}), 401)

    evaluation = Evaluation.query.get(evaluation_id)
    if evaluation is None:
        return None, (jsonify({"error": "Evaluation not found", "evaluation_id": evaluation_id}), 404)

    if evaluation.user_id != user.user_id:
        return None, (jsonify({"error": "Forbidden", "details": "This evaluation belongs to another manager."}), 403)

    return evaluation, None


def _serialize_log(entry: ScenarioApprovalLog) -> dict:
    return {
        "decision": entry.decision.value,
        "reviewer": entry.reviewer.email if entry.reviewer else None,
        "comment": entry.comment,
        "decided_at": entry.decided_at.isoformat() + "Z" if entry.decided_at else None,
    }


def _serialize_scenario(scenario: PersonalizedScenario, task, guideline) -> dict:
    return {
        "task_id": scenario.task_id,
        "task_title": task.title if task else scenario.cenario_base_title_snapshot,
        "guideline_title": guideline.title if guideline else None,
        "status": scenario.status.value,
        "cenario_personalizado": scenario.cenario_personalizado,
        "etapas_omitidas": scenario.etapas_omitidas or [],
        "recursos_removidos_validacao": scenario.recursos_removidos_validacao or [],
        "error": scenario.error_message,
        "generated_at": scenario.generated_at.isoformat() + "Z" if scenario.generated_at else None,
        # RF22 (log de origem): rastreabilidade recurso -> campo do JSON estruturado
        # que o sustenta, e o snapshot dos inputs usados nesta geracao - Task.title/
        # description e Evaluation.seco_portal_description sao editaveis depois, o
        # snapshot e o unico jeito de saber o que foi realmente usado nesta versao.
        "justificativas": scenario.justificativas or [],
        "recursos_confirmados": scenario.recursos_confirmados or [],
        "cenario_base_title_snapshot": scenario.cenario_base_title_snapshot,
        "cenario_base_description_snapshot": scenario.cenario_base_description_snapshot,
        "manager_description_snapshot": scenario.manager_description_snapshot,
        "provider": scenario.provider,
        "model": scenario.model,
        "approval_history": [_serialize_log(e) for e in scenario.approval_log],
    }


def _tasks_and_guidelines(evaluation: Evaluation) -> dict:
    """{task_id: (task, guideline)} - mesma resolucao 1:1 de serializers.guideline_for_task,
    mas ja carregada em massa para nao repetir a mesma travessia por task."""
    result = {}
    for process in evaluation.seco_processes:
        guideline = process.guidelines[0] if process.guidelines else None
        for task in process.tasks:
            result[task.task_id] = (task, guideline)
    return result


@app.route('/evaluations/<int:evaluation_id>/scenarios')
def evaluation_scenarios(evaluation_id: int):
    """Tela dedicada de personalizacao de cenarios - e para onde o cadastro do
    portal redireciona agora (RF21), em vez da lista de avaliacoes. Mesmos
    componentes de `eval.html` (`.scenario-panel`, `#collection-info`,
    scenario_approval.js), aqui como o conteudo principal da pagina - com um
    stepper mostrando em qual etapa do pipeline a avaliacao esta - em vez de
    uma secao a mais entre varias outras.
    """
    if not isLogged():
        flash('Please sign in to access this page.', 'warning')
        return redirect(url_for('signin'))

    evaluation = Evaluation.query.options(
        selectinload(Evaluation.seco_processes).selectinload(SECO_process.guidelines),
        selectinload(Evaluation.seco_processes).selectinload(SECO_process.tasks),
    ).get(evaluation_id)
    if evaluation is None:
        abort(404)

    user = _current_user()
    if user is None or evaluation.user_id != user.user_id:
        abort(403)

    procedures_data = [
        {
            "process": process,
            "guideline": process.guidelines[0] if process.guidelines else None,
            "tasks": process.tasks,
        }
        for process in evaluation.seco_processes
    ]

    return render_template(
        'scenario_status.html', evaluation=evaluation, procedures_data=procedures_data
    )


@app.route('/api/scenarios/<int:evaluation_id>')
def api_scenarios(evaluation_id: int):
    """Estado da coleta + um cartao por task selecionada, em linguagem legivel."""
    evaluation, error = _guard(evaluation_id)
    if error:
        return error

    collection = PortalCollection.query.filter_by(evaluation_id=evaluation_id).first()
    tasks_by_id = _tasks_and_guidelines(evaluation)

    scenarios = (
        PersonalizedScenario.query
        .filter_by(evaluation_id=evaluation_id)
        .order_by(PersonalizedScenario.task_id)
        .all()
    )
    scenario_task_ids = {s.task_id for s in scenarios}

    payload_scenarios = [
        _serialize_scenario(s, *tasks_by_id.get(s.task_id, (None, None)))
        for s in scenarios
    ]
    # Tasks selecionadas que ainda nao ganharam nem uma linha de PersonalizedScenario
    # (a coleta ainda nao terminou, ou a avaliacao acabou de ser criada) - a tela
    # precisa mostrar "gerando..." pra elas tambem, nao so silencio.
    for task_id, (task, guideline) in tasks_by_id.items():
        if task_id in scenario_task_ids:
            continue
        payload_scenarios.append({
            "task_id": task_id,
            "task_title": task.title,
            "guideline_title": guideline.title if guideline else None,
            "status": "PENDING",
            "cenario_personalizado": None,
            "etapas_omitidas": [],
            "recursos_removidos_validacao": [],
            "error": None,
            "generated_at": None,
            "justificativas": [],
            "recursos_confirmados": [],
            "cenario_base_title_snapshot": None,
            "cenario_base_description_snapshot": None,
            "manager_description_snapshot": None,
            "provider": None,
            "model": None,
            "approval_history": [],
        })
    payload_scenarios.sort(key=lambda s: s["task_id"])

    return jsonify({
        "collection": {
            "status": collection.status.value if collection else "PENDING",
            "modo_coleta": collection.modo_coleta if collection else None,
            "motivos_degradacao": (collection.motivos_degradacao if collection else None) or [],
            "generated_at": (
                collection.generated_at.isoformat() + "Z"
                if collection and collection.generated_at else None
            ),
            "error": collection.error_message if collection else None,
        },
        "scenarios": payload_scenarios,
        "all_approved": bool(payload_scenarios) and all(
            s["status"] == StatusScenario.APPROVED.value for s in payload_scenarios
        ),
    })


@app.route('/api/scenarios/<int:evaluation_id>/<int:task_id>/approve', methods=['POST'])
def api_scenario_approve(evaluation_id: int, task_id: int):
    evaluation, error = _guard(evaluation_id)
    if error:
        return error

    scenario = PersonalizedScenario.query.filter_by(evaluation_id=evaluation_id, task_id=task_id).first()
    if scenario is None:
        return jsonify({"error": "Scenario not found"}), 404
    if scenario.status != StatusScenario.AWAITING_APPROVAL:
        return jsonify({
            "error": "Scenario is not awaiting approval",
            "details": f"current status: {scenario.status.value}",
        }), 409

    user = _current_user()
    scenario.status = StatusScenario.APPROVED
    db.session.add(ScenarioApprovalLog(
        personalized_scenario_id=scenario.id,
        decision=ScenarioApprovalDecision.APPROVED,
        reviewer_user_id=user.user_id,
        decided_at=datetime.utcnow(),
    ))
    db.session.commit()

    return api_scenarios(evaluation_id)


@app.route('/api/scenarios/<int:evaluation_id>/<int:task_id>/reject', methods=['POST'])
def api_scenario_reject(evaluation_id: int, task_id: int):
    """Rejeita e regenera do zero (chamadas 1 e 2 de novo) - decisao travada em
    CLAUDE.md: nao ha edicao previa pelo gestor antes de tentar de novo."""
    evaluation, error = _guard(evaluation_id)
    if error:
        return error

    scenario = PersonalizedScenario.query.filter_by(evaluation_id=evaluation_id, task_id=task_id).first()
    if scenario is None:
        return jsonify({"error": "Scenario not found"}), 404
    if scenario.status != StatusScenario.AWAITING_APPROVAL:
        return jsonify({
            "error": "Scenario is not awaiting approval",
            "details": f"current status: {scenario.status.value}",
        }), 409

    body = request.get_json(silent=True) or {}
    user = _current_user()
    db.session.add(ScenarioApprovalLog(
        personalized_scenario_id=scenario.id,
        decision=ScenarioApprovalDecision.REJECTED,
        reviewer_user_id=user.user_id,
        comment=(body.get("comment") or None),
        decided_at=datetime.utcnow(),
    ))
    db.session.commit()

    result = schedule_scenario(evaluation_id, task_id)
    return jsonify({**api_scenarios(evaluation_id).get_json(), "schedule": result})


@app.route('/api/scenarios/<int:evaluation_id>/<int:task_id>/retry', methods=['POST'])
def api_scenario_retry(evaluation_id: int, task_id: int):
    """Tenta gerar de novo depois de uma falha TECNICA (status ERROR) - sem
    log de aprovacao, porque nao houve nada para o gestor revisar e rejeitar."""
    evaluation, error = _guard(evaluation_id)
    if error:
        return error

    scenario = PersonalizedScenario.query.filter_by(evaluation_id=evaluation_id, task_id=task_id).first()
    if scenario is None or scenario.status != StatusScenario.ERROR:
        return jsonify({
            "error": "Scenario is not in an error state",
            "details": f"current status: {scenario.status.value if scenario else 'NONE'}",
        }), 409

    result = schedule_scenario(evaluation_id, task_id)
    return jsonify({**api_scenarios(evaluation_id).get_json(), "schedule": result})
