"""
Modulo 4 - Validacao automatica (deterministica, SEM IA)

Responsabilidade: conferir, etapa a etapa, se as justificativas que a
personalizacao (modulo 3) produziu realmente se sustentam no JSON estruturado
(saida do modulo 2, fonte da verdade). Nenhuma chamada de IA aqui - e essa a
garantia que mantem a etapa inteira deterministica: nenhum modelo valida a
saida de outro modelo (CLAUDE.md, decisao travada).

Duas checagens, nesta ordem, por etapa:
  1. Estrutural: o `campo_fonte` apontado pela chamada 1 existe de fato no
     JSON estruturado?
  2. De conteudo: o valor desse campo sustenta o `recurso_real` citado? Por
     correspondencia textual aproximada - normalizacao (sem acento, minusculo)
     e intersecao de tokens - nunca por chamada a IA.

Um item que falhar em QUALQUER uma das duas e removido por inteiro da
enumeracao do cenario personalizado. Isso so e seguro sem outra chamada de IA
porque a chamada 2 (personalizacao.py) NUNCA costura os recursos confirmados
numa frase so - devolve `persona_e_contexto`/`frase_objetivo`/`fechamento`
(a moldura do paragrafo, generica, sem citar nenhum recurso) separados de
`itens_objetivo` (um por recurso). Remover um item da enumeracao e so tirar
da lista antes de `_montar_paragrafo` juntar tudo - nunca corta uma frase pela
metade, nunca quebra a gramatica do resto. O motivo da remocao e sempre
registrado (RF17) para entrar no log de origem.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Tuple

# Fracao dos tokens do recurso citado que precisa aparecer no campo fonte para
# a citacao ser considerada sustentada. Abaixo de 1.0 de proposito: a chamada 2
# reescreve o recurso com liberdade ("reescrita ampla" - CLAUDE.md), entao
# exigir 100% dos tokens rejeitaria citacoes legitimas so por causa da
# parafrase.
_LIMIAR_CONFIANCA = 0.6

# Tokens mais curtos que isso nao entram na comparacao (artigos, preposicoes,
# sigla de 2 letras) - normalmente aparecem em qualquer texto e nao carregam
# informacao sobre a citacao ser real ou nao.
_TAMANHO_MIN_TOKEN = 3

_SEGMENTO_CAMINHO_RE = re.compile(r"([^\[\].]+)|\[(\d+)\]")


def _slug(texto: str) -> str:
    """Sem acento, minusculo, espacos colapsados - mesma normalizacao de
    estruturacao.py, para os dois modulos concordarem sobre o que e 'o mesmo
    texto'."""
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def _tokens(texto: str) -> set[str]:
    return {t for t in re.findall(r"\w+", _slug(texto)) if len(t) >= _TAMANHO_MIN_TOKEN}


def resolver_campo(dados_portal: dict, caminho: str) -> Any:
    """Resolve um caminho tipo 'paginas_coletadas[2].texto' ou
    'estrutura_navegacao.itens_menu[0]' dentro do JSON estruturado.

    Devolve None se qualquer segmento do caminho nao existir - nunca lanca
    excecao, porque um campo_fonte invalido e um resultado ESPERADO da checagem
    (a chamada 1 tambem pode alucinar o caminho), nao um erro de programacao.
    """
    if not caminho:
        return None

    atual: Any = dados_portal
    for chave, indice in _SEGMENTO_CAMINHO_RE.findall(caminho):
        try:
            if chave:
                atual = atual[chave]
            else:
                atual = atual[int(indice)]
        except (KeyError, IndexError, TypeError, ValueError):
            return None
    return atual


def _confianca(recurso_real: str, valor_campo: Any) -> float:
    """Fracao dos tokens de `recurso_real` que aparecem no campo citado.

    Deliberadamente a recall do recurso dentro do campo, nao Jaccard: o campo
    (ex.: o texto inteiro de uma pagina) tem vocabulario muito maior que a
    citacao, entao Jaccard penalizaria qualquer campo grande mesmo quando ele
    sustenta a citacao por completo.
    """
    tokens_recurso = _tokens(recurso_real)
    if not tokens_recurso:
        return 0.0

    if isinstance(valor_campo, str):
        candidatos = [valor_campo]
    elif isinstance(valor_campo, list):
        candidatos = [c for c in valor_campo if isinstance(c, str)]
    else:
        # Numero, dict, None, etc.: nao ha texto para comparar.
        return 0.0

    melhor = 0.0
    for candidato in candidatos:
        tokens_campo = _tokens(candidato)
        if not tokens_campo:
            continue
        score = len(tokens_recurso & tokens_campo) / len(tokens_recurso)
        melhor = max(melhor, score)
    return melhor


def validar_etapa(etapa: Dict[str, Any], dados_portal: dict) -> Tuple[bool, str]:
    """Confere uma etapa personalizada (ordem, texto, recurso_real,
    campo_fonte) contra o JSON estruturado.

    Devolve `(confirmada, motivo)` - `motivo` so vem preenchido quando
    `confirmada` e False.
    """
    campo_fonte = etapa.get("campo_fonte")
    recurso_real = etapa.get("recurso_real") or ""

    if not campo_fonte:
        return False, "sem campo_fonte informado pela personalizacao"

    valor_campo = resolver_campo(dados_portal, campo_fonte)
    if valor_campo is None:
        return False, f"campo_fonte '{campo_fonte}' nao existe no JSON estruturado coletado"

    confianca = _confianca(recurso_real, valor_campo)
    if confianca < _LIMIAR_CONFIANCA:
        return False, (
            f"conteudo de '{campo_fonte}' nao sustenta o recurso citado "
            f"(confianca {confianca:.0%}, minimo exigido {_LIMIAR_CONFIANCA:.0%})"
        )
    return True, ""


def validar(
    itens_objetivo: List[Dict[str, Any]],
    dados_portal: dict,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Aplica `validar_etapa` a cada item confirmado (um por recurso).

    Devolve `(itens_validados, recursos_removidos)` - a segunda lista ja no
    formato que `PersonalizedScenario.recursos_removidos_validacao` guarda.
    """
    validados: List[Dict[str, Any]] = []
    removidos: List[Dict[str, Any]] = []

    for item in itens_objetivo:
        confirmada, motivo = validar_etapa(item, dados_portal)
        if confirmada:
            validados.append(item)
        else:
            removidos.append({
                "recurso": item.get("recurso_real"),
                "fonte": item.get("campo_fonte"),
                "motivo": motivo,
            })
    return validados, removidos


def _com_ponto_final(frase: str) -> str:
    """Garante pontuacao final sem chamada de IA - a moldura do paragrafo
    (persona/fechamento) e escrita pela IA como frase completa, mas nao ha
    garantia estrutural disso (nao e um contrato do schema), entao normaliza
    aqui em vez de arriscar duas frases coladas sem separador."""
    frase = (frase or "").strip()
    if not frase:
        return frase
    return frase if frase[-1] in ".!?" else frase + "."


def _montar_paragrafo(
    persona_e_contexto: str,
    frase_objetivo: str,
    itens_texto: List[str],
    fechamento: str,
    conectivo_final: str = "e",
) -> str:
    """Junta a moldura do paragrafo (escrita pela IA, nunca validada porque
    nunca cita um recurso especifico) com os itens confirmados (validados
    item a item) numa unica enumeracao - sem chamada de IA. E essa
    enumeracao, montada aqui e nao pela IA, que permite remover um recurso
    reprovado na validacao sem quebrar a gramatica do resto do paragrafo.

    `conectivo_final` vem da propria chamada de IA (a palavra "e"/"and"/"y" no
    idioma do cenario-base) - o cenario-base pode estar em qualquer idioma, e
    um conectivo fixo em portugues quebraria a fluencia de um cenario em
    ingles (ou em qualquer outro idioma).
    """
    partes = []
    abertura = _com_ponto_final(persona_e_contexto)
    if abertura:
        partes.append(abertura)

    itens_limpos = [t.strip().rstrip(".") for t in itens_texto if t and t.strip()]
    if itens_limpos:
        conectivo = (conectivo_final or "e").strip() or "e"
        lista = itens_limpos[0] if len(itens_limpos) == 1 else (
            ", ".join(itens_limpos[:-1]) + f" {conectivo} " + itens_limpos[-1]
        )
        objetivo = frase_objetivo.strip()
        frase = f"{objetivo} {lista}." if objetivo else f"{lista[0].upper()}{lista[1:]}."
        partes.append(frase)

    fechamento_final = _com_ponto_final(fechamento)
    if fechamento_final:
        partes.append(fechamento_final)

    return " ".join(partes)


def montar_resultado_validado(resultado_modulo3: dict, dados_portal: dict) -> dict:
    """Ponto de entrada do modulo 4 para quem orquestra o pipeline
    (services/scenario_personalization/pipeline.py, Fase 3).

    Recebe o resultado ainda por item de `personalizacao.personalizar()` e
    devolve o JSON final da etapa 4 do metodo (CLAUDE.md): `cenario_personalizado`
    ja e o paragrafo definitivo (persona + objetivo + fechamento, no formato do
    cenario-base), com os recursos nao confirmados removidos da enumeracao, e
    `recursos_confirmados`/`justificativas` refletem so o que sobreviveu.
    `etapas_omitidas` (chamada 1 - sem correspondencia nenhuma) e
    `recursos_removidos_validacao` (aqui - correspondencia alegada mas nao
    confirmada) ficam separados de proposito: sao motivos diferentes, e o log
    de origem (etapa 7) precisa distingui-los.
    """
    itens_validados, recursos_removidos = validar(
        resultado_modulo3["itens_objetivo"], dados_portal
    )
    itens_validados.sort(key=lambda e: e["ordem"])

    return {
        "cenario_personalizado": _montar_paragrafo(
            resultado_modulo3.get("persona_e_contexto", ""),
            resultado_modulo3.get("frase_objetivo", ""),
            [e["texto"] for e in itens_validados],
            resultado_modulo3.get("fechamento", ""),
            resultado_modulo3.get("conectivo_final", "e"),
        ),
        "etapas_omitidas": resultado_modulo3["etapas_omitidas"],
        "recursos_confirmados": [e["recurso_real"] for e in itens_validados],
        "justificativas": [
            {"recurso": e["recurso_real"], "fonte": e["campo_fonte"]}
            for e in itens_validados
        ],
        "recursos_removidos_validacao": recursos_removidos,
    }
