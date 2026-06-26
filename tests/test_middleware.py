"""Tests for the gateway request middleware.

Covers the three security/correctness invariants:
- API-key auth gates every non-health request (the gateway exposes order
  placement and account state).
- Request IDs round-trip for traceability.
- The MT5 serialization lock is never leaked (a leak would deadlock the gateway,
  since the MetaTrader5 module is shared single-threaded state).
"""
from mt5_connection import MT5Connection


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
