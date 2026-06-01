import logging
import threading
import time

import MetaTrader5 as mt5
from decorators import require_mt5_connection
from errors import internal_error_response
from flasgger import swag_from
from flask import Blueprint, g, jsonify

account_bp = Blueprint('account', __name__)
logger = logging.getLogger(__name__)

# terminal_info().trade_allowed reports the MT5 terminal's local trade permission.
# It almost never changes, yet /account is polled ~1 Hz, so fetching it on every
# request wastes one MT5 IPC call (~5-15ms through Wine) under api_lock. Cache the
# value with a short TTL; a stale-by-30s "trade allowed" flag is low risk — a
# rejected/skipped order self-corrects on the next refresh.
_TERMINAL_TRADE_ALLOWED_TTL_S = 30
_terminal_cache_lock = threading.Lock()
_terminal_trade_allowed = False
_terminal_cache_ts = 0.0


def _get_terminal_trade_allowed() -> bool:
    """Return cached terminal_info().trade_allowed, refreshing past the TTL.

    Callers must already hold MT5Connection.api_lock (the request middleware does)
    so the mt5.terminal_info() refresh is serialized against other MT5 calls.
    """
    global _terminal_trade_allowed, _terminal_cache_ts
    now = time.monotonic()
    with _terminal_cache_lock:
        if now - _terminal_cache_ts < _TERMINAL_TRADE_ALLOWED_TTL_S:
            return _terminal_trade_allowed

    terminal_info = mt5.terminal_info()
    allowed = terminal_info.trade_allowed if terminal_info is not None else False

    with _terminal_cache_lock:
        _terminal_trade_allowed = allowed
        _terminal_cache_ts = now
    return allowed


def reset_terminal_cache():
    """Drop the cached terminal_info().trade_allowed value.

    Called on reconnect (a fresh session may report differently) and between
    tests for isolation.
    """
    global _terminal_trade_allowed, _terminal_cache_ts
    with _terminal_cache_lock:
        _terminal_trade_allowed = False
        _terminal_cache_ts = 0.0

@account_bp.route('/account', methods=['GET'])
@require_mt5_connection
@swag_from({
    'tags': ['Account'],
    'summary': 'Get account information',
    'description': 'Retrieve current account state including balance, equity, margin, and leverage. This is a point-in-time snapshot - values change as positions and market move.',
    'responses': {
        200: {
            'description': 'Account information retrieved successfully.',
            'schema': {
                '$ref': '#/definitions/AccountInfo'
            }
        },
        503: {
            'description': 'MT5 unavailable or failed to get account info.',
            'schema': {
                '$ref': '#/definitions/ErrorResponse'
            }
        }
    }
})
def get_account_info():
    """
    Get Account Information
    ---
    description: Retrieve current account information including balance, equity, margin, and other details.
    """
    try:
        account_info = mt5.account_info()
        if account_info is None:
            request_id = getattr(g, 'request_id', None)
            error_code, error_str = mt5.last_error()

            response = {
                "error": "Failed to get account info",
                "error_type": "connection_error",
                "mt5_error": {
                    "error_code": error_code,
                    "error_string": error_str
                }
            }

            if request_id:
                response["request_id"] = request_id

            logger.error(f"Failed to get account info: {error_str}", extra={
                "error_code": error_code,
                "request_id": request_id
            })

            return jsonify(response), 503

        terminal_trade_allowed = _get_terminal_trade_allowed()

        logger.info(f"Account info retrieved: login={account_info.login}, equity={account_info.equity}, margin_free={account_info.margin_free}, terminal_trade_allowed={terminal_trade_allowed}")

        result = account_info._asdict()
        result["terminal_trade_allowed"] = terminal_trade_allowed
        return jsonify(result)

    except Exception as e:
        return internal_error_response("get_account_info", e)
