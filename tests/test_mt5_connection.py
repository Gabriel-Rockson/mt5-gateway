"""Tests for MT5Connection's reconnect cooldown.

Without a cooldown, every request that arrives while MT5 is disconnected
triggers its own full multi-attempt initialize() sequence — each attempt can
block a waitress worker thread for up to ~60s. Enough concurrent requests
exhausts the whole thread pool, starving even /health/live (which never
touches MT5) of a free thread to run on. These tests lock in that a failed
initialize() sequence is followed by a cooldown window where ensure_connection()
fails fast instead of retrying.
"""
import time

from mt5_connection import MT5Connection


class TestReconnectCooldown:
    def test_does_not_retry_within_cooldown_after_a_failed_attempt(self, mt5, monkeypatch):
        conn = MT5Connection.get_instance()
        monkeypatch.setattr(conn, "is_connected", lambda: False)
        monkeypatch.setattr(conn, "_reconnect_cooldown", 30.0)
        monkeypatch.setattr(conn, "_last_initialize_attempt", time.monotonic())

        mt5.initialize.reset_mock()
        result = conn.ensure_connection()

        assert result is False
        mt5.initialize.assert_not_called()

    def test_retries_again_once_the_cooldown_elapses(self, mt5, monkeypatch):
        conn = MT5Connection.get_instance()
        monkeypatch.setattr(conn, "is_connected", lambda: False)
        monkeypatch.setattr(conn, "_reconnect_cooldown", 30.0)
        monkeypatch.setattr(conn, "_last_initialize_attempt", time.monotonic() - 31.0)
        mt5.initialize.return_value = True

        result = conn.ensure_connection()

        assert result is True
        mt5.initialize.assert_called()

    def test_a_failed_initialize_sequence_starts_the_cooldown(self, mt5, monkeypatch):
        conn = MT5Connection.get_instance()
        monkeypatch.setattr(conn, "_max_reconnect_attempts", 1)
        monkeypatch.setattr(conn, "_base_delay", 0.01)
        monkeypatch.setattr(conn, "_last_initialize_attempt", 0.0)
        mt5.initialize.return_value = False
        mt5.last_error.return_value = (-10004, "No IPC connection")

        before = time.monotonic()
        result = conn.initialize()

        assert result is False
        assert conn._last_initialize_attempt >= before

    def test_a_successful_initialize_does_not_need_the_cooldown(self, mt5, monkeypatch):
        conn = MT5Connection.get_instance()
        monkeypatch.setattr(conn, "_last_initialize_attempt", time.monotonic())
        mt5.initialize.return_value = True

        result = conn.initialize()

        assert result is True
        assert conn.is_connected()
