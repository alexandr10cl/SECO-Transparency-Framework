"""Mapas de calor por pagina como CONTEXTO da analise de IA — nunca como peso.

A camada 2 ja deixa em cache uma imagem por pagina com o calor renderizado, mais os
hotspots numa grade 4x4. Este modulo leva isso para dentro do prompt:

    fetch_pages(evaluation_id, token)  paginas normalizadas + metadados da busca
    catalog_records(pages)             {'HM-1': registro, ...} para o catalogo
    image_parts(pages)                 [(rotulo, bytes, mime), ...] na MESMA ordem
    render_section(pages)              a secao '## MAPAS DE CALOR POR PAGINA' do prompt

O dado e a distribuicao espacial agregada de INTERACOES, nunca de atencao: a UXT declara
os campos como "Contagem de interacoes na zona" e "Posicao X/Y central em porcentagem", e
nao ha rastreamento ocular em lugar nenhum do produto. Nenhum texto produzido aqui pode
dizer atencao, olhar, viu/nao viu, percebeu ou ignorou. Por isso tambem o registro nasce
com `participant_id = None` e `task_id = None` — ver `metrics.AGGREGATE_TYPES`.

INVARIANTE: NENHUMA FUNCAO DESTE MODULO LEVANTA EXCECAO.

Toda falha vira lista vazia mais um motivo legivel (`REASON_LABEL`). `fetch_used_codes` e
`fetch_heatmap_summary` fazem `raise_for_status()`, entao sem isto um 401 ou a UXT fora do
ar deixariam em ERROR uma analise de texto que rodaria perfeitamente.
"""
from __future__ import annotations

import base64
import binascii
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import requests

from config_flags import AI_HEATMAP_MAX_PAGES, UXT_INTEGRATION
from index import app
from services.ai.urls import compact_url
from services.heatmap_cache import get_cached_payload
from services.heatmap_service import build_scenarios_payload
from services.uxt_service import is_ownership_error

# Teto de 55s contra os 150s dos defaults. O relogio de `pipeline.STALE_AFTER` (10min)
# comeca em `schedule()`, antes de a thread pegar slot: a busca do heatmap nao pode comer
# a janela de uma analise que ainda nem chamou o modelo.
USED_CODES_TIMEOUT_S = 10
SUMMARY_TIMEOUT_S = 45

# No maximo 3 zonas no summary, so as marcadas como hotspot pela UXT.
MAX_ZONES = 3

# Piso de relevancia: abaixo disto nao ha distribuicao espacial para ler numa grade de 16
# zonas, sao pontos soltos — e a pagina custaria uma imagem inteira.
#
# ABSOLUTO, nunca uma fracao do total. Um piso relativo tem por denominador a soma de
# TODAS as paginas, e por isso erra nas duas pontas: endurece sozinho conforme a avaliacao
# cobre mais paginas — no limite, com paginas parelhas demais, descarta o conjunto inteiro
# — e afrouxa justamente quando ha pouco dado, deixando passar paginas de 1 interacao.
MIN_INTERACTIONS = 5

_SUMMARY_PREFIX = "mapa de calor da pagina "


class _Unavailable(Exception):
    """Falha ja classificada na taxonomia de motivos. Nunca escapa do modulo."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# ---------------------------------------------------------------------------
# Busca
# ---------------------------------------------------------------------------

def _new_meta() -> Dict[str, Any]:
    return {
        "pages": 0,
        "source": None,
        "fetch_s": 0.0,
        "reason": None,
        "detail": None,
        "dropped": {"no_image": 0, "bad_image": 0, "below_floor": 0, "over_budget": 0},
    }


def fetch_pages(
    evaluation_id: int,
    token: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginas elegiveis + metadados da busca. NUNCA levanta.

    Devolve `([], {"reason": <codigo>, ...})` em qualquer caminho de falha; os codigos e
    seus rotulos estao em `REASON_LABEL`, no fim deste arquivo.
    """
    meta = _new_meta()
    started = time.time()
    pages: List[Dict[str, Any]] = []

    try:
        pages = _collect(evaluation_id, token, meta)
    except _Unavailable as exc:
        meta["reason"] = exc.reason
    except requests.exceptions.Timeout:
        meta["reason"] = "timeout"
    except requests.exceptions.ConnectionError:
        meta["reason"] = "unreachable"
    except requests.HTTPError as exc:
        meta["reason"] = _http_reason(exc)
        meta["detail"] = _detail(exc)
    except Exception as exc:  # noqa: BLE001 - a invariante do modulo depende disto
        meta["reason"] = "error"
        meta["detail"] = _detail(exc)
        _log(
            "ai-analysis: avaliacao %s — falha buscando mapas de calor; "
            "a analise segue texto-so.",
            evaluation_id,
        )

    meta["fetch_s"] = round(time.time() - started, 2)
    meta["pages"] = len(pages)
    if not pages and meta["reason"] is None:
        meta["reason"] = "error"
    return pages, meta


def _collect(
    evaluation_id: int,
    token: Optional[str],
    meta: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if AI_HEATMAP_MAX_PAGES <= 0:
        raise _Unavailable("disabled")
    if not UXT_INTEGRATION:
        raise _Unavailable("uxt_disabled")
    if not token:
        # CLI e sessao expirada. `get_gestor_token()` devolve None em SILENCIO dentro de
        # uma thread, por isso o token e resolvido na requisicao e passado como argumento.
        raise _Unavailable("no_token")

    payload = get_cached_payload(evaluation_id, 'scenarios')
    if payload:
        meta["source"] = "cache"
    else:
        meta["source"] = "network"
        # Nao popula o cache: a aba Hotspots tem o proprio caminho, com o seu TTL.
        payload = build_scenarios_payload(
            evaluation_id,
            token,
            used_codes_timeout=USED_CODES_TIMEOUT_S,
            summary_timeout=SUMMARY_TIMEOUT_S,
        )

    metadata = (payload or {}).get("metadata") or {}
    raw_pages = [
        p for p in ((payload or {}).get("heatmaps_by_url") or []) if isinstance(p, dict)
    ]
    if not raw_pages:
        raise _Unavailable("no_images" if metadata.get("sessions_found") else "no_sessions")

    return _apply_budget(raw_pages, metadata, meta)


def _apply_budget(
    raw_pages: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    meta: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Descarta sem imagem -> piso de relevancia -> teto, normalizando o que sobra.

    Devolve dicts NOVOS: nada aqui pode mutar o payload, que no caminho de cache e o
    objeto vivo servido a aba Hotspots. Nada cai em silencio — todo descarte e contado.
    """
    raw_pages = sorted(
        raw_pages, key=lambda p: _int(p.get("total_interactions")), reverse=True
    )
    sessions = _int(metadata.get("sessions_analyzed"))
    grid = _grid_label(metadata.get("grid_configuration"))

    # 1) Sem imagem. A UXT as vezes devolve hotspots sem captura, e descartar ANTES do
    #    orcamento e o que garante que [HM-n] e a n-esima imagem sempre correspondam.
    with_image: List[Dict[str, Any]] = []
    for raw in raw_pages:
        encoded = raw.get("image")
        if not encoded:
            meta["dropped"]["no_image"] += 1
            continue
        image = _decode(encoded)
        if image is None:
            meta["dropped"]["bad_image"] += 1
            continue
        with_image.append(_normalize(raw, image, sessions, grid))

    if not with_image:
        raise _Unavailable("no_images")

    # 2) Piso de relevancia.
    eligible = []
    for page in with_image:
        if page["interactions"] < MIN_INTERACTIONS:
            meta["dropped"]["below_floor"] += 1
            continue
        eligible.append(page)

    if not eligible:
        # Motivo PROPRIO: reusar "no_images" aqui atribuiria a UX-Tracking, que respondeu
        # com imagens, um descarte que foi nosso.
        raise _Unavailable("below_floor")

    # 3) Teto. `raw_pages` ja veio ordenado por interacoes, entao sobram as mais movimentadas.
    if len(eligible) > AI_HEATMAP_MAX_PAGES:
        meta["dropped"]["over_budget"] += len(eligible) - AI_HEATMAP_MAX_PAGES
        eligible = eligible[:AI_HEATMAP_MAX_PAGES]

    return eligible


def _normalize(
    raw: Dict[str, Any],
    image: bytes,
    sessions: int,
    grid: str,
) -> Dict[str, Any]:
    """A pagina como o resto do modulo a consome, desacoplada da resposta da UXT."""
    raw_url = raw.get("url") or ""
    return {
        "url": compact_url(raw_url) or raw_url,  # a MESMA forma das linhas [NAV-n]
        "interactions": _int(raw.get("total_interactions")),
        "sessions": sessions,
        "grid": grid,
        "scenarios": _scenarios(raw),
        "hotspots": _hotspots(raw),
        "image": image,
        "mime": raw.get("mime") or "image/jpeg",
    }


def _scenarios(raw: Dict[str, Any]) -> List[int]:
    """Cenarios cuja navegacao passou por esta pagina — CONTEXTO, nunca recorte.

    A imagem soma todas as sessoes daquela URL, independentemente de qual cenario estava
    em execucao; por isso o `task_id` do registro continua None.
    """
    ids = []
    for item in (raw.get("scenarios_involved") or []):
        if isinstance(item, dict) and item.get("task_id") is not None:
            ids.append(item["task_id"])
    return ids


def _hotspots(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """As zonas com mais interacoes, no maximo `MAX_ZONES`, so as marcadas como hotspot.

    `x`/`y` sao a POSICAO do centro da zona, nunca uma medida — quem quantifica e `count`.
    """
    spots = []
    for spot in (raw.get("top_hotspots") or []):
        if not isinstance(spot, dict) or not spot.get("is_hotspot"):
            continue
        spots.append({
            "count": _int(spot.get("interaction_count")),
            "percentage": spot.get("percentage"),
            "x": spot.get("center_x_percent"),
            "y": spot.get("center_y_percent"),
            "zone_id": spot.get("zone_id"),
        })
    spots.sort(key=lambda s: s["count"], reverse=True)
    return spots[:MAX_ZONES]


def _grid_label(grid_configuration: Any) -> str:
    """"4x4" a partir de `grid_configuration`, que a UXT entrega como string."""
    if isinstance(grid_configuration, str) and grid_configuration.strip():
        return grid_configuration.strip().lower().replace(" ", "").replace("×", "x")
    return "4x4"  # e o que `fetch_heatmap_summary` pede


def _http_reason(exc: requests.HTTPError) -> str:
    response = getattr(exc, "response", None)
    if is_ownership_error(response):
        return "ownership"
    if response is not None and response.status_code == 401:
        return "unauthorized"
    return "error"


def _decode(encoded: str) -> Optional[bytes]:
    """base64 -> bytes. `_split_data_uri` ja tirou o prefixo `data:` no heatmap_service."""
    try:
        return base64.b64decode(encoded)
    except (binascii.Error, ValueError, TypeError):
        return None


def _detail(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"[:200]


def _log(message: str, *args: Any) -> None:
    """Logar nunca pode derrubar a analise (nem sempre ha app context na CLI)."""
    try:
        app.logger.exception(message, *args)
    except Exception:  # noqa: BLE001
        pass


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Registro de evidencia
# ---------------------------------------------------------------------------

def catalog_records(
    pages: List[Dict[str, Any]],
) -> "OrderedDict[str, Dict[str, Any]]":
    """{'HM-1': registro, ...} — a MESMA ordem de `image_parts` e de `render_section`.

    `type`/`participant_id`/`task_id`/`summary` sao indexados DIRETAMENTE por
    `metrics.build_evidence_snapshot`, e `payload["url"]` por
    `metrics.attach_finding_metrics`, que o usa para montar `evidence_urls` — a linha
    "Paginas envolvidas" do prompt da etapa 2. Dizer ONDE e a maior contribuicao do mapa.

    O `payload` inteiro e persistido no snapshot (ver `build_evidence_snapshot`): e dele
    que a tela monta a linha de heatmap, sem reparsear o `summary`.
    """
    records: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for index, page in enumerate(pages or [], start=1):
        records[f"HM-{index}"] = {
            "type": "heatmap",
            "participant_id": None,  # EXPLICITO — sinal agregado, sem dono
            "task_id": None,         # EXPLICITO — uma pagina nao e um cenario
            "summary": _SUMMARY_PREFIX + _body(page),
            "payload": {
                "url": page["url"],
                "interactions": page["interactions"],
                "sessions": page["sessions"],
                "grid": page["grid"],
                "scenarios": page["scenarios"],
                "hotspots": page["hotspots"],
            },
        }
    return records


def _body(page: Dict[str, Any]) -> str:
    """O corpo do `summary`, reusado como linha [HM-n] do prompt.

        <url> · cenarios 3, 5 · 312 interacoes registradas em 5 sessoes
        · zonas com mais interacoes (grade 4x4): 106 (34%) em topo-centro

    A CONTAGEM ABSOLUTA VEM PRIMEIRO, de proposito: `interaction_count` e inequivoco,
    enquanto `percentage` a UXT documenta so como "porcentagem de interacoes", sem
    declarar o denominador — por isso ele sai entre parenteses, como entregue.
    """
    segments = [page["url"]]

    # Sem cenarios mapeados o segmento sai INTEIRO — nunca vira "cenarios " vazio.
    if page["scenarios"]:
        segments.append("cenarios " + ", ".join(str(t) for t in page["scenarios"]))

    segments.append(
        f"{page['interactions']} interacoes registradas em {page['sessions']} sessoes"
    )

    if page["hotspots"]:
        zones = " · ".join(
            f"{h['count']} ({_percent(h['percentage'])}%) em {_zone_name(h)}"
            for h in page["hotspots"]
        )
        segments.append(f"zonas com mais interacoes (grade {page['grid']}): {zones}")

    return " · ".join(segments)


def _zone_name(hotspot: Dict[str, Any]) -> str:
    """Nome da zona a partir da POSICAO do seu centro ("topo-centro"), para o prompt.

    A tela nao usa isto: ela nomeia em ingles a partir de `x`/`y` do payload, com o mesmo
    `describeZone` da aba Hotspots.
    """
    try:
        x = float(hotspot["x"])
        y = float(hotspot["y"])
    except (KeyError, TypeError, ValueError):
        return hotspot.get("zone_id") or "zona desconhecida"
    vertical = "topo" if y < 33 else ("base" if y > 66 else "meio")
    horizontal = "esquerda" if x < 33 else ("direita" if x > 66 else "centro")
    return f"{vertical}-{horizontal}"


def _percent(value: Any) -> str:
    """O percentual COMO A UXT O ENTREGA — sem arredondar nem inventar casas."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return "?"


# ---------------------------------------------------------------------------
# Imagens
# ---------------------------------------------------------------------------

def image_parts(pages: List[Dict[str, Any]]) -> List[Tuple[str, bytes, str]]:
    """[(rotulo, bytes, mime), ...] na MESMA ordem de `catalog_records`.

    O alinhamento entre [HM-n] e a imagem e resolvido por construcao: cada imagem e
    precedida do seu proprio rotulo no interleave do provider, entao o modelo nunca
    precisa contar posicoes.
    """
    return [
        (f"[HM-{index}] {page['url']}", page["image"], page["mime"])
        for index, page in enumerate(pages or [], start=1)
    ]


# ---------------------------------------------------------------------------
# Secao do prompt
# ---------------------------------------------------------------------------

_SECTION_HEADER = """\
## MAPAS DE CALOR POR PÁGINA

As linhas [HM-n] descrevem páginas visitadas durante a avaliação — uma linha por página,
cada uma seguida imediatamente da imagem correspondente. A imagem é a captura daquela
página com a DISTRIBUIÇÃO ESPACIAL DAS INTERAÇÕES desenhada sobre ela: as regiões mais
quentes são aquelas onde MAIS INTERAÇÕES FORAM REGISTRADAS.

Cada imagem traz DOIS dados, e os dois são úteis:

1. O CONTEÚDO DA PÁGINA. O texto, os rótulos, os links e o arranjo visíveis na captura são
   o conteúdo que aquela página apresentava durante a coleta. Esta seção é o único lugar
   deste contexto onde esse conteúdo aparece: todo o resto são URLs, marcações de tempo e
   o que os participantes escreveram. Leia-o.

2. A DISTRIBUIÇÃO DAS INTERAÇÕES, resumida na linha [HM-n] e desenhada sobre a captura.

Leia com estas ressalvas, que fazem parte do dado:

- SÓ O QUE ESTIVER LEGÍVEL. A captura tem resolução finita e o calor é desenhado POR CIMA
  da página, então parte do conteúdo pode estar coberta ou ilegível. Relate apenas o que
  você conseguir efetivamente ler na imagem; não complete nem deduza o que não deu para
  ler, e não descreva uma página cujo conteúdo você não conseguiu distinguir.

- É AGREGADO. Cada imagem soma as interações de TODAS as sessões que passaram por aquela
  página. Não é a tela de uma pessoa. Nenhum [HM-n] tem participante dono, e por isso
  mapas de calor não contam na abrangência nem na confiança de um finding.

- A GRADE É 4x4. As zonas ("topo-centro", "meio-esquerda") são os 16 blocos dessa grade, e
  o nome de cada zona diz apenas ONDE ela fica na página. O primeiro número é a CONTAGEM de
  interações registradas naquele bloco; o valor entre parênteses é o percentual como a
  ferramenta de captura o fornece.

- OS CENÁRIOS SÃO CONTEXTO, NÃO RECORTE. Os cenários listados em cada [HM-n] são aqueles
  cuja navegação passou por aquela página. A distribuição NÃO está separada por cenário — a
  imagem mistura todas as sessões. Use os cenários para saber em que contexto a página foi
  visitada; nunca afirme que uma zona pertence a um cenário específico.

- INTERAÇÃO NÃO É PROBLEMA. Uma concentração de interações diz onde elas ocorreram — pode
  ser exatamente o elemento certo sendo usado como se esperava. Muita interação numa região
  não é, por si só, sinal de dificuldade, e pouca interação não é sinal de facilidade.

- USE ESTA SEÇÃO PARA CONTEXTUALIZAR. Quando um finding envolve uma destas páginas, o
  [HM-n] é o único sinal que mostra a página em si e diz ONDE nela as interações se
  concentraram: a trilha [NAV-n] diz que o participante esteve ali, o mapa mostra o que
  havia na tela e em que região ele agiu. Cite-o e acrescente UMA FRASE dizendo o que você
  tirou dele — do conteúdo, da distribuição, ou dos dois. O único uso a evitar é citar sem
  dizer nada, só porque a URL coincide.

"""


def render_section(pages: Optional[List[Dict[str, Any]]]) -> str:
    """A secao '## MAPAS DE CALOR POR PAGINA'. String vazia quando nao ha paginas."""
    if not pages:
        return ""

    lines = [_SECTION_HEADER]
    for index, page in enumerate(pages, start=1):
        lines.append(f"[HM-{index}] {_body(page)}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Observabilidade
# ---------------------------------------------------------------------------

REASON_LABEL = {
    "disabled": "desligado por AI_HEATMAP_MAX_PAGES=0",
    "uxt_disabled": "integracao UX-Tracking desligada",
    "no_token": "token do gestor ausente",
    "ownership": "codigo gerado por outra conta UX-Tracking",
    "unauthorized": "UX-Tracking recusou o token (401)",
    "timeout": "UX-Tracking nao respondeu a tempo",
    "unreachable": "UX-Tracking fora do ar",
    "no_sessions": "nenhuma sessao coletada sob o codigo",
    "no_images": "a UX-Tracking respondeu sem imagem utilizavel",
    "below_floor": f"nenhuma pagina alcancou o piso de {MIN_INTERACTIONS} interacoes",
    "error": "falha inesperada na busca",
}


def describe_reason(reason: Optional[str]) -> str:
    if not reason:
        return ""
    return REASON_LABEL.get(reason, reason)
