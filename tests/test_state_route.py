"""Tests for GET /state — the coalesced account + positions + orders snapshot.

Locks the response shape (mirrors /account, /get_positions, /orders so mimi can
reuse its structs) and the all-or-nothing contract: any broker read returning
None fails the whole request with 503, and account money fields stay live.
"""
from _mt5_fake import Struct


def state(client, headers):
    return client.get("/state", headers=headers)


def _position(**overrides):
    base = dict(
        ticket=11,
        magic=700001,
        symbol="XAUUSD",
        type=0,
        volume=0.10,
        profit=5.0,
        time=1700000000,
        time_msc=1700000000000,
        time_update=1700000000,
        time_update_msc=1700000000000,
    )
    base.update(overrides)
    return Struct(**base)


def _order(**overrides):
    base = dict(
        ticket=21,
        magic=700001,
        symbol="XAUUSD",
        type=2,  # BUY_LIMIT
        price_open=99.0,
        volume_current=0.10,
        volume_initial=0.10,
        time_setup=1700000000,
        time_setup_msc=1700000000000,
        time_done=0,
        time_done_msc=0,
        time_expiration=0,
    )
    base.update(overrides)
    return Struct(**base)


class TestStateSnapshot:
    def test_success_shape_when_flat(self, client, auth_headers, mt5):
        mt5.positions_get.return_value = []
        mt5.orders_get.return_value = []
        resp = state(client, auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert set(body) == {"account", "positions", "orders"}
        assert body["account"]["login"] == 5000123
        assert body["account"]["terminal_trade_allowed"] is True
        assert body["positions"] == []
        assert body["orders"] == {"total": 0, "orders": []}

    def test_positions_and_orders_included(self, client, auth_headers, mt5):
        mt5.positions_get.return_value = [_position(ticket=11), _position(ticket=12)]
        mt5.orders_get.return_value = [_order(ticket=21)]
        resp = state(client, auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert {p["ticket"] for p in body["positions"]} == {11, 12}
        assert body["orders"]["total"] == 1
        assert body["orders"]["orders"][0]["ticket"] == 21
        # type_str is added just like the standalone /orders endpoint.
        assert "type_str" in body["orders"]["orders"][0]

    def test_account_none_short_circuits_503(self, client, auth_headers, mt5):
        mt5.account_info.return_value = None
        resp = state(client, auth_headers)
        assert resp.status_code == 503
        # Fails before touching positions/orders — true all-or-nothing.
        assert not mt5.positions_get.called
        assert not mt5.orders_get.called

    def test_positions_none_is_503(self, client, auth_headers, mt5):
        mt5.positions_get.return_value = None
        resp = state(client, auth_headers)
        assert resp.status_code == 503
        assert not mt5.orders_get.called

    def test_orders_none_is_503(self, client, auth_headers, mt5):
        mt5.positions_get.return_value = []
        mt5.orders_get.return_value = None
        resp = state(client, auth_headers)
        assert resp.status_code == 503

    def test_requires_api_key(self, client):
        resp = client.get("/state")
        assert resp.status_code == 401
