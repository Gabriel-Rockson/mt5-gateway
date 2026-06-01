"""Unit tests for the gateway's order-validation logic (app/lib.py).

These lock the broker-facing safety checks that stand between the trading engine
and real money. The fake MT5 supplies symbol constraints as data; the assertions
verify the gateway's own decisions.
"""
import lib
import pytest
from _mt5_fake import Struct, fake_mt5

mt5 = fake_mt5


class TestValidateSLTP:
    def test_buy_valid(self):
        assert lib.validate_sl_tp(mt5.ORDER_TYPE_BUY, 100.0, sl=99.0, tp=101.0) == (True, None)

    def test_sell_valid(self):
        assert lib.validate_sl_tp(mt5.ORDER_TYPE_SELL, 100.0, sl=101.0, tp=99.0) == (True, None)

    def test_buy_sl_above_price_rejected(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_BUY, 100.0, sl=101.0, tp=None)
        assert ok is False and "SL must be below" in msg

    def test_buy_tp_below_price_rejected(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_BUY, 100.0, sl=None, tp=99.0)
        assert ok is False and "TP must be above" in msg

    def test_sell_sl_below_price_rejected(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_SELL, 100.0, sl=99.0, tp=None)
        assert ok is False and "SL must be above" in msg

    def test_sell_tp_above_price_rejected(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_SELL, 100.0, sl=None, tp=101.0)
        assert ok is False and "TP must be below" in msg

    def test_non_positive_sl_rejected(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_BUY, 100.0, sl=0.0, tp=None)
        assert ok is False and "Stop loss must be positive" in msg

    def test_non_positive_tp_rejected(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_BUY, 100.0, sl=None, tp=-5.0)
        assert ok is False and "Take profit must be positive" in msg

    def test_both_none_allowed(self):
        assert lib.validate_sl_tp(mt5.ORDER_TYPE_BUY, 100.0, sl=None, tp=None) == (True, None)

    def test_buy_limit_treated_as_buy(self):
        ok, msg = lib.validate_sl_tp(mt5.ORDER_TYPE_BUY_LIMIT, 100.0, sl=101.0, tp=None)
        assert ok is False and "below" in msg


class TestValidateVolume:
    def test_valid_on_step(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(
            volume_min=0.01, volume_max=100.0, volume_step=0.01
        )
        assert lib.validate_volume("XAUUSD", 0.10) == (True, None)

    def test_below_minimum_rejected(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(volume_min=0.10)
        ok, msg = lib.validate_volume("XAUUSD", 0.05)
        assert ok is False and "below minimum" in msg

    def test_above_maximum_rejected(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(volume_max=50.0)
        ok, msg = lib.validate_volume("XAUUSD", 75.0)
        assert ok is False and "exceeds maximum" in msg

    def test_off_step_rejected(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(
            volume_min=0.01, volume_step=0.10
        )
        ok, msg = lib.validate_volume("XAUUSD", 0.15)
        assert ok is False and "steps of" in msg

    def test_symbol_info_none_rejected(self, mt5):
        mt5.symbol_info.return_value = None
        ok, msg = lib.validate_volume("XAUUSD", 0.10)
        assert ok is False and "unavailable" in msg


class TestValidatePendingPrice:
    def test_buy_limit_above_ask_rejected(self, mt5):
        mt5.symbol_info_tick.return_value = lib_struct(bid=100.0, ask=100.10)
        mt5.symbol_info.return_value = mt5.default_symbol_info(trade_freeze_level=0)
        ok, msg = lib.validate_pending_price(mt5.ORDER_TYPE_BUY_LIMIT, "XAUUSD", 100.50)
        assert ok is False and "below current ask" in msg

    def test_sell_limit_below_bid_rejected(self, mt5):
        mt5.symbol_info_tick.return_value = lib_struct(bid=100.0, ask=100.10)
        mt5.symbol_info.return_value = mt5.default_symbol_info(trade_freeze_level=0)
        ok, msg = lib.validate_pending_price(mt5.ORDER_TYPE_SELL_LIMIT, "XAUUSD", 99.0)
        assert ok is False and "above current bid" in msg

    def test_buy_stop_below_ask_rejected(self, mt5):
        mt5.symbol_info_tick.return_value = lib_struct(bid=100.0, ask=100.10)
        mt5.symbol_info.return_value = mt5.default_symbol_info(trade_freeze_level=0)
        ok, msg = lib.validate_pending_price(mt5.ORDER_TYPE_BUY_STOP, "XAUUSD", 100.0)
        assert ok is False and "above current ask" in msg

    def test_within_freeze_level_rejected(self, mt5):
        mt5.symbol_info_tick.return_value = lib_struct(bid=100.0, ask=100.10)
        mt5.symbol_info.return_value = mt5.default_symbol_info(
            trade_freeze_level=100, point=0.01  # freeze band = 1.0
        )
        ok, msg = lib.validate_pending_price(mt5.ORDER_TYPE_BUY_STOP, "XAUUSD", 100.5)
        assert ok is False and "too close to market" in msg.lower()

    def test_valid_buy_stop_accepted(self, mt5):
        mt5.symbol_info_tick.return_value = lib_struct(bid=100.0, ask=100.10)
        mt5.symbol_info.return_value = mt5.default_symbol_info(trade_freeze_level=0)
        assert lib.validate_pending_price(mt5.ORDER_TYPE_BUY_STOP, "XAUUSD", 101.0) == (True, None)

    def test_no_tick_rejected(self, mt5):
        mt5.symbol_info_tick.return_value = None
        ok, msg = lib.validate_pending_price(mt5.ORDER_TYPE_BUY_STOP, "XAUUSD", 101.0)
        assert ok is False and "current price" in msg


class TestValidateTypeFilling:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("FOK", fake_mt5.ORDER_FILLING_FOK),
            ("IOC", fake_mt5.ORDER_FILLING_IOC),
            ("RETURN", fake_mt5.ORDER_FILLING_RETURN),
            ("ioc", fake_mt5.ORDER_FILLING_IOC),
        ],
    )
    def test_string_maps_to_constant(self, name, expected):
        value, err = lib.validate_type_filling(name)
        assert err is None and value == expected

    def test_bad_string_rejected(self):
        value, err = lib.validate_type_filling("BOGUS")
        assert value is None and "Invalid type_filling" in err

    def test_int_passthrough(self):
        assert lib.validate_type_filling(2) == (2, None)

    def test_wrong_type_rejected(self):
        value, err = lib.validate_type_filling(1.5)
        assert value is None and "must be a string" in err


class TestGetTimeframe:
    def test_valid(self):
        assert lib.get_timeframe("H1") == fake_mt5.TIMEFRAME_H1

    def test_lowercase_normalized(self):
        assert lib.get_timeframe("m5") == fake_mt5.TIMEFRAME_M5

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            lib.get_timeframe("X9")


class TestGetSymbolFillingMode:
    def test_ioc_preferred(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(filling_mode=2)
        assert lib.get_symbol_filling_mode("XAUUSD") == mt5.ORDER_FILLING_IOC

    def test_return_when_only_bit4(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(filling_mode=4)
        assert lib.get_symbol_filling_mode("XAUUSD") == mt5.ORDER_FILLING_RETURN

    def test_fok_when_only_bit1(self, mt5):
        mt5.symbol_info.return_value = mt5.default_symbol_info(filling_mode=1)
        assert lib.get_symbol_filling_mode("XAUUSD") == mt5.ORDER_FILLING_FOK

    def test_none_info_returns_return(self, mt5):
        mt5.symbol_info.return_value = None
        assert lib.get_symbol_filling_mode("XAUUSD") == mt5.ORDER_FILLING_RETURN


def lib_struct(**kw):
    return Struct(**kw)
