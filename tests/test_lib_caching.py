"""Tests for the lib.py symbol caches and the removal of redundant positions_total.

These lock the IPC-reduction behavior: a symbol's selection state and contract
spec are fetched from MT5 at most once per TTL (and dropped on reconnect via
reset_symbol_caches), and position fetches no longer pay an extra positions_total
call before positions_get.
"""
import lib
from _mt5_fake import Struct


def _position(**overrides):
    base = dict(
        ticket=1,
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


class TestSymbolSelectCache:
    def test_select_cached_within_ttl(self, mt5):
        assert lib.validate_symbol("XAUUSD") is True
        assert lib.validate_symbol("XAUUSD") is True
        # Second call inside the TTL is served from cache — no extra IPC.
        assert mt5.symbol_select.call_count == 1

    def test_select_refetched_after_ttl(self, mt5, monkeypatch):
        clock = {"t": 1000.0}
        monkeypatch.setattr(lib.time, "monotonic", lambda: clock["t"])
        assert lib.validate_symbol("XAUUSD") is True
        assert mt5.symbol_select.call_count == 1
        clock["t"] += lib._SYMBOL_SELECT_TTL_S + 1
        assert lib.validate_symbol("XAUUSD") is True
        assert mt5.symbol_select.call_count == 2

    def test_failed_select_not_cached(self, mt5):
        mt5.symbol_select.return_value = False
        assert lib.validate_symbol("BOGUS") is False
        assert lib.validate_symbol("BOGUS") is False
        # A failed select must retry every call, never be remembered as ok.
        assert mt5.symbol_select.call_count == 2

    def test_distinct_symbols_cached_independently(self, mt5):
        lib.validate_symbol("XAUUSD")
        lib.validate_symbol("EURUSD")
        lib.validate_symbol("XAUUSD")
        assert mt5.symbol_select.call_count == 2

    def test_reset_forces_reselect(self, mt5):
        lib.validate_symbol("XAUUSD")
        lib.reset_symbol_caches()
        lib.validate_symbol("XAUUSD")
        assert mt5.symbol_select.call_count == 2


class TestSymbolInfoCache:
    def test_symbol_info_cached_within_ttl(self, mt5):
        lib.validate_volume("XAUUSD", 0.10)
        lib.validate_volume("XAUUSD", 0.20)
        assert mt5.symbol_info.call_count == 1

    def test_symbol_info_refetched_after_ttl(self, mt5, monkeypatch):
        clock = {"t": 1000.0}
        monkeypatch.setattr(lib.time, "monotonic", lambda: clock["t"])
        lib.validate_volume("XAUUSD", 0.10)
        assert mt5.symbol_info.call_count == 1
        clock["t"] += lib._SYMBOL_INFO_TTL_S + 1
        lib.validate_volume("XAUUSD", 0.10)
        assert mt5.symbol_info.call_count == 2

    def test_none_symbol_info_not_cached(self, mt5):
        mt5.symbol_info.return_value = None
        lib.validate_volume("XAUUSD", 0.10)
        lib.validate_volume("XAUUSD", 0.10)
        # A None result is an error, not a cacheable spec — retry each call.
        assert mt5.symbol_info.call_count == 2

    def test_cache_shared_across_consumers(self, mt5):
        # validate_volume and get_symbol_filling_mode both read symbol_info;
        # the second consumer should hit the cache the first one populated.
        lib.validate_volume("XAUUSD", 0.10)
        lib.get_symbol_filling_mode("XAUUSD")
        assert mt5.symbol_info.call_count == 1

    def test_reset_forces_refetch(self, mt5):
        lib.validate_volume("XAUUSD", 0.10)
        lib.reset_symbol_caches()
        lib.validate_volume("XAUUSD", 0.10)
        assert mt5.symbol_info.call_count == 2


class TestGetPositions:
    def test_no_positions_total_call(self, mt5):
        lib.get_positions()
        assert not mt5.positions_total.called
        assert mt5.positions_get.called

    def test_none_returns_empty_frame(self, mt5):
        mt5.positions_get.return_value = None
        df = lib.get_positions()
        assert df.empty

    def test_empty_returns_columned_frame(self, mt5):
        mt5.positions_get.return_value = []
        df = lib.get_positions()
        assert df.empty
        assert "ticket" in df.columns and "magic" in df.columns

    def test_positions_returned(self, mt5):
        mt5.positions_get.return_value = [_position(ticket=11), _position(ticket=12)]
        df = lib.get_positions()
        assert len(df) == 2
        assert set(df["ticket"]) == {11, 12}

    def test_magic_filter(self, mt5):
        mt5.positions_get.return_value = [
            _position(ticket=11, magic=700001),
            _position(ticket=12, magic=700002),
        ]
        df = lib.get_positions(magic=700002)
        assert len(df) == 1
        assert df.iloc[0]["ticket"] == 12


class TestCloseAllPositions:
    def test_no_positions_total_call_when_none(self, mt5):
        mt5.positions_get.return_value = None
        assert lib.close_all_positions() == []
        assert not mt5.positions_total.called

    def test_no_positions_total_call_when_empty(self, mt5):
        mt5.positions_get.return_value = []
        assert lib.close_all_positions() == []
        assert not mt5.positions_total.called
