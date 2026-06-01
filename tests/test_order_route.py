"""Tests for POST /order — the endpoint that places real money orders.

Locks request validation, the global volume cap, market-price sourcing, and the
broker-result handling that decides success vs rejection.
"""
from _mt5_fake import Struct


def order(client, headers, **body):
    return client.post("/order", headers=headers, json=body)


class TestOrderValidation:
    def test_valid_market_buy_succeeds(self, client, auth_headers, mt5):
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY")
        assert resp.status_code == 200
        assert mt5.order_send.called
        sent = mt5.order_send.call_args.args[0]
        assert sent["action"] == mt5.TRADE_ACTION_DEAL
        assert sent["type"] == mt5.ORDER_TYPE_BUY
        assert sent["volume"] == 0.1
        # Market BUY must use the ask, not a caller-supplied price.
        assert sent["price"] == mt5.symbol_info_tick.return_value.ask

    def test_market_sell_uses_bid(self, client, auth_headers, mt5):
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="SELL")
        assert resp.status_code == 200
        sent = mt5.order_send.call_args.args[0]
        assert sent["price"] == mt5.symbol_info_tick.return_value.bid

    def test_missing_required_field_rejected(self, client, auth_headers, mt5):
        resp = order(client, auth_headers, symbol="XAUUSD", type="BUY")  # no volume
        assert resp.status_code == 400
        assert not mt5.order_send.called

    def test_unknown_order_type_rejected(self, client, auth_headers, mt5):
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="SIDEWAYS")
        assert resp.status_code == 400
        assert not mt5.order_send.called

    def test_non_positive_volume_rejected(self, client, auth_headers, mt5):
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0, type="BUY")
        assert resp.status_code == 400
        assert not mt5.order_send.called

    def test_volume_over_global_cap_rejected(self, client, auth_headers, mt5):
        # MAX_VOLUME_LOTS defaults to 100; ask for more.
        resp = order(client, auth_headers, symbol="XAUUSD", volume=250, type="BUY")
        assert resp.status_code == 400
        assert "global maximum" in resp.get_json()["error"]
        assert not mt5.order_send.called

    def test_unselectable_symbol_rejected(self, client, auth_headers, mt5):
        mt5.symbol_select.return_value = False
        resp = order(client, auth_headers, symbol="BOGUS", volume=0.1, type="BUY")
        assert resp.status_code == 400
        assert not mt5.order_send.called

    def test_invalid_sl_rejected(self, client, auth_headers, mt5):
        # BUY with SL above entry is invalid.
        resp = order(
            client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY", sl=200.0
        )
        assert resp.status_code == 400
        assert not mt5.order_send.called

    def test_no_tick_rejected(self, client, auth_headers, mt5):
        mt5.symbol_info_tick.return_value = None
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY")
        assert resp.status_code == 400
        assert not mt5.order_send.called


class TestBrokerResultHandling:
    def test_order_send_none_is_error(self, client, auth_headers, mt5):
        mt5.order_send.return_value = None
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY")
        assert resp.status_code == 400
        assert "returned None" in resp.get_json()["error"]

    def test_broker_rejection_propagated(self, client, auth_headers, mt5):
        mt5.order_send.return_value = Struct(
            retcode=10013, comment="Invalid request", price=0.0, order=0, deal=0, volume=0.0
        )
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY")
        assert resp.status_code in (400, 503)
        body = resp.get_json()
        assert body["mt5_error"]["retcode"] == 10013

    def test_partial_fill_flagged(self, client, auth_headers, mt5):
        mt5.order_send.return_value = Struct(
            retcode=mt5.TRADE_RETCODE_DONE_PARTIAL,
            comment="Partial",
            price=100.1,
            order=1,
            deal=2,
            volume=0.05,
        )
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY")
        assert resp.status_code == 200
        assert resp.get_json()["partial_fill"] is True


class TestPendingOrders:
    def test_pending_requires_price(self, client, auth_headers, mt5):
        resp = order(client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY_LIMIT")
        assert resp.status_code == 400
        assert not mt5.order_send.called

    def test_valid_buy_limit_placed(self, client, auth_headers, mt5):
        # Default tick bid/ask 100.0/100.10; BUY_LIMIT below ask is valid.
        resp = order(
            client, auth_headers, symbol="XAUUSD", volume=0.1, type="BUY_LIMIT", price=99.0
        )
        assert resp.status_code == 200
        sent = mt5.order_send.call_args.args[0]
        assert sent["action"] == mt5.TRADE_ACTION_PENDING
        assert sent["price"] == 99.0
