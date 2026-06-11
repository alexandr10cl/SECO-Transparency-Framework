from __future__ import annotations

import os
import threading
import time
from typing import Optional, Tuple

import requests
from flask import current_app, has_request_context, session

from config_flags import UXT_INTEGRATION

LOGIN_URL = os.getenv("UXT_LOGIN_URL", "https://uxt-stage.liis.com.br/auth/login")
TOKEN_SESSION_KEY = "uxt_access_token"
TOKEN_EXPIRY_KEY = "uxt_token_expires_at"

_DEFAULT_TTL = 3600  # seconds
_REFRESH_BUFFER = 60  # seconds

_service_cache = {"token": None, "expires_at": 0.0}
_service_lock = threading.Lock()


def _now() -> float:
    return time.time()


def _compute_expiration(expires_in: Optional[int]) -> float:
    try:
        ttl = int(expires_in)
    except (TypeError, ValueError):
        ttl = _DEFAULT_TTL

    ttl = max(ttl - _REFRESH_BUFFER, _REFRESH_BUFFER)
    return _now() + ttl


def set_session_uxt_token(token: Optional[str], expires_in: Optional[int] = None) -> None:
    """Cache UX Tracking token inside the current user session."""
    if not has_request_context():
        return

    if token:
        session[TOKEN_SESSION_KEY] = token
        session[TOKEN_EXPIRY_KEY] = _compute_expiration(expires_in)
    else:
        clear_session_uxt_token()


def clear_session_uxt_token() -> None:
    """Remove UX Tracking credentials from the current session."""
    if not has_request_context():
        return

    session.pop(TOKEN_SESSION_KEY, None)
    session.pop(TOKEN_EXPIRY_KEY, None)


def _get_session_token() -> Optional[str]:
    if not has_request_context():
        return None

    token = session.get(TOKEN_SESSION_KEY)
    expires_at = session.get(TOKEN_EXPIRY_KEY, 0)

    if not token:
        return None

    if expires_at and _now() >= expires_at:
        clear_session_uxt_token()
        return None

    return token


def _get_service_credentials() -> Tuple[Optional[str], Optional[str]]:
    config = getattr(current_app, "config", {})
    email = (
        config.get("UXT_SERVICE_EMAIL")
        or os.getenv("UXT_SERVICE_EMAIL")
        or os.getenv("ADMIN_EMAIL")
    )
    password = (
        config.get("UXT_SERVICE_PASSWORD")
        or os.getenv("UXT_SERVICE_PASSWORD")
        or os.getenv("ADMIN_PASSWORD")
    )
    return email, password


def _refresh_service_token(force: bool = False) -> Optional[str]:
    if not UXT_INTEGRATION:
        return None

    with _service_lock:
        if (
            not force
            and _service_cache["token"]
            and _now() < _service_cache["expires_at"]
        ):
            return _service_cache["token"]

        email, password = _get_service_credentials()
        if not email or not password:
            current_app.logger.warning(
                "UXT service credentials are not configured. "
                "Set UXT_SERVICE_EMAIL and UXT_SERVICE_PASSWORD."
            )
            return _service_cache["token"]

        try:
            response = requests.post(
                LOGIN_URL,
                json={"email": email, "password": password},
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            current_app.logger.error("Failed to refresh UX Tracking token: %s", exc)
            return _service_cache["token"]

        data = response.json()
        token = data.get("access_token")
        if not token:
            current_app.logger.error(
                "UX Tracking login response did not include an access token."
            )
            return _service_cache["token"]

        expires_at = _compute_expiration(data.get("expires_in"))
        _service_cache["token"] = token
        _service_cache["expires_at"] = expires_at
        return token


def get_uxt_token(force_refresh: bool = False) -> Optional[str]:
    """
    Return a valid UX Tracking token.

    Order of preference:
        1. Session token (if available and still valid)
        2. Cached service token (shared across sessions)
        3. Fresh service token (using configured credentials)

    Returns None immediately when UXT_INTEGRATION is disabled.
    """
    if not UXT_INTEGRATION:
        return None

    token = None

    if not force_refresh:
        token = _get_session_token()
        if token:
            return token

    if force_refresh and has_request_context():
        clear_session_uxt_token()

    token = _refresh_service_token(force=force_refresh)

    if token and has_request_context():
        # Mirror the shared token inside the session so subsequent requests reuse it.
        session[TOKEN_SESSION_KEY] = token
        session[TOKEN_EXPIRY_KEY] = _service_cache["expires_at"]

    return token

