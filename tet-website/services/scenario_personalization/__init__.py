"""Personalizacao de cenarios de avaliacao com IA (TCC).

Pipeline em 3 modulos, cada um com uma responsabilidade que nao se mistura com as
outras (ver contexto/CLAUDE.md, decisao travada "separacao fisica"):

    coleta.py          modulo 1 - scraping real do portal (Playwright), sem interpretar nada
    estruturacao.py     modulo 2 - organiza o bruto em JSON de schema fixo, SEM IA
    personalizacao.py   modulo 3 - duas chamadas de IA encadeadas, ancoradas no schema fixo

Nenhum destes modulos grava no banco - eles sao funcoes puras (entrada -> saida). A
orquestracao (agendar, persistir em PortalCollection/PersonalizedScenario, servir de
lock contra execucao duplicada) e responsabilidade de um modulo `pipeline.py` futuro,
no mesmo molde de `services/ai/pipeline.py`.
"""
