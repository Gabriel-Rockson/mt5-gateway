"""Tests for the health endpoints.

The key regression these lock: /health is exempt from the MT5 serialization
middleware (it holds no api_lock), so it MUST NOT call into the non-thread-safe
MetaTrader5 module — doing so races the broker_clock probe thread and in-flight
order_send calls. It must answer from cached connection state only.
"""
from mt5_connection import ConnectionStatus, MT5Connection


class TestHealthDoesNotTouchMT5:
    def test_health_does_not_call_mt5(self, client, mt5):
        resp = client.get("/health")
        assert resp.status_code == 200
        mt5.account_info.assert_not_called()

    def test_health_reports_cached_state(self, client):
        resp = client.get("/health")
        body = resp.get_json()
        assert body["status"] == "healthy"
        assert "mt5_status" in body
        assert "uptime_seconds" in body


class TestReadiness:
    def test_ready_when_connected(self, client, monkeypatch):
        conn = MT5Connection.get_instance()
        monkeypatch.setattr(conn, "is_connected", lambda: True)
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ready"

    def test_not_ready_when_disconnected(self, client, monkeypatch):
        conn = MT5Connection.get_instance()
        monkeypatch.setattr(conn, "is_connected", lambda: False)
        monkeypatch.setattr(conn, "get_status", lambda: ConnectionStatus.DISCONNECTED)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.get_json()["status"] == "not_ready"


class TestLiveness:
    def test_live_always_ok(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "alive"
