"""Tests for the gateway request middleware.

Covers the three security/correctness invariants:
- API-key auth gates every non-health request (the gateway exposes order
  placement and account state).
- Request IDs round-trip for traceability.
- The MT5 serialization lock is never leaked (a leak would deadlock the gateway,
  since the MetaTrader5 module is shared single-threaded state).
"""
import base64

import pytest
from flask import Flask

from config import Config
from middleware import DocsAuthMiddleware
from mt5_connection import MT5Connection


def _basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class TestAPIKeyAuth:
    def test_missing_key_rejected(self, client):
        resp = client.post("/order", json={"symbol": "XAUUSD", "volume": 0.1, "type": "BUY"})
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "unauthorized"

    def test_wrong_key_rejected(self, client):
        resp = client.post(
            "/order",
            headers={"X-API-Key": "wrong-key"},
            json={"symbol": "XAUUSD", "volume": 0.1, "type": "BUY"},
        )
        assert resp.status_code == 401

    def test_correct_key_passes_auth(self, client, auth_headers):
        resp = client.post(
            "/order",
            headers=auth_headers,
            json={"symbol": "XAUUSD", "volume": 0.1, "type": "BUY"},
        )
        assert resp.status_code != 401

    def test_health_paths_exempt(self, client):
        for path in ("/health", "/health/ready", "/health/live"):
            resp = client.get(path)
            assert resp.status_code != 401, path

    def test_apidocs_paths_exempt(self, client):
        # The docs and their assets describe the API but expose no account
        # state, so they must be reachable without the X-API-Key header.
        for path in (
            "/apidocs/",
            "/apispec_1.json",
            "/flasgger_static/swagger-ui.css",
        ):
            resp = client.get(path)
            assert resp.status_code != 401, path


class TestDocsAuth:
    DOCS_USER = "docs"
    DOCS_PASSWORD = "s3cret"

    @pytest.fixture
    def docs_client(self):
        app = Flask(__name__)

        @app.route("/apidocs/")
        def apidocs():
            return "docs"

        @app.route("/flasgger_static/<path:_asset>")
        def asset(_asset):
            return "asset"

        @app.route("/order", methods=["POST"])
        def order():
            return "ok"

        @app.route("/health")
        def health():
            return "ok"

        DocsAuthMiddleware(app, self.DOCS_USER, self.DOCS_PASSWORD)
        return app.test_client()

    def test_missing_credentials_challenged(self, docs_client):
        resp = docs_client.get("/apidocs/")
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"].startswith("Basic ")

    def test_wrong_credentials_rejected(self, docs_client):
        resp = docs_client.get("/apidocs/", headers=_basic_auth("docs", "wrong"))
        assert resp.status_code == 401

    def test_correct_credentials_allowed(self, docs_client):
        resp = docs_client.get(
            "/apidocs/", headers=_basic_auth(self.DOCS_USER, self.DOCS_PASSWORD)
        )
        assert resp.status_code == 200

    def test_static_assets_protected(self, docs_client):
        resp = docs_client.get("/flasgger_static/swagger-ui.css")
        assert resp.status_code == 401
        resp = docs_client.get(
            "/flasgger_static/swagger-ui.css",
            headers=_basic_auth(self.DOCS_USER, self.DOCS_PASSWORD),
        )
        assert resp.status_code == 200

    def test_non_docs_paths_untouched(self, docs_client):
        # Docs auth gates only the docs paths; the API key check (a separate
        # middleware) is what guards these.
        assert docs_client.post("/order").status_code == 200
        assert docs_client.get("/health").status_code == 200

    def test_requires_both_credentials(self):
        with pytest.raises(RuntimeError):
            DocsAuthMiddleware(Flask(__name__), "docs", "")


class TestConfigDocsAuth:
    @pytest.fixture
    def _restore_docs_env(self):
        original = (Config.MT5_DOCS_USER, Config.MT5_DOCS_PASSWORD)
        yield
        Config.MT5_DOCS_USER, Config.MT5_DOCS_PASSWORD = original

    def test_both_set_enables_auth(self, _restore_docs_env):
        Config.MT5_DOCS_USER, Config.MT5_DOCS_PASSWORD = "docs", "pw"
        assert Config.docs_auth_enabled()
        Config.validate()

    def test_neither_set_keeps_docs_public(self, _restore_docs_env):
        Config.MT5_DOCS_USER, Config.MT5_DOCS_PASSWORD = "", ""
        assert not Config.docs_auth_enabled()
        Config.validate()

    def test_only_one_set_fails_validation(self, _restore_docs_env):
        Config.MT5_DOCS_USER, Config.MT5_DOCS_PASSWORD = "docs", ""
        with pytest.raises(ValueError):
            Config.validate()


class TestRequestID:
    def test_response_carries_request_id(self, client):
        resp = client.get("/health/live")
        assert resp.headers.get("X-Request-ID")

    def test_supplied_request_id_echoed(self, client):
        resp = client.get("/health/live", headers={"X-Request-ID": "abc-123"})
        assert resp.headers.get("X-Request-ID") == "abc-123"


class TestMT5SerializeLock:
    def test_lock_released_after_authenticated_request(self, client, auth_headers):
        client.post(
            "/order",
            headers=auth_headers,
            json={"symbol": "XAUUSD", "volume": 0.1, "type": "BUY"},
        )
        # If the middleware leaked the lock, this would block forever.
        acquired = MT5Connection.api_lock.acquire(blocking=False)
        assert acquired, "api_lock was not released after the request"
        MT5Connection.api_lock.release()

    def test_lock_not_held_for_exempt_path(self, client):
        client.get("/health/live")
        acquired = MT5Connection.api_lock.acquire(blocking=False)
        assert acquired
        MT5Connection.api_lock.release()

    def test_lock_released_after_rejected_request(self, client):
        # Auth failure returns before the serialize middleware acquires the lock.
        client.post("/order", json={"symbol": "XAUUSD", "volume": 0.1, "type": "BUY"})
        acquired = MT5Connection.api_lock.acquire(blocking=False)
        assert acquired
        MT5Connection.api_lock.release()
