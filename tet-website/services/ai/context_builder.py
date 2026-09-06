"""
Montagem do catálogo de evidências e do contexto que vai para o modelo de IA.

um dicionario unico {id_prefixado -> registro}, onde o id prefixado (PT-591, NAV-476, ANS-1722,
DQ-115, DBT-42) resolve a colisao entre PKs de tabelas diferentes — `performed_task 591` e
`navigation 591` existem os dois — e da a rastreabilidade.

O contexto enviado ao modelo renderiza cada dado ja prefixado pelo seu id, entao nao
existe duplicacao entre "catalogo" e "narrativa", e a validacao depois confere ID por ID
contra este mesmo dicionario.

Fora do escopo por enquanto: heatmaps.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qsl, urlsplit

from index import db
from models import (
    Answer,
    CollectedData,
    DeveloperQuestionnaire,
    Doubt,
    Evaluation,
    Guideline,
    EvaluationCriterionWheight,
    Key_success_criterion,
    Navigation,
    PerformedTask,
    Question,
    Task,
)


class EvaluationNotAnalyzable(Exception):
    """A avaliacao existe mas nao tem o que analisar (nenhuma sessao coletada)."""


# ---------------------------------------------------------------------------
# 1) Metadados da avaliacao
# ---------------------------------------------------------------------------

def fetch_evaluation(evaluation_id: int) -> Evaluation:
    evaluation = Evaluation.query.get(evaluation_id)
    if evaluation is None:
        raise EvaluationNotAnalyzable(f"Avaliacao {evaluation_id} nao existe.")
    return evaluation


def fetch_participants(evaluation_id: int) -> List[CollectedData]:
    return (
        CollectedData.query
        .filter_by(evaluation_id=evaluation_id)
        .order_by(CollectedData.collected_data_id)
        .all()
    )


# ---------------------------------------------------------------------------
# 2) Escopo do framework -> lista fechada de ksc_id permitidos
# ---------------------------------------------------------------------------

def fetch_framework_scope(evaluation_id: int) -> List[Dict[str, Any]]:
    """KSCs que o gestor selecionou/pesou para esta avaliacao.

    E esta lista - e nao o catalogo inteiro de KSCs - que vai ao prompt e que define os
    ksc_id aceitos na validacao (principio framework-anchored, secao 2.2 da ideacao).
    """
    rows = (
        db.session.query(
            Key_success_criterion.key_success_criterion_id.label("ksc_id"),
            Key_success_criterion.title.label("ksc_title"),
            Key_success_criterion.description.label("ksc_description"),
            Guideline.guidelineID.label("guideline_id"),
            Guideline.title.label("guideline_title"),
            Guideline.description.label("guideline_description"),
            db.func.max(EvaluationCriterionWheight.weight).label("weight"),
        )
        .join(
            Key_success_criterion,
            Key_success_criterion.key_success_criterion_id == EvaluationCriterionWheight.ksc_id,
        )
        .join(Guideline, Guideline.guidelineID == Key_success_criterion.guideline_id)
        .filter(EvaluationCriterionWheight.evaluation_id == evaluation_id)
        .group_by(
            Key_success_criterion.key_success_criterion_id,
            Key_success_criterion.title,
            Key_success_criterion.description,
            Guideline.guidelineID,
            Guideline.title,
            Guideline.description,
        )
        .order_by(Guideline.guidelineID, Key_success_criterion.key_success_criterion_id)
        .all()
    )

    if not rows:
        # Avaliacao sem pesos definidos: cai para o catalogo completo.
        rows = (
            db.session.query(
                Key_success_criterion.key_success_criterion_id.label("ksc_id"),
                Key_success_criterion.title.label("ksc_title"),
                Key_success_criterion.description.label("ksc_description"),
                Guideline.guidelineID.label("guideline_id"),
                Guideline.title.label("guideline_title"),
                Guideline.description.label("guideline_description"),
                db.literal(None).label("weight"),
            )
            .join(Guideline, Guideline.guidelineID == Key_success_criterion.guideline_id)
            .order_by(Guideline.guidelineID, Key_success_criterion.key_success_criterion_id)
            .all()
        )

    return [dict(row._mapping) for row in rows]


# ---------------------------------------------------------------------------
# 3) Catalogo de evidencias
# ---------------------------------------------------------------------------

def _duration_s(start, end) -> int:
    try:
        return int((end - start).total_seconds())
    except Exception:  # noqa: BLE001 - timestamp ausente ou invertido
        return 0


def _clean(text: Optional[str]) -> str:
    return " ".join((text or "").split())


def _enum_name(value) -> str:
    """Nome do membro do enum, que e o que a coluna guarda e o que a PoC renderizava."""
    return getattr(value, "name", value if value is None else str(value))


# -- compactacao da trilha de navegacao ------------------------------------
# A navegacao e ~58% do prompt e cresce ~2,6k tokens por participante, contra ~0,7k do
# resto. Boa parte disso e moldura repetida linha a linha, nao informacao: o rotulo da
# acao, o horario, o `https://` e os parametros de rastreamento.

_TRACKING_KEYS = {"_gl", "gclid", "fbclid", "msclkid", "gs_lcrp", "oq"}
_TRACKING_PREFIXES = ("_ga", "_gcl", "utm_")
_TITLE_SEPARATORS = (" - ", " | ", " · ", " — ")


def _is_tracking(key: str) -> bool:
    """`gs_lcrp` e `oq` entram aqui: sao ruido do buscador, nao a busca (`q` fica)."""
    return key in _TRACKING_KEYS or key.startswith(_TRACKING_PREFIXES)


def _compact_url(url: str) -> str:
    """URL sem o `https://` e sem os parametros de rastreamento.

    O filtro e por lista de chaves, nunca pela presenca de `?`: os parametros de busca
    (`?q=`, `?query=`, `&text=`) guardam, nas palavras do proprio participante, aquilo que
    ele nao conseguiu encontrar navegando — a evidencia mais direta de uma lacuna de
    descoberta que existe no conjunto.
    """
    parts = urlsplit(url or "")
    if parts.scheme not in ("http", "https") or not parts.netloc:
        # chrome://newtab, about:blank e afins ficam inteiros: sem o scheme viram
        # "newtab", que nao diz ao modelo que aquilo e uma pagina do navegador e nao
        # do portal.
        return (url or "").strip()

    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(key)
    ]
    query = "?" + "&".join(f"{k}={v}" for k, v in kept) if kept else ""
    fragment = f"#{parts.fragment}" if parts.fragment else ""
    return f"{parts.netloc}{parts.path.rstrip('/')}{query}{fragment}"


def _common_title_suffixes(titles: List[str], min_count: int = 4) -> Set[str]:
    """Sufixos de site que se repetem nos titulos desta avaliacao.

    " - Docs by LangChain" aparece em 135 dos 247 eventos da avaliacao piloto. O nome do
    site ja esta no host da URL, na mesma linha, entao repeti-lo em cada titulo e custo
    sem informacao. O limiar evita cortar um titulo que so por acaso termina assim.
    """
    counter: Dict[str, int] = defaultdict(int)
    for title in titles:
        for separator in _TITLE_SEPARATORS:
            head, found, tail = title.rpartition(separator)
            if found and head and tail:
                counter[separator + tail] += 1
    return {suffix for suffix, count in counter.items() if count >= min_count}


def _trim_title(title: str, suffixes: Set[str]) -> str:
    """Tira o sufixo recorrente. Nunca devolve vazio — titulo curto fica como esta."""
    for suffix in suffixes:
        if title.endswith(suffix) and len(title) > len(suffix):
            return title[: -len(suffix)]
    return title


def build_evidence_catalog(evaluation_id: int) -> "OrderedDict[str, Dict[str, Any]]":
    """Devolve {evidence_id -> registro}, cada um com type/participant_id/task_id/summary.

    `participant_id` e `task_id` sao o que permite ao sistema calcular participantes
    afetados e recorrencia sem perguntar nada ao modelo.

    A ORDEM de insercao importa: e ela que define a ordem das tarefas na renderizacao
    do contexto (ver `render_data`). Questionarios primeiro, depois execucoes na ordem
    em que aconteceram, depois navegacao, depois respostas.
    """
    catalog: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    # -- questionario do desenvolvedor (perfil + emocao + comentario final)
    questionnaires = (
        db.session.query(DeveloperQuestionnaire)
        .join(CollectedData, CollectedData.collected_data_id == DeveloperQuestionnaire.collected_data_id)
        .filter(CollectedData.evaluation_id == evaluation_id)
        .order_by(DeveloperQuestionnaire.collected_data_id)
        .all()
    )
    for dq in questionnaires:
        catalog[f"DQ-{dq.developer_questionnaire_id}"] = {
            "type": "developer_questionnaire",
            "participant_id": dq.collected_data_id,
            "task_id": None,
            "summary": (
                f"{_enum_name(dq.academic_level)} · usa portais {_enum_name(dq.previus_xp)} · "
                f"{dq.experience} anos de xp · segmento {_enum_name(dq.segment)} · "
                f"emocao {dq.emotion}/5 · comentario final: \"{_clean(dq.comments)}\""
            ),
            "payload": {
                "academic_level": _enum_name(dq.academic_level),
                "previus_xp": _enum_name(dq.previus_xp),
                "emotion": dq.emotion,
                "comments": _clean(dq.comments),
                "segment": _enum_name(dq.segment),
                "experience": dq.experience,
            },
        }

    # -- execucoes de tarefa (status + duracao + comentario)
    performed = (
        db.session.query(PerformedTask, Task.title)
        .join(CollectedData, CollectedData.collected_data_id == PerformedTask.collected_data_id)
        .join(Task, Task.task_id == PerformedTask.task_id)
        .filter(CollectedData.evaluation_id == evaluation_id)
        .order_by(PerformedTask.collected_data_id, PerformedTask.initial_timestamp)
        .all()
    )
    for pt, task_title in performed:
        duration = _duration_s(pt.initial_timestamp, pt.final_timestamp)
        comment = _clean(pt.comments)
        catalog[f"PT-{pt.performed_task_id}"] = {
            "type": "performed_task",
            "participant_id": pt.collected_data_id,
            "task_id": pt.task_id,
            "summary": (
                f"status={_enum_name(pt.status)} · {duration}s"
                + (f" · comentario: \"{comment}\"" if comment else " · sem comentario")
            ),
            "payload": {
                "status": _enum_name(pt.status),
                "duration_s": duration,
                "comments": comment,
                "task_title": task_title,
            },
        }

    # -- navegacao (trilha comportamental)
    navigations = (
        db.session.query(Navigation)
        .join(CollectedData, CollectedData.collected_data_id == Navigation.collected_data_id)
        .filter(CollectedData.evaluation_id == evaluation_id)
        .order_by(Navigation.collected_data_id, Navigation.timestamp, Navigation.navigation_id)
        .all()
    )
    title_suffixes = _common_title_suffixes([_clean(nav.title) for nav in navigations])

    for nav in navigations:
        catalog[f"NAV-{nav.navigation_id}"] = {
            "type": "navigation",
            "participant_id": nav.collected_data_id,
            "task_id": nav.task_id,
            # `summary` NAO pode mudar de formato: ele e congelado no snapshot
            # `ai_finding.evidence` (metrics.build_evidence_snapshot) e a tela faz parse
            # dele (RE_NAV_ACTION em static/js/ai_analysis.js). Mexer aqui quebra os cards
            # e as analises ja gravadas.
            "summary": (
                f"{_enum_name(nav.action)} · \"{_clean(nav.title)}\" · {nav.url} · "
                f"{nav.timestamp:%H:%M:%S}"
            ),
            # Ja a linha que vai ao prompt e enxuta: o rotulo da acao vira " (aba)" so nos
            # TAB_SWITCH, o horario sai (a secao declara que a trilha esta em ordem) e a
            # URL perde o scheme e o rastreamento. Ver `render_data`.
            "prompt_line": (
                f"\"{_trim_title(_clean(nav.title), title_suffixes)}\" "
                f"{_compact_url(nav.url)}"
                + (" (aba)" if _enum_name(nav.action) == "TAB_SWITCH" else "")
            ),
            "payload": {
                "action": _enum_name(nav.action),
                "title": _clean(nav.title),
                "url": nav.url,
                "timestamp": str(nav.timestamp),
            },
        }

    # -- duvidas registradas durante a execucao do cenario (RF-03)
    doubts = (
        db.session.query(Doubt)
        .join(CollectedData, CollectedData.collected_data_id == Doubt.collected_data_id)
        .filter(CollectedData.evaluation_id == evaluation_id)
        .order_by(Doubt.collected_data_id, Doubt.timestamp, Doubt.doubt_id)
        .all()
    )
    for doubt in doubts:
        elapsed = doubt.elapsed_time or "?"
        catalog[f"DBT-{doubt.doubt_id}"] = {
            "type": "doubt",
            "participant_id": doubt.collected_data_id,
            "task_id": doubt.task_id,
            # Formato congelado, como o de navigation: este texto vai para o snapshot
            # `ai_finding.evidence` e a tela faz parse dele (RE_DOUBT em
            # static/js/ai_analysis.js). Mexer aqui quebra as analises ja gravadas.
            "summary": f"duvida em {elapsed} de cenario: \"{_clean(doubt.text)}\"",
            "payload": {
                "text": _clean(doubt.text),
                "elapsed_time": doubt.elapsed_time,
                "timestamp": str(doubt.timestamp),
            },
        }

    # -- respostas aos KSC (0-100)
    answers = (
        db.session.query(
            Answer,
            Question.question,
            Key_success_criterion.key_success_criterion_id,
            Key_success_criterion.title,
        )
        .join(CollectedData, CollectedData.collected_data_id == Answer.collected_data_id)
        .join(Question, Question.question_id == Answer.question_id)
        .join(
            Key_success_criterion,
            Key_success_criterion.key_success_criterion_id == Question.key_success_criterion_id,
        )
        .filter(CollectedData.evaluation_id == evaluation_id)
        .order_by(Answer.collected_data_id, Key_success_criterion.key_success_criterion_id)
        .all()
    )
    for answer, question_text, ksc_id, ksc_title in answers:
        catalog[f"ANS-{answer.answer_id}"] = {
            "type": "answer",
            "participant_id": answer.collected_data_id,
            "task_id": None,
            "ksc_id": ksc_id,
            "summary": f"KSC {ksc_id} \"{ksc_title}\" -> {answer.answer}/100",
            "payload": {
                "score": answer.answer,
                "ksc_id": ksc_id,
                "ksc_title": ksc_title,
                "question": _clean(question_text),
            },
        }

    return catalog


# ---------------------------------------------------------------------------
# 4) Renderizacao do contexto para o prompt
# ---------------------------------------------------------------------------

def render_framework(scope: List[Dict[str, Any]]) -> str:
    lines = ["## FRAMEWORK DE TRANSPARENCIA — KSCs no escopo desta avaliacao", ""]
    lines.append(
        "Estes sao os UNICOS ksc_id que voce pode usar. Nao invente nem crie novos.\n"
    )
    by_guideline: "OrderedDict[int, List[Dict[str, Any]]]" = OrderedDict()
    for k in scope:
        by_guideline.setdefault(k["guideline_id"], []).append(k)

    for gid, kscs in by_guideline.items():
        lines.append(f"### Guideline G{gid} — {kscs[0]['guideline_title']}")
        lines.append(f"{_clean(kscs[0]['guideline_description'])}")
        for k in kscs:
            weight = f" [peso do gestor: {k['weight']}/5]" if k.get("weight") else ""
            lines.append(f"- ksc_id={k['ksc_id']} — {k['ksc_title']}{weight}")
            lines.append(f"    {_clean(k['ksc_description'])}")
        lines.append("")
    return "\n".join(lines)


def render_data(
    participants: List[CollectedData],
    catalog: Dict[str, Dict[str, Any]],
    tasks: Dict[int, str],
) -> str:
    """Dados da avaliacao agrupados por participante -> tarefa, cada linha com seu ID."""
    by_participant: Dict[int, Dict[str, Any]] = defaultdict(
        lambda: {"dq": [], "by_task": defaultdict(list), "answers": []}
    )
    for eid, rec in catalog.items():
        bucket = by_participant[rec["participant_id"]]
        if rec["type"] == "developer_questionnaire":
            bucket["dq"].append((eid, rec))
        elif rec["type"] == "answer":
            bucket["answers"].append((eid, rec))
        else:
            bucket["by_task"][rec["task_id"]].append((eid, rec))

    lines = ["## DADOS CAPTURADOS NA AVALIACAO", ""]
    lines.append(
        "Cada linha comeca com o ID da evidencia entre colchetes. Use EXATAMENTE esses "
        "IDs em supporting_data_ids. IDs que nao aparecem abaixo nao existem.\n"
    )
    lines.append(
        "A navegacao de cada tarefa esta em ORDEM CRONOLOGICA, uma linha por evento: "
        "[NAV-n] \"titulo da pagina\" url. O `https://` foi omitido e os parametros de "
        "rastreamento (_gl, _ga, utm_) foram removidos; os parametros de busca foram "
        "preservados como o participante os produziu. `(aba)` marca troca de aba em vez "
        "de carregamento de pagina.\n"
    )
    lines.append(
        "As linhas [DBT-n] sao duvidas que o participante escreveu com as proprias "
        "palavras DURANTE a execucao daquele cenario, sem interromper a tarefa. O tempo "
        "entre parenteses e quanto havia decorrido do cenario quando ele registrou a "
        "duvida.\n"
    )

    for index, participant in enumerate(participants, start=1):
        pid = participant.collected_data_id
        bucket = by_participant.get(pid)
        lines.append(f"### Participante P{index} (collected_data_id={pid})")
        if not bucket:
            lines.append("(sem dados capturados)\n")
            continue

        for eid, rec in bucket["dq"]:
            lines.append(f"[{eid}] perfil: {rec['summary']}")
        lines.append("")

        # As tarefas saem na ordem de insercao no catalogo — ou seja, na ordem em que o
        # participante as executou, porque as execucoes entram ordenadas por
        # initial_timestamp e sao elas que criam as chaves de `by_task`.
        for task_id in bucket["by_task"]:
            entries = bucket["by_task"][task_id]
            title = tasks.get(task_id, f"task {task_id}")
            lines.append(f"  Tarefa {task_id} — {title}")
            for eid, rec in entries:
                if rec["type"] == "performed_task":
                    lines.append(f"    [{eid}] execucao: {rec['summary']}")
            for eid, rec in entries:
                if rec["type"] == "navigation":
                    # `prompt_line` em vez de `summary`: o prefixo "navegacao:" e
                    # redundante com o proprio ID (NAV-) e a linha compacta corta ~46% do
                    # bloco. Fallback defensivo para registros sem a chave.
                    lines.append(
                        f"    [{eid}] {rec.get('prompt_line') or rec['summary']}"
                    )
            for eid, rec in entries:
                if rec["type"] == "doubt":
                    payload = rec.get("payload") or {}
                    lines.append(
                        f"    [{eid}] duvida ({payload.get('elapsed_time') or '?'}): "
                        f"\"{payload.get('text') or ''}\""
                    )
            lines.append("")

        if bucket["answers"]:
            lines.append("  Respostas do participante aos KSC (0=pessimo, 100=otimo):")
            for eid, rec in sorted(
                bucket["answers"], key=lambda e: e[1]["payload"]["ksc_id"]
            ):
                lines.append(f"    [{eid}] {rec['summary']}")
            lines.append("")

    return "\n".join(lines)


def render_header(evaluation: Evaluation, n_participants: int) -> str:
    processes = "\n".join(
        f"- {p.description}" for p in evaluation.seco_processes
    )
    return (
        "## AVALIACAO ANALISADA\n\n"
        f"- Nome: {evaluation.name}\n"
        f"- Portal do ecossistema: {evaluation.seco_portal} ({evaluation.seco_portal_url})\n"
        f"- Tipo de SECO: {_enum_name(evaluation.seco_type)}\n"
        f"- Participantes: {n_participants}\n"
        f"- Objetivo declarado pelo gestor: {_clean(evaluation.manager_objective)}\n"
        f"\nProcessos do ecossistema no escopo:\n{processes}\n"
    )


def build_context(evaluation_id: int) -> Dict[str, Any]:
    """Ponto de entrada: devolve tudo que as etapas seguintes precisam."""
    evaluation = fetch_evaluation(evaluation_id)
    participants = fetch_participants(evaluation_id)

    if not participants:
        raise EvaluationNotAnalyzable(
            f"Avaliacao {evaluation_id} nao tem nenhuma sessao coletada — nada a analisar."
        )

    scope = fetch_framework_scope(evaluation_id)
    catalog = build_evidence_catalog(evaluation_id)
    tasks = {task.task_id: task.title for task in Task.query.all()}

    prompt = "\n".join([
        render_header(evaluation, len(participants)),
        render_framework(scope),
        render_data(participants, catalog, tasks),
    ])

    return {
        "evaluation": evaluation,
        "participants": participants,
        "framework_scope": scope,
        "catalog": catalog,
        "tasks": tasks,
        "prompt": prompt,
    }
