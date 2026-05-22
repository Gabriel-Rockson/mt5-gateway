import hmac
import logging
import uuid

from flask import g, jsonify, request

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
        if request.path in _AUTH_EXEMPT_PATHS:
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
