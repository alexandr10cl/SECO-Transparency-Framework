"""Overall score de transparencia de uma avaliacao.

O score e a media das medias, em tres niveis:

    respostas (0-100) -> media por KSC -> media por guideline -> media das guidelines

Nenhum nivel e ponderado: `EvaluationCriterionWheight` existe, mas o peso do gestor so
ordena as improvement actions do dashboard, nunca entrou nesta conta.

Este modulo existe para que a mesma formula sirva ao dashboard (uma avaliacao por vez) e
ao historico da tela de evaluations (todas as avaliacoes do gestor de uma vez). A formula
mora aqui e em nenhum outro lugar: duas implementacoes divergiriam na primeira vez que
alguem ajustasse uma delas, e a tela passaria a discordar do grafico.

Sobre o custo: percorrer `guideline -> ksc -> question -> question.answers` pelos
relacionamentos ORM parece natural, mas `Question.answers` e lazy e traz as respostas de
TODAS as avaliacoes do banco, filtradas depois em Python. Por avaliacao isso ja e caro; em
lote seria inviavel. Por isso `compute_scores_for_evaluations` desce para uma query so,
que ja chega filtrada e agrupada.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from index import db
from models import Answer, CollectedData, Guideline, Key_success_criterion, Question


def parse_answer_to_fraction(ans: Any) -> Optional[float]:
    """Normaliza uma resposta para 0.0..1.0, ou None quando nao da para interpretar.

    Aceita int, float, '50', '50.0', '50%', '0.5' e os tokens antigos 'yes'/'partial'/'no'.
    A coluna `answer.answer` e Integer 0-100 desde a migracao para a escala continua, mas os
    tokens continuam aceitos: bases anteriores a essa mudanca ainda os tem gravados, e
    deixar de reconhece-los mudaria silenciosamente o score de avaliacoes antigas.
    """
    if ans is None:
        return None

    # se ja e numero
    if isinstance(ans, (int, float)):
        v = float(ans)
        if 0.0 <= v <= 1.0:
            return v
        if 0.0 <= v <= 100.0:
            return v / 100.0
        return None

    # string: tenta interpretar
    if isinstance(ans, str):
        s = ans.strip().lower()
        # antigos tokens
        if s in ('yes', 'y', 'sim'):
            return 1.0
        if s in ('partial', 'parcial'):
            return 0.5
        if s in ('no', 'n', 'não', 'nao'):
            return 0.0
        # remove '%' e tenta converter
        s_clean = s.rstrip('%')
        try:
            v = float(s_clean)
        except ValueError:
            return None
        if 0.0 <= v <= 1.0:
            return v
        if 0.0 <= v <= 100.0:
            return v / 100.0
        return None

    # fallback
    try:
        v = float(ans)
        if 0.0 <= v <= 1.0:
            return v
        if 0.0 <= v <= 100.0:
            return v / 100.0
    except Exception:  # noqa: BLE001 - qualquer tipo inesperado vira "sem resposta"
        return None

    return None


def _average_of_guideline_averages(
    scores_by_guideline: Dict[int, Dict[int, List[float]]]
) -> Optional[int]:
    """{guideline_id: {ksc_id: [frações]}} -> score 0-100, ou None se nao ha resposta.

    Guideline sem nenhuma resposta valida nao entra na media — nao conta como zero.
    """
    guideline_averages: List[float] = []
    for ksc_scores in scores_by_guideline.values():
        averages = [
            sum(fractions) / len(fractions)
            for fractions in ksc_scores.values() if fractions
        ]
        if averages:
            # round(_, 2) reproduz `g_data['average_score']` do dashboard: o
            # arredondamento intermediario faz parte da formula publicada na tela.
            guideline_averages.append(round(sum(averages) / len(averages) * 100, 2))

    if not guideline_averages:
        return None
    return round(sum(guideline_averages) / len(guideline_averages))


def compute_scores_for_evaluations(
    evaluation_ids: Iterable[int]
) -> Dict[int, Optional[int]]:
    """{evaluation_id -> score 0-100 ou None}, com UMA query para todo o conjunto.

    Avaliacao sem nenhuma resposta valida devolve None, e nao 0: no historico, plotar zero
    desenharia uma queda que nunca aconteceu, quando o que houve foi ausencia de coleta.
    """
    ids = list(evaluation_ids)
    if not ids:
        return {}

    rows = (
        db.session.query(
            CollectedData.evaluation_id,
            Guideline.guidelineID,
            Key_success_criterion.key_success_criterion_id,
            Answer.answer,
        )
        .join(CollectedData, CollectedData.collected_data_id == Answer.collected_data_id)
        .join(Question, Question.question_id == Answer.question_id)
        .join(
            Key_success_criterion,
            Key_success_criterion.key_success_criterion_id == Question.key_success_criterion_id,
        )
        .join(Guideline, Guideline.guidelineID == Key_success_criterion.guideline_id)
        .filter(CollectedData.evaluation_id.in_(ids))
        .all()
    )

    grouped: Dict[int, Dict[int, Dict[int, List[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for evaluation_id, guideline_id, ksc_id, raw_answer in rows:
        fraction = parse_answer_to_fraction(raw_answer)
        if fraction is None:
            continue
        grouped[evaluation_id][guideline_id][ksc_id].append(fraction)

    return {
        evaluation_id: _average_of_guideline_averages(grouped.get(evaluation_id, {}))
        for evaluation_id in ids
    }


def compute_overall_score(evaluation) -> Optional[int]:
    """Score de uma avaliacao. None quando ela nao tem nenhuma resposta valida."""
    return compute_scores_for_evaluations([evaluation.evaluation_id]).get(
        evaluation.evaluation_id
    )
