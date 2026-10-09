"""Parte pura de personalizacao.py: montagem de prompt, sem chamar a API. As
duas chamadas de IA de verdade ficam em test_personalizacao_integration.py,
marcadas e desligadas por padrao.
"""
from services.scenario_personalization.personalizacao import (
    CenarioBase, MAX_CHARS_FEEDBACK, MAX_FEEDBACKS, MapeamentoItem, _portal_para_prompt,
    build_adaptacao_prompt, build_mapeamento_prompt, selecionar_feedback,
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


# --- feedback do gestor (comentario da rejeicao) ---------------------------------

def _prompt_mapeamento(feedback=None):
    return build_mapeamento_prompt(
        cenario_base=CenarioBase(titulo="T", descricao="D"),
        diretriz={"id": "G1"},
        descricao_gestor="",
        dados_portal=DADOS_PORTAL,
        feedback_gestor=feedback,
    )


def test_selecionar_feedback_descarta_vazios_e_normaliza_espacos():
    assert selecionar_feedback([None, "", "   ", " muito   generico\n"]) == ["muito generico"]


def test_selecionar_feedback_mantem_so_os_mais_recentes_em_ordem():
    comentarios = [f"c{i}" for i in range(MAX_FEEDBACKS + 2)]
    assert selecionar_feedback(comentarios) == comentarios[-MAX_FEEDBACKS:]


def test_selecionar_feedback_trunca_texto_livre():
    assert len(selecionar_feedback(["x" * (MAX_CHARS_FEEDBACK + 300)])[0]) == MAX_CHARS_FEEDBACK


def test_prompt_de_mapeamento_sem_feedback_e_identico_ao_de_antes():
    assert "Feedback do gestor" not in _prompt_mapeamento()
    assert _prompt_mapeamento([]) == _prompt_mapeamento(None) == _prompt_mapeamento(["  "])


def test_prompt_de_mapeamento_com_feedback_inclui_antes_dos_dados_do_portal():
    prompt = _prompt_mapeamento(["use a pagina de docs, nao o menu"])

    assert "use a pagina de docs, nao o menu" in prompt
    assert prompt.index("Feedback do gestor") < prompt.index("Dados reais coletados do portal")


def test_prompt_de_adaptacao_com_feedback():
    confirmados = [MapeamentoItem(
        ordem=1, objetivo="o", texto="t", corresponde=True,
        campo_fonte="paginas_coletadas[0].texto", recurso_real="Documentation", motivo="m",
    )]
    base = dict(cenario_base=CenarioBase(titulo="T", descricao="D"), diretriz={"id": "G1"}, confirmados=confirmados)

    assert "Feedback do gestor" not in build_adaptacao_prompt(**base)
    assert "mais curto" in build_adaptacao_prompt(**base, feedback_gestor=["mais curto"])
