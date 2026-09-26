"""Contrato que todo provider de LLM precisa cumprir.

Um provider implementa **uma funcao so**:

    generate(system_instruction, prompt, schema, model, images=None, temperature=0)
        -> tuple[BaseModel, dict]

Regras do contrato:

1. Devolve o objeto pydantic ja validado contra `schema` e um dict de metadados
   `{"model": str, "elapsed_s": float, "tokens": {...} | None}`.
2. **Nao tenta de novo.** A politica de retry, backoff e cadeia de fallback e agnostica
   de provedor e vive em `services/ai/provider.py`. O provider so faz uma tentativa.
3. Traduz qualquer falha do SDK para `AIProviderError`, marcando `retryable` conforme
   `RETRYABLE_CODES`. Essa traducao e a unica parte especifica do provedor — e por isso
   que ela mora aqui e nao no orquestrador.
4. **`images`** e uma lista de `(rotulo, bytes, mime)`, ou None. Havendo imagens, o
   provider as INTERCALA com o texto, cada uma precedida do seu proprio rotulo — e assim
   que a linha `[HM-n]` e a imagem correspondente se encontram. Quando e None ou vazia, o
   conteudo enviado tem de ser exatamente o de antes (texto puro): a degradacao texto-so
   de `pipeline._analyze` depende disso.
5. **O `schema` recebido tem de ser strict-JSON-Schema-compatible.** Sem `Optional`/
   `Union`/valor default, sem `Field(min_length/max_length/pattern/ge/le/...)`, raiz
   sempre um objeto. O Gemini tolera essas construcoes; o provider OpenAI nao — ele
   converte a classe pydantic para JSON Schema em modo strict, e uma violacao vira 400
   *no request*, ou seja `retryable=False`, o que mata a cadeia inteira de uma vez e
   ainda queima o retry texto-so de `pipeline._analyze` (regra 4). Sem testes no repo
   para pegar isso automaticamente, esta regra e o unico lugar que avisa antes do fato.

Nenhum modulo fora de `services/ai/providers/` deve importar o SDK de um provedor.
"""
from __future__ import annotations

import os
from typing import Optional

RETRYABLE_CODES = frozenset({429, 500, 502, 503, 504})

# Compartilhado entre providers porque e politica agnostica (regra 2): sem timeout uma
# chamada pode ficar pendurada indefinidamente num socket, segurando uma das threads do
# executor ate o processo reiniciar. SEMPRE EM SEGUNDOS — cada provider converte para a
# unidade que o seu SDK espera (o Gemini quer milissegundos, ver `gemini.py::_timeout_ms`).
DEFAULT_TIMEOUT_S = 180


def timeout_seconds() -> float:
    try:
        return float(os.getenv("AI_TIMEOUT_S") or DEFAULT_TIMEOUT_S)
    except ValueError:
        return DEFAULT_TIMEOUT_S

class AIProviderError(Exception):
    """Falha normalizada de um provider de LLM.

    `retryable=True` significa "tente de novo em alguns segundos" (sobrecarga,
    rate limit). `retryable=False` significa "esse modelo nao vai responder"
    (chave invalida, modelo inexistente, prompt rejeitado) — o orquestrador pula
    direto para o proximo modelo da cadeia.
    """

    def __init__(self, message: str, *, code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
