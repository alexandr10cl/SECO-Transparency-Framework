"""Teste de integracao real do modulo 3: as duas chamadas de IA contra a API
do Gemini de verdade. Marcado `integration` (desligado por padrao) E pulado se
GEMINI_API_KEY nao estiver configurada - sem a chave nao ha o que testar, e
isso nao e uma falha de codigo.

Usa um `dados_portal` minimo e sintetico (nao uma coleta real) de proposito:
o alvo aqui e provar que o contrato com `call_ai`/Pydantic funciona ponta a
ponta, nao validar a qualidade da coleta - isso e coberto pelos testes de
estruturacao e pelo teste de integracao de coleta, e mantem o custo de tokens
baixo (poucas linhas de contexto, nao um portal inteiro).
"""
import os

import pytest

from services.scenario_personalization import personalizacao

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY nao configurada neste ambiente",
    ),
]

DADOS_PORTAL = {
    "portal": {"url": "https://exemplo.com", "dominio": "exemplo.com"},
    "estrutura_navegacao": {"itens_menu": ["Documentation", "GitHub"]},
    "paginas_coletadas": [
        {
            "url": "https://exemplo.com/docs",
            "titulo": "Documentation",
            "texto": "Central de documentacao tecnica com guias de API, SDK e exemplos de codigo.",
            "links_internos": [],
        },
    ],
    "metadados": {"titulo_site": "Exemplo", "meta_description": "", "lang": "en", "sitemap_encontrado": False},
    "recursos_mencionados": ["Documentation", "GitHub"],
    "modo_coleta": "completo",
    "motivos_degradacao": [],
    "timestamp_coleta": "2026-01-01T00:00:00+00:00",
}

DIRETRIZ = {
    "id": "G1",
    "titulo": "Provide Access to Documentation, Source Code, and Development Tools",
    "descricao": "Portais devem centralizar documentacao, codigo-fonte e ferramentas.",
    "procedimento_comum_seco": "Access to documentation, source code, and tools.",
    "dimensoes": ["Technical"],
    "fatores_condicionantes": [],
    "fatores_experiencia_desenvolvedor": [],
    "criterios_sucesso": [
        {"titulo": "Documentacao centralizada", "descricao": "Facil de encontrar.", "exemplo": "Um so lugar."}
    ],
    "notas": "",
}


def test_personalizar_roda_as_duas_chamadas_e_devolve_o_schema_esperado():
    cenario_base = personalizacao.CenarioBase(
        titulo="Explorar recursos para comecar o desenvolvimento",
        descricao="Encontre a documentacao tecnica e o repositorio de codigo para comecar a integrar com a plataforma.",
    )

    resultado, meta = personalizacao.personalizar(
        cenario_base=cenario_base,
        diretriz=DIRETRIZ,
        descricao_gestor="Portal de exemplo para teste de integracao.",
        dados_portal=DADOS_PORTAL,
    )

    assert "etapas_personalizadas" in resultado
    assert "etapas_omitidas" in resultado
    assert isinstance(resultado["etapas_personalizadas"], list)

    for etapa in resultado["etapas_personalizadas"]:
        assert set(etapa.keys()) == {"ordem", "texto", "recurso_real", "campo_fonte"}

    assert meta["provider"] == "gemini"
    assert meta["model"]
    assert meta["ai_duration_s"] > 0
