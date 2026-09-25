"""
Modulo 2 - Estruturacao (deterministica, SEM IA)

Responsabilidade: organizar os dados brutos da coleta em um JSON de
schema fixo. Nao interpreta o conteudo, nao classifica paginas, nao
decide o que e "relevante" - apenas normaliza e organiza.

Essa etapa e deliberadamente deterministica: e ela que produz a "fonte da
verdade" contra a qual o modulo de validacao vai conferir, mais adiante, se a
IA citou recursos que existem de fato.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

from .coleta import ColetaBruta


# Itens de navegacao que nao indicam um recurso do portal.
# Lista de exclusao puramente lexica - nao e interpretacao de conteudo.
_RUIDO = {
    "home", "início", "inicio", "página inicial", "pagina inicial",
    "login", "entrar", "sair", "logout", "cadastrar", "cadastre-se",
    "registrar", "criar conta", "minha conta",
    "voltar", "próximo", "proximo", "anterior", "menu", "buscar", "pesquisar",
    "leia mais", "saiba mais", "ver mais", "clique aqui", "veja mais",
    "pt", "en", "es", "português", "portugues", "english", "español", "espanol",
    "twitter", "facebook", "instagram", "linkedin", "youtube", "github",
}

_LIMITE_TEXTO = 3_000  # corta textos muito longos por pagina
_MIN_TEXTO_PAGINA = 120  # abaixo disso, a pagina nao entra como coletada

# Teto de recursos_mencionados: sem isso a lista cresce com o numero de
# paginas (cada uma pode contribuir links novos), e vira a parte que mais
# infla o prompt da chamada 1 (personalizacao.py) sem trazer informacao nova
# depois de cobrir a navegacao principal do portal.
_MAX_RECURSOS_MENCIONADOS = 150


def _slug(texto: str) -> str:
    """Normaliza para comparacao: sem acento, minusculo, sem espaco extra."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s", " ", t).strip().lower()

def _e_ruido(texto: str) -> bool:
    s = _slug(texto)
    if len(s) < 3 or len(s) > 60:
        return True
    if s in {_slug(r) for r in _RUIDO}:
        return True
    if s.isdigit():
        return True
    return False

def estruturar(coleta: ColetaBruta) -> dict:
    """Converte a coleta bruta no JSON de schema fixo do metodo."""

    # --- 1. estrutura de navegacao ---------------------------------
    itens_menu: list[str] = []
    vistos_menu: set[str] = set()
    for item in coleta.itens_menu:
        texto = re.sub(r"\s", " ", item.get("texto", "")).strip()
        if not texto or _e_ruido(texto):
            continue
        chave = _slug(texto)
        if chave in vistos_menu:
            continue
        vistos_menu.add(chave)
        itens_menu.append(texto)

    # --- 2. paginas coletadas ---------------------------------------
    paginas: list[dict] = []
    for p in coleta.paginas:
        if p.erro or len(p.texto) < _MIN_TEXTO_PAGINA:
            continue

        internos: list[str] = []
        vistos_links: set[str] = set()
        for link in p.links:
            href = link.get("href", "")
            if not href.startswith(("http://", "https://")):
                continue
            host = urlparse(href).netloc.lower()
            host = host[4:] if host.startswith("www.") else host
            if host != coleta.dominio or href in vistos_links:
                continue
            vistos_links.add(href)
            internos.append(href)

        paginas.append({
            "url": p.url,
            "titulo": p.titulo,
            "texto": p.texto[:_LIMITE_TEXTO],
            "links_internos": internos,
        })

    # --- 3. recursos mencionados (lista crua, sem interpretacao) -------
    recursos: list[str] = []
    vistos_rec: set[str] = set(vistos_menu)
    recursos.extend(itens_menu)

    for pagina in coleta.paginas:
        if pagina.erro:
            continue
        for link in pagina.links:
            texto = re.sub(r"\s+", " ", link.get("texto", "")).strip()
            if not texto or _e_ruido(texto):
                continue
            chave = _slug(texto)
            if chave in vistos_rec:
                continue
            vistos_rec.add(chave)
            recursos.append(texto)

    # --- 4. schema final ----------------------------------------
    return {
        "portal": {
            "url": coleta.url_inicial,
            "dominio": coleta.dominio,
        },
        "estrutura_navegacao": {
            "itens_menu": itens_menu,
        },
        "paginas_coletadas": paginas,
        "metadados": {
            "titulo_site": coleta.metadados.get("titulo_site", ""),
            "meta_description": coleta.metadados.get("meta_description", ""),
            "lang": coleta.metadados.get("lang", ""),
            "sitemap_encontrado": coleta.sitemap_encontrado,
        },
        "recursos_mencionados": recursos[:_MAX_RECURSOS_MENCIONADOS],
        "modo_coleta": coleta.modo,
        "motivos_degradacao": coleta.motivos_degradacao,
        "timestamp_coleta": coleta.timestamp,
    }
