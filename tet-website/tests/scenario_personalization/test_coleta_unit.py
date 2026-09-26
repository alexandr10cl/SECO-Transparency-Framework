"""So a parte pura e sem rede de coleta.py: `_avaliar_modo` (RF06/RF07 - decide
modo completo vs degradado). O resto do modulo (`coletar`) abre um Chromium de
verdade - fica em test_coleta_integration.py, marcado e desligado por padrao.
"""
from services.scenario_personalization.coleta import ColetaBruta, PaginaBruta, _avaliar_modo


def _coleta_base(**overrides) -> ColetaBruta:
    base = dict(
        url_inicial="https://exemplo.com",
        dominio="exemplo.com",
        timestamp="2026-01-01T00:00:00+00:00",
        paginas=[PaginaBruta(url="https://exemplo.com", texto="x" * 300)],
        itens_menu=[{"texto": "Docs", "href": "https://exemplo.com/docs"}],
    )
    base.update(overrides)
    return ColetaBruta(**base)


def test_coleta_saudavel_fica_completa():
    coleta = _coleta_base()
    _avaliar_modo(coleta)

    assert coleta.modo == "completo"
    assert coleta.motivos_degradacao == []


def test_sem_paginas_fica_degradada_com_motivo_especifico():
    coleta = _coleta_base(paginas=[])
    _avaliar_modo(coleta)

    assert coleta.modo == "degradado"
    assert "pagina inicial inacessivel" in coleta.motivos_degradacao


def test_primeira_pagina_com_erro_fica_degradada():
    coleta = _coleta_base(paginas=[PaginaBruta(url="https://exemplo.com", erro="timeout")])
    _avaliar_modo(coleta)

    assert coleta.modo == "degradado"
    assert "pagina inicial inacessivel" in coleta.motivos_degradacao


def test_nenhuma_pagina_com_conteudo_suficiente_tem_motivo_proprio_sem_duplicar_o_da_pagina_inicial():
    # Regressao: no protototipo original as duas checagens produziam a mesma frase (com um
    # typo), tornando os dois motivos indistinguiveis. Aqui tem que ser dois motivos
    # DIFERENTES quando so a segunda condicao dispara (primeira pagina existe e nao deu
    # erro, mas nenhuma pagina tem texto suficiente).
    coleta = _coleta_base(paginas=[PaginaBruta(url="https://exemplo.com", texto="curto")])
    _avaliar_modo(coleta)

    assert coleta.modo == "degradado"
    assert "pagina inicial inacessivel" not in coleta.motivos_degradacao
    assert "nenhuma pagina coletada com conteudo suficiente" in coleta.motivos_degradacao
    assert not any("incessivel" in m for m in coleta.motivos_degradacao)  # o typo original


def test_sem_itens_de_menu_fica_degradada():
    coleta = _coleta_base(itens_menu=[])
    _avaliar_modo(coleta)

    assert coleta.modo == "degradado"
    assert "nenhum item de navegacao identificado" in coleta.motivos_degradacao
