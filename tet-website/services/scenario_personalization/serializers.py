"""Traduz models ORM (Guideline, Task) para os dicts que `personalizacao.py`
espera - o schema de entrada do metodo (contexto/CLAUDE.md do TCC), que usa
chaves em portugues e nomes diferentes dos campos do banco (em ingles).
"""
from __future__ import annotations

from typing import Optional

from models import Guideline, Task


def guideline_for_task(task: Task) -> Optional[Guideline]:
    """A diretriz associada a uma task, via task -> processo -> diretriz.

    O schema do banco permite N:M nas duas pontas (task_seco_process,
    guideline_seco_process), mas na pratica e 1:1 - confirmado no seed_data.json
    (task 1 <-> processo 1 <-> guideline 1, ..., task 7 <-> processo 7 <->
    guideline 7). Por isso basta pegar a primeira combinacao encontrada; se
    isso deixar de ser 1:1 no futuro, esta funcao passa a devolver "a primeira
    que aparecer" em silencio, o que caberia revisar.
    """
    for process in task.seco_processes:
        for guideline in process.guidelines:
            return guideline
    return None


def serialize_guideline(guideline: Guideline) -> dict:
    """Guideline (+ relacionamentos) -> dict no schema de `diretriz` que
    `personalizacao.py` espera - mesmas chaves de `guideline_example.json`."""
    processo = guideline.seco_processes[0] if guideline.seco_processes else None
    return {
        "id": f"G{guideline.guidelineID}",
        "titulo": guideline.title,
        "descricao": guideline.description,
        "procedimento_comum_seco": processo.description if processo else "",
        "dimensoes": [d.name for d in guideline.seco_dimensions],
        "fatores_condicionantes": [f.description for f in guideline.conditioning_factors],
        "fatores_experiencia_desenvolvedor": [f.description for f in guideline.dx_factors],
        "criterios_sucesso": [
            {
                "titulo": ksc.title,
                "descricao": ksc.description,
                # O banco permite varios exemplos por KSC; o schema do metodo tem
                # so um "exemplo" por criterio - junta todos em vez de descartar
                # dado real cadastrado.
                "exemplo": " ".join(e.description for e in ksc.examples) if ksc.examples else "",
            }
            for ksc in guideline.key_success_criteria
        ],
        "notas": guideline.notes or "",
    }
