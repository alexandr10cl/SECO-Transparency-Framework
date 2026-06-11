"""Central feature flags read from the environment (.env).

This module must stay free of app imports so it can be imported from
index.py, views and services without any circular-import risk.

Flags:
    DEV_MODE        dev vs production behavior (email verification skip, etc.)
    UXT_INTEGRATION toggles every call to the external UX-Tracking API
                    (signup, login token, password reset, heatmaps,
                    evaluation-code generation). Defaults to True so an
                    unset production environment keeps today's behavior.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


DEV_MODE = _env_bool("DEV_MODE", False)
UXT_INTEGRATION = _env_bool("UXT_INTEGRATION", True)
