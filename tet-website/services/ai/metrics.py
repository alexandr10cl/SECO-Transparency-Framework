"""
Nada aqui vem do LLM. Todas as medidas sao derivadas das evidencias que sustentam cada
finding.

Estas funcoes rodam nos dois sentidos: na geracao, sobre o catalogo recem-montado; e na
leitura, sobre a lista `evidence` gravada em `ai_finding`. Por isso o nucleo recebe
sempre uma lista de registros de evidencia, nunca o banco. E tambem por isso nenhuma
metrica virou coluna — ajustar uma formula aqui re-pontua as analises ja gravadas.

Duas medidas entram nas formulas, e so duas:

- ABRANGENCIA (`affected_ratio`): quantos participantes distintos, sobre o total. E a
  medida mais concreta que a avaliacao produz — conta pessoas, nao artefatos.
- CONFIANCA (`confidence_band`): o quanto a evidencia esta triangulada, por uma tabela de
  duas entradas (participantes distintos x tipos de sinal distintos). Sem pesos para
  calibrar e explicavel ao gestor numa frase.

`recurrence` continua sendo calculado, mas apenas como numero DESCRITIVO exibido na tela
("seen in 4 occurrences"). Ele nao entra em nenhuma formula: contar ocorrencias favorece
sinais verbosos — navegacao gera dezenas de linhas por participante — e diz pouco alem do
que a abrangencia ja diz.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Confianca = triangulacao. Duas dimensoes, cada uma medindo uma coisa so:
#   participantes distintos -> o sinal se repete entre pessoas?
#   tipos de sinal distintos -> o sinal aparece por caminhos diferentes?
# Deliberadamente NAO entra aqui a contagem bruta de evidencias: cinco linhas de
# navegacao do mesmo participante nao sustentam mais que um comentario de tres pessoas.
_CONFIDENCE_MIN_PARTICIPANTS = 2
_CONFIDENCE_MIN_TYPES = 2

# Peso ordinal da confianca dentro da prioridade. Entra como fator de desconto sobre a
# abrangencia — nao como terceira dimensao continua, que so comprimiria a escala.
_CONFIDENCE_WEIGHT = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}

_PRIORITY_BANDS = ((0.45, "HIGH"), (0.20, "MEDIUM"), (0.0, "LOW"))


def _band(value: float, bands) -> str:
    for threshold, label in bands:
        if value >= threshold:
            return label
    return bands[-1][1]


def confidence_band(n_participants: int, n_types: int) -> str:
    """Triangulacao da evidencia, por tabela de duas entradas.

                     | 1 tipo de sinal | 2+ tipos
        1 participante|      LOW        |  MEDIUM
        2+ participan.|     MEDIUM      |   HIGH
    """
    strong_participants = n_participants >= _CONFIDENCE_MIN_PARTICIPANTS
    strong_types = n_types >= _CONFIDENCE_MIN_TYPES
    if strong_participants and strong_types:
        return "HIGH"
    if strong_participants or strong_types:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

def compute_finding_metrics(
    evidence: List[Dict[str, Any]],
    total_participants: int,
) -> Dict[str, Any]:
    """Abrangencia e confianca de um finding, a partir das evidencias que o sustentam.

    Cada registro de `evidence` precisa ter `type`, `participant_id` e `task_id` — que e
    exatamente o que o catalogo produz e o que fica gravado em `ai_finding.evidence`.
    """
    participants = {r["participant_id"] for r in evidence}
    types = {r["type"] for r in evidence}
    # Descritivo: pares distintos (participante, tarefa). Evidencias sem tarefa
    # (questionario, resposta de KSC) contam como um par proprio do participante.
    pairs = {(r["participant_id"], r["task_id"]) for r in evidence}

    n_participants = len(participants)
    affected_ratio = (
        n_participants / total_participants if total_participants else 0.0
    )

    return {
        "evidence_count": len(evidence),
        "participants_affected": n_participants,
        "participants_total": total_participants,
        "affected_participants": f"{n_participants}/{total_participants}",
        "affected_ratio": round(affected_ratio, 3),
        "recurrence": len(pairs),
        "evidence_types": sorted(types),
        "confidence_band": confidence_band(n_participants, len(types)),
        "participant_ids": sorted(participants),
    }


def build_evidence_snapshot(
    supporting_data_ids: List[str],
    catalog: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Congela as evidencias validadas no formato que vai para o banco e para a tela."""
    return [
        {
            "id": eid,
            "type": catalog[eid]["type"],
            "participant_id": catalog[eid]["participant_id"],
            "task_id": catalog[eid]["task_id"],
            "summary": catalog[eid]["summary"],
        }
        for eid in supporting_data_ids
    ]


def attach_finding_metrics(
    findings: List[Dict[str, Any]],
    catalog: Dict[str, Dict[str, Any]],
    total_participants: int,
) -> None:
    """Preenche `evidence`, `metrics` e `evidence_urls` em cada finding (in place).

    So usado na geracao, quando o catalogo ainda existe em memoria. Na leitura, o
    `evidence` ja esta gravado e basta `compute_finding_metrics`.
    """
    for finding in findings:
        finding["evidence"] = build_evidence_snapshot(
            finding["supporting_data_ids"], catalog
        )
        finding["metrics"] = compute_finding_metrics(
            finding["evidence"], total_participants
        )
        urls = []
        for eid in finding["supporting_data_ids"]:
            url = catalog[eid].get("payload", {}).get("url")
            if url and url not in urls:
                urls.append(url)
        finding["evidence_urls"] = urls


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

def compute_action_metrics(
    linked_metrics: List[Dict[str, Any]],
    total_participants: int,
) -> Dict[str, Any]:
    """Impacto e prioridade de uma acao, a partir dos findings que ela resolve.

    Impacto NAO e estimativa do modelo: e a uniao dos participantes afetados pelos
    findings que a acao resolve, sobre o total — medida operacional de abrangencia.

        priority = impacto x peso_da_melhor_confianca

    A confianca entra como desconto ordinal (HIGH 1.0 / MEDIUM 0.6 / LOW 0.3) em vez de
    fator continuo proprio. Multiplicar tres fracoes comprimia o resultado a ponto de
    quase nada alcancar a faixa HIGH; com dois fatores a escala volta a discriminar e o
    teto 1.0 e atingivel de fato.

    AGRUPAR NUNCA PODE REBAIXAR UMA ACAO. E por isso que a confianca aqui e o MAXIMO entre
    os findings ligados, e nao a media: se um dos findings esta bem triangulado, ele ja
    justifica agir, e recolher junto um finding correlato mais fraco nao torna a
    intervencao menos fundamentada — com media, absorver um finding LOW derrubaria a
    prioridade de uma acao que resolve mais problemas. Pela mesma razao nao ha
    normalizacao contra as outras acoes da analise: cada acao e pontuada isoladamente.
    (A formula anterior dividia pelo numero de findings resolvidos, penalizando o
    agrupamento justamente que o prompt da etapa 2 pede.)
    """
    participants = set()
    for m in linked_metrics:
        participants.update(m["participant_ids"])

    impact_ratio = (
        len(participants) / total_participants if total_participants else 0.0
    )
    confidence_weight = max(
        (_CONFIDENCE_WEIGHT[m["confidence_band"]] for m in linked_metrics),
        default=0.0,
    )

    score = impact_ratio * confidence_weight

    return {
        "impact": f"{len(participants)}/{total_participants}",
        "impact_ratio": round(impact_ratio, 3),
        "participants_affected": sorted(participants),
        "confidence_weight": round(confidence_weight, 3),
        "findings_resolved": len(linked_metrics),
        "priority_score": round(score, 3),
        "priority_band": _band(score, _PRIORITY_BANDS),
    }


PRIORITY_FORMULA = (
    "priority = participantes afetados / total x peso da melhor confianca entre os "
    "findings resolvidos. Formula operacional para ordenar o plano de acao, nao um "
    "modelo validado."
)

CONFIDENCE_FORMULA = (
    f"confidence: HIGH quando ha >= {_CONFIDENCE_MIN_PARTICIPANTS} participantes "
    f"distintos E >= {_CONFIDENCE_MIN_TYPES} tipos de sinal distintos; MEDIUM quando so "
    "uma das duas condicoes vale; LOW quando nenhuma."
)
