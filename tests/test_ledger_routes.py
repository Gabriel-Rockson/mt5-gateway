"""Tests for the trade-ledger read endpoints the live engine reconciles against.

These lock the contract the Go reconciler depends on:
  - /get_positions exposes the POSITION_IDENTIFIER distinctly from the ticket.
  - /history_deals_get returns position_id, profit, swap, commission, entry and
    the (timezone-normalized) time for every deal, with the position filter and
    time-window passed through.
  - /get_deal_from_ticket reflects the round trip (open from the entry deal,
    realized P&L/close from the exit deal) instead of the entry deal alone.
"""
from _mt5_fake import Struct


def _position(**overrides):
    base = dict(
        ticket=500,
        identifier=9001,
        magic=700001,
        symbol="XAUUSD",
        type=0,
        volume=0.10,
        price_open=2000.0,
        price_current=2010.0,
        sl=1990.0,
        tp=2030.0,
        swap=-1.0,
        profit=10.0,
        comment="",
        external_id="",
        reason=0,
        time=1700000000,
        time_msc=1700000000000,
        time_update=1700000100,
        time_update_msc=1700000100000,
    )
    base.update(overrides)
    return Struct(**base)


def _deal(**overrides):
    base = dict(
        ticket=1,
        order=10,
        position_id=9001,
        symbol="XAUUSD",
        type=0,
        entry=0,
        volume=0.10,
        price=2000.0,
        profit=0.0,
        commission=-0.5,
        swap=0.0,
        fee=0.0,
        comment="",
        external_id="",
        reason=0,
        magic=700001,
        time=1700000000,
        time_msc=1700000000000,
    )
    base.update(overrides)
    return Struct(**base)


class TestGetPositions:
    def test_exposes_identifier_distinct_from_ticket(self, client, auth_headers, mt5):
        mt5.positions_get.return_value = [_position(ticket=500, identifier=9001)]

        resp = client.get("/get_positions", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body) == 1
        pos = body[0]
        assert pos["ticket"] == 500
        assert pos["identifier"] == 9001, "POSITION_IDENTIFIER must be surfaced for reconciliation"

    def test_magic_filter_applied(self, client, auth_headers, mt5):
        mt5.positions_get.return_value = [
            _position(ticket=500, identifier=9001, magic=700001),
            _position(ticket=501, identifier=9002, magic=700002),
        ]
        resp = client.get("/get_positions?magic=700002", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert [p["ticket"] for p in body] == [501]


class TestHistoryDealsGet:
    def test_returns_close_fields_and_passes_filters(self, client, auth_headers, mt5):
        mt5.history_deals_get.return_value = [
            _deal(ticket=1, entry=0, profit=0.0),
            _deal(ticket=2, entry=1, profit=42.0, swap=-1.0, commission=-0.5, price=2010.0),
        ]

        resp = client.get(
            "/history_deals_get"
            "?from_date=2023-11-01T00:00:00Z&to_date=2023-12-01T00:00:00Z&position=9001",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body) == 2
        exit_deal = next(d for d in body if d["entry"] == 1)
        assert exit_deal["position_id"] == 9001
        assert exit_deal["profit"] == 42.0
        assert exit_deal["swap"] == -1.0
        assert exit_deal["commission"] == -0.5
        assert "time" in exit_deal

        # The position filter must be forwarded to MT5.
        _, kwargs = mt5.history_deals_get.call_args
        assert kwargs.get("position") == 9001

    def test_rejects_reversed_window(self, client, auth_headers, mt5):
        resp = client.get(
            "/history_deals_get"
            "?from_date=2023-12-01T00:00:00Z&to_date=2023-11-01T00:00:00Z&position=9001",
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestGetDealFromTicket:
    def test_reports_round_trip_not_just_entry_deal(self, client, auth_headers, mt5):
        # Entry deal (profit 0) + exit deal (the realized close).
        mt5.history_deals_get.return_value = [
            _deal(ticket=1, entry=0, profit=0.0, commission=-0.5, price=2000.0, time=1700000000),
            _deal(ticket=2, entry=1, profit=42.0, swap=-1.0, commission=-0.5, price=2010.0, time=1700000200),
        ]

        resp = client.get("/get_deal_from_ticket?ticket=9001", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["open_price"] == 2000.0
        assert body["close_price"] == 2010.0, "close price must come from the exit deal"
        assert body["profit"] == 42.0, "round-trip profit must reflect the exit deal, not the ~0 entry"
        assert body["commission"] == -1.0, "commission summed across the round trip"
        assert body["swap"] == -1.0
        assert body["position_id"] == 9001
