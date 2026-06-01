"""Test harness for the MT5 gateway.

The MetaTrader5 package is Windows-only and the production app runs under Wine
Python. To exercise the gateway's business logic on Linux/CI we inject the fake
`MetaTrader5` module (and a no-op `algo_trading_enabler`, which otherwise pulls
in `ctypes.wintypes`) into `sys.modules` before any app module is imported.

Tests assert the gateway's own decisions (validation outcomes, request mapping,
what it does or does not call) — not the fake's configured return values.
"""
import os
import sys
import types
from pathlib import Path

import pytest

from _mt5_fake import fake_mt5

APP_DIR = Path(__file__).resolve().parent.parent / "app"

# Env must be set before importing app modules: broker_clock refuses to start
# without BROKER_TIMEZONE, and Config.validate() requires a >=32 char API key.
os.environ.setdefault("BROKER_TIMEZONE", "UTC")
os.environ.setdefault("MT5_API_KEY", "test-api-key-" + "x" * 32)
os.environ.setdefault("LOG_LEVEL", "WARNING")

TEST_API_KEY = os.environ["MT5_API_KEY"]

# Register fakes before any app module imports them.
sys.modules["MetaTrader5"] = fake_mt5

_fake_enabler = types.ModuleType("algo_trading_enabler")
_fake_enabler.enable_algo_trading = lambda: None
sys.modules["algo_trading_enabler"] = _fake_enabler

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


@pytest.fixture(autouse=True)
def _reset_fake_mt5():
    """Each test starts from clean default MT5 behavior and empty caches."""
    fake_mt5.reset()
    import lib
    from routes.account import reset_terminal_cache

    lib.reset_symbol_caches()
    reset_terminal_cache()
    yield


@pytest.fixture
def mt5():
    """The fake MetaTrader5 module (configure return_value / side_effect on it)."""
    return fake_mt5


@pytest.fixture(scope="session")
def flask_app():
    import app as app_module

    app_module.app.config.update(TESTING=True)
    return app_module.app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}
