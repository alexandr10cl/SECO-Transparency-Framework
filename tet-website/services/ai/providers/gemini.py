"""Provider Gemini
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel

from services.ai.providers.base import RETRYABLE_CODES, AIProviderError

# Sem timeout uma chamada pode ficar pendurada indefinidamente num socket, segurando
# uma das threads do executor ate o processo reiniciar — e o `status=RUNNING` no banco
# so seria destravado pela guarda de execucao travada, sem ninguem trabalhando.
DEFAULT_TIMEOUT_S = 180

# Quantos tokens o modelo gasta olhando CADA imagem. Tabela do Gemini 3, por imagem:
#
#     LOW 280 · MEDIUM 560 · HIGH 1.120 · ULTRA_HIGH 2.240 · UNSPECIFIED 1.120
MEDIA_RESOLUTION = "MEDIA_RESOLUTION_HIGH"


def _timeout_ms() -> int:
    try:
        seconds = float(os.getenv("AI_TIMEOUT_S") or DEFAULT_TIMEOUT_S)
    except ValueError:
        seconds = DEFAULT_TIMEOUT_S
    return int(seconds * 1000)  # HttpOptions.timeout e em milissegundos


def _build_contents(prompt: str, images, types):
    """Texto + imagens INTERLEAVED, cada imagem precedida do seu proprio rotulo.

    O alinhamento entre a linha [HM-n] do prompt e a imagem correspondente e resolvido
    por construcao: o modelo le o rotulo imediatamente antes dos bytes e nunca precisa
    contar posicoes.

    A resolucao vai POR PART, e nao no `GenerateContentConfig`. Duas consequencias: a
    string crua e aceita (`Part._t_part_media_resolution` a converte em
    `PartMediaResolution`), e resolucao por part so existe em modelos Gemini 3 — se a
    cadeia de fallback descer para um 2.x as imagens podem ser recusadas, e quem recupera
    e o `except AIProviderError` de `pipeline._analyze`, repetindo a etapa 1 texto-so.
    """
    if not images:
        return prompt

    parts = [types.Part.from_text(text=prompt)]
    for label, data, mime in images:
        parts.append(types.Part.from_text(text=label))
        parts.append(types.Part.from_bytes(
            data=data, mime_type=mime, media_resolution=MEDIA_RESOLUTION,
        ))
    return parts


def generate(
    system_instruction: str,
    prompt: str,
    schema: type[BaseModel],
    model: str,
    images: Optional[List[Tuple[str, bytes, str]]] = None,
) -> Tuple[BaseModel, Dict[str, Any]]:
    """Uma tentativa contra a API do Gemini. Ver o contrato em `providers/base.py`."""
    from google import genai
    from google.genai import errors, types

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise AIProviderError(
            "GEMINI_API_KEY nao encontrada. Defina no ambiente ou em tet-website/.env",
            retryable=False,
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=_timeout_ms()),
    )
    started = time.time()

    try:
        response = client.models.generate_content(
            model=model,
            contents=_build_contents(prompt, images, types),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0,  # mitigacao: reduzir variacao entre execucoes
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
    except (errors.ServerError, errors.ClientError) as exc:
        code = getattr(exc, "code", None)
        raise AIProviderError(
            f"{model}: {exc}", code=code, retryable=code in RETRYABLE_CODES
        ) from exc
    except httpx.TimeoutException as exc:
        # Transitorio como um 503: vale tentar de novo e, depois, cair no fallback.
        raise AIProviderError(
            f"{model}: sem resposta em {_timeout_ms() // 1000}s ({exc.__class__.__name__})",
            code=504,
            retryable=True,
        ) from exc

    elapsed = time.time() - started

    parsed = response.parsed
    if parsed is None:
        # response_schema falhou; tenta o texto cru antes de desistir.
        try:
            parsed = schema.model_validate_json(response.text)
        except Exception as exc:  # noqa: BLE001 - resposta fora do schema
            raise AIProviderError(
                f"{model} devolveu uma resposta fora do schema: {exc}", retryable=False
            ) from exc

    usage = getattr(response, "usage_metadata", None)
    meta = {
        "model": model,
        "elapsed_s": round(elapsed, 2),
        "tokens": {
            "prompt": getattr(usage, "prompt_token_count", None),
            "output": getattr(usage, "candidates_token_count", None),
            "total": getattr(usage, "total_token_count", None),
        } if usage else None,
    }
    return parsed, meta
