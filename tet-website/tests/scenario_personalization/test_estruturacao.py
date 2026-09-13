"""Modulo 2 (estruturacao.py) e deterministico e sem rede - a suite inteira
roda em milissegundos, sem Playwright nem app-context. Cobre o schema fixo da
etapa 2 do metodo: filtragem de ruido, dedup, truncamento de texto e o filtro
de links por dominio.
"""
from services.scenario_personalization.coleta import ColetaBruta, PaginaBruta
from services.scenario_personalization.estruturacao import estruturar


def _coleta_base(**overrides) -> ColetaBruta:
    base = dict(
        url_inicial="https://exemplo.com",
        dominio="exemplo.com",
        timestamp="2026-01-01T00:00:00+00:00",
        paginas=[],
        itens_menu=[],
        metadados={"titulo_site": "Exemplo", "meta_description": "desc", "lang": "en"},
        sitemap_encontrado=True,
        modo="completo",
        motivos_degradacao=[],
    )
    base.update(overrides)
    return ColetaBruta(**base)


def test_schema_fixo_passa_metadados_e_status_de_coleta():
    coleta = _coleta_base(modo="degradado", motivos_degradacao=["pagina inicial inacessivel"])
    resultado = estruturar(coleta)

    assert resultado["portal"] == {"url": "https://exemplo.com", "dominio": "exemplo.com"}
    assert resultado["metadados"]["titulo_site"] == "Exemplo"
    assert resultado["metadados"]["sitemap_encontrado"] is True
    assert resultado["modo_coleta"] == "degradado"
    assert resultado["motivos_degradacao"] == ["pagina inicial inacessivel"]
    assert resultado["timestamp_coleta"] == "2026-01-01T00:00:00+00:00"


def test_itens_de_menu_ruidosos_sao_removidos():
    # "github" esta na mesma lista de ruido de redes sociais/plataformas
    # externas (_RUIDO) - por isso o exemplo de item que sobrevive e "Support",
    # nao "GitHub".
    coleta = _coleta_base(itens_menu=[
        {"texto": "Documentation", "href": "https://exemplo.com/docs"},
        {"texto": "Login", "href": "https://exemplo.com/login"},
        {"texto": "GitHub", "href": "https://github.com/exemplo"},
        {"texto": "Support", "href": "https://exemplo.com/support"},
        {"texto": "  ", "href": "https://exemplo.com/x"},
    ])
    resultado = estruturar(coleta)

    assert resultado["estrutura_navegacao"]["itens_menu"] == ["Documentation", "Support"]


def test_itens_de_menu_duplicados_por_acento_e_maiuscula_sao_deduplicados():
    coleta = _coleta_base(itens_menu=[
        {"texto": "Documentação", "href": "https://exemplo.com/a"},
        {"texto": "documentacao", "href": "https://exemplo.com/b"},
    ])
    resultado = estruturar(coleta)

    assert resultado["estrutura_navegacao"]["itens_menu"] == ["Documentação"]


def test_pagina_com_texto_curto_demais_e_descartada():
    coleta = _coleta_base(paginas=[
        PaginaBruta(url="https://exemplo.com/vazia", titulo="Vazia", texto="pouco texto"),
        PaginaBruta(url="https://exemplo.com/cheia", titulo="Cheia", texto="x" * 200),
    ])
    resultado = estruturar(coleta)

    urls = [p["url"] for p in resultado["paginas_coletadas"]]
    assert urls == ["https://exemplo.com/cheia"]


def test_pagina_com_erro_e_descartada():
    coleta = _coleta_base(paginas=[
        PaginaBruta(url="https://exemplo.com/erro", texto="x" * 200, erro="timeout"),
    ])
    resultado = estruturar(coleta)

    assert resultado["paginas_coletadas"] == []


def test_texto_da_pagina_e_truncado_no_limite():
    coleta = _coleta_base(paginas=[
        PaginaBruta(url="https://exemplo.com/longa", texto="a" * 7000),
    ])
    resultado = estruturar(coleta)

    assert len(resultado["paginas_coletadas"][0]["texto"]) == 6000


def test_links_internos_filtram_por_dominio_e_deduplicam():
    coleta = _coleta_base(paginas=[
        PaginaBruta(
            url="https://exemplo.com/pagina",
            texto="x" * 200,
            links=[
                {"texto": "Docs", "href": "https://exemplo.com/docs"},
                {"texto": "Docs de novo", "href": "https://exemplo.com/docs"},
                {"texto": "www variante", "href": "https://www.exemplo.com/outra"},
                {"texto": "Externo", "href": "https://outro-dominio.com/x"},
                {"texto": "sem protocolo", "href": "/relativo"},
            ],
        ),
    ])
    resultado = estruturar(coleta)

    assert resultado["paginas_coletadas"][0]["links_internos"] == [
        "https://exemplo.com/docs",
        "https://www.exemplo.com/outra",
    ]


def test_recursos_mencionados_junta_menu_e_links_sem_ruido_nem_duplicata():
    coleta = _coleta_base(
        itens_menu=[{"texto": "Documentation", "href": "https://exemplo.com/docs"}],
        paginas=[
            PaginaBruta(
                url="https://exemplo.com/pagina",
                texto="x" * 200,
                links=[
                    {"texto": "Documentation", "href": "https://exemplo.com/docs"},  # ja no menu
                    {"texto": "API Reference", "href": "https://exemplo.com/api"},
                    {"texto": "Twitter", "href": "https://twitter.com/exemplo"},  # ruido
                ],
            ),
        ],
    )
    resultado = estruturar(coleta)

    assert resultado["recursos_mencionados"] == ["Documentation", "API Reference"]
