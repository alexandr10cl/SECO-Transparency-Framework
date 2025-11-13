from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz
import requests

from index import app
from models import Evaluation, PerformedTask


def normalize_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Normalize various timestamp formats to UTC-aware datetime."""
    if not timestamp_str:
        return None

    try:
        timestamp_str = str(timestamp_str).strip()

        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.astimezone(pytz.UTC)
        if '+' in timestamp_str[-6:] or timestamp_str[-6:-3] == '-':
            dt = datetime.fromisoformat(timestamp_str)
            return dt.astimezone(pytz.UTC)

        dt = datetime.fromisoformat(timestamp_str)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(pytz.UTC)
    except (ValueError, AttributeError, TypeError):
        app.logger.warning("Failed to normalize timestamp %s", timestamp_str)
        return None


def build_task_interval_map(performed_tasks: List[PerformedTask]) -> Dict[str, Dict[str, Any]]:
    task_map: Dict[str, Dict[str, Any]] = {}

    for pt in performed_tasks:
        try:
            initial_ts = normalize_timestamp(str(pt.initial_timestamp))
            final_ts = normalize_timestamp(str(pt.final_timestamp))
            if not initial_ts or not final_ts:
                continue

            task_map[pt.task_id] = {
                'initial_timestamp': initial_ts,
                'final_timestamp': final_ts,
                'title': pt.task.title,
                'description': getattr(pt.task, 'description', ''),
                'duration_minutes': (final_ts - initial_ts).total_seconds() / 60,
            }
        except Exception as exc:
            app.logger.warning("Failed to build interval for task %s: %s", pt.task_id, exc)

    return task_map


def build_navigation_task_map(
    performed_tasks: List[PerformedTask],
    navigation_data: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    task_intervals = build_task_interval_map(performed_tasks)
    task_url_map: Dict[str, Dict[str, Any]] = {}

    for task_id, task_data in task_intervals.items():
        task_url_map[task_id] = {
            'title': task_data['title'],
            'description': task_data['description'],
            'duration_minutes': task_data['duration_minutes'],
            'navigation_count': 0,
            'url_diversity': set(),
            'urls': set(),
            'initial_timestamp': task_data['initial_timestamp'],
            'final_timestamp': task_data['final_timestamp'],
            'url_details_map': {},
        }

    for nav in navigation_data:
        nav_timestamp = normalize_timestamp(nav.get('timestamp'))
        nav_task_id = nav.get('task_id')
        if not nav_timestamp or nav_task_id not in task_url_map:
            continue

        task_data = task_url_map[nav_task_id]
        url = nav.get('url') or 'unknown'
        task_data['urls'].add(url)
        task_data['navigation_count'] += 1
        task_data['url_diversity'].add(url)

        url_stats = task_data['url_details_map'].setdefault(url, {
            'first_seen': nav_timestamp,
            'last_seen': nav_timestamp,
            'count': 0,
        })
        url_stats['count'] += 1
        if nav_timestamp < url_stats['first_seen']:
            url_stats['first_seen'] = nav_timestamp
        if nav_timestamp > url_stats['last_seen']:
            url_stats['last_seen'] = nav_timestamp

    for task_id, task_data in task_url_map.items():
        url_details_list = []
        for url, stats in sorted(
            task_data['url_details_map'].items(),
            key=lambda item: item[1]['first_seen'],
        ):
            url_details_list.append({
                'url': url,
                'first_seen': stats['first_seen'].isoformat() if stats['first_seen'] else None,
                'last_seen': stats['last_seen'].isoformat() if stats['last_seen'] else None,
                'count': stats['count'],
            })
        task_data['url_details'] = url_details_list
        task_data['urls'] = [item['url'] for item in url_details_list]
        task_data['url_diversity'] = len(task_data['url_diversity'])

    return task_url_map


def segment_heatmaps_by_tasks(
    heatmap_data: List[Dict[str, Any]],
    task_url_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    segmented: Dict[str, Dict[str, Any]] = {}

    for task_id, task_data in task_url_map.items():
        segmented[task_id] = {
            'task_info': {
                'task_id': task_id,
                'title': task_data['title'],
                'description': task_data['description'],
                'duration_minutes': task_data.get('duration_minutes', 0),
                'navigation_count': task_data.get('navigation_count', 0),
                'url_diversity': task_data.get('url_diversity', 0),
                'urls_visited': task_data['urls'],
                'url_details': task_data.get('url_details', []),
                'initial_timestamp': task_data.get('initial_timestamp'),
                'final_timestamp': task_data.get('final_timestamp'),
            },
            'heatmaps': [],
        }

    def _ranges_overlap(
        a_start: Optional[datetime], a_end: Optional[datetime],
        b_start: Optional[datetime], b_end: Optional[datetime],
    ) -> bool:
        if not a_start or not a_end or not b_start or not b_end:
            return False
        return max(a_start, b_start) <= min(a_end, b_end)

    for item in heatmap_data:
        if not isinstance(item, dict):
            continue
        page_images = item.get('heatmap_images', [])
        if not isinstance(page_images, list):
            continue
        time_range = item.get('time_range', {})
        heatmap_start = normalize_timestamp(time_range.get('start')) if isinstance(time_range, dict) else None
        heatmap_end = normalize_timestamp(time_range.get('end')) if isinstance(time_range, dict) else None

        for page_image in page_images:
            if not isinstance(page_image, dict):
                continue
            page_url = page_image.get('url')
            if not page_url:
                continue

            candidate_matches: List[Tuple[str, float, bool, bool]] = []
            for task_id, task_data in task_url_map.items():
                url_details = task_data.get('url_details_map', {}).get(page_url)
                if not url_details:
                    continue
                range_match = _ranges_overlap(
                    task_data.get('initial_timestamp'),
                    task_data.get('final_timestamp'),
                    heatmap_start or url_details['first_seen'],
                    heatmap_end or url_details['last_seen'],
                )
                points = page_image.get('points', []) or []
                point_timestamps = [normalize_timestamp(p.get('timestamp')) for p in points if p.get('timestamp')]
                points_match = any(
                    task_data.get('initial_timestamp') <= ts <= task_data.get('final_timestamp')
                    for ts in point_timestamps if ts
                ) if point_timestamps else False

                if not (range_match or points_match):
                    continue

                confidence = 0.0
                if page_url in task_data['urls']:
                    confidence += 0.4
                if range_match:
                    confidence += 0.3
                if points_match:
                    confidence += 0.3
                candidate_matches.append((task_id, confidence, range_match, points_match))

            if not candidate_matches:
                continue

            candidate_matches.sort(key=lambda item: item[1], reverse=True)
            for task_id, confidence_score, range_match, points_match in candidate_matches:
                if confidence_score < 0.5:
                    continue
                nav_window = task_url_map[task_id].get('url_details_map', {}).get(page_url, {})
                heatmap_item = {
                    'height': page_image.get('height'),
                    'image': page_image.get('image'),
                    'points': page_image.get('points', []),
                    'scroll_positions': page_image.get('scroll_positions'),
                    'url': page_url,
                    'width': page_image.get('width'),
                    'metadata': {
                        'total_points': len(page_image.get('points', [])),
                        'task_id': task_id,
                        'task_title': task_url_map[task_id]['title'],
                        'matched_strategy': 'points+url' if points_match else ('url+range' if range_match else 'url'),
                        'confidence': round(confidence_score, 2),
                        'heatmap_time_range': {
                            'start': heatmap_start.isoformat() if heatmap_start else None,
                            'end': heatmap_end.isoformat() if heatmap_end else None,
                        },
                        'navigation_window': {
                            'count': nav_window.get('count'),
                            'first_seen': nav_window.get('first_seen').isoformat() if nav_window.get('first_seen') else None,
                            'last_seen': nav_window.get('last_seen').isoformat() if nav_window.get('last_seen') else None,
                        },
                    },
                }
                segmented.setdefault(task_id, {'task_info': {}, 'heatmaps': []})['heatmaps'].append(heatmap_item)

    return segmented


def aggregate_heatmaps_by_url(
    heatmap_data: List[Dict[str, Any]],
    navigation_data: List[Dict[str, Any]],
    performed_tasks: List[PerformedTask],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[int, Dict[str, Any]]]:
    scenario_lookup: Dict[int, Dict[str, Any]] = {}
    for pt in performed_tasks:
        if pt.task_id not in scenario_lookup:
            scenario_lookup[pt.task_id] = {
                'task_id': pt.task_id,
                'title': getattr(pt.task, 'title', f'Scenario {pt.task_id}'),
                'description': getattr(pt.task, 'description', '') or getattr(pt.task, 'summary', ''),
                'process_id': getattr(pt.task, 'seco_process_id', None),
            }

    url_map: Dict[str, Dict[str, Any]] = {}
    navigation_map: Dict[str, Dict[str, Any]] = {}
    unique_scenarios_with_navigation: set[int] = set()
    total_heatmap_images = 0

    for nav in navigation_data:
        url = nav.get('url')
        scenario_id = nav.get('task_id')
        if not url or scenario_id is None:
            continue
        scenario_info = scenario_lookup.get(scenario_id)
        if not scenario_info:
            continue
        scenario_nav_map = navigation_map.setdefault(url, {})
        scenario_entry = scenario_nav_map.setdefault(scenario_id, {
            'task_id': scenario_id,
            'scenario_title': scenario_info['title'],
            'scenario_description': scenario_info['description'],
            'navigation_hits': 0,
            'participants': set(),
        })
        scenario_entry['navigation_hits'] += 1
        cd_id = nav.get('collected_data_id')
        if cd_id is not None:
            scenario_entry['participants'].add(cd_id)
        unique_scenarios_with_navigation.add(scenario_id)

    for item in heatmap_data:
        if not isinstance(item, dict):
            continue
        page_images = item.get('heatmap_images', [])
        if not isinstance(page_images, list):
            continue
        for page_image in page_images:
            if not isinstance(page_image, dict):
                continue
            url = page_image.get('url') or 'Unknown URL'
            total_heatmap_images += 1
            entry = url_map.setdefault(url, {
                'url': url,
                'title': page_image.get('title') or page_image.get('page_title') or url,
                'mime': page_image.get('mime') or page_image.get('content_type') or 'image/jpeg',
                'image': page_image.get('image'),
                'width': page_image.get('width'),
                'height': page_image.get('height'),
                'aggregated_points': [],
                'heatmap_count': 0,
                'sources': [],
            })
            if not entry.get('image') and page_image.get('image'):
                entry['image'] = page_image.get('image')
            if not entry.get('mime') and page_image.get('mime'):
                entry['mime'] = page_image.get('mime')
            if not entry.get('width') and page_image.get('width'):
                entry['width'] = page_image.get('width')
            if not entry.get('height') and page_image.get('height'):
                entry['height'] = page_image.get('height')
            points = page_image.get('points', [])
            if isinstance(points, list):
                entry['aggregated_points'].extend(points)
            entry['heatmap_count'] += 1
            entry['sources'].append({
                'points': len(points),
                'index': entry['heatmap_count'],
            })

    aggregated_list: List[Dict[str, Any]] = []
    total_points = 0
    total_navigation_hits = 0

    for url, entry in url_map.items():
        nav_info = navigation_map.get(url, {})
        scenarios_for_url = []
        navigation_hits_for_url = 0
        for scenario_id, scenario_data in nav_info.items():
            participants = scenario_data.get('participants', set())
            navigation_hits_for_url += scenario_data['navigation_hits']
            scenarios_for_url.append({
                'task_id': scenario_id,
                'scenario_title': scenario_data['scenario_title'],
                'scenario_description': scenario_data['scenario_description'],
                'navigation_hits': scenario_data['navigation_hits'],
                'unique_participants': len(participants),
            })
        scenarios_for_url.sort(key=lambda item: item['navigation_hits'], reverse=True)
        points_for_url = len(entry['aggregated_points'])
        total_points += points_for_url
        total_navigation_hits += navigation_hits_for_url
        aggregated_list.append({
            'url': url,
            'title': entry['title'] or url,
            'mime': entry['mime'] or 'image/jpeg',
            'image': entry['image'],
            'width': entry.get('width'),
            'height': entry.get('height'),
            'aggregated_points': entry['aggregated_points'],
            'total_points': points_for_url,
            'heatmap_count': entry['heatmap_count'],
            'total_navigation_hits': navigation_hits_for_url,
            'scenarios_involved': scenarios_for_url,
            'scenarios_count': len(scenarios_for_url),
            'sources': entry['sources'],
        })

    aggregated_list.sort(key=lambda item: item['total_points'], reverse=True)
    aggregation_stats = {
        'total_urls': len(aggregated_list),
        'total_points': total_points,
        'total_navigation_hits': total_navigation_hits,
        'total_heatmap_images': total_heatmap_images,
        'scenarios_with_navigation': len(unique_scenarios_with_navigation),
    }
    return aggregated_list, aggregation_stats, scenario_lookup


def fetch_heatmap_from_uxt(evaluation_id: int, token: str, timeout: int = 300) -> List[Dict[str, Any]]:
    url_get_heatmap = f'https://uxt-stage.liis.com.br/view/heatmap/code/{evaluation_id}'
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url_get_heatmap, headers=headers, timeout=timeout)
    if response.status_code != 200:
        raise requests.HTTPError(
            f"Failed to retrieve heatmap data (status {response.status_code})",
            response=response,
        )
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON response from UX Tracking API") from exc
    return data if isinstance(data, list) else [data]


def build_scenarios_payload(evaluation_id: int, token: str) -> Dict[str, Any]:
    evaluation = Evaluation.query.get(evaluation_id)
    if not evaluation:
        raise ValueError(f"Evaluation {evaluation_id} not found")

    heatmap_data = fetch_heatmap_from_uxt(evaluation_id, token)
    performed_tasks: List[PerformedTask] = []
    navigation_data: List[Dict[str, Any]] = []

    for col_data in evaluation.collected_data:
        performed_tasks.extend(col_data.performed_tasks)
        for nav in col_data.navigation:
            navigation_data.append({
                'action': nav.action.value if hasattr(nav.action, 'value') else str(nav.action),
                'url': nav.url,
                'title': nav.title,
                'timestamp': nav.timestamp.isoformat(),
                'task_id': nav.task_id,
                'collected_data_id': nav.collected_data_id,
            })

    aggregated_urls, aggregation_stats, scenario_lookup = aggregate_heatmaps_by_url(
        heatmap_data,
        navigation_data,
        performed_tasks,
    )

    scenario_mapping_available = any(item['scenarios_involved'] for item in aggregated_urls)
    data_quality_score = 0
    data_quality_warnings = []

    if aggregation_stats['total_heatmap_images'] > 0:
        data_quality_score += 40
    else:
        data_quality_warnings.append("No heatmap images returned from UX Tracking.")

    if len(navigation_data) > 0:
        data_quality_score += 30
    else:
        data_quality_warnings.append("No navigation data recorded for this evaluation.")

    if scenario_mapping_available:
        data_quality_score += 30
    else:
        data_quality_warnings.append("Unable to map heatmaps to specific scenarios (missing navigation data).")

    metadata = {
        'total_urls': aggregation_stats['total_urls'],
        'total_points_processed': aggregation_stats['total_points'],
        'total_heatmaps': aggregation_stats['total_heatmap_images'],
        'navigation_data_count': len(navigation_data),
        'total_navigation_hits': aggregation_stats['total_navigation_hits'],
        'scenarios_with_navigation': aggregation_stats['scenarios_with_navigation'],
        'processed_at': datetime.now(pytz.UTC).isoformat(),
        'evaluation_id': evaluation_id,
        'segmentation_method': 'aggregated_by_url',
        'data_quality_score': data_quality_score,
        'data_quality_warnings': data_quality_warnings,
        'fallback_used': not scenario_mapping_available,
        'scenario_mapping_available': scenario_mapping_available,
    }

    if not scenario_mapping_available:
        metadata['scenario_mapping_reason'] = (
            "Navigation data was missing or could not be mapped to scenarios."
        )

    available_scenarios = sorted(
        scenario_lookup.values(),
        key=lambda scenario: (scenario.get('title') or '').lower(),
    )

    return {
        'heatmaps_by_url': aggregated_urls,
        'available_scenarios': available_scenarios,
        'metadata': metadata,
    }
