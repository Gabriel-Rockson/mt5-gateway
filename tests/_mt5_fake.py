"""Fake MetaTrader5 module for tests.

The real MetaTrader5 package is Windows-only and the production app runs under
Wine Python. This fake supplies the integer constants the gateway references at
import time and exposes MT5 functions as MagicMocks tests configure. It is a
singleton so conftest and the test modules share the same object.
"""
from unittest.mock import MagicMock


class Struct:
    """Attribute bag standing in for MT5's namedtuple-like result objects."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def _asdict(self):
        return dict(self.__dict__)


class FakeMT5:
    # Order types
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7
    # Filling modes (FOK is 0, which MT5 rejects — see get_symbol_filling_mode)
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    # Actions
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    # Order lifetime
    ORDER_TIME_GTC = 0
    ORDER_TIME_SPECIFIED = 2
    # Retcodes the order route branches on
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    # Timeframes (values are opaque to the gateway)
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 16385
    TIMEFRAME_H4 = 16388
    TIMEFRAME_D1 = 16408
    TIMEFRAME_W1 = 32769
    TIMEFRAME_MN1 = 49153

    def __init__(self):
        self._dynamic = {}
        self._dynamic_counter = 90000
        self.reset()

    def reset(self):
        """Restore default behavior between tests."""
        self.initialize = MagicMock(return_value=True)
        self.shutdown = MagicMock()
        self.last_error = MagicMock(return_value=(0, "no error"))
        self.account_info = MagicMock(
            return_value=Struct(login=5000123, server="Demo-Server")
        )
        self.symbol_select = MagicMock(return_value=True)
        self.symbol_info = MagicMock(return_value=self.default_symbol_info())
        self.symbol_info_tick = MagicMock(
            return_value=Struct(bid=100.0, ask=100.10, time=0)
        )
        self.order_send = MagicMock(
            return_value=Struct(
                retcode=self.TRADE_RETCODE_DONE,
                comment="Done",
                price=100.10,
                order=111,
                deal=222,
                volume=0.10,
            )
        )
        self.positions_get = MagicMock(return_value=[])
        self.positions_total = MagicMock(return_value=0)
        self.symbols_get = MagicMock(return_value=[])
        self.history_deals_get = MagicMock(return_value=[])
        self.history_orders_get = MagicMock(return_value=[])

    @staticmethod
    def default_symbol_info(**overrides):
        base = dict(
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            point=0.01,
            trade_freeze_level=0,
            filling_mode=2,  # bit 2 set -> IOC supported
        )
        base.update(overrides)
        return Struct(**base)

    def __getattr__(self, name):
        # Reached only for attributes not set above (the description-only
        # TRADE_RETCODE_* table in constants.py). Serve a stable unique int.
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._dynamic:
            self._dynamic_counter += 1
            self._dynamic[name] = self._dynamic_counter
        return self._dynamic[name]


fake_mt5 = FakeMT5()
