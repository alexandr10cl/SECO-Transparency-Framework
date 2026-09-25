"""`call_ai()` — a unica porta de saida para qualquer LLM.

Nenhum modulo fora de services/ai/providers/ importa o SDK de um provedor. Trocar de modelo ou de provedor
é mexer no .env; trocar de SDK e escrever um arquivo novo em `providers/` e somar uma linha em `_PROVIDERS`.

A divisao que faz a abstracao valer:

    provider.py  ->  politica de retry, backoff e cadeia de fallback   (agnostica)
    providers/*  ->  uma chamada e a traducao do erro do SDK           (especifica)

Configuracao:

    AI_PROVIDER          gemini
    AI_MODEL             modelo padrao
    AI_FALLBACK_MODELS   usados em ordem quando o padrao esta indisponivel
    AI_MODELS            lista oferecida no <select> da tela

"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

from services.ai.providers import gemini
from services.ai.providers.base import AIProviderError

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

DEFAULT_PICKER_MODELS = [DEFAULT_MODEL, "gemini-3.7-flash"] + DEFAULT_FALLBACK_MODELS

# Registry. O segundo provider e uma linha aqui mais um arquivo em providers/.
_PROVIDERS = {
    "gemini": gemini.generate,
}

_logger = logging.getLogger(__name__)


def _log(message: str, *args: Any) -> None:
    """Loga pelo app quando ha contexto; pelo logging padrao na CLI e em testes."""
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            current_app.logger.info(message, *args)
            return
    except Exception:  # noqa: BLE001 - logar nunca pode derrubar a analise
        pass
    _logger.info(message, *args)


def _env_list(name: str) -> List[str]:
    raw = os.getenv(name) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def provider_name() -> str:
    return (os.getenv("AI_PROVIDER") or DEFAULT_PROVIDER).strip().lower()


def default_model() -> str:
    return (os.getenv("AI_MODEL") or DEFAULT_MODEL).strip()


def fallback_models() -> List[str]:
    return _env_list("AI_FALLBACK_MODELS") or list(DEFAULT_FALLBACK_MODELS)


def available_models() -> List[str]:
    """Modelos oferecidos no seletor da tela.

    Sem `AI_MODELS`, cai para uma lista util de fabrica. O modelo configurado entra
    sempre — senao o seletor mostraria uma opcao diferente da que esta em uso.
    """
    models = _env_list("AI_MODELS") or list(DEFAULT_PICKER_MODELS)
    return list(dict.fromkeys([default_model()] + models))  # dedup preservando ordem


def resolve_model(requested: Optional[str]) -> str:
    """Modelo pedido, se ele estiver na lista configurada; senao o padrao.

    Filtrar contra `available_models()` impede que um POST arbitrario da tela mande
    o backend chamar um modelo que o gestor nao deveria poder escolher.
    """
    if requested and requested.strip() in available_models():
        return requested.strip()
    return default_model()


def call_ai(
    system_instruction: str,
    prompt: str,
    schema: type[BaseModel],
    model: Optional[str] = None,
    fallbacks: Optional[List[str]] = None,
    attempts: int = 4,
    images: Optional[List[Tuple[str, bytes, str]]] = None,
    temperature: float = 0,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[BaseModel, Dict[str, Any]]:
    """Uma chamada estruturada a um LLM, com retry e fallback de modelo.

    Devolve `(objeto pydantic validado, meta)`, onde meta traz o modelo que de fato
    respondeu — que pode nao ser o pedido, se a cadeia de fallback entrou em acao.

    `images` e uma lista de `(rotulo, bytes, mime)` que o provider intercala com o texto,
    cada imagem precedida do seu rotulo. Repassada como esta: quem decide repetir sem
    imagem e `pipeline._analyze`.

    `temperature` default 0 preserva o comportamento original (mitigacao: reduzir
    variacao entre execucoes) para quem nao passar nada — a analise de transparencia
    (services/ai/analyzer.py) sempre chamou assim. Existe para chamadas que precisam de
    mais de um ponto na escala, como a personalizacao de cenarios (mapeamento factual em
    baixa temperatura, reescrita em temperatura moderada).

    O 503 UNAVAILABLE ("high demand") e comum nos modelos flash mais novos e e
    transitorio: tentamos o mesmo modelo algumas vezes com backoff exponencial e, se
    ele continuar indisponivel, descemos a cadeia. Erro nao-retryable (chave invalida,
    modelo inexistente para a chave) pula direto para o proximo modelo.

    `on_progress`, se passado, e chamado de forma SINCRONA (bloqueia a mesma thread que
    esta esperando a API) a cada evento da cadeia - antes de cada tentativa, quando um
    modelo e trocado pelo proximo, e quando a cadeia inteira se esgota. Existe pra quem
    chama poder mostrar isso na tela (personalizacao de cenarios) enquanto a chamada
    ainda esta rodando, sem esperar o resultado final. Nunca deve levantar - quem
    implementa e responsavel por nao derrubar a chamada de IA por causa de um log.
    """
    name = provider_name()
    generate = _PROVIDERS.get(name)
    if generate is None:
        raise AIProviderError(
            f"AI_PROVIDER='{name}' desconhecido. Disponiveis: {sorted(_PROVIDERS)}",
            retryable=False,
        )

    requested = model or default_model()
    chain = [requested] + [
        m for m in (fallbacks if fallbacks is not None else fallback_models())
        if m != requested
    ]

    def _progress(event: Dict[str, Any]) -> None:
        if on_progress is None:
            return
        try:
            on_progress(event)
        except Exception:  # noqa: BLE001 - um erro no callback de UI nunca pode derrubar a chamada de IA
            _log("ai: on_progress levantou, ignorando.")

    started = time.time()
    last_error: Optional[AIProviderError] = None
    previous_candidate: Optional[str] = None

    for chain_index, candidate in enumerate(chain):
        if previous_candidate is not None:
            _progress({
                "event": "model_switch", "from": previous_candidate, "to": candidate,
                "chain_index": chain_index,
            })
        previous_candidate = candidate

        for attempt in range(1, attempts + 1):
            _progress({
                "event": "attempt", "model": candidate, "attempt": attempt,
                "attempts_max": attempts, "chain_index": chain_index,
            })
            try:
                parsed, meta = generate(
                    system_instruction, prompt, schema, candidate,
                    images=images, temperature=temperature,
                )
            except AIProviderError as exc:
                last_error = exc
                if not exc.retryable:
                    _log("ai: %s respondeu %s, indo para o proximo modelo.", candidate, exc.code)
                    _progress({
                        "event": "model_failed", "model": candidate, "attempt": attempt,
                        "code": exc.code, "retryable": False,
                    })
                    break
                if attempt == attempts:
                    _log("ai: %s indisponivel apos %s tentativas.", candidate, attempts)
                    _progress({
                        "event": "model_failed", "model": candidate, "attempt": attempt,
                        "code": exc.code, "retryable": True,
                    })
                    break
                wait = 2 ** attempt  # 2s, 4s, 8s
                _log(
                    "ai: %s respondeu %s (%s/%s); nova tentativa em %ss...",
                    candidate, exc.code, attempt, attempts, wait,
                )
                _progress({
                    "event": "retry_wait", "model": candidate, "attempt": attempt,
                    "attempts_max": attempts, "code": exc.code, "wait_s": wait,
                })
                time.sleep(wait)
                continue

            meta["provider"] = name
            meta["model_requested"] = requested
            meta["attempt"] = attempt
            meta["model_switches"] = chain_index
            # Tempo de parede da cadeia inteira, incluindo as esperas — e o numero que
            # interessa para comparar custo entre modelos.
            meta["elapsed_s"] = round(time.time() - started, 2)
            _progress({
                "event": "success", "model": candidate, "attempt": attempt,
                "chain_index": chain_index,
            })
            return parsed, meta

    _progress({"event": "chain_exhausted", "chain": chain})
    raise AIProviderError(
        f"Nenhum modelo respondeu. Tentados: {', '.join(chain)}. Ultimo erro: {last_error}",
        code=getattr(last_error, "code", None),
        retryable=False,
    )
