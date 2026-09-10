"""Compactacao de URL para o contexto da IA.

Modulo proprio, sem dependencia de `index` nem de `models`, para `context_builder` e
`heatmap_evidence` poderem importar os dois no topo: eles se importam mutuamente e esta
funcao era o unico motivo do ciclo.

O espelho em JavaScript e `secoCompactUrl` (static/js/hotspots_heatmaps.js), usado para
casar a pagina do mapa de calor com a linha [NAV-n] correspondente.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

_TRACKING_KEYS = {"_gl", "gclid", "fbclid", "msclkid", "gs_lcrp", "oq"}
_TRACKING_PREFIXES = ("_ga", "_gcl", "utm_")


def _is_tracking(key: str) -> bool:
    """`gs_lcrp` e `oq` entram aqui: sao ruido do buscador, nao a busca (`q` fica)."""
    return key in _TRACKING_KEYS or key.startswith(_TRACKING_PREFIXES)


def compact_url(url: str) -> str:
    """URL sem o `https://` e sem os parametros de rastreamento.

    O filtro e por lista de chaves, nunca pela presenca de `?`: os parametros de busca
    (`?q=`, `?query=`, `&text=`) guardam, nas palavras do proprio participante, aquilo que
    ele nao conseguiu encontrar navegando — a evidencia mais direta de uma lacuna de
    descoberta que existe no conjunto.
    """
    parts = urlsplit(url or "")
    if parts.scheme not in ("http", "https") or not parts.netloc:
        # chrome://newtab, about:blank e afins ficam inteiros: sem o scheme viram
        # "newtab", que nao diz ao modelo que aquilo e uma pagina do navegador e nao
        # do portal.
        return (url or "").strip()

    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(key)
    ]
    query = "?" + "&".join(f"{k}={v}" for k, v in kept) if kept else ""
    fragment = f"#{parts.fragment}" if parts.fragment else ""
    return f"{parts.netloc}{parts.path.rstrip('/')}{query}{fragment}"
