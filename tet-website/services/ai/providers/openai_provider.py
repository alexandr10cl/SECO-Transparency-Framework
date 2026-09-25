"""Provider OpenAI.

Nome com sufixo (`openai_provider`, nao `openai`) para o arquivo nao sombrear o pacote
`openai` na hora do `import openai` la embaixo em `generate()`.

Sem `temperature`: a familia GPT-6 rejeita o parametro (HTTP 400) com raciocinio ligado,
que e sempre o caso aqui — sem equivalente ao `temperature=0` do `gemini.py`.

`reasoning.effort` faz parte do MODELO (tabela `MODELS` abaixo), nao e constante global:
o mesmo `gpt-6-luna` aparece duas vezes no seletor com esforcos diferentes.
"""
from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from services.ai.providers import base
from services.ai.providers.base import RETRYABLE_CODES, AIProviderError

# Equivalente ao MEDIA_RESOLUTION_HIGH do Gemini, mas o custo escala com os pixels da
# imagem em vez de ser fixo por nivel — ver CLAUDE.md, secao de heatmaps na analise de IA.
IMAGE_DETAIL = "high"

# Teto de output, reasoning tokens incluidos (cobrados como saida). Errar para BAIXO e
# pior que nao ter teto: truncar (`status="incomplete"`) e retryable=False, o que mata a
# cadeia inteira e ainda dispara o retry texto-so de `pipeline._analyze`.
MAX_OUTPUT_TOKENS = 32000

# Rotulo do seletor -> (modelo real da API, esforco de raciocinio). E aqui que "barato e
# rapido" e "muito bom" viram tres entradas: o mesmo gpt-6-luna com "medium" e com "high".
# Um rotulo fora desta tabela (AI_MODEL customizado) cai no esforco default abaixo.
MODELS: Dict[str, Tuple[str, str]] = {
    "gpt-6-luna": ("gpt-6-luna", "medium"),
    "gpt-6-luna-high": ("gpt-6-luna", "high"),
    "gpt-6-sol": ("gpt-6-sol", "medium"),
}
DEFAULT_EFFORT = "medium"


def _resolve(label: str) -> Tuple[str, str]:
    return MODELS.get(label, (label, DEFAULT_EFFORT))


def _data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _build_input(prompt: str, images):
    """Texto puro sem imagens; INTERLEAVED com elas quando ha.

    Espelha `gemini.py::_build_contents`: sem imagens o conteudo enviado tem de ser
    EXATAMENTE a string antes (contrato, regra 4) — e disso que depende a degradacao
    texto-so de `pipeline._analyze`. Com imagens, cada uma e precedida do seu proprio
    rotulo `[HM-n]`, resolvendo por construcao o alinhamento entre o texto e a imagem.
    """
    if not images:
        return prompt

    content = [{"type": "input_text", "text": prompt}]
    for label, data, mime in images:
        content.append({"type": "input_text", "text": label})
        content.append({
            "type": "input_image",
            "image_url": _data_url(data, mime),
            "detail": IMAGE_DETAIL,
        })
    return [{"role": "user", "content": content}]


def _refusal_text(response) -> Optional[str]:
    """Varre `response.output` por uma parte do tipo refusal, se houver.

    Itens de reasoning nao tem `.content`, por isso o getattr defensivo em cada nivel.
    """
    for item in getattr(response, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                return getattr(part, "refusal", None) or "recusado sem detalhe"
    return None


def generate(
    system_instruction: str,
    prompt: str,
    schema: type[BaseModel],
    model: str,
    images: Optional[List[Tuple[str, bytes, str]]] = None,
) -> Tuple[BaseModel, Dict[str, Any]]:
    """Uma tentativa contra a API da OpenAI. Ver o contrato em `providers/base.py`."""
    import openai
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Explicito e ANTES de construir o client: sem isto, `OpenAI()` levantaria
        # `openai.OpenAIError` na propria construcao, fora do try abaixo — escaparia como
        # excecao crua do SDK em vez de `AIProviderError` (contrato, regra 3).
        raise AIProviderError(
            "OPENAI_API_KEY nao encontrada. Defina no ambiente ou em tet-website/.env",
            retryable=False,
        )

    api_model, effort = _resolve(model)
    started = time.time()

    try:
        # max_retries=0: a politica de retry e da cadeia de `provider.py` (contrato,
        # regra 2). O default do SDK e 2 e transformaria cada tentativa daqui em ate 3
        # chamadas de rede, escondido do orquestrador.
        with OpenAI(
            api_key=api_key, max_retries=0, timeout=base.timeout_seconds(),
        ) as client:
            response = client.responses.parse(
                model=api_model,
                instructions=system_instruction,
                input=_build_input(prompt, images),
                text_format=schema,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                reasoning={"effort": effort},
            )
    except openai.APIStatusError as exc:
        # Unica classe com .status_code: 400/401/403/404/409/422/429/5xx.
        code = exc.status_code
        raise AIProviderError(
            f"{model}: {str(exc)[:500]}", code=code, retryable=code in RETRYABLE_CODES
        ) from exc
    except openai.APITimeoutError as exc:
        # ANTES de APIConnectionError: e subclasse dela. Sem resposta HTTP, sem status_code
        # — tratado como 504, no mesmo espirito do httpx.TimeoutException do gemini.py.
        raise AIProviderError(
            f"{model}: sem resposta em {base.timeout_seconds():.0f}s ({exc.__class__.__name__})",
            code=504,
            retryable=True,
        ) from exc
    except openai.APIConnectionError as exc:
        raise AIProviderError(
            f"{model}: falha de conexao ({exc.__class__.__name__})", code=503, retryable=True,
        ) from exc
    except (openai.LengthFinishReasonError, openai.ContentFilterFinishReasonError) as exc:
        # Nao descendem de APIStatusError — sem esta clausula escapariam como excecao crua
        # do SDK, pulando a degradacao texto-so de `pipeline._analyze` (contrato, regra 3).
        raise AIProviderError(
            f"{model}: {exc.__class__.__name__} ({str(exc)[:300]})", retryable=False,
        ) from exc
    except openai.OpenAIError as exc:
        # Piso do SDK: cobre o que mais nao tiver .status_code (ex.: chave malformada).
        # Sem `except Exception` aqui — um erro de validacao pydantic e bug legitimo e
        # deve escapar alto, como em gemini.py.
        raise AIProviderError(f"{model}: {str(exc)[:500]}", retryable=False) from exc

    elapsed = time.time() - started
    usage = getattr(response, "usage", None)

    if getattr(response, "status", None) == "incomplete":
        reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
        usage_note = (
            f" (usage: input={getattr(usage, 'input_tokens', '?')}, "
            f"output={getattr(usage, 'output_tokens', '?')}, cap={MAX_OUTPUT_TOKENS})"
        )
        raise AIProviderError(
            f"{model}: resposta incompleta ({reason}){usage_note}. "
            "Suba MAX_OUTPUT_TOKENS ou baixe o esforco de raciocinio se persistir.",
            retryable=False,
        )

    error = getattr(response, "error", None)
    if error is not None:
        raise AIProviderError(
            f"{model}: {getattr(error, 'code', '?')}: {getattr(error, 'message', error)}",
            retryable=False,
        )

    refusal = _refusal_text(response)
    if refusal is not None:
        raise AIProviderError(f"{model}: recusado — {refusal[:300]}", retryable=False)

    parsed = response.output_parsed
    if parsed is None:
        raise AIProviderError(f"{model} devolveu uma resposta fora do schema.", retryable=False)

    reasoning_tokens = getattr(
        getattr(usage, "output_tokens_details", None), "reasoning_tokens", None,
    )
    meta = {
        "model": model,
        "elapsed_s": round(elapsed, 2),
        "tokens": {
            "prompt": getattr(usage, "input_tokens", None),
            "output": getattr(usage, "output_tokens", None),
            "total": getattr(usage, "total_tokens", None),
            "reasoning": reasoning_tokens,
        } if usage else None,
    }
    return parsed, meta
