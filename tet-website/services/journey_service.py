from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

from models import Evaluation
from models.enums import NavigationType, PerformedTaskStatus, AcademicLevel, PreviousExperience, SegmentType

STATUS_LABELS = {
    PerformedTaskStatus.SOLVED: ("Solved", "solved"),
    PerformedTaskStatus.NOT_SURE: ("Not sure", "not-sure"),
    PerformedTaskStatus.COULDNT_SOLVE: ("Couldn't solve", "couldnt-solve"),
}

ACADEMIC_LABELS = {
    AcademicLevel.HIGH_SCHOOL: "High School",
    AcademicLevel.BACHELOR: "Graduation",
    AcademicLevel.MASTER: "Master",
    AcademicLevel.DOCTORATE: "PhD",
}

FAMILIARITY_LABELS = {
    PreviousExperience.NEVER: "Never",
    PreviousExperience.RARELY: "Rarely",
    PreviousExperience.OFTEN: "Often",
    PreviousExperience.AWAYS: "Always",
}

SEGMENT_LABELS = {
    SegmentType.ACADEMIA: "Academia",
    SegmentType.INDUSTRY: "Industry",
    SegmentType.BOTH: "Both",
}

MAX_PATH_LENGTH = 60


def _build_path(url: str) -> str:
    try:
        path = urlparse(url).path or "/"
    except ValueError:
        return "/"
    if len(path) > MAX_PATH_LENGTH:
        return path[: MAX_PATH_LENGTH - 1] + "…"
    return path


def _build_scenario_index(evaluation: Evaluation) -> Dict[int, str]:
    """Assign S1, S2... in the same order used by scenario_cards in views/index.py."""
    task_order: List[int] = []
    seen = set()
    for process in evaluation.seco_processes:
        for task in process.tasks:
            if task.task_id not in seen:
                seen.add(task.task_id)
                task_order.append(task.task_id)

    return {task_id: f"S{index}" for index, task_id in enumerate(task_order, start=1)}


def _build_profile(questionnaire) -> Dict[str, Any]:
    if questionnaire is None:
        return {
            "academic_level": None,
            "experience_years": None,
            "segment": None,
            "portal_familiarity": None,
        }

    return {
        "academic_level": ACADEMIC_LABELS.get(questionnaire.academic_level),
        "experience_years": questionnaire.experience,
        "segment": SEGMENT_LABELS.get(questionnaire.segment),
        "portal_familiarity": FAMILIARITY_LABELS.get(questionnaire.previus_xp),
    }


def _build_event(nav) -> Dict[str, Any]:
    kind = "tab_switch" if nav.action == NavigationType.TAB_SWITCH else "navigation"
    return {
        "kind": kind,
        "timestamp": nav.timestamp.isoformat(),
        "title": nav.title,
        "url": nav.url,
        "path": _build_path(nav.url),
    }


def _build_scenario(performed_task, scenario_ref: str, navigation_events: List) -> Dict[str, Any]:
    status_label, status_tone = STATUS_LABELS.get(
        performed_task.status, (None, None)
    )

    try:
        duration_seconds = max(
            0.0,
            (performed_task.final_timestamp - performed_task.initial_timestamp).total_seconds(),
        )
    except TypeError:
        duration_seconds = 0.0

    initial_ts = performed_task.initial_timestamp

    events = []
    for nav in sorted(navigation_events, key=lambda n: n.timestamp):
        event = _build_event(nav)
        try:
            offset_seconds = max(0.0, (nav.timestamp - initial_ts).total_seconds())
        except TypeError:
            offset_seconds = 0.0
        event["offset_seconds"] = offset_seconds
        events.append(event)

    return {
        "scenario_ref": scenario_ref,
        "task_id": performed_task.task_id,
        "title": performed_task.task.title,
        "status": status_tone,
        "status_label": status_label,
        "duration_seconds": duration_seconds,
        "comment": performed_task.comments,
        "events": events,
    }


def build_journey_payload(evaluation: Evaluation) -> Dict[str, Any]:
    scenario_index = _build_scenario_index(evaluation)

    collected_data_sorted = sorted(
        evaluation.collected_data, key=lambda cd: cd.collected_data_id
    )

    participants = []
    for index, collected_data in enumerate(collected_data_sorted, start=1):
        navigation_by_task: Dict[int, List] = {}
        for nav in collected_data.navigation:
            navigation_by_task.setdefault(nav.task_id, []).append(nav)

        performed_tasks_sorted = sorted(
            collected_data.performed_tasks,
            key=lambda pt: scenario_index.get(pt.task_id, ""),
        )

        scenarios = []
        for performed_task in performed_tasks_sorted:
            scenario_ref = scenario_index.get(performed_task.task_id)
            if scenario_ref is None:
                continue
            navigation_events = navigation_by_task.get(performed_task.task_id, [])
            scenarios.append(_build_scenario(performed_task, scenario_ref, navigation_events))

        try:
            duration_seconds = max(
                0.0,
                (collected_data.end_time - collected_data.start_time).total_seconds(),
            )
        except TypeError:
            duration_seconds = 0.0

        participants.append({
            "participant_ref": f"P{index}",
            "collected_data_id": collected_data.collected_data_id,
            "profile": _build_profile(collected_data.developer_questionnaire),
            "session": {
                "start": collected_data.start_time.isoformat() if collected_data.start_time else None,
                "end": collected_data.end_time.isoformat() if collected_data.end_time else None,
                "duration_seconds": duration_seconds,
            },
            "scenarios": scenarios,
        })

    return {
        "evaluation_id": evaluation.evaluation_id,
        "participants": participants,
    }
