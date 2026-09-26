"""`call_ai()` — a unica porta de saida para qualquer LLM.

Nenhum modulo fora de services/ai/providers/ importa o SDK de um provedor. Trocar de modelo ou de provedor
é mexer no .env; trocar de SDK é escrever um arquivo novo em `providers/` e somar uma entrada em
`_PROVIDERS` (generate, modelos, default, fallbacks e os prefixos de nome do provider).

A divisao que faz a abstracao valer:

    provider.py  ->  politica de retry, backoff e cadeia de fallback   (agnostica)
    providers/*  ->  uma chamada e a traducao do erro do SDK           (especifica)

O provider de uma chamada e derivado do MODELO, nao so de `AI_PROVIDER`: `available_models()`
e a uniao dos modelos de todos os providers, e `provider_for()` roteia cada um ao seu dono.
`AI_PROVIDER` só decide o provider de um `AI_MODEL` customizado, fora de toda tabela.

Configuracao:

    AI_PROVIDER          gemini (so importa para modelo fora da tabela de nenhum provider)
    AI_MODEL             modelo padrao
    AI_FALLBACK_MODELS   usados em ordem quando o padrao esta indisponivel (mesmo provider)
    AI_MODELS            lista oferecida no <select> da tela

"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from pydantic import BaseModel

from services.ai.providers import gemini, openai_provider
from services.ai.providers.base import AIProviderError

DEFAULT_PROVIDER = "gemini"


class _Provider(NamedTuple):
    generate: Callable[..., Tuple[BaseModel, Dict[str, Any]]]
    models: List[str]
    default_model: str
    fallback_models: List[str]
    # Prefixos que identificam um nome de modelo como "deste provider" — so para o aviso
    # de (b): nome que NAO casa com prefixo nenhum e modelo customizado legitimo, e passa
    # calado. Nome que casa com o prefixo de OUTRO provider registrado e o typo provavel.
    model_prefixes: Tuple[str, ...]


# Registry. Um segundo provider e um arquivo em providers/ mais uma entrada aqui.
_PROVIDERS: Dict[str, _Provider] = {
    "gemini": _Provider(
        generate=gemini.generate,
        models=["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash"],
        default_model="gemini-3.6-flash",
        fallback_models=["gemini-3.5-flash"],
        model_prefixes=("gemini",),
    ),
    "openai": _Provider(
        generate=openai_provider.generate,
        # Rotulos do seletor, nao nomes de modelo da API — a traducao (e o esforco de
        # raciocinio de cada um) vive inteira em `openai_provider.MODELS`.
        models=list(openai_provider.MODELS),
        default_model="gpt-6-luna",
        fallback_models=[],  # decisao deliberada: sem escalada de custo por falha
        model_prefixes=("gpt-", "o1", "o3", "ft:gpt"),
    ),
}

# {modelo -> provider}: e o seletor da tela que escolhe o provider, nao so a env.
_PROVIDER_BY_MODEL: Dict[str, str] = {
    model: name for name, entry in _PROVIDERS.items() for model in entry.models
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


def _active() -> _Provider:
    """O provider de `provider_name()`, ou o padrao quando o nome e desconhecido.

    NUNCA levanta — so `call_ai` pode falhar por provider invalido.
    """
    return _PROVIDERS.get(provider_name(), _PROVIDERS[DEFAULT_PROVIDER])


def provider_for(model: str) -> str:
    """Provider dono deste modelo pela tabela; sem dono, cai na env `AI_PROVIDER`."""
    return _PROVIDER_BY_MODEL.get(model) or provider_name()


def default_model() -> str:
    return (os.getenv("AI_MODEL") or _active().default_model).strip()


def fallback_models(model: str) -> List[str]:
    """Cadeia de fallback para `model`, restrita ao SEU provider (`AI_FALLBACK_MODELS` e
    um unico campo de texto, sem nocao de qual provider cada nome pertence)."""
    provider = provider_for(model)
    configured = _env_list("AI_FALLBACK_MODELS")
    if configured:
        return [m for m in configured if provider_for(m) == provider]
    entry = _PROVIDERS.get(provider)
    return list(entry.fallback_models) if entry else []


def available_models() -> List[str]:
    """Modelos oferecidos no seletor da tela.

    Sem `AI_MODELS`, e a UNIAO dos modelos de todos os providers registrados — e como os
    modelos OpenAI passam a aparecer ao lado dos do Gemini sem tocar em JS. O modelo
    configurado entra sempre — senao o seletor mostraria uma opcao diferente da em uso.
    """
    models = _env_list("AI_MODELS") or [
        model for entry in _PROVIDERS.values() for model in entry.models
    ]
    return list(dict.fromkeys([default_model()] + models))  # dedup preservando ordem


def resolve_model(requested: Optional[str]) -> str:
    """Modelo pedido, se ele estiver na lista configurada; senao o padrao.

    Filtrar contra `available_models()` impede que um POST arbitrario da tela mande
    o backend chamar um modelo que o gestor nao deveria poder escolher.
    """
    if requested and requested.strip() in available_models():
        return requested.strip()
    return default_model()


def _warn_if_cross_provider(model: str, resolved_provider: str) -> None:
    """Avisa SO quando o nome casa com o prefixo de OUTRO provider registrado — nome
    desconhecido pode ser um AI_MODEL customizado legitimo, e nao gera aviso."""
    for name, entry in _PROVIDERS.items():
        if name == resolved_provider:
            continue
        if any(model.startswith(prefix) for prefix in entry.model_prefixes):
            _log(
                "ai: modelo '%s' parece ser do provider '%s', mas foi roteado para '%s' "
                "— confira AI_MODEL/AI_MODELS/AI_FALLBACK_MODELS no .env.",
                model, name, resolved_provider,
            )
            return


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

    O provider de CADA candidato da cadeia e resolvido individualmente por
    `provider_for()` — a cadeia pode, em tese, misturar modelos de providers diferentes
    (nao acontece hoje: nenhum provider tem fallback cross-provider configurado).
    """
    requested = model or default_model()
    chain = [requested] + [
        m for m in (fallbacks if fallbacks is not None else fallback_models(requested))
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

    for candidate in chain:
        provider = provider_for(candidate)
        _warn_if_cross_provider(candidate, provider)
        entry = _PROVIDERS.get(provider)
        if entry is None:
            last_error = AIProviderError(
                f"AI_PROVIDER='{provider}' desconhecido (modelo '{candidate}'). "
                f"Disponiveis: {sorted(_PROVIDERS)}",
                retryable=False,
            )
            _log("ai: %s -> provider '%s' desconhecido, indo para o proximo modelo.",
                 candidate, provider)
            continue

        for attempt in range(1, attempts + 1):
            _progress({
                "event": "attempt", "model": candidate, "attempt": attempt,
                "attempts_max": attempts, "chain_index": chain_index,
            })
            try:
                parsed, meta = entry.generate(
                    system_instruction, prompt, schema, candidate, images=images
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

            meta["provider"] = provider
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
