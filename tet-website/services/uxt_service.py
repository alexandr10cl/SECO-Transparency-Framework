"""Single gateway for ALL UX-Tracking (UXT) external integration.

Every call to the external UX-Tracking API (https://uxt.liis.com.br, docs at
/api/docs) lives in
this module. The rest of the backend depends on the local functions exported here
(login, register, password reset, evaluation-code generation, heatmap fetch and token
management) instead of importing ``requests`` or hardcoding UXT URLs.

Design: this is an Anti-Corruption Layer. Functions that talk to UXT return plain
result dicts and never touch Flask flash messages / redirects — the views interpret the
result and own the user-facing presentation. The only Flask state this module manages is
the UXT access token cached in ``session`` (set/clear_session_uxt_token), which is itself
a UXT concern.

Import discipline mirrors the former ``uxt_token_manager``: it imports ``config_flags``
and Flask helpers only, never ``from index import app``, to avoid circular imports.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Optional, Tuple

import requests
from flask import current_app, has_request_context, session

from config_flags import UXT_INTEGRATION

# ---------------------------------------------------------------------------
# Configuration / constants
# ---------------------------------------------------------------------------
BASE_URL = "https://uxt.liis.com.br"

# Auth endpoints
AUTH_LOGIN_URL = f"{BASE_URL}/auth/login"
# The service-token login keeps the existing UXT_LOGIN_URL env override.
LOGIN_URL = os.getenv("UXT_LOGIN_URL", AUTH_LOGIN_URL)
REGISTER_URL = f"{BASE_URL}/auth/register"
ME_URL = f"{BASE_URL}/auth/me"
CHANGE_ROLE_URL = f"{BASE_URL}/auth/change-role"
FORGOT_PASSWORD_URL = f"{BASE_URL}/auth/forgot-password"
RESET_PASSWORD_URL = f"{BASE_URL}/auth/reset-password"

# Other endpoints
GENERATE_CODE_URL = f"{BASE_URL}/generate-code?horas=730"

# Message shown to the UI when the integration is disabled (UXT_INTEGRATION=False).
UXT_DISABLED_MESSAGE = "Integração UX-Tracking desativada"

# Session keys for the per-user UXT token.
TOKEN_SESSION_KEY = "uxt_access_token"
TOKEN_EXPIRY_KEY = "uxt_token_expires_at"

_DEFAULT_TTL = 3600  # seconds
_REFRESH_BUFFER = 60  # seconds

_service_cache = {"token": None, "expires_at": 0.0}
_service_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Token management (migrated verbatim from the former uxt_token_manager.py)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Authentication flows (migrated from views/auth.py)
#
# These perform the UXT HTTP calls and return a plain result dict. The view layer
# interprets the result to set flash messages / redirects, preserving the existing
# user-facing behavior. The UXT token session helpers above are used internally
# where the original code did so (login).
# ---------------------------------------------------------------------------
def login(email: str, password: str) -> dict:
    """Authenticate the user against UXT and mirror the token into the session.

    The caller may ignore the return value (login proceeds regardless of UXT status).
    """
    uxt_dados = {
        "email": email,
        "password": password,
    }

    try:
        # Set timeout to prevent hanging (increased to 15s for slower UXT API responses)
        resposta = requests.post(AUTH_LOGIN_URL, json=uxt_dados, timeout=60)

        if resposta.status_code == 200:
            data = resposta.json()
            access_token = data.get('access_token')
            if access_token:
                set_session_uxt_token(access_token, data.get('expires_in'))
                print(f"[UXT] Token de acesso obtido com sucesso para '{email}'.")
                return {"ok": True, "status_code": 200, "error_kind": None, "data": data}
            else:
                print("[UXT] Nenhum token de acesso retornado.")
                clear_session_uxt_token()
                return {"ok": False, "status_code": 200, "error_kind": None, "data": data}
        else:
            print(f"[UXT] Erro ao autenticar na API UXT (status {resposta.status_code}).")
            print(f"[UXT] Resposta: {resposta.text}")
            clear_session_uxt_token()
            return {"ok": False, "status_code": resposta.status_code, "error_kind": "http", "data": {}}

    except requests.exceptions.Timeout:
        # UXT API timeout - allow login anyway
        print("[UXT] Timeout ao conectar com API UXT. Continuando login sem UXT token.")
        clear_session_uxt_token()
        return {"ok": False, "status_code": None, "error_kind": "timeout", "data": {}}

    except requests.exceptions.ConnectionError:
        # UXT API not reachable - allow login anyway
        print("[UXT] Erro de conexão com API UXT. Continuando login sem UXT token.")
        clear_session_uxt_token()
        return {"ok": False, "status_code": None, "error_kind": "connection", "data": {}}

    except requests.exceptions.RequestException as e:
        # Any other request error - allow login anyway
        print(f"[UXT] Erro ao conectar com API UXT: {str(e)}. Continuando login sem UXT token.")
        clear_session_uxt_token()
        return {"ok": False, "status_code": None, "error_kind": "request", "data": {}}


def register(email: str, username: str, password: str) -> dict:
    """Register the user in UXT and promote them to SECO Manager.

    Returns one of:
        {"ok": True}
        {"ok": False, "reason": "register_http", "status_code": <int>}
        {"ok": False, "reason": "role_assignment"}
        {"ok": False, "reason": "connection" | "timeout" | "request"}
    """
    uxt_dados = {
        "email": email,
        "username": username,
        "password": password,
        "role": 1
    }
    try:
        resposta = requests.post(REGISTER_URL, json=uxt_dados)
        if resposta.status_code != 201:
            print(f"[UXT] Registration failed at UXT API (status {resposta.status_code}).")
            print(f"[UXT] Response: {resposta.text}")
            return {"ok": False, "reason": "register_http", "status_code": resposta.status_code}

        print(f"[UXT] Account successfully registered at UXT API for '{email}'.")
        access_token = resposta.json().get('access_token')
        me_data = None
        if access_token:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            me_resp = requests.get(ME_URL, headers=headers)
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                print(f"[UXT] Logged in user data: {me_data}")
            else:
                print(f"[UXT] Failed to access /auth/me: {me_resp.status_code}")
                print(f"[UXT] Response: {me_resp.text}")
        else:
            print("[UXT] No access token returned.")
        # Get admin token to change role
        admin_credentials = {
            "email": os.getenv("ADMIN_EMAIL"),
            "password": os.getenv("ADMIN_PASSWORD")
        }
        resposta_admin = requests.post(AUTH_LOGIN_URL, json=admin_credentials)
        if resposta_admin.status_code == 200 and me_data:
            token = resposta_admin.json().get("access_token")
            managerId = me_data.get("idUser")
            changeRole_data = {
                "userId": managerId,
                "newRole": 2  # SECO Manager
            }
            headers_admin = {
                'Authorization': f'Bearer {token}'
            }
            resposta_changeRole = requests.post(CHANGE_ROLE_URL, json=changeRole_data, headers=headers_admin)
            if resposta_changeRole.status_code == 200:
                print(f"[UXT] User role for '{email}' changed to SECO Manager successfully.")
            else:
                print(f"[UXT] Error changing user role: {resposta_changeRole.text}")
                return {"ok": False, "reason": "role_assignment"}
        else:
            print(f"[UXT] Error obtaining admin token or user data: {resposta_admin.text if resposta_admin.status_code != 200 else 'No user data'}")
            return {"ok": False, "reason": "role_assignment"}
    except requests.exceptions.ConnectionError:
        print("[UXT] Connection error: Could not connect to UXTracking API")
        return {"ok": False, "reason": "connection"}
    except requests.exceptions.Timeout:
        print("[UXT] Timeout error: UXTracking API request timed out")
        return {"ok": False, "reason": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"[UXT] Request error with UXT API: {str(e)}")
        return {"ok": False, "reason": "request"}

    return {"ok": True}


def request_password_reset(email: str) -> dict:
    """Ask UXT to send a password-reset code. Returns {"ok": bool, "reason": ...}."""
    uxt_dados = {
        "email": email
    }

    try:
        resposta = requests.post(FORGOT_PASSWORD_URL, json=uxt_dados)
        if resposta.status_code == 200:
            print(f"[UXT] Password reset email sent successfully to '{email}'.")
            return {"ok": True}
        else:
            print(f"[UXT] Error sending password reset email (status {resposta.status_code}).")
            return {"ok": False, "reason": "http"}
    except requests.exceptions.ConnectionError:
        print("[UXT] Connection error: Could not connect to UXTracking API")
        return {"ok": False, "reason": "connection"}
    except requests.exceptions.Timeout:
        print("[UXT] Timeout error: UXTracking API request timed out")
        return {"ok": False, "reason": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"[UXT] Error sending password reset email: {str(e)}")
        return {"ok": False, "reason": "request"}


def reset_password(email: str, code: str, new_password: str) -> dict:
    """Reset the user's password in UXT. Returns {"ok": bool, "reason": ...}.

    The caller is responsible for updating the local DB password on success.
    """
    uxt_dados = {
        "email": email,
        "code": code,
        "newPassword": new_password,
        "confirmNewPassword": new_password
    }

    try:
        resposta = requests.post(RESET_PASSWORD_URL, json=uxt_dados)
        if resposta.status_code == 200:
            print(f"[UXT] Password reset successfully for '{email}'.")
            return {"ok": True}
        else:
            print(f"[UXT] Error resetting password (status {resposta.status_code}).")
            return {"ok": False, "reason": "http"}
    except requests.exceptions.ConnectionError:
        print("[UXT] Connection error: Could not connect to UXTracking API")
        return {"ok": False, "reason": "connection"}
    except requests.exceptions.Timeout:
        print("[UXT] Timeout error: UXTracking API request timed out")
        return {"ok": False, "reason": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"[UXT] Error resetting password: {str(e)}")
        return {"ok": False, "reason": "request"}


# ---------------------------------------------------------------------------
# Evaluation-code generation (migrated from views/index.py)
# ---------------------------------------------------------------------------
def _request_code(token_value: str):
    print("LOG: Fazendo chamada para API UXT...")
    response = requests.post(
        GENERATE_CODE_URL,
        headers={'Authorization': f'Bearer {token_value}'},
        timeout=10
    )
    print(f"LOG: Resposta da API UXT - Status: {response.status_code}")
    print(f"LOG: Resposta da API UXT - Conteúdo: {response.text}")
    return response


def generate_evaluation_code() -> Optional[str]:
    """Generate an evaluation code via the UXT API.

    Returns the code (``cod``) on success, or ``None`` when UXT is disabled, no token is
    available, or the API call fails. The caller is responsible for the local random
    fallback when this returns ``None``.
    """
    if UXT_INTEGRATION:
        access_token = get_uxt_token()
        print(f"=== LOG: Iniciando geração de código de avaliação ===")
        print(f"LOG: Access token disponível: {bool(access_token)}")
    else:
        access_token = None

    if access_token:
        try:
            r = _request_code(access_token)
            if r.status_code == 201:
                data = r.json() or {}
                evaluation_id = data.get('cod')
                print(f"LOG: Código gerado pela API UXT: {evaluation_id}")
                return evaluation_id
            elif r.status_code == 401:
                print("LOG: Token expirado ao gerar código. Tentando renovar token.")
                refreshed = get_uxt_token(force_refresh=True)
                if refreshed:
                    r = _request_code(refreshed)
                    if r.status_code == 201:
                        data = r.json() or {}
                        evaluation_id = data.get('cod')
                        print(f"LOG: Código gerado após renovação: {evaluation_id}")
                        return evaluation_id
                    else:
                        print(f"LOG: Segunda tentativa também falhou: {r.status_code}")
                else:
                    print("LOG: Não foi possível renovar o token UXT.")
            else:
                print(f"LOG: API UXT não retornou status 201. Status: {r.status_code}")
        except Exception as e:
            print(f"LOG: ERRO ao chamar API UXT: {str(e)}")
            return None
    else:
        print("LOG: Sem access token disponível, usando fallback")

    return None


# ---------------------------------------------------------------------------
# Heatmap fetch (migrated from services/heatmap_service.py and views/api.py)
# ---------------------------------------------------------------------------
def fetch_heatmap_from_uxt(evaluation_id: int, token: str, timeout: int = 300) -> list:
    """Fetch raw heatmap data from UXT. Raises on non-200 or invalid JSON.

    Used by heatmap_service.build_scenarios_payload (300s timeout).
    """
    url_get_heatmap = f'{BASE_URL}/view/heatmap/code/{evaluation_id}'
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


def fetch_heatmap_via_api(evaluation_id: int, token: str, timeout: int = 120):
    """Fetch raw heatmap JSON from UXT for the /api/view_heatmap and /api/heatmap-tasks
    endpoints. Uses ``raise_for_status`` (120s timeout) and returns the decoded JSON.
    """
    response = requests.get(
        f'{BASE_URL}/view/heatmap/code/{evaluation_id}',
        headers={'Authorization': f'Bearer {token}'},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
