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

DOIS TOKENS, DOIS PAPEIS — nunca um como reserva do outro:

``get_gestor_token()``   token do gestor logado, guardado na sessao pelo ``login``.
                         E o unico valido para DADOS: gerar codigo de avaliacao, ler
                         heatmap, rodar analise.
``get_service_token()``  conta de integracao do .env (SUPERVISOR). Serve so para
                         PROVISIONAR: criar a conta do gestor na UXT e promove-la a
                         MANAGER no cadastro.

A separacao nao e estetica. A UXT segrega os dados por gestor: o codigo da avaliacao
embute o id de quem o gerou nos 3 ultimos digitos, a coleta cai numa colecao desse
gestor e ler codigo alheio devolve 403 ("Voce so pode consultar codigos que voce mesmo
gerou"). A versao anterior caia da sessao para a conta de servico sem avisar, o que
produzia dois estragos: leitura em nome de uma conta que nao enxerga nada, e — se o
fallback pegasse na CRIACAO da avaliacao — um codigo pertencente a conta de servico,
cujos dados o gestor nunca mais conseguiria ler. Por isso, sem token do gestor a
operacao falha com mensagem clara em vez de degradar.

Import discipline mirrors the former ``uxt_token_manager``: it imports ``config_flags``
and Flask helpers only, never ``from index import app``, to avoid circular imports.
"""
from __future__ import annotations

import base64
import binascii
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
USED_CODES_URL = f"{BASE_URL}/generate-code/used"
HEATMAP_SUMMARY_URL = f"{BASE_URL}/analysis/heatmap_summary"

# Message shown to the UI when the integration is disabled (UXT_INTEGRATION=False).
UXT_DISABLED_MESSAGE = "Integração UX-Tracking desativada"

# Sessão do gestor ausente/expirada: a operação não tem como prosseguir em nome dele.
UXT_NO_GESTOR_TOKEN_MESSAGE = (
    "Sessão UX-Tracking expirada. Saia e entre novamente para recarregar os heatmaps."
)

# A UXT recusa leitura de código gerado por outra conta. Acontece com avaliações
# criadas antes desta correção, quando o código podia nascer sob a conta de serviço.
UXT_OWNERSHIP_MESSAGE = (
    "Esta avaliação foi criada com outra conta UX-Tracking. Só a conta que gerou o "
    "código consegue ler os heatmaps dela."
)

# Session keys for the per-user UXT token.
TOKEN_SESSION_KEY = "uxt_access_token"
TOKEN_EXPIRY_KEY = "uxt_token_expires_at"

_DEFAULT_TTL = 3600  # seconds
_REFRESH_BUFFER = 60  # seconds

# Sem isto, um .env sem credenciais de integração dispara um login por requisição:
# `_refresh_service_token` devolve None e nada fica em cache para barrar a próxima.
_FAILURE_BACKOFF = 60  # seconds

_service_cache = {"token": None, "expires_at": 0.0, "retry_after": 0.0}
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


def jwt_claims(token: Optional[str]) -> dict:
    """Claims do JWT, sem validar assinatura — só o payload, que é público.

    Não é autenticação: quem valida é a UXT. Serve para saber a validade real e o id
    da conta, dados que a resposta de login não traz.
    """
    try:
        payload = token.split(".")[1]
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        claims = json.loads(raw)
    except (AttributeError, IndexError, ValueError, binascii.Error, UnicodeDecodeError):
        return {}
    return claims if isinstance(claims, dict) else {}


def _token_expiration(token: str, expires_in: Optional[int]) -> float:
    """Validade real do token, tirada do claim `exp`.

    O login da UXT não devolve `expires_in`, então o cálculo antigo assumia o default de
    1h e descartava aos 59 minutos um token de MANAGER que vale 24h — e cada descarte
    levava o gestor a perder os heatmaps no meio da sessão. Quando o `exp` não é legível,
    cai no comportamento anterior.
    """
    exp = jwt_claims(token).get("exp")
    try:
        return max(float(exp) - _REFRESH_BUFFER, _now())
    except (TypeError, ValueError):
        return _compute_expiration(expires_in)


def set_session_uxt_token(token: Optional[str], expires_in: Optional[int] = None) -> None:
    """Cache UX Tracking token inside the current user session."""
    if not has_request_context():
        return

    if token:
        session[TOKEN_SESSION_KEY] = token
        session[TOKEN_EXPIRY_KEY] = _token_expiration(token, expires_in)
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


def _log(level: str, message: str, *args) -> None:
    """Logger tolerante a chamadas fora do contexto da app (threads de prefetch)."""
    try:
        getattr(current_app.logger, level)(message, *args)
    except RuntimeError:
        print(f"[UXT] {message % args if args else message}")


def _get_service_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Credenciais da conta de integração, guardadas em `ADMIN_EMAIL`/`ADMIN_PASSWORD`.

    Apesar do nome, não são o admin do portal — são uma conta da UXT, que precisa ser
    SUPERVISOR (role 3) lá. Vieram do commit db20d88, que tirou do código o login
    hardcoded usado para promover o gestor a MANAGER; o prefixo saiu da variável
    `uxt_admin_login_url` da época. Servem só para provisionar: ler dados é sempre com o
    token do gestor (`get_gestor_token`).
    """
    config = getattr(current_app, "config", {})
    email = config.get("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL")
    password = config.get("ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
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

        if not force and _now() < _service_cache["retry_after"]:
            # Falhou há pouco: não repete o login a cada requisição.
            return _service_cache["token"]

        def _fail(message: str, *args) -> Optional[str]:
            _log("error", message, *args)
            _service_cache["retry_after"] = _now() + _FAILURE_BACKOFF
            return _service_cache["token"]

        email, password = _get_service_credentials()
        if not email or not password:
            return _fail(
                "Conta de integração UXT não configurada. Defina ADMIN_EMAIL e "
                "ADMIN_PASSWORD no .env."
            )

        try:
            response = requests.post(
                LOGIN_URL,
                json={"email": email, "password": password},
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return _fail("Falha ao autenticar a conta de integração UXT: %s", exc)

        data = response.json()
        token = data.get("access_token")
        if not token:
            return _fail("Login da conta de integração UXT não devolveu access_token.")

        _service_cache["token"] = token
        _service_cache["expires_at"] = _token_expiration(token, data.get("expires_in"))
        _service_cache["retry_after"] = 0.0
        return token


def get_gestor_token() -> Optional[str]:
    """Token do gestor logado — o único válido para dados (código, heatmap, análise).

    Devolve None quando não há sessão UXT válida: quem chama traduz isso em erro para o
    usuário (``UXT_NO_GESTOR_TOKEN_MESSAGE``). Cair para a conta de serviço aqui seria
    pior que falhar — ela não enxerga nenhum dado do gestor, e um código gerado sob ela
    nunca mais poderia ser lido por ele.
    """
    if not UXT_INTEGRATION:
        return None
    return _get_session_token()


def get_service_token(force_refresh: bool = False) -> Optional[str]:
    """Token da conta de integração — só para provisionar contas de gestores na UXT.

    Não serve para ler dados: essa conta não é dona de nenhuma coleta.
    """
    if not UXT_INTEGRATION:
        return None
    return _refresh_service_token(force=force_refresh)


def is_ownership_error(response) -> bool:
    """A UXT recusou a leitura por o código ser de outra conta.

    Na rota de heatmap por código o 403 vem embrulhado num 400 (o NestJS captura a
    exceção do serviço interno e a repassa como BadRequest), então não basta olhar o
    status da resposta.
    """
    if response is None:
        return False
    if response.status_code == 403:
        return True
    try:
        body = response.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    if body.get("statusCode") == 403 or body.get("status") == 403:
        return True
    inner = body.get("response")
    return isinstance(inner, dict) and inner.get("statusCode") == 403


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
        resposta = requests.post(REGISTER_URL, json=uxt_dados, timeout=30)
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
            me_resp = requests.get(ME_URL, headers=headers, timeout=30)
            if me_resp.status_code == 200:
                me_data = me_resp.json()
                print(f"[UXT] Logged in user data: {me_data}")
            else:
                print(f"[UXT] Failed to access /auth/me: {me_resp.status_code}")
                print(f"[UXT] Response: {me_resp.text}")
        else:
            print("[UXT] No access token returned.")
        # Promoção a SECO Manager: é a única operação que precisa da conta de
        # integração (a UXT exige SUPERVISOR em change-role). Antes daqui saía um login
        # inline com ADMIN_EMAIL/ADMIN_PASSWORD; agora usa o mesmo token de serviço
        # cacheado do resto do módulo.
        service_token = get_service_token()
        if not service_token or not me_data:
            print(
                "[UXT] Sem token de serviço ou sem dados do usuário — não foi possível "
                "promover a SECO Manager."
            )
            return {"ok": False, "reason": "role_assignment"}

        managerId = me_data.get("idUser")
        resposta_changeRole = requests.post(
            CHANGE_ROLE_URL,
            json={"userId": managerId, "newRole": 2},  # 2 = SECO Manager
            headers={'Authorization': f'Bearer {service_token}'},
            timeout=30,
        )
        if resposta_changeRole.status_code == 200:
            print(f"[UXT] User role for '{email}' changed to SECO Manager successfully.")
        else:
            print(
                f"[UXT] Erro ao promover a SECO Manager (status "
                f"{resposta_changeRole.status_code}): {resposta_changeRole.text}"
            )
            if resposta_changeRole.status_code == 403:
                print(
                    "[UXT] 403 em change-role: a conta de integração precisa ser "
                    "SUPERVISOR (role 3) na UXT."
                )
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
        resposta = requests.post(FORGOT_PASSWORD_URL, json=uxt_dados, timeout=30)
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
        resposta = requests.post(RESET_PASSWORD_URL, json=uxt_dados, timeout=30)
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
    """Gera o código da avaliação na UXT, EM NOME DO GESTOR LOGADO.

    Tem de ser o token dele: o código carrega o id de quem o gerou e é esse gestor que
    passa a ser dono das sessões coletadas. Gerar com a conta de serviço produziria uma
    avaliação que ele nunca conseguiria ler.

    Devolve o ``cod`` ou ``None`` quando a integração está desligada, não há sessão UXT
    válida, ou a chamada falha. Com a integração ligada, ``None`` é erro — quem chama
    não deve inventar um código local (ver ``views/index.py``).
    """
    if not UXT_INTEGRATION:
        return None

    access_token = get_gestor_token()
    print("=== LOG: Iniciando geração de código de avaliação ===")
    print(f"LOG: Token do gestor disponível: {bool(access_token)}")

    if not access_token:
        print(
            "LOG: Sem token do gestor na sessão. A conta de serviço NÃO é usada aqui: "
            "o código pertenceria a ela e o gestor jamais leria os heatmaps."
        )
        return None

    try:
        r = _request_code(access_token)
    except Exception as e:  # noqa: BLE001 - rede/timeout, tratado como falha da geração
        print(f"LOG: ERRO ao chamar API UXT: {str(e)}")
        return None

    if r.status_code == 201:
        evaluation_id = (r.json() or {}).get('cod')
        print(f"LOG: Código gerado pela API UXT: {evaluation_id}")
        return evaluation_id

    if r.status_code == 401:
        # Sessão UXT vencida. Não há como renovar sem a senha do gestor — ela só existe
        # no formulário de login —, então limpa e pede novo login.
        print("LOG: Token do gestor expirado (401). Necessário fazer login novamente.")
        clear_session_uxt_token()
    elif r.status_code == 403:
        print(
            "LOG: 403 ao gerar código: a conta do gestor na UXT não tem papel MANAGER. "
            "Verifique se a promoção no cadastro concluiu."
        )
    else:
        print(f"LOG: API UXT não retornou 201. Status: {r.status_code}")

    return None


# ---------------------------------------------------------------------------
# Heatmaps — caminho atual: código -> sessões -> heatmap_summary
#
# `GET /view/heatmap/code/{code}` (usado até aqui) responde 200 com
# `heatmap_images: []` em produção, mesmo declarando `total_interactions` > 0: sucesso
# aparente e tela vazia, sem erro em lugar nenhum. `POST /analysis/heatmap_summary` —
# que é o que a própria interface da UXT consome — devolve, para a mesma sessão, uma
# imagem por página com o calor já renderizado e os hotspots calculados. Daí a troca.
# ---------------------------------------------------------------------------
def fetch_used_codes(code, token: str, timeout: int = 30) -> list:
    """IDs das sessões coletadas sob um código de avaliação.

    A UXT devolve ``{"codigo", "idGestor", "codigos": [[cod_derivado, sessionId], ...]}``
    — cada participante gera um código derivado (``<código>-XXXX``) com a sessão dele.
    """
    response = requests.get(
        f"{USED_CODES_URL}/{code}",
        headers={'Authorization': f'Bearer {token}'},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json() or {}

    session_ids = []
    for entry in (data.get('codigos') or []):
        if isinstance(entry, (list, tuple)) and len(entry) >= 2 and entry[1] is not None:
            session_id = str(entry[1])
            if session_id not in session_ids:
                session_ids.append(session_id)
    return session_ids


def fetch_heatmap_summary(
    session_ids: list,
    token: str,
    grid_rows: int = 4,
    grid_cols: int = 4,
    timeout: int = 120,
) -> dict:
    """Heatmaps renderizados + hotspots por página, para as sessões informadas.

    Resposta: ``{"heatmap_images": [{"url", "image" (base64 com o calor desenhado),
    "total_interactions", "hotspots_count", "top_hotspots": [...]}], "total_interactions",
    "sessions_analyzed", "hotspot_threshold_percent", "grid_configuration"}``.

    A UXT injeta o ``user_id`` do próprio token em cada sessão, então isto só enxerga
    sessões da conta que está chamando — mais uma razão para usar o token do gestor.
    """
    if not session_ids:
        return {}

    response = requests.post(
        HEATMAP_SUMMARY_URL,
        headers={'Authorization': f'Bearer {token}'},
        json={
            "sessions": [{"session_id": str(sid)} for sid in session_ids],
            "grid_rows": grid_rows,
            "grid_cols": grid_cols,
        },
        timeout=timeout,
    )
    response.raise_for_status()  # 201 é o sucesso aqui, não 200
    data = response.json()
    return data if isinstance(data, dict) else {}


def fetch_heatmap_via_api(evaluation_id: int, token: str, timeout: int = 120):
    """Heatmap cru por código — LEGADO, só para ``/api/view_heatmap`` e
    ``/api/heatmap-tasks``, que dependem dos pontos x/y que só este endpoint traz.

    Em produção ele vem devolvendo `heatmap_images: []`, então essas duas rotas (que
    nenhum menu referencia) tendem a aparecer vazias. A aba Hotspots não passa mais por
    aqui — ver `build_scenarios_payload`.
    """
    response = requests.get(
        f'{BASE_URL}/view/heatmap/code/{evaluation_id}',
        headers={'Authorization': f'Bearer {token}'},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
