"""Modulo 4 (validacao.py) e deterministico e sem rede - nenhuma chamada de IA
aqui, por decisao travada do metodo (CLAUDE.md). Cobre os dois caminhos de
rejeicao (estrutural e de conteudo) e o caminho de sucesso, com string e com
lista como campo_fonte.
"""
from services.scenario_personalization import validacao


DADOS_PORTAL = {
    "paginas_coletadas": [
        {
            "url": "https://exemplo.com/docs",
            "titulo": "Docs",
            "texto": "Central de documentacao e API reference completa para desenvolvedores.",
        },
    ],
    "estrutura_navegacao": {"itens_menu": ["GitHub", "Suporte", "Precos"]},
}


def test_resolver_campo_string_por_indice():
    valor = validacao.resolver_campo(DADOS_PORTAL, "paginas_coletadas[0].texto")
    assert valor == DADOS_PORTAL["paginas_coletadas"][0]["texto"]


def test_resolver_campo_lista_por_indice():
    valor = validacao.resolver_campo(DADOS_PORTAL, "estrutura_navegacao.itens_menu[0]")
    assert valor == "GitHub"


def test_resolver_campo_inexistente_devolve_none_sem_lancar():
    assert validacao.resolver_campo(DADOS_PORTAL, "paginas_coletadas[5].texto") is None
    assert validacao.resolver_campo(DADOS_PORTAL, "campo.que.nao.existe") is None
    assert validacao.resolver_campo(DADOS_PORTAL, "") is None


def test_confianca_recurso_presente_no_campo():
    score = validacao._confianca("documentacao e API reference", DADOS_PORTAL["paginas_coletadas"][0]["texto"])
    assert score == 1.0


def test_confianca_recurso_ausente_do_campo():
    score = validacao._confianca("tabela de precos detalhada", DADOS_PORTAL["paginas_coletadas"][0]["texto"])
    assert score == 0.0


def test_confianca_tolera_parafrase_parcial():
    # A chamada 2 reescreve com liberdade - exigir 100% dos tokens rejeitaria
    # citacoes legitimas so por causa da parafrase (ver docstring do limiar).
    score = validacao._confianca("documentacao tecnica completa", DADOS_PORTAL["paginas_coletadas"][0]["texto"])
    assert 0 < score < 1.0


def test_validar_etapa_sem_campo_fonte_e_rejeitada():
    confirmada, motivo = validacao.validar_etapa(
        {"recurso_real": "algo", "campo_fonte": None}, DADOS_PORTAL
    )
    assert confirmada is False
    assert "sem campo_fonte" in motivo


def test_validar_etapa_com_campo_inexistente_e_rejeitada():
    confirmada, motivo = validacao.validar_etapa(
        {"recurso_real": "changelog", "campo_fonte": "paginas_coletadas[9].texto"}, DADOS_PORTAL
    )
    assert confirmada is False
    assert "nao existe" in motivo


def test_validar_etapa_com_conteudo_nao_sustentado_e_rejeitada():
    confirmada, motivo = validacao.validar_etapa(
        {"recurso_real": "tabela de precos por regiao", "campo_fonte": "paginas_coletadas[0].texto"},
        DADOS_PORTAL,
    )
    assert confirmada is False
    assert "nao sustenta" in motivo


def test_validar_etapa_confirmada_com_sucesso():
    confirmada, motivo = validacao.validar_etapa(
        {"recurso_real": "documentacao e API reference", "campo_fonte": "paginas_coletadas[0].texto"},
        DADOS_PORTAL,
    )
    assert confirmada is True
    assert motivo == ""


def test_montar_resultado_validado_separa_confirmadas_de_removidas_e_junta_o_texto_final():
    resultado_modulo3 = {
        "etapas_personalizadas": [
            {
                "ordem": 1,
                "texto": "Acesse a documentacao completa.",
                "recurso_real": "documentacao e API reference",
                "campo_fonte": "paginas_coletadas[0].texto",
            },
            {
                "ordem": 2,
                "texto": "Veja o changelog de versoes.",
                "recurso_real": "changelog",
                "campo_fonte": "paginas_coletadas[9].texto",
            },
        ],
        "etapas_omitidas": [{"etapa": "sem correspondencia", "motivo": "nao encontrado"}],
    }

    resultado = validacao.montar_resultado_validado(resultado_modulo3, DADOS_PORTAL)

    assert resultado["cenario_personalizado"] == "Acesse a documentacao completa."
    assert resultado["recursos_confirmados"] == ["documentacao e API reference"]
    assert resultado["justificativas"] == [
        {"recurso": "documentacao e API reference", "fonte": "paginas_coletadas[0].texto"}
    ]
    assert resultado["etapas_omitidas"] == resultado_modulo3["etapas_omitidas"]
    assert len(resultado["recursos_removidos_validacao"]) == 1
    assert resultado["recursos_removidos_validacao"][0]["recurso"] == "changelog"
    assert "nao existe" in resultado["recursos_removidos_validacao"][0]["motivo"]
