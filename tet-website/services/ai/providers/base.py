"""Contrato que todo provider de LLM precisa cumprir.

Um provider implementa **uma funcao so**:

    generate(system_instruction, prompt, schema, model) -> tuple[BaseModel, dict]

Regras do contrato:

1. Devolve o objeto pydantic ja validado contra `schema` e um dict de metadados
   `{"model": str, "elapsed_s": float, "tokens": {...} | None}`.
2. **Nao tenta de novo.** A politica de retry, backoff e cadeia de fallback e agnostica
   de provedor e vive em `services/ai/provider.py`. O provider so faz uma tentativa.
3. Traduz qualquer falha do SDK para `AIProviderError`, marcando `retryable` conforme
   `RETRYABLE_CODES`. Essa traducao e a unica parte especifica do provedor — e por isso
   que ela mora aqui e nao no orquestrador.

Nenhum modulo fora de `services/ai/providers/` deve importar o SDK de um provedor.
"""
from __future__ import annotations

from typing import Optional

RETRYABLE_CODES = frozenset({429, 500, 502, 503, 504})

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
