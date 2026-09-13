"""
Modulo 1 - Coleta de dados reais do portal

Responsabilidade: acessar o portal e extrair dados brutos.
NAO interpreta, NAO classifica, NAO filtra por relevancia - isso e responsabilidade
do modulo de estruturacao.

Usa navegador headless (Playwright/Chromium) porque portais de ecossistemas de
software frequentemente sao SPAs: um scraper de HTML estatico perderia o conteudo
renderizado por JavaScript.

Roda dentro de uma thread do executor (ver services/scenario_personalization/pipeline.py,
no molde de services/ai/pipeline.py) - por isso usa a API sincrona do Playwright, nao a
async: nao ha event loop do Flask para compartilhar.
"""

from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urldefrag

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------
# Configuracao
# ---------------------------------------------

@dataclass
class ConfigColeta:
    # Profundidade de rastreamento: 0 = so a home, 1 = home + links da home, etc.
    # Deixado como parametro por ser variavel experimental do trabalho.
    profundidade: int = 1

    # Teto de paginas visitadas - protege contra portais muito grandes.
    max_paginas: int = 25

    # Tempo maximo de espera por pagina (ms).
    timeout_ms: int = 20_000

    # Espera adicional apos o load, para SPAs que renderizam em duas etapas.
    espera_render_ms: int = 1_500

    # Pausa entre requisicoes, por educacao com o servidor avaliado.
    pausa_entre_paginas_s: float = 0.7

    # Respeitar robots.txt. Manter True: o SECO-TransP avalia transparencia,
    # seria contraditorio coletar dados ignorando a politica do portal.
    respeitar_robots: bool = True

    user_agent: str = (
        "SECO-TransP/1.0 (avaliacao academica de transparencia;"
        "contato: contato@seco-transp.org)"
    )

    # Palavras que sinalizam paginas relevantes para avaliacao de transparencia.
    # Usadas apenas para PRIORIZAR o que visitar dentro do orcamento de paginas,
    # nao para classificar o conteudo coletado.
    termos_paginas_chave: tuple[str, ...] = (
        "sobre", "about", "quem-somos", "institucional", "faq", "ajuda", "help", "suporte", "support", "doc", "documenta", "api", "guia", "guide", "termos", "terms", "privacidade", "privacy", "politica", "policy",
        "contato", "contact", "fale-conosco", "licenca", "license", "governanca", "governance", "dados", "transparencia", "transparency"
    )

@dataclass
class PaginaBruta:
    url: str
    titulo: str = ""
    texto: str = ""
    links: list[dict] = field(default_factory=list)  # {"texto":..., "href":...}
    profundidade: int = 0
    erro: str | None = None

@dataclass
class ColetaBruta:
    url_inicial: str
    dominio: str
    timestamp: str
    paginas: list[PaginaBruta] = field(default_factory=list)
    itens_menu: list[dict] = field(default_factory=list)
    metadados: dict = field(default_factory=dict)
    sitemap_encontrado: bool = False
    modo: str = "completo"  # "completo" | "degradado"
    motivos_degradacao: list[str] = field(default_factory=list)


# ---------------------------------------------
# Helpers
# ---------------------------------------------

def _mesmo_dominio(url: str, dominio: str) -> bool:
    """Verifica se a URL pertence ao mesmo dominio do portal avaliado."""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    host = host[4:] if host.startswith("www.") else host
    return host == dominio

def _normalizar(url: str) -> str:
    """Remove fragmento (#secao) e barra final, para nao visitar duplicatas."""
    url, _ = urldefrag(url)
    if url.endswith("/") and len(urlparse(url).path) > 1:
        url = url[:-1]
    return url

def _prioridade(url: str, texto: str, cfg: ConfigColeta) -> int:
    """Menor valor = visitar antes. Prioriza paginas-chave de transparencia."""
    alvo = f"{url} {texto}".lower()
    return 0 if any(t in alvo for t in cfg.termos_paginas_chave) else 1

# Sinais de que a coleta nao conseguiu ver o portal de verdade.
_SINAIS_BLOQUEIO = (
    "captcha", "recaptcha", "verifique que você não é um robô", "verify you are not a robot", "acesso negado", "access denied", "403 forbidden", "faça login para continuar", "please log in to continue", "login required", "erro 404", "error 404", "página não encontrada", "page not found",
)

def _parece_bloqueado(titulo: str, texto: str) -> str | None:
    """Detecta sinais de que o portal bloqueou a coleta, para reportar no log."""
    alvo = f"{titulo} {texto[:1500]}".lower()
    for sinal in _SINAIS_BLOQUEIO:
        if sinal in alvo:
            return sinal
    return None


# ---------------------------------------------
# Extracao dentro da pagina
# ---------------------------------------------

_JS_EXTRAI = """
() => {
    const limpar = (s) => (s || "").replace(/\\s+/g, " ").trim();

    // Links de navegacao: preferimos os que estao em nav/header.
    const navSel = 'nav a[href], header a[href], [role="navigation"] a[href]';
    const menu = Array.from(document.querySelectorAll(navSel))
        .map(a => ({texto: limpar(a.innerText), href: a.href}))
        .filter(x => x.texto && x.href);

    // Todos os links da pagina.
    const links = Array.from(document.querySelectorAll('a[href]'))
        .map(a => ({texto: limpar(a.innerText), href: a.href}))
        .filter(x => x.href);

    // Texto principal: tenta main/article antes de cair no body.
    const alvo = document.querySelector('main, article, [role="main"]') || document.body;
    const texto = limpar(alvo ? alvo.innerText : "");

    const metaDesc = document.querySelector('meta[name="description"]');
    const metaOg = document.querySelector('meta[property="og:description"]');

    return {
        titulo: limpar(document.title),
        texto,
        menu,
        links,
        meta_description: limpar(metaDesc ? metaDesc.content : (metaOg ? metaOg.content : "")),
        lang: document.documentElement.lang || "",
    };
}
"""

def _visitar(page, url: str, cfg: ConfigColeta) -> tuple[PaginaBruta, dict]:
    """Abre uma URL e devolve (PaginaBruta, dados_extras)."""
    bruta = PaginaBruta(url=url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=cfg.timeout_ms)
        # SPAs costumam renderizar depois do domcontentloaded.
        try:
            page.wait_for_load_state("networkidle", timeout=cfg.timeout_ms)
        except PWTimeout:
            pass  # networkidle nem sempre chega em paginas com polling
        page.wait_for_timeout(cfg.espera_render_ms)

        dados = page.evaluate(_JS_EXTRAI)
        bruta.titulo = dados["titulo"]
        bruta.texto = dados["texto"]
        bruta.links = dados["links"]
        return bruta, dados

    except PWTimeout:
        bruta.erro = "timeout"
    except Exception as exc:  # noqa: BLE001
        bruta.erro = f"{type(exc).__name__}: {exc}"
    return bruta, {}

# ---------------------------------------------
# Coleta
# ---------------------------------------------

def coletar(url_inicial: str, cfg: ConfigColeta | None = None) -> ColetaBruta:
    cfg = cfg or ConfigColeta()
    url_inicial = _normalizar(url_inicial)
    dominio = urlparse(url_inicial).netloc.lower()
    dominio = dominio[4:] if dominio.startswith("www.") else dominio

    coleta = ColetaBruta(
        url_inicial=url_inicial,
        dominio=dominio,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    # robots.txt
    robots = None
    if cfg.respeitar_robots:
        robots = urllib.robotparser.RobotFileParser()
        robots.set_url(urljoin(url_inicial, "/robots.txt"))
        try:
            robots.read()
        except Exception:  # noqa: BLE001
            robots = None  # sem robots.txt legivel, segue

    def permitido(u: str) -> bool:
        return robots.can_fetch(cfg.user_agent, u) if robots else True

    fila: list[tuple[str, int, int]] = [(url_inicial, 0, 0)]  # (url, prof, prio)
    vistas: set[str] = set()

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        contexto = navegador.new_context(
            user_agent=cfg.user_agent,
            viewport={"width": 1366, "height": 900},
            locale="pt-BR",
        )
        page = contexto.new_page()

        # sitemap.xml - atalho para descobrir estrutura sem navegar
        try:
            resp = contexto.request.get(
                urljoin(url_inicial, "/sitemap.xml"), timeout=cfg.timeout_ms
            )
            coleta.sitemap_encontrado = resp.ok
        except Exception:
            coleta.sitemap_encontrado = False

        primeira = True
        while fila and len(coleta.paginas) < cfg.max_paginas:
            fila.sort(key=lambda item: (item[1], item[2]))  # profundidade, prioridade
            url, prof, _ = fila.pop(0)

            url = _normalizar(url)
            if url in vistas or not permitido(url):
                continue
            vistas.add(url)

            bruta, dados = _visitar(page, url, cfg)
            bruta.profundidade = prof
            coleta.paginas.append(bruta)

            if bruta.erro:
                if primeira:
                    coleta.motivos_degradacao.append(
                        f"falha ao carregar a pagina inicial ({bruta.erro})"
                    )
                primeira = False
                continue

            bloqueio = _parece_bloqueado(bruta.titulo, bruta.texto)
            if bloqueio:
                coleta.motivos_degradacao.append(
                    f"possivel bloqueio de acesso em {url} (sinal: '{bloqueio}')"
                )

            if primeira:
                coleta.itens_menu = dados.get("menu", [])
                coleta.metadados = {
                    "titulo_site": bruta.titulo,
                    "meta_description": dados.get("meta_description", ""),
                    "lang": dados.get("lang", "")
                }
                primeira = False

            if prof < cfg.profundidade:
                for link in bruta.links:
                    href = _normalizar(link["href"])
                    if not href.startswith(("http://", "https://")):
                        continue
                    if not _mesmo_dominio(href, dominio) or href in vistas:
                        continue
                    fila.append((href, prof + 1, _prioridade(href, link["texto"], cfg)))

            time.sleep(cfg.pausa_entre_paginas_s)

        contexto.close()
        navegador.close()

    _avaliar_modo(coleta)
    return coleta

def _avaliar_modo(coleta: ColetaBruta) -> None:
    """Decide se a coleta foi completa ou degradada (RF06/RF07)."""
    uteis = [p for p in coleta.paginas if not p.erro and len(p.texto) > 200]

    if not coleta.paginas or coleta.paginas[0].erro:
        coleta.motivos_degradacao.append("pagina inicial inacessivel")
    if not uteis:
        coleta.motivos_degradacao.append("nenhuma pagina coletada com conteudo suficiente")
    if not coleta.itens_menu:
        coleta.motivos_degradacao.append("nenhum item de navegacao identificado")

    coleta.modo = "degradado" if coleta.motivos_degradacao else "completo"
