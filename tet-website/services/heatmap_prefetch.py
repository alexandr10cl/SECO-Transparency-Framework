from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, Optional

from flask import current_app

from index import app
from models import Evaluation
from services.heatmap_cache import get_cached_payload, set_cached_payload
from services.heatmap_service import build_scenarios_payload

_prefetch_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='heatmap-prefetch')


def schedule_heatmap_prefetch(
    evaluation_ids: Iterable[int],
    token: Optional[str],
    cache_type: str = 'scenarios',
    priority: bool = False,
) -> None:
    """
    Schedule async prefetch of heatmap payloads for provided evaluations.
    
    Args:
        evaluation_ids: List of evaluation IDs to prefetch
        token: UXT access token
        cache_type: Type of cache ('scenarios' or 'tasks')
        priority: If True, submit all at once for parallel execution (faster)
    """
    if not token:
        # Without a valid UX Tracking token we cannot prefetch.
        current_app.logger.debug("Skipping heatmap prefetch: missing UX Tracking token")
        return

    unique_ids = list(dict.fromkeys(evaluation_ids))
    if not unique_ids:
        return

    # Submit ALL evaluations simultaneously for parallel loading
    # With max_workers=10, up to 10 heatmaps load at the same time
    for evaluation_id in unique_ids:
        _prefetch_executor.submit(_prefetch_heatmap, evaluation_id, token, cache_type)
    
    if priority:
        app.logger.info("Priority prefetch scheduled for %d evaluation(s): %s", len(unique_ids), unique_ids)
    else:
        app.logger.debug("Prefetch scheduled for %d evaluation(s): %s", len(unique_ids), unique_ids)


def _prefetch_heatmap(evaluation_id: int, token: str, cache_type: str) -> None:
    with app.app_context():
        if get_cached_payload(evaluation_id, cache_type):
            return
        try:
            payload = build_scenarios_payload(evaluation_id, token)
            set_cached_payload(evaluation_id, cache_type, payload)
            app.logger.info("Prefetched heatmap cache for evaluation %s", evaluation_id)
        except Exception as exc:
            app.logger.warning(
                "Failed to prefetch heatmap for evaluation %s: %s", evaluation_id, exc
            )

