"""Orquestracao da camada analitica: contexto -> IA -> validacao -> persistencia -> leitura.

Este e o unico modulo de `services/ai/` que escreve no banco, e o unico ponto de entrada
que o resto do app usa:

    schedule(evaluation_id, model)   agenda a analise numa thread; idempotente
    get_status(evaluation_id)        estado + payload serializado para a tela
    run_sync(evaluation_id, model)   mesma analise, sincrona (CLI)
    build_dry_run(evaluation_id)     so monta o contexto, sem chamar a API

Execucao em background segue o molde de `services/heatmap_prefetch.py`: ThreadPoolExecutor
com `app.app_context()` dentro do worker.

Quatro regras de operacao, todas com o mesmo motivo — nao deixar o gestor numa tela quebrada:

1. A linha do banco e o lock. `status == RUNNING` impede que duas abas disparem duas analises.
2. Execucao travada expira. RUNNING velho demais vira ERROR e libera nova tentativa; sem
   isso, uma thread que morreu travaria a avaliacao para sempre.
3. Regenerar nao destroi antes da hora. Os findings antigos ficam ate a nova analise dar
   certo; a troca acontece numa transacao so.
4. Falha preserva o resultado anterior. Se havia um DONE, ele continua sendo exibido.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from index import app, db
from models import AIAction, AIAnalysis, AIFinding, AIAnalysisStatus, AIReviewStatus, CollectedData
from services.ai import analyzer, metrics as metrics_mod
from services.ai.context_builder import EvaluationNotAnalyzable, build_context
from services.ai.provider import call_ai, provider_name, resolve_model

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='ai-analysis')

_schedule_lock = threading.Lock()

# Depois disso, um RUNNING e considerado morto (thread derrubada, processo reiniciado).
STALE_AFTER = timedelta(minutes=10)


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------

def _get_analysis(evaluation_id: int, for_update: bool = False) -> Optional[AIAnalysis]:
    query = AIAnalysis.query.filter_by(evaluation_id=evaluation_id)
    if for_update:
        query = query.with_for_update()
    return query.first()


def _is_stale(analysis: AIAnalysis) -> bool:
    if analysis.status != AIAnalysisStatus.RUNNING:
        return False
    if analysis.started_at is None:
        return True
    return datetime.utcnow() - analysis.started_at > STALE_AFTER


def schedule(evaluation_id: int, model: Optional[str] = None) -> Dict[str, Any]:
    """Agenda uma analise. Se ja houver uma rodando, nao dispara outra.

    Devolve `{"status": ..., "already_running": bool}` — o caller decide entre 202 e 409.
    """
    requested = resolve_model(model)

    with _schedule_lock:
        analysis = _get_analysis(evaluation_id, for_update=True)

        if analysis is not None and analysis.status == AIAnalysisStatus.RUNNING:
            if not _is_stale(analysis):
                db.session.rollback()
                return {"status": AIAnalysisStatus.RUNNING.value, "already_running": True}
            app.logger.warning(
                "ai-analysis: execucao travada na avaliacao %s desde %s; reiniciando.",
                evaluation_id, analysis.started_at,
            )

        if analysis is None:
            analysis = AIAnalysis(evaluation_id=evaluation_id)
            db.session.add(analysis)

        analysis.status = AIAnalysisStatus.RUNNING
        analysis.started_at = datetime.utcnow()
        analysis.error_message = None
        db.session.commit()

    _executor.submit(_run, evaluation_id, requested)
    return {"status": AIAnalysisStatus.RUNNING.value, "already_running": False}


def _run(evaluation_id: int, model: str) -> None:
    """Worker da thread. Nunca levanta — falha vira status ERROR no banco."""
    with app.app_context():
        try:
            result = _analyze(evaluation_id, model)
            _persist(evaluation_id, result)
            app.logger.info(
                "ai-analysis: avaliacao %s concluida — %s findings, %s actions, %ss",
                evaluation_id, len(result["findings"]), len(result["actions"]),
                result["ai_duration_s"],
            )
            _echo_debug(evaluation_id, result)
        except Exception as exc:  # noqa: BLE001 - qualquer falha precisa virar ERROR
            app.logger.exception("ai-analysis: falha na avaliacao %s", evaluation_id)
            _fail(evaluation_id, exc)


def _format_debug(evaluation_id: int, result: Dict[str, Any]) -> str:
    """Relatorio de uma geracao, em texto, para o terminal.

    Existe porque o sinal que importa depois de gerar nao e o resultado — e o que o modelo
    ERROU: ID inventado, ksc_id fora do escopo, finding sem action. Isso tudo fica na
    coluna `debug`, que so seria legivel indo no banco ler um JSON. Aqui sai formatado
    assim que a analise termina, nos dois caminhos (botao do dashboard e CLI).

    So imprime as secoes que tem conteudo: numa geracao limpa o bloco e curto.
    """
    debug = result.get("debug") or {}
    findings = result.get("findings") or []
    actions = result.get("actions") or []
    width = 72

    lines = [
        "",
        "=" * width,
        f"AI ANALYSIS DEBUG — avaliacao {evaluation_id}",
        "=" * width,
        f"  modelo      : {result.get('model')} ({result.get('provider')})",
        f"  duracao     : {result.get('ai_duration_s')}s"
        f" · {result.get('tokens_total')} tokens",
        f"  entrada     : {debug.get('evidence_catalog_size')} evidencias no catalogo"
        f" · {debug.get('framework_scope_size')} KSCs no escopo"
        f" · {result.get('participants_total')} participantes",
        f"  saida       : {len(findings)} findings · {len(actions)} actions",
    ]

    rejected_findings = debug.get("rejected_findings") or []
    if rejected_findings:
        lines.append("")
        lines.append(f"  FINDINGS REJEITADOS ({len(rejected_findings)}):")
        for item in rejected_findings:
            lines.append(f"    - \"{item.get('title')}\"")
            lines.append(f"      motivo: {item.get('reason')}")

    invalid_ids = debug.get("invalid_ids_dropped") or {}
    if invalid_ids:
        lines.append("")
        lines.append(f"  IDS DE EVIDENCIA INVENTADOS ({len(invalid_ids)} findings):")
        for finding_id, ids in invalid_ids.items():
            lines.append(f"    - {finding_id}: {', '.join(ids)}")

    rejected_actions = debug.get("rejected_actions") or []
    if rejected_actions:
        lines.append("")
        lines.append(f"  ACTIONS REJEITADAS ({len(rejected_actions)}):")
        for item in rejected_actions:
            lines.append(f"    - \"{item.get('title')}\"")
            lines.append(f"      motivo: {item.get('reason')}")

    uncovered = debug.get("uncovered_findings") or []
    if uncovered:
        lines.append("")
        lines.append(f"  FINDINGS SEM NENHUMA ACTION ({len(uncovered)}):")
        lines.append(f"    {', '.join(uncovered)}")

    if not (rejected_findings or invalid_ids or rejected_actions or uncovered):
        lines.append("")
        lines.append("  Nada rejeitado: todos os findings e actions passaram na validacao.")

    # Modelo que de fato respondeu — a cadeia de fallback pode ter trocado o pedido.
    stage1 = debug.get("stage1") or {}
    requested = stage1.get("model_requested")
    if requested and requested != result.get("model"):
        lines.append("")
        lines.append(f"  ATENCAO: pediu {requested}, respondeu {result.get('model')} (fallback).")

    lines.append("=" * width)
    lines.append("")
    return "\n".join(lines)


def _echo_debug(evaluation_id: int, result: Dict[str, Any]) -> None:
    """Imprime o relatorio sem nunca derrubar a analise por causa de formatacao."""
    try:
        print(_format_debug(evaluation_id, result), flush=True)
    except Exception:  # noqa: BLE001 - relatorio de debug nao pode quebrar a geracao
        app.logger.exception("ai-analysis: falha formatando o debug da avaliacao %s", evaluation_id)


def _fail(evaluation_id: int, exc: Exception) -> None:
    """Marca ERROR sem tocar nos findings/actions ja gravados (regra 4)."""
    try:
        db.session.rollback()
        analysis = _get_analysis(evaluation_id)
        if analysis is None:
            return
        analysis.status = AIAnalysisStatus.ERROR
        analysis.error_message = str(exc)[:2000]
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        app.logger.exception("ai-analysis: nao consegui registrar o erro da avaliacao %s", evaluation_id)


# ---------------------------------------------------------------------------
# Analise
# ---------------------------------------------------------------------------

def _analyze(evaluation_id: int, model: str) -> Dict[str, Any]:
    context = build_context(evaluation_id)
    catalog = context["catalog"]
    scope = context["framework_scope"]
    total_participants = len(context["participants"])

    # o que esta errado?
    findings_raw, meta1 = call_ai(
        analyzer.SYSTEM_FINDINGS, context["prompt"], analyzer.FindingsResponse, model
    )

    # validacao tecnica
    findings, rejected_findings = analyzer.validate_findings(
        findings_raw.findings, catalog, scope
    )

    # -- Metricas dos findings: entram no prompt da etapa 2 como abrangencia ja calculada
    metrics_mod.attach_finding_metrics(findings, catalog, total_participants)

    actions: List[Dict[str, Any]] = []
    rejected_actions: List[Dict[str, Any]] = []
    meta2: Dict[str, Any] = {}

    if findings:
        # -- Etapa 2: o que devemos fazer? (todos os findings de uma vez, para agrupar)
        actions_prompt = analyzer.build_actions_prompt(findings, context["evaluation"])
        actions_raw, meta2 = call_ai(
            analyzer.SYSTEM_ACTIONS, actions_prompt, analyzer.ActionsResponse, model
        )
        actions, rejected_actions = analyzer.validate_actions(actions_raw.actions, findings)
    else:
        app.logger.info(
            "ai-analysis: avaliacao %s sem findings validados — etapa 2 pulada "
            "(resultado valido, secao 12).", evaluation_id,
        )

    uncovered = analyzer.uncovered_findings(findings, actions)
    if uncovered:
        app.logger.warning(
            "ai-analysis: avaliacao %s tem findings sem nenhuma action: %s",
            evaluation_id, uncovered,
        )

    tokens = [
        (meta.get("tokens") or {}).get("total") or 0
        for meta in (meta1, meta2) if meta
    ]

    return {
        "findings": findings,
        "actions": actions,
        "provider": meta1.get("provider") or provider_name(),
        "model": meta1.get("model"),
        "participants_total": total_participants,
        "tokens_total": sum(tokens) or None,
        # `elapsed_s` e a chave do contrato dos providers (services/ai/providers/base.py);
        # aqui a soma das duas etapas vira `ai_duration_s`, o nome que persiste.
        "ai_duration_s": round(sum(m.get("elapsed_s") or 0 for m in (meta1, meta2) if m), 2),
        "debug": {
            # Tamanho da entrada da geracao — util para explicar um resultado magro
            # ("so 12 evidencias no catalogo"), sem ser insumo de nenhuma metrica.
            "evidence_catalog_size": len(catalog),
            "framework_scope_size": len(scope),
            "rejected_findings": rejected_findings,
            "rejected_actions": rejected_actions,
            "uncovered_findings": uncovered,
            "invalid_ids_dropped": {
                f["id"]: f["invalid_ids_dropped"]
                for f in findings if f.get("invalid_ids_dropped")
            },
            "stage1": meta1,
            "stage2": meta2 or None,
        },
    }


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def _persist(evaluation_id: int, result: Dict[str, Any]) -> None:
    """Troca os findings/actions da avaliacao numa transacao so (regra 3)."""
    analysis = _get_analysis(evaluation_id)
    if analysis is None:  # avaliacao apagada no meio da execucao
        return

    # cascade='all, delete-orphan' apaga as linhas antigas e as ligacoes M:N.
    analysis.findings.clear()
    analysis.actions.clear()
    db.session.flush()

    by_code: Dict[str, AIFinding] = {}
    for finding in result["findings"]:
        row = AIFinding(
            analysis=analysis,
            title=finding["title"],
            observation=finding["observation"],
            ksc_id=finding["ksc"]["id"],
            evidence=finding["evidence"],
        )
        db.session.add(row)
        by_code[finding["id"]] = row

    for action in result["actions"]:
        row = AIAction(
            analysis=analysis,
            title=action["title"],
            description=action["description"],
            where_to_act=action["where"],
        )
        row.findings = [by_code[fid] for fid in action["finding_ids"] if fid in by_code]
        db.session.add(row)

    analysis.status = AIAnalysisStatus.DONE
    analysis.error_message = None
    analysis.provider = result["provider"]
    analysis.model = result["model"]
    analysis.participants_total = result["participants_total"]
    analysis.tokens_total = result["tokens_total"]
    analysis.ai_duration_s = result["ai_duration_s"]
    analysis.generated_at = datetime.utcnow()
    analysis.debug = result["debug"]

    db.session.commit()


# ---------------------------------------------------------------------------
# Leitura — as metricas sao recalculadas aqui, nao lidas de colunas
# ---------------------------------------------------------------------------

def _participant_labels(evaluation_id: int) -> Dict[int, str]:
    """{collected_data_id -> "P1"}, na mesma numeracao que o contexto usa no prompt.

    O `evidence` guarda o collected_data_id cru; mostrar "P126" na tela nao diz nada ao
    gestor e nao bate com o "participante P3" que a IA escreveu na observation. A
    numeracao sai da mesma ordem do `context_builder.fetch_participants`.
    """
    rows = (
        db.session.query(CollectedData.collected_data_id)
        .filter(CollectedData.evaluation_id == evaluation_id)
        .order_by(CollectedData.collected_data_id)
        .all()
    )
    return {row[0]: f"P{index}" for index, row in enumerate(rows, start=1)}


def _serialize_finding(
    finding: AIFinding, code: str, total: int, labels: Dict[int, str]
) -> Dict[str, Any]:
    ksc = finding.ksc
    evidence = [
        dict(item, participant=labels.get(item.get("participant_id"), "?"))
        for item in (finding.evidence or [])
    ]
    return {
        "code": code,
        "title": finding.title,
        "observation": finding.observation,
        "ksc": {
            "id": ksc.key_success_criterion_id,
            "title": ksc.title,
            "description": ksc.description,
            "guideline_id": ksc.guideline_id,
            "guideline_title": ksc.guideline.title if ksc.guideline else None,
        },
        "metrics": metrics_mod.compute_finding_metrics(finding.evidence or [], total),
        "evidence": evidence,
    }


def _serialize(analysis: AIAnalysis) -> Dict[str, Any]:
    """Payload da tela. Findings na ordem de insercao, actions por prioridade."""
    total = analysis.participants_total or 0
    labels = _participant_labels(analysis.evaluation_id)

    findings = list(analysis.findings)  # ja ordenados por PK pelo relationship
    code_by_id = {f.ai_finding_id: f"F-{i:02d}" for i, f in enumerate(findings, start=1)}
    serialized_findings = [
        _serialize_finding(f, code_by_id[f.ai_finding_id], total, labels) for f in findings
    ]
    metrics_by_id = {
        f.ai_finding_id: s["metrics"] for f, s in zip(findings, serialized_findings)
    }

    actions = []
    for action in analysis.actions:
        linked = [
            metrics_by_id[f.ai_finding_id]
            for f in action.findings if f.ai_finding_id in metrics_by_id
        ]
        action_metrics = metrics_mod.compute_action_metrics(linked, total)
        actions.append({
            "id": action.ai_action_id,
            "title": action.title,
            "description": action.description,
            "where": action.where_to_act or [],
            "resolves": [
                code_by_id[f.ai_finding_id]
                for f in action.findings if f.ai_finding_id in code_by_id
            ],
            "metrics": action_metrics,
            "priority_score": action_metrics["priority_score"],
            "priority_band": action_metrics["priority_band"],
            "decision": action.decision.value,
            "manual_rank": action.manual_rank,
        })

    # Ordem do plano: manual_rank quando o gestor ja mexeu nas setas, senao prioridade
    # calculada. Actions com manual_rank vem antes das sem (bloco unico, nao intercalado).
    actions.sort(key=lambda a: (
        0 if a["manual_rank"] is not None else 1,
        a["manual_rank"] if a["manual_rank"] is not None else 0,
        -a["priority_score"],
    ))
    for index, action in enumerate(actions, start=1):
        action["code"] = f"A-{index:02d}"

    return {
        "status": analysis.status.value,
        "error": analysis.error_message,
        "provider": analysis.provider,
        "model": analysis.model,
        # utcnow() e ingenuo; o sufixo Z evita o cliente interpretar como hora local.
        "generated_at": (
            analysis.generated_at.isoformat() + "Z" if analysis.generated_at else None
        ),
        "stats": {
            "participants": analysis.participants_total,
            "tokens_total": analysis.tokens_total,
            "ai_duration_s": analysis.ai_duration_s,
        },
        "formulas": {
            "confidence": metrics_mod.CONFIDENCE_FORMULA,
            "priority": metrics_mod.PRIORITY_FORMULA,
        },
        "findings": serialized_findings,
        "actions": actions,
    }


def get_status(evaluation_id: int) -> Dict[str, Any]:
    """Estado atual da analise. Sempre devolve os cards que existirem.

    Durante um RUNNING de regeneracao isso significa devolver o resultado anterior junto
    com o status — a tela mostra os cards antigos com o aviso, em vez de piscar vazia.
    """
    analysis = _get_analysis(evaluation_id)
    if analysis is None:
        return {"status": "NONE", "findings": [], "actions": []}

    if _is_stale(analysis):
        app.logger.warning(
            "ai-analysis: execucao da avaliacao %s expirou sem terminar.", evaluation_id
        )
        analysis.status = AIAnalysisStatus.ERROR
        analysis.error_message = (
            "A analise foi interrompida antes de terminar. Tente gerar de novo."
        )
        db.session.commit()

    return _serialize(analysis)


# ---------------------------------------------------------------------------
# Revisao do gestor — editar, decidir e reordenar actions
# ---------------------------------------------------------------------------

class ActionNotFound(Exception):
    """A action nao existe ou nao pertence a avaliacao informada."""


_DECISION_VALUES = {status.value for status in AIReviewStatus}


def _get_action(evaluation_id: int, action_id: int) -> AIAction:
    action = (
        AIAction.query
        .join(AIAnalysis)
        .filter(
            AIAnalysis.evaluation_id == evaluation_id,
            AIAction.ai_action_id == action_id,
        )
        .first()
    )
    if action is None:
        raise ActionNotFound(f"Action {action_id} nao encontrada na avaliacao {evaluation_id}")
    return action


def update_action(
    evaluation_id: int,
    action_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    where: Optional[List[str]] = None,
    decision: Optional[str] = None,
) -> Dict[str, Any]:
    """Edita titulo/descricao/where e/ou muda a decisao (aprovar/descartar/resetar).

    Campos omitidos (None) ficam como estavam. Devolve o payload completo da tela, ja
    que uma mudanca aqui pode afetar o `planPanel` (filtro por decision=ACCEPTED).
    """
    action = _get_action(evaluation_id, action_id)

    if title is not None:
        action.title = title
    if description is not None:
        action.description = description
    if where is not None:
        action.where_to_act = where
    if decision is not None:
        if decision not in _DECISION_VALUES:
            raise ValueError(f"decision invalida: {decision}")
        action.decision = AIReviewStatus(decision)

    db.session.commit()
    return get_status(evaluation_id)


def move_action(evaluation_id: int, action_id: int, direction: str) -> Dict[str, Any]:
    """Troca a posicao da action com a vizinha (setas da UI).

    Le a ordem ja serializada (a mesma que a tela mostra) para achar o vizinho correto —
    inclusive quando nenhuma action tem manual_rank ainda, caso em que este e o primeiro
    movimento manual e o rank precisa ser inicializado para todas.
    """
    if direction not in ("up", "down"):
        raise ValueError(f"direction invalida: {direction}")

    analysis = _get_analysis(evaluation_id)
    if analysis is None:
        raise ActionNotFound(f"Avaliacao {evaluation_id} sem analise de IA")

    current = _serialize(analysis)["actions"]
    codes = [a["id"] for a in current]
    if action_id not in codes:
        raise ActionNotFound(f"Action {action_id} nao encontrada na avaliacao {evaluation_id}")

    index = codes.index(action_id)
    swap_index = index - 1 if direction == "up" else index + 1
    if swap_index < 0 or swap_index >= len(codes):
        return get_status(evaluation_id)  # ja esta na ponta, nada a fazer

    # Inicializa o rank de todas pela ordem atual (automatica ou ja parcialmente manual),
    # depois troca as duas posicoes envolvidas no movimento.
    by_id = {row.ai_action_id: row for row in analysis.actions}
    for rank, entry in enumerate(current, start=1):
        by_id[entry["id"]].manual_rank = rank

    a_id, b_id = codes[index], codes[swap_index]
    by_id[a_id].manual_rank, by_id[b_id].manual_rank = (
        by_id[b_id].manual_rank, by_id[a_id].manual_rank,
    )

    db.session.commit()
    return get_status(evaluation_id)


# ---------------------------------------------------------------------------
# Entradas sincronas — CLI
# ---------------------------------------------------------------------------

def run_sync(evaluation_id: int, model: Optional[str] = None) -> Dict[str, Any]:
    """Roda a analise no processo atual e persiste. Levanta em caso de falha."""
    requested = resolve_model(model)
    analysis = _get_analysis(evaluation_id)
    if analysis is None:
        analysis = AIAnalysis(evaluation_id=evaluation_id)
        db.session.add(analysis)
    analysis.status = AIAnalysisStatus.RUNNING
    analysis.started_at = datetime.utcnow()
    analysis.error_message = None
    db.session.commit()

    try:
        result = _analyze(evaluation_id, requested)
        _persist(evaluation_id, result)
    except Exception as exc:
        _fail(evaluation_id, exc)
        raise

    _echo_debug(evaluation_id, result)
    return get_status(evaluation_id)


def build_dry_run(evaluation_id: int) -> Dict[str, Any]:
    """Monta o contexto sem chamar a API — para iterar no prompt de graca."""
    context = build_context(evaluation_id)
    by_type: Dict[str, int] = {}
    for record in context["catalog"].values():
        by_type[record["type"]] = by_type.get(record["type"], 0) + 1
    return {
        "prompt": context["prompt"],
        "participants": len(context["participants"]),
        "evidence_catalog_size": len(context["catalog"]),
        "framework_scope_size": len(context["framework_scope"]),
        "catalog_by_type": by_type,
    }
