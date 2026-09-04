"""Camada analitica de IA (V2) do SECO-TransP.

Transforma os dados capturados numa avaliacao em Findings ancorados nos KSCs do
framework e sustentados por evidencias rastreaveis, e depois em Actions priorizadas.

    context_builder.py   dados da avaliacao -> catalogo de evidencias + escopo -> prompt
    analyzer.py          schemas, prompts e a validacao tecnica das respostas da IA
    metrics.py           o que o SISTEMA calcula (confianca, abrangencia, prioridade)
    pipeline.py          orquestra tudo, roda em background e persiste
    provider.py          call_ai(): a unica porta de saida para qualquer LLM

Ponto de entrada para o resto do app: `services.ai.pipeline`.
"""
