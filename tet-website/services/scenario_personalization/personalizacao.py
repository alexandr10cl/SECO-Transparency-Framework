"""
Modulo 3 - Personalizacao de cenarios com IA

Responsabilidade: a partir do cenario-base (titulo + descricao em texto corrido,
SEM segmentacao previa) e dos dados reais do portal (saida do modulo de
estruturacao), gerar um cenario personalizado ancorado no que existe de fato na
interface avaliada.

Prompt engineering sobre modelo ja treinado. NAO ha fine-tuning.

A conversa com a API nao mora aqui — e `services/ai/provider.call_ai`, o mesmo
gateway usado pela analise de transparencia (retry, fallback de modelo, chave de
API, telemetria de tokens). Este modulo cuida só dos prompts e dos contratos de
saida, no mesmo molde de `services/ai/analyzer.py`.

Duas chamadas de IA encadeadas, nunca uma so:
  - Chamada 1 (mapear_recursos):  primeiro segmenta o cenario-base (que chega
    como bloco unico de titulo+descricao) em etapas/sub-objetivos, depois decide,
    para CADA etapa, o que e real no portal. So confirma o que conseguir apontar
    num campo exato do JSON estruturado. Temperatura baixa - e uma decisao
    factual, nao uma tarefa criativa. Nao existe segmentacao previa armazenada no
    banco: e aqui, e so aqui, que ela acontece.
  - Chamada 2 (adaptar_etapas):   recebe SOMENTE as etapas que a chamada 1
    confirmou, por isso nunca tem chance de inventar recurso. Reescreve de forma
    ampla, usando os termos reais da interface. Temperatura moderada - precisa
    soar natural, nao so repetir o texto original com o nome do recurso colado.

Este modulo NAO valida se as justificativas da chamada 1 realmente sustentam o
recurso citado - a IA tambem pode alucinar a justificativa. Isso e
responsabilidade do modulo de validacao (modulo 4), que confere o `campo_fonte`
contra o JSON estruturado de verdade.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from services.ai.provider import call_ai, provider_name

# Chamada 1 e decisao factual (o que existe?) - baixa temperatura.
TEMPERATURA_MAPEAMENTO = 0.1

# Chamada 2 e reescrita natural - temperatura moderada.
TEMPERATURA_ADAPTACAO = 0.6


# ---------------------------------------------
# Entrada
# ---------------------------------------------

@dataclass
class CenarioBase:
    """Cenario-base como armazenado no repositorio: bloco unico, sem
    segmentacao. Corresponde a `title`/`description` do model Task."""
    titulo: str
    descricao: str


# ---------------------------------------------
# Schemas de saida estruturada (Pydantic -> response_schema do Gemini)
# ---------------------------------------------

class MapeamentoItem(BaseModel):
    """Uma etapa/sub-objetivo segmentada E mapeada pela chamada 1 - as duas
    coisas acontecem juntas, na mesma chamada, porque o cenario-base nao chega
    pre-segmentado."""
    ordem: int = Field(description="Posicao da etapa na sequencia, comecando em 1.")
    objetivo: str = Field(description="O que essa etapa avalia, ligado a diretriz.")
    texto: str = Field(description="Instrucao da etapa, como segmentada a partir do cenario-base.")
    corresponde: bool = Field(description="True somente se um campo exato do JSON estruturado sustenta a etapa.")
    campo_fonte: Optional[str] = Field(
        default=None,
        description='Caminho no JSON estruturado que sustenta a correspondencia, ex.: "paginas_coletadas[2].texto".',
    )
    recurso_real: Optional[str] = Field(default=None, description="Nome/trecho real do recurso encontrado no portal.")
    motivo: str = Field(description="Por que corresponde (cita o campo) OU por que foi omitida.")


class MapeamentoResponse(BaseModel):
    itens: List[MapeamentoItem]


class EtapaPersonalizada(BaseModel):
    ordem: int
    texto: str = Field(description="Etapa reescrita, usando termos reais da interface.")


class AdaptacaoResponse(BaseModel):
    etapas: List[EtapaPersonalizada]


# ---------------------------------------------
# Prompts - Chamada 1 (segmentacao + mapeamento)
# ---------------------------------------------

SYSTEM_MAPEAMENTO = """\
Voce esta transformando um cenario generico de teste de usabilidade em um \
cenario ancorado nos dados reais de um portal de ecossistema de software.

O cenario-base fornecido NAO vem dividido em etapas - e um bloco unico de \
titulo e descricao corrida. Sua primeira tarefa e segmenta-lo em \
etapas/sub-objetivos numeradas (campo "ordem", comecando em 1), preservando \
a ordem logica das acoes que a descricao original propoe.

Em seguida, para CADA etapa que voce criar, decida se existe correspondencia \
real no portal. Voce so pode marcar "corresponde": true se conseguir apontar \
um campo EXATO do JSON estruturado fornecido que sustente essa correspondencia \
(em "campo_fonte", como um caminho, ex.: "paginas_coletadas[2].texto" ou \
"estrutura_navegacao.itens_menu[0]"). Se nao houver correspondencia clara, \
marque "corresponde": false e explique o motivo em "motivo" - NAO invente \
recursos que nao estao no JSON.
"""

_PROMPT_MAPEAMENTO = """\
Diretriz de transparencia associada a este cenario (inclui os criterios de \
sucesso que as etapas segmentadas devem poder refletir):
{diretriz}

Cenario-base a segmentar e mapear:
Titulo: {titulo_cenario}
Descricao: {descricao_cenario}

Descricao do portal fornecida pelo gestor:
{descricao_gestor}

Dados reais coletados do portal (JSON estruturado, fonte da verdade):
{dados_portal}
"""


def build_mapeamento_prompt(
    cenario_base: CenarioBase,
    diretriz: dict,
    descricao_gestor: str,
    dados_portal: dict,
) -> str:
    return _PROMPT_MAPEAMENTO.format(
        diretriz=json.dumps(diretriz, ensure_ascii=False),
        titulo_cenario=cenario_base.titulo,
        descricao_cenario=cenario_base.descricao,
        descricao_gestor=descricao_gestor or "(nao informada)",
        dados_portal=json.dumps(dados_portal, ensure_ascii=False),
    )


# ---------------------------------------------
# Prompts - Chamada 2 (adaptacao)
# ---------------------------------------------

SYSTEM_ADAPTACAO = """\
Reescreva as etapas de um cenario de teste de usabilidade para que usem os \
termos reais da interface do portal avaliado, em vez de linguagem generica. \
Voce so recebe etapas ja confirmadas como reais - pode e deve citar o \
recurso real pelo nome, mas NAO invente nada alem do que foi informado.

A reescrita pode reestruturar frases livremente para soar natural, desde \
que o objetivo de cada etapa continue reconhecivel.
"""

_PROMPT_ADAPTACAO = """\
Diretriz de transparencia associada a este cenario:
{diretriz}

Etapas confirmadas (objetivo original + recurso real encontrado no portal):
{etapas}
"""


def _formatar_etapas_adaptacao(confirmados: List[MapeamentoItem]) -> str:
    linhas = [
        f'- ordem {item.ordem}: objetivo="{item.objetivo}" | '
        f'texto_original="{item.texto}" | recurso_real="{item.recurso_real}"'
        for item in confirmados
    ]
    return "\n".join(linhas)


def build_adaptacao_prompt(diretriz: dict, confirmados: List[MapeamentoItem]) -> str:
    return _PROMPT_ADAPTACAO.format(
        diretriz=json.dumps(diretriz, ensure_ascii=False),
        etapas=_formatar_etapas_adaptacao(confirmados),
    )


# ---------------------------------------------
# Chamada 1 - segmentacao + mapeamento
# ---------------------------------------------

def mapear_recursos(
    cenario_base: CenarioBase,
    diretriz: dict,
    descricao_gestor: str,
    dados_portal: dict,
    model: Optional[str] = None,
) -> Tuple[MapeamentoResponse, Dict[str, Any]]:
    prompt = build_mapeamento_prompt(cenario_base, diretriz, descricao_gestor, dados_portal)
    return call_ai(
        SYSTEM_MAPEAMENTO, prompt, MapeamentoResponse,
        model=model, temperature=TEMPERATURA_MAPEAMENTO,
    )


# ---------------------------------------------
# Chamada 2 - adaptacao
# ---------------------------------------------

def adaptar_etapas(
    mapeamento: MapeamentoResponse,
    diretriz: dict,
    model: Optional[str] = None,
) -> Tuple[AdaptacaoResponse, Dict[str, Any]]:
    confirmados = [item for item in mapeamento.itens if item.corresponde]
    if not confirmados:
        return AdaptacaoResponse(etapas=[]), {}

    prompt = build_adaptacao_prompt(diretriz, confirmados)
    resposta, meta = call_ai(
        SYSTEM_ADAPTACAO, prompt, AdaptacaoResponse,
        model=model, temperature=TEMPERATURA_ADAPTACAO,
    )
    resposta.etapas.sort(key=lambda e: e.ordem)
    return resposta, meta


# ---------------------------------------------
# Orquestracao - monta a saida do modulo 3, ainda por etapa
# ---------------------------------------------

def montar_resultado(
    mapeamento: MapeamentoResponse,
    adaptacao: AdaptacaoResponse,
) -> dict:
    """Monta a saida do modulo 3 a partir das duas chamadas, MANTENDO a
    granularidade por etapa (nao junta `cenario_personalizado` num texto so
    aqui). O modulo 4 (validacao) precisa poder remover uma etapa individual
    cujo recurso nao se confirme contra o JSON estruturado - impossivel de
    fazer com cirurgia de string depois que o texto de varias etapas ja virou
    um paragrafo unico. Quem junta o texto final e
    `validacao.montar_resultado_validado`, depois de remover o que nao passar.
    """
    etapas_omitidas = [
        {"etapa": item.objetivo, "motivo": item.motivo}
        for item in mapeamento.itens
        if not item.corresponde
    ]
    confirmados = [item for item in mapeamento.itens if item.corresponde]
    texto_por_ordem = {e.ordem: e.texto for e in adaptacao.etapas}

    etapas_personalizadas = [
        {
            "ordem": item.ordem,
            # Fallback ao texto original so no caso (nao esperado) da chamada 2
            # nao ter devolvido essa ordem - nao deveria acontecer, ja que ela
            # so recebe exatamente os itens confirmados.
            "texto": texto_por_ordem.get(item.ordem, item.texto),
            "recurso_real": item.recurso_real,
            "campo_fonte": item.campo_fonte,
        }
        for item in confirmados
    ]

    return {
        "etapas_personalizadas": etapas_personalizadas,
        "etapas_omitidas": etapas_omitidas,
    }


def personalizar(
    cenario_base: CenarioBase,
    diretriz: dict,
    descricao_gestor: str,
    dados_portal: dict,
    model: Optional[str] = None,
) -> Tuple[dict, Dict[str, Any]]:
    """Roda as duas chamadas e devolve `(resultado_modulo3, meta)`.

    `resultado_modulo3` ainda esta por etapa (`etapas_personalizadas` +
    `etapas_omitidas`) - quem monta o `cenario_personalizado` final e
    `validacao.montar_resultado_validado`, depois de remover o que o modulo 4
    (validacao) nao confirmar.

    `meta` ja vem no formato que PersonalizedScenario espera (provider, model,
    tokens_total, ai_duration_s, debug) - mesma agregacao de
    `services/ai/pipeline.py` para AIAnalysis, para as duas features lerem igual
    na tela e no log.
    """
    mapeamento, meta1 = mapear_recursos(cenario_base, diretriz, descricao_gestor, dados_portal, model)
    adaptacao, meta2 = adaptar_etapas(mapeamento, diretriz, model)
    resultado = montar_resultado(mapeamento, adaptacao)

    tokens = [
        (meta.get("tokens") or {}).get("total") or 0
        for meta in (meta1, meta2) if meta
    ]
    meta = {
        "provider": meta1.get("provider") or provider_name(),
        "model": meta1.get("model"),
        "tokens_total": sum(tokens) or None,
        "ai_duration_s": round(sum(m.get("elapsed_s") or 0 for m in (meta1, meta2) if m), 2),
        "debug": {"stage1": meta1, "stage2": meta2 or None},
    }
    return resultado, meta
