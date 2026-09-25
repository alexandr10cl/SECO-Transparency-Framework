"""Parte pura de personalizacao.py: montagem de prompt, sem chamar a API. As
duas chamadas de IA de verdade ficam em test_personalizacao_integration.py,
marcadas e desligadas por padrao.
"""
from services.scenario_personalization.personalizacao import (
    CenarioBase, _portal_para_prompt, build_mapeamento_prompt,
)

DADOS_PORTAL = {
    "portal": {"url": "https://exemplo.com", "dominio": "exemplo.com"},
    "estrutura_navegacao": {"itens_menu": ["Documentation"]},
    "paginas_coletadas": [
        {
            "url": "https://exemplo.com/docs",
            "titulo": "Documentation",
            "texto": "Central de documentacao tecnica.",
            "links_internos": ["https://exemplo.com/docs/a", "https://exemplo.com/docs/b"],
        },
    ],
    "recursos_mencionados": ["Documentation"],
}


def test_portal_para_prompt_remove_links_internos_mas_preserva_o_resto():
    # links_internos e so URLs cruas, sem texto de link - a IA nao tem como
    # citar um recurso legivel a partir disso, entao so pesa tokens no
    # prompt sem nunca virar campo_fonte na pratica.
    resultado = _portal_para_prompt(DADOS_PORTAL)

    assert "links_internos" not in resultado["paginas_coletadas"][0]
    assert resultado["paginas_coletadas"][0]["texto"] == "Central de documentacao tecnica."
    assert resultado["estrutura_navegacao"] == DADOS_PORTAL["estrutura_navegacao"]
    assert resultado["recursos_mencionados"] == DADOS_PORTAL["recursos_mencionados"]


def test_portal_para_prompt_nao_muda_o_dict_original():
    # collection.dados_portal (banco) tem que continuar intacto - e ele que
    # a validacao (modulo 4) confere depois, com links_internos incluido.
    _portal_para_prompt(DADOS_PORTAL)

    assert "links_internos" in DADOS_PORTAL["paginas_coletadas"][0]


def test_build_mapeamento_prompt_nao_inclui_links_internos():
    prompt = build_mapeamento_prompt(
        cenario_base=CenarioBase(titulo="T", descricao="D"),
        diretriz={"id": "G1"},
        descricao_gestor="",
        dados_portal=DADOS_PORTAL,
    )

    assert "links_internos" not in prompt
    assert "docs/a" not in prompt
    assert "Central de documentacao tecnica." in prompt
