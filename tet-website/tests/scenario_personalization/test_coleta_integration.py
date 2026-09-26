"""Teste de integracao real do modulo 1: abre um Chromium de verdade e navega
ate um portal real. Marcado `integration` - fica DESLIGADO por padrao (ver
pytest.ini); rode com `pytest -m integration`.

Usa example.com de proposito: e o dominio reservado pela IANA para exemplos
(RFC 2606), estavel e sempre no ar, mas sem menu de navegacao nem texto
suficiente na home - o que faz a coleta cair em modo degradado com os DOIS
motivos previstos. E um teste real contra rede, so que do caminho degradado,
nao do caminho feliz (esse ja foi validado manualmente contra portais maiores
como docs.langchain.com - ver o historico de smoke tests das Fases 1-3).
"""
import pytest

from services.scenario_personalization import coleta

pytestmark = pytest.mark.integration


def test_coleta_contra_portal_real_sem_menu_fica_degradada():
    bruta = coleta.coletar(
        "https://example.com/", coleta.ConfigColeta(profundidade=0, max_paginas=1)
    )

    assert len(bruta.paginas) == 1
    assert bruta.paginas[0].erro is None
    assert bruta.paginas[0].titulo == "Example Domain"
    assert bruta.modo == "degradado"
    assert "nenhum item de navegacao identificado" in bruta.motivos_degradacao
