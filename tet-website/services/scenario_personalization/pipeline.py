"""Orquestracao do pipeline de personalizacao de cenarios (RF21, RNF01, RNF02).

Pontos de entrada usados pelo resto do app:

    schedule_evaluation(evaluation_id)         agenda a avaliacao inteira: coleta
                                                 (uma vez) + um cenario por task
                                                 selecionada (em sequencia)
    schedule_scenario(evaluation_id, task_id)   regenera UM cenario avulso, reusando
                                                 a coleta ja existente - e o que a
                                                 rejeicao do gestor chama (Fase 4/6):
                                                 "rejeitar regenera do zero (chamadas
                                                 1 e 2), nao a coleta" (CLAUDE.md)

Execucao em background segue o mesmo molde de `services/ai/pipeline.py` e
`services/heatmap_prefetch.py`: ThreadPoolExecutor com `app.app_context()` dentro
do worker, status da linha do banco como lock contra disparo duplo, RUNNING
travado ha tempo demais vira ERROR e libera nova tentativa.

Dois niveis de granularidade (models/portal_collection.py,
models/personalized_scenario.py):
  - PortalCollection: uma vez por avaliacao (modulos 1-2: coleta + estruturacao).
  - PersonalizedScenario: uma vez por (avaliacao, task) - so roda depois que a
    coleta da avaliacao estiver DONE (modulos 3-4: personalizacao + validacao).

As tasks de uma mesma avaliacao rodam em SEQUENCIA dentro do worker de
`schedule_evaluation`, uma de cada vez - decisao deliberada (mais simples de
depurar erro parcial e de raciocinar sobre o estado do banco); o tempo total
ate a avaliacao ficar pronta pra aprovacao cresce com o numero de tasks
selecionadas, mas nada trava a UI do gestor nem a sessao do avaliador (RNF01
so exige isso).
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from index import app, db
from models import (
    Evaluation, PersonalizedScenario, PortalCollection, StatusCollection,
    StatusScenario, Task,
)
from services.scenario_personalization import coleta, estruturacao, personalizacao, validacao
from services.scenario_personalization.serializers import guideline_for_task, serialize_guideline

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='scenario-personalization')

_schedule_lock = threading.Lock()

# Coleta pode legitimamente levar minutos num portal grande (ate 25 paginas,
# ConfigColeta padrao) - teto mais folgado que o da analise de IA (10min).
COLLECTION_STALE_AFTER = timedelta(minutes=15)

# So personalizacao (2 chamadas de IA) - no teste real da Fase 1, ~30s.
SCENARIO_STALE_AFTER = timedelta(minutes=5)


# ---------------------------------------------------------------------------
# PortalCollection - estado e lock
# ---------------------------------------------------------------------------

def _get_collection(evaluation_id: int, for_update: bool = False) -> Optional[PortalCollection]:
    query = PortalCollection.query.filter_by(evaluation_id=evaluation_id)
    if for_update:
        query = query.with_for_update()
    return query.first()


def _collection_is_stale(collection: PortalCollection) -> bool:
    if collection.status != StatusCollection.RUNNING:
        return False
    if collection.started_at is None:
        return True
    return datetime.utcnow() - collection.started_at > COLLECTION_STALE_AFTER


def _tasks_for_evaluation(evaluation: Evaluation) -> List[Task]:
    """Uma task por processo selecionado, deduplicada - cada task e um cenario-base."""
    seen: set[int] = set()
    tasks: List[Task] = []
    for process in evaluation.seco_processes:
        for task in process.tasks:
            if task.task_id in seen:
                continue
            seen.add(task.task_id)
            tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# PersonalizedScenario - estado e lock
# ---------------------------------------------------------------------------

def _get_scenario(evaluation_id: int, task_id: int, for_update: bool = False) -> Optional[PersonalizedScenario]:
    query = PersonalizedScenario.query.filter_by(evaluation_id=evaluation_id, task_id=task_id)
    if for_update:
        query = query.with_for_update()
    return query.first()


def _scenario_is_stale(scenario: PersonalizedScenario) -> bool:
    if scenario.status != StatusScenario.RUNNING:
        return False
    if scenario.started_at is None:
        return True
    return datetime.utcnow() - scenario.started_at > SCENARIO_STALE_AFTER


def _mark_scenario_running(evaluation_id: int, task_id: int, portal_collection_id: int) -> PersonalizedScenario:
    """Cria (ou reaproveita) a linha, marca RUNNING e comita. Chamado ja dentro
    de uma secao que decidiu que pode prosseguir - nao faz nenhuma checagem de
    lock sozinho, isso e responsabilidade de quem chama."""
    scenario = _get_scenario(evaluation_id, task_id)
    if scenario is None:
        scenario = PersonalizedScenario(
            evaluation_id=evaluation_id,
            task_id=task_id,
            portal_collection_id=portal_collection_id,
        )
        db.session.add(scenario)
    scenario.status = StatusScenario.RUNNING
    scenario.started_at = datetime.utcnow()
    scenario.error_message = None
    db.session.commit()
    return scenario


# ---------------------------------------------------------------------------
# Agendamento - avaliacao inteira
# ---------------------------------------------------------------------------

def schedule_evaluation(evaluation_id: int) -> Dict[str, Any]:
    """Agenda coleta + personalizacao de todas as tasks da avaliacao.

    Chamado uma unica vez, no cadastro do portal (RF21) - ver hook em
    `views/index.py:create_evaluation`. Se ja houver uma coleta rodando para
    esta avaliacao, nao dispara outra.
    """
    with _schedule_lock:
        collection = _get_collection(evaluation_id, for_update=True)

        if collection is not None and collection.status == StatusCollection.RUNNING:
            if not _collection_is_stale(collection):
                db.session.rollback()
                return {"status": StatusCollection.RUNNING.value, "already_running": True}
            app.logger.warning(
                "scenario-personalization: coleta travada na avaliacao %s desde %s; reiniciando.",
                evaluation_id, collection.started_at,
            )

        if collection is None:
            collection = PortalCollection(evaluation_id=evaluation_id)
            db.session.add(collection)

        collection.status = StatusCollection.RUNNING
        collection.started_at = datetime.utcnow()
        collection.error_message = None
        db.session.commit()

    _executor.submit(_run_evaluation, evaluation_id)
    return {"status": StatusCollection.RUNNING.value, "already_running": False}


def _run_evaluation(evaluation_id: int) -> None:
    """Worker do executor: coleta + estruturacao, depois uma task de cada vez.

    Nunca levanta - toda falha vira ERROR na linha correspondente (coleta ou
    cenario individual). Uma task falhar nao impede as demais.
    """
    with app.app_context():
        try:
            collection = _collect(evaluation_id)
        except Exception as exc:  # noqa: BLE001 - falha na coleta precisa virar ERROR
            app.logger.exception("scenario-personalization: falha na coleta da avaliacao %s", evaluation_id)
            _fail_collection(evaluation_id, exc)
            return

        evaluation = Evaluation.query.get(evaluation_id)
        if evaluation is None:  # avaliacao apagada no meio da execucao
            return

        for task in _tasks_for_evaluation(evaluation):
            scenario = _get_scenario(evaluation_id, task.task_id)
            if scenario is not None and scenario.status == StatusScenario.RUNNING and not _scenario_is_stale(scenario):
                continue  # ja sendo gerado por uma regeneracao avulsa concorrente

            _mark_scenario_running(evaluation_id, task.task_id, collection.id)
            try:
                _generate_scenario(evaluation_id, task.task_id, model=None)
            except Exception as exc:  # noqa: BLE001 - uma task falhar nao pode derrubar as outras
                app.logger.exception(
                    "scenario-personalization: falha ao gerar cenario (avaliacao %s, task %s)",
                    evaluation_id, task.task_id,
                )
                _fail_scenario(evaluation_id, task.task_id, exc)


def _collect(evaluation_id: int) -> PortalCollection:
    """Modulos 1-2 (coleta + estruturacao) e persistencia em PortalCollection."""
    evaluation = Evaluation.query.get(evaluation_id)
    if evaluation is None:
        raise RuntimeError(f"avaliacao {evaluation_id} nao encontrada")

    bruta = coleta.coletar(evaluation.seco_portal_url)
    dados_portal = estruturacao.estruturar(bruta)

    collection = _get_collection(evaluation_id)
    collection.status = StatusCollection.DONE
    collection.dados_portal = dados_portal
    collection.modo_coleta = dados_portal["modo_coleta"]
    collection.motivos_degradacao = dados_portal["motivos_degradacao"]
    collection.generated_at = datetime.utcnow()
    db.session.commit()

    app.logger.info(
        "scenario-personalization: coleta da avaliacao %s concluida (modo=%s, %s paginas)",
        evaluation_id, collection.modo_coleta, len(dados_portal["paginas_coletadas"]),
    )
    return collection


def _fail_collection(evaluation_id: int, exc: Exception) -> None:
    try:
        db.session.rollback()
        collection = _get_collection(evaluation_id)
        if collection is None:
            return
        collection.status = StatusCollection.ERROR
        collection.error_message = str(exc)[:2000]
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        app.logger.exception(
            "scenario-personalization: nao consegui registrar erro de coleta da avaliacao %s", evaluation_id
        )


# ---------------------------------------------------------------------------
# Agendamento - um cenario avulso (regeneracao, Fase 4/6)
# ---------------------------------------------------------------------------

def schedule_scenario(evaluation_id: int, task_id: int, model: Optional[str] = None) -> Dict[str, Any]:
    """Regenera UM cenario, reaproveitando a coleta ja existente da avaliacao.

    E o que a rejeicao do gestor chama: "rejeitar regenera o cenario do zero
    (chamadas 1 e 2 rodam de novo)" - nunca reroda a coleta, so a
    personalizacao + validacao desta task. Recusa se a coleta ainda nao
    estiver pronta (`COLLECTION_NOT_READY`) - nao ha o que personalizar sem ela.
    """
    collection = _get_collection(evaluation_id)
    if collection is None or collection.status != StatusCollection.DONE:
        return {"status": "COLLECTION_NOT_READY", "already_running": False}

    with _schedule_lock:
        scenario = _get_scenario(evaluation_id, task_id, for_update=True)

        if scenario is not None and scenario.status == StatusScenario.RUNNING:
            if not _scenario_is_stale(scenario):
                db.session.rollback()
                return {"status": StatusScenario.RUNNING.value, "already_running": True}
            app.logger.warning(
                "scenario-personalization: cenario travado (avaliacao %s, task %s) desde %s; reiniciando.",
                evaluation_id, task_id, scenario.started_at,
            )

        _mark_scenario_running(evaluation_id, task_id, collection.id)

    _executor.submit(_run_single_scenario, evaluation_id, task_id, model)
    return {"status": StatusScenario.RUNNING.value, "already_running": False}


def _run_single_scenario(evaluation_id: int, task_id: int, model: Optional[str]) -> None:
    """Worker do executor para uma regeneracao avulsa."""
    with app.app_context():
        try:
            _generate_scenario(evaluation_id, task_id, model)
        except Exception as exc:  # noqa: BLE001
            app.logger.exception(
                "scenario-personalization: falha ao regenerar cenario (avaliacao %s, task %s)",
                evaluation_id, task_id,
            )
            _fail_scenario(evaluation_id, task_id, exc)


def _generate_scenario(evaluation_id: int, task_id: int, model: Optional[str]) -> None:
    """Modulos 3-4 (personalizacao + validacao) de UMA task e persistencia.

    Assume que a linha ja foi marcada RUNNING e comitada por quem chamou
    (`_mark_scenario_running`, em `_run_evaluation` ou `schedule_scenario`) -
    e assume um `app.app_context()` ja aberto pelo chamador.
    """
    evaluation = Evaluation.query.get(evaluation_id)
    task = Task.query.get(task_id)
    collection = _get_collection(evaluation_id)

    if evaluation is None or task is None:
        raise RuntimeError(f"avaliacao {evaluation_id} ou task {task_id} nao encontrada")
    if collection is None or collection.status != StatusCollection.DONE:
        raise RuntimeError(f"coleta da avaliacao {evaluation_id} nao esta pronta (DONE)")

    guideline = guideline_for_task(task)
    if guideline is None:
        raise RuntimeError(f"task {task_id} nao tem diretriz associada (via processo)")

    cenario_base = personalizacao.CenarioBase(titulo=task.title, descricao=task.description)
    diretriz = serialize_guideline(guideline)

    resultado_modulo3, meta = personalizacao.personalizar(
        cenario_base=cenario_base,
        diretriz=diretriz,
        descricao_gestor=evaluation.seco_portal_description or "",
        dados_portal=collection.dados_portal,
        model=model,
    )
    resultado_final = validacao.montar_resultado_validado(resultado_modulo3, collection.dados_portal)

    scenario = _get_scenario(evaluation_id, task_id)
    scenario.status = StatusScenario.AWAITING_APPROVAL
    scenario.cenario_personalizado = resultado_final["cenario_personalizado"]
    scenario.etapas_omitidas = resultado_final["etapas_omitidas"]
    scenario.recursos_confirmados = resultado_final["recursos_confirmados"]
    scenario.justificativas = resultado_final["justificativas"]
    scenario.recursos_removidos_validacao = resultado_final["recursos_removidos_validacao"]
    scenario.cenario_base_title_snapshot = task.title
    scenario.cenario_base_description_snapshot = task.description
    scenario.manager_description_snapshot = evaluation.seco_portal_description
    scenario.provider = meta.get("provider")
    scenario.model = meta.get("model")
    scenario.tokens_total = meta.get("tokens_total")
    scenario.ai_duration_s = meta.get("ai_duration_s")
    scenario.error_message = None
    scenario.generated_at = datetime.utcnow()
    db.session.commit()

    app.logger.info(
        "scenario-personalization: cenario gerado (avaliacao %s, task %s) - "
        "%s recursos confirmados, %s omitidos, %s removidos na validacao",
        evaluation_id, task_id,
        len(scenario.recursos_confirmados or []),
        len(scenario.etapas_omitidas or []),
        len(scenario.recursos_removidos_validacao or []),
    )


def _fail_scenario(evaluation_id: int, task_id: int, exc: Exception) -> None:
    try:
        db.session.rollback()
        scenario = _get_scenario(evaluation_id, task_id)
        if scenario is None:
            return
        scenario.status = StatusScenario.ERROR
        scenario.error_message = str(exc)[:2000]
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        app.logger.exception(
            "scenario-personalization: nao consegui registrar erro (avaliacao %s, task %s)",
            evaluation_id, task_id,
        )
