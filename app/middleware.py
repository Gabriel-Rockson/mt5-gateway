import hmac
import logging
import uuid

from flask import g, jsonify, request

from mt5_connection import MT5Connection

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

    def after_request(self, response):
        request_id = getattr(g, 'request_id', None)
        if request_id:
            response.headers['X-Request-ID'] = request_id
        return response


# Health probes don't carry the API key — they're called by container
# orchestrators (Docker, k8s) that don't have access to app secrets.
_AUTH_EXEMPT_PATHS = frozenset({
    '/health',
    '/health/ready',
    '/health/live',
})

# The Swagger UI and its spec describe the API but expose no account state or
# trading actions, so they don't need the X-API-Key header — the protection
# belongs on the API routes. The UI page lives under /apidocs/, fetches its
# spec from /apispec_1.json, and loads its assets from /flasgger_static/
# (prefix match). These are instead gated by DocsAuthMiddleware when docs
# credentials are configured.
_DOCS_PREFIXES = (
    '/apidocs',
    '/apispec_1.json',
    '/flasgger_static/',
)


def _is_docs_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _DOCS_PREFIXES)


def _is_auth_exempt(path: str) -> bool:
    return path in _AUTH_EXEMPT_PATHS or _is_docs_path(path)


class APIKeyMiddleware:
    """Enforces a shared-secret X-API-Key header on every request.

    Required because the gateway exposes order placement, position close,
    and account state to anyone who can reach the port. Health probes are
    exempt by exact path match. Constant-time compare avoids timing oracle.
    """

    def __init__(self, app, api_key: str):
        if not api_key:
            raise RuntimeError(
                "APIKeyMiddleware requires a non-empty api_key — set MT5_API_KEY env var"
            )
        self.api_key = api_key
        app.before_request(self.before_request)

    def before_request(self):
        if _is_auth_exempt(request.path):
            return None

        provided = request.headers.get('X-API-Key', '')
        if not hmac.compare_digest(provided, self.api_key):
            request_id = getattr(g, 'request_id', None)
            logger.warning(
                "rejected request: missing or invalid X-API-Key",
                extra={
                    "request_id": request_id,
                    "path": request.path,
                    "method": request.method,
                    "remote_addr": request.remote_addr,
                },
            )
            response = jsonify({"error": "unauthorized", "request_id": request_id})
            response.status_code = 401
            return response
        return None


class DocsAuthMiddleware:
    """Gates the API docs paths behind HTTP Basic auth.

    The docs are exempt from the X-API-Key check (they expose no account state
    or trading actions), but the API surface they describe shouldn't be readable
    by anyone who can reach the port. Basic auth puts a native browser login in
    front of /apidocs, its spec, and its static assets, using credentials
    separate from the API key. Only installed when both docs credentials are
    configured; otherwise the docs stay public.
    """

    _REALM = 'MT5 Gateway API docs'

    def __init__(self, app, username: str, password: str):
        if not username or not password:
            raise RuntimeError(
                "DocsAuthMiddleware requires non-empty username and password"
            )
        self.username = username
        self.password = password
        app.before_request(self.before_request)

    def before_request(self):
        if not _is_docs_path(request.path):
            return None

        auth = request.authorization
        if (
            auth is None
            or auth.type != 'basic'
            or not hmac.compare_digest(auth.username or '', self.username)
            or not hmac.compare_digest(auth.password or '', self.password)
        ):
            return self._challenge()
        return None

    def _challenge(self):
        response = jsonify({"error": "unauthorized"})
        response.status_code = 401
        response.headers['WWW-Authenticate'] = f'Basic realm="{self._REALM}"'
        return response


class MT5SerializeMiddleware:
    """Holds MT5Connection.api_lock for the lifetime of each request handler.

    The MetaTrader5 Python module is not thread-safe and the gateway runs an
    in-process broker_clock probe thread alongside the request handler thread.
    Without serialization, the probe's mt5.symbol_info_tick() can interleave
    with a request's mt5.order_send() and corrupt either's result. Health
    probes and the API docs are exempt — they don't touch MT5.
    """

    def __init__(self, app):
        app.before_request(self.before_request)
        app.teardown_request(self.teardown_request)

    def before_request(self):
        if _is_auth_exempt(request.path):
            return None
        MT5Connection.api_lock.acquire()
        g.mt5_lock_held = True
        return None

    def teardown_request(self, exception=None):  # noqa: ARG002 — Flask signature
        if getattr(g, 'mt5_lock_held', False):
            MT5Connection.api_lock.release()
            g.mt5_lock_held = False
