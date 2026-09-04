"""Central feature flags read from the environment (.env).

This module must stay free of app imports so it can be imported from
index.py, views and services without any circular-import risk.

Flags:
    DEV_MODE        dev vs production behavior (email verification skip, etc.)
    UXT_INTEGRATION toggles every call to the external UX-Tracking API
                    (signup, login token, password reset, heatmaps,
                    evaluation-code generation). Defaults to True so an
                    unset production environment keeps today's behavior.
    AI_ANALYSIS     master switch for the AI analytical layer (Findings and
                    Action Plan tabs in the evaluation dashboard). Defaults to
                    False: the feature costs API calls and needs a provider key,
                    so it must be turned on deliberately.
    AI_ALLOW_REGENERATE
                    shows the "Regenerate" control with the model picker on
                    those tabs. Meant for development and for comparing models
                    on the same evaluation; keep it off in production.

Provider settings (AI_PROVIDER, AI_MODEL, AI_MODELS, ...) are NOT here: they are
read by services/ai/provider.py, their only consumer.
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
AI_ANALYSIS = _env_bool("AI_ANALYSIS", False)
AI_ALLOW_REGENERATE = _env_bool("AI_ALLOW_REGENERATE", False)
