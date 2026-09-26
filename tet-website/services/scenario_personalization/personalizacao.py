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
    confirmou, por isso nunca tem chance de inventar recurso. Nao reescreve mais
    etapa por etapa como uma lista de instrucoes - compoe o cenario final no
    MESMO formato do cenario-base: um unico paragrafo corrido, com persona e
    objetivo (ex.: "Imagine que voce e um desenvolvedor que acabou de entrar
    neste projeto e precisa..."), citando os recursos reais em vez dos genericos
    do cenario-base. Temperatura moderada - precisa soar natural, nao so repetir
    o texto original com o nome do recurso colado.

    A moldura do paragrafo (abertura com a persona, fechamento convidando a
    explorar) e escrita pela IA mas nunca e validada contra o JSON estruturado -
    de proposito, porque essas frases nunca citam um recurso especifico (so
    contexto/motivacao). So os recursos entram como uma ENUMERACAO montada em
    Python (`validacao._montar_paragrafo`), nao costurada pela IA numa frase so:
    e o que permite ao modulo 4 remover um recurso individual que falhar na
    validacao sem quebrar a gramatica do resto e sem precisar de outra chamada
    de IA (ver docstring de validacao.py).

Este modulo NAO valida se as justificativas da chamada 1 realmente sustentam o
recurso citado - a IA tambem pode alucinar a justificativa. Isso e
responsabilidade do modulo de validacao (modulo 4), que confere o `campo_fonte`
contra o JSON estruturado de verdade.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from services.ai.provider import call_ai, provider_name

# Chamada 1 e decisao factual (o que existe?) - baixa temperatura.
TEMPERATURA_MAPEAMENTO = 0.1

# Chamada 2 e reescrita natural - temperatura moderada.
TEMPERATURA_ADAPTACAO = 0.6

ProgressCallback = Callable[[Dict[str, Any]], None]


def _tag_stage(on_progress: Optional[ProgressCallback], stage: str) -> Optional[ProgressCallback]:
    """Encapsula `on_progress` marcando cada evento com a etapa que o gerou -
    as duas chamadas de `call_ai` (mapeamento, adaptacao) escrevem no mesmo
    log de progresso, e quem le (tela do gestor) precisa saber qual delas
    esta rodando."""
    if on_progress is None:
        return None

    def _wrapped(event: Dict[str, Any]) -> None:
        on_progress({**event, "stage": stage})

    return _wrapped


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


class RecursoObjetivo(BaseModel):
    """Um recurso confirmado, ja pronto para entrar como item de uma
    enumeracao (nao e uma frase completa nem uma instrucao imperativa)."""
    ordem: int = Field(description="Mesma ordem da etapa correspondente recebida (chamada 1), para o modulo 4 conseguir remover este item sozinho se a validacao rejeitar.")
    texto: str = Field(
        description='Frase nominal curta nomeando O QUE e o recurso real (nao ONDE ele '
        'fica), pronta para entrar numa lista como "..., X, Y e Z." - ex.: \'um guia '
        'introdutorio para iniciantes\' ou \'a referencia da linguagem\'. Pode citar o '
        'nome real do recurso quando ele proprio descreve o conteudo (ex.: "o \'Beginner\'s '
        'Guide\'"), mas NUNCA descreva caminho de navegacao, menu, secao ou pagina onde '
        'encontra-lo (nada de "em...", "na pagina...", "no menu...", breadcrumbs tipo '
        '"X / Y / Z") - o avaliador precisa descobrir o caminho sozinho, a etapa 4 do '
        'metodo so existe para confirmar que o recurso existe de fato, nao para revelar '
        'onde esta. NAO e uma frase completa, NAO comeca com maiuscula nem termina com '
        'pontuacao.'
    )


class AdaptacaoResponse(BaseModel):
    persona_e_contexto: str = Field(
        description='Frase de abertura do cenario, no MESMO estilo e tom do cenario-base '
        'recebido: apresenta uma persona (quem esta executando a acao) e a '
        'situacao/motivacao geral - ex. "Imagine que você é um desenvolvedor que acabou '
        'de ingressar neste projeto e precisa começar uma nova integração com a '
        'plataforma." NUNCA cita um recurso especifico do portal - essa frase nunca '
        'passa pela validacao automatica.'
    )
    frase_objetivo: str = Field(
        description='Inicio da frase que introduz os recursos, SEM pontuacao final e SEM '
        'os recursos em si - ex.: "Seu objetivo é encontrar rapidamente" ou "Você '
        'precisa localizar". Os recursos confirmados (campo "itens") sao encaixados '
        'logo em seguida, automaticamente, como uma enumeracao.'
    )
    fechamento: str = Field(
        description='Frase final do cenario, convidando a explorar livremente - no MESMO '
        'estilo de "Explore o portal livremente, como faria em uma situação real, até '
        'sentir que encontrou as informações necessárias." NUNCA cita um recurso '
        'especifico do portal.'
    )
    conectivo_final: str = Field(
        description='A palavra que significa "e" no MESMO idioma do cenario-base recebido '
        '(ex.: "and" em ingles, "e" em portugues, "y" em espanhol) - usada so entre o '
        'penultimo e o ultimo item da enumeracao de recursos.'
    )
    itens: List[RecursoObjetivo]


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


def _portal_para_prompt(dados_portal: dict) -> dict:
    """Copia `dados_portal` sem `links_internos` por pagina, so para o texto
    do prompt - o dado completo continua intacto em `collection.dados_portal`
    (banco) para a validacao (modulo 4).

    `links_internos` e so URLs cruas, sem texto de link - a IA nao tem como
    citar um recurso a partir disso (o schema pede um "recurso_real"
    legivel), entao o campo so pesa no prompt sem nunca virar `campo_fonte`
    na pratica. Removido aqui, nunca visto pelo modelo, nunca citado -
    seguro por construcao, sem precisar validar nada a mais no modulo 4.
    """
    return {
        **dados_portal,
        "paginas_coletadas": [
            {k: v for k, v in pagina.items() if k != "links_internos"}
            for pagina in dados_portal.get("paginas_coletadas", [])
        ],
    }


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
        dados_portal=json.dumps(_portal_para_prompt(dados_portal), ensure_ascii=False),
    )


# ---------------------------------------------
# Prompts - Chamada 2 (adaptacao)
# ---------------------------------------------

SYSTEM_ADAPTACAO = """\
Voce esta compondo a versao personalizada de um cenario de teste de \
usabilidade, no MESMO formato do cenario-base recebido: um UNICO paragrafo \
corrido, em segunda pessoa, que apresenta uma persona e um objetivo - NAO uma \
lista de instrucoes passo a passo, NAO um roteiro de cliques citando nomes \
literais de botoes/menus.

Voce recebe as etapas ja confirmadas como reais (chamada anterior) - cada uma \
com o objetivo original e o recurso real encontrado no portal. Sua tarefa tem \
cinco partes, sempre no mesmo idioma do cenario-base recebido:

1. "persona_e_contexto": a frase de abertura do cenario-base, adaptada - \
mesma persona/situacao/motivacao, sem citar nenhum recurso especifico do \
portal.
2. "frase_objetivo": o inicio da frase que introduz os recursos (ex.: "Seu \
objetivo e encontrar rapidamente"), sem pontuacao final - os recursos \
confirmados entram logo depois, automaticamente, como uma enumeracao.
3. "itens": para CADA etapa confirmada recebida, uma frase nominal curta \
nomeando O QUE e o recurso real (pode e deve usar o nome real do recurso, \
mas NAO invente nada alem do que foi informado) - NUNCA descrevendo ONDE \
encontra-lo. Isto e essencial: o cenario avalia se o AVALIADOR consegue achar \
o caminho sozinho, entao NUNCA inclua menu, secao, pagina ou breadcrumb \
("na pagina X", "no menu Y", "em X / Y / Z") - so o que o recurso e, nunca \
como chegar la.
4. "fechamento": a frase final do cenario-base, adaptada no mesmo estilo \
(convite a explorar livremente ate encontrar o que precisa) - sem citar \
nenhum recurso especifico.
5. "conectivo_final": a palavra que significa "e" no idioma do cenario-base \
(ex.: "and" se o cenario-base estiver em ingles) - vai entrar so entre o \
penultimo e o ultimo item da enumeracao.

"persona_e_contexto" e "fechamento" NUNCA podem citar um recurso especifico \
do portal: eles nao passam pela validacao automatica que confere os itens \
contra os dados coletados, entao qualquer recurso citado ali nao seria \
verificado.
"""

_PROMPT_ADAPTACAO = """\
Cenario-base original - siga o MESMO estilo, tom e idioma (persona, \
motivacao, fechamento); so os recursos genericos citados devem ser trocados \
pelos reais listados abaixo, nunca o formato:
Titulo: {titulo_cenario}
Descricao: {descricao_cenario}

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


def build_adaptacao_prompt(
    cenario_base: CenarioBase,
    diretriz: dict,
    confirmados: List[MapeamentoItem],
) -> str:
    return _PROMPT_ADAPTACAO.format(
        titulo_cenario=cenario_base.titulo,
        descricao_cenario=cenario_base.descricao,
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
    on_progress: Optional[ProgressCallback] = None,
) -> Tuple[MapeamentoResponse, Dict[str, Any]]:
    prompt = build_mapeamento_prompt(cenario_base, diretriz, descricao_gestor, dados_portal)
    return call_ai(
        SYSTEM_MAPEAMENTO, prompt, MapeamentoResponse,
        model=model, temperature=TEMPERATURA_MAPEAMENTO,
        on_progress=_tag_stage(on_progress, "mapeamento"),
    )


# ---------------------------------------------
# Chamada 2 - adaptacao
# ---------------------------------------------

def adaptar_etapas(
    cenario_base: CenarioBase,
    mapeamento: MapeamentoResponse,
    diretriz: dict,
    model: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> Tuple[AdaptacaoResponse, Dict[str, Any]]:
    confirmados = [item for item in mapeamento.itens if item.corresponde]
    if not confirmados:
        return AdaptacaoResponse(
            persona_e_contexto="", frase_objetivo="", fechamento="", conectivo_final="", itens=[],
        ), {}

    prompt = build_adaptacao_prompt(cenario_base, diretriz, confirmados)
    resposta, meta = call_ai(
        SYSTEM_ADAPTACAO, prompt, AdaptacaoResponse,
        model=model, temperature=TEMPERATURA_ADAPTACAO,
        on_progress=_tag_stage(on_progress, "adaptacao"),
    )
    resposta.itens.sort(key=lambda e: e.ordem)
    return resposta, meta


# ---------------------------------------------
# Orquestracao - monta a saida do modulo 3, ainda por etapa
# ---------------------------------------------

def montar_resultado(
    mapeamento: MapeamentoResponse,
    adaptacao: AdaptacaoResponse,
) -> dict:
    """Monta a saida do modulo 3 a partir das duas chamadas, MANTENDO os
    recursos confirmados como itens separados (nao junta `cenario_personalizado`
    num paragrafo aqui). O modulo 4 (validacao) precisa poder remover um item
    individual cujo recurso nao se confirme contra o JSON estruturado - por
    isso `persona_e_contexto`/`frase_objetivo`/`fechamento` (a moldura do
    paragrafo, que nunca cita um recurso especifico) viajam separados de
    `itens_objetivo` (a enumeracao, validada item a item). Quem junta o texto
    final e `validacao.montar_resultado_validado`, depois de remover o que nao
    passar - sem precisar costurar prosa de novo, so montar a enumeracao.
    """
    etapas_omitidas = [
        {"etapa": item.objetivo, "motivo": item.motivo}
        for item in mapeamento.itens
        if not item.corresponde
    ]
    confirmados = [item for item in mapeamento.itens if item.corresponde]
    texto_por_ordem = {i.ordem: i.texto for i in adaptacao.itens}

    itens_objetivo = [
        {
            "ordem": item.ordem,
            # Fallback ao recurso real (cru) so no caso (nao esperado) da
            # chamada 2 nao ter devolvido essa ordem - nao deveria acontecer,
            # ja que ela so recebe exatamente os itens confirmados.
            "texto": texto_por_ordem.get(item.ordem, item.recurso_real or item.texto),
            "recurso_real": item.recurso_real,
            "campo_fonte": item.campo_fonte,
        }
        for item in confirmados
    ]

    return {
        "persona_e_contexto": adaptacao.persona_e_contexto,
        "frase_objetivo": adaptacao.frase_objetivo,
        "fechamento": adaptacao.fechamento,
        "conectivo_final": adaptacao.conectivo_final,
        "itens_objetivo": itens_objetivo,
        "etapas_omitidas": etapas_omitidas,
    }


def personalizar(
    cenario_base: CenarioBase,
    diretriz: dict,
    descricao_gestor: str,
    dados_portal: dict,
    model: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> Tuple[dict, Dict[str, Any]]:
    """Roda as duas chamadas e devolve `(resultado_modulo3, meta)`.

    `resultado_modulo3` ainda tem os recursos confirmados como itens
    separados (`itens_objetivo` + a moldura do paragrafo + `etapas_omitidas`)
    - quem monta o `cenario_personalizado` final e
    `validacao.montar_resultado_validado`, depois de remover o que o modulo 4
    (validacao) nao confirmar.

    `meta` ja vem no formato que PersonalizedScenario espera (provider, model,
    tokens_total, ai_duration_s, debug) - mesma agregacao de
    `services/ai/pipeline.py` para AIAnalysis, para as duas features lerem igual
    na tela e no log. Tambem soma `model_switches` e leva `final_attempt` da
    ULTIMA chamada que efetivamente rodou (adaptacao, ou mapeamento se a
    adaptacao nem chegou a chamar a API por falta de itens confirmados) - e o
    que a tela do gestor mostra como resumo ao terminar (pedido do RNF01: dar
    visibilidade de quanto a espera custou em tentativas e trocas de modelo).
    """
    mapeamento, meta1 = mapear_recursos(cenario_base, diretriz, descricao_gestor, dados_portal, model, on_progress)
    adaptacao, meta2 = adaptar_etapas(cenario_base, mapeamento, diretriz, model, on_progress)
    resultado = montar_resultado(mapeamento, adaptacao)

    tokens = [
        (meta.get("tokens") or {}).get("total") or 0
        for meta in (meta1, meta2) if meta
    ]
    final_stage_meta = meta2 or meta1
    switches_total = sum((m.get("model_switches") or 0) for m in (meta1, meta2) if m)
    meta = {
        "provider": meta1.get("provider") or provider_name(),
        "model": final_stage_meta.get("model"),
        "tokens_total": sum(tokens) or None,
        "ai_duration_s": round(sum(m.get("elapsed_s") or 0 for m in (meta1, meta2) if m), 2),
        "model_switches": switches_total,
        "final_attempt": final_stage_meta.get("attempt"),
        "debug": {"stage1": meta1, "stage2": meta2 or None},
    }
    return resultado, meta
