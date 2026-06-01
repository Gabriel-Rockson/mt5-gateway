import logging

import MetaTrader5 as mt5
from broker_clock import broker_clock
from constants import ORDER_TYPE_TO_STRING
from decorators import require_mt5_connection
from errors import internal_error_response
from flasgger import swag_from
from flask import Blueprint, g, jsonify

from routes.account import _get_terminal_trade_allowed

state_bp = Blueprint("state", __name__)
logger = logging.getLogger(__name__)


def _connection_error(what):
    request_id = getattr(g, "request_id", None)
    error_code, error_str = mt5.last_error()
    response = {
        "error": f"Failed to get {what}",
        "error_type": "connection_error",
        "mt5_error": {"error_code": error_code, "error_string": error_str},
    }
    if request_id:
        response["request_id"] = request_id
    logger.error(
        f"/state failed to get {what}: {error_str}",
        extra={"error_code": error_code, "request_id": request_id},
    )
    return jsonify(response), 503


@state_bp.route("/state", methods=["GET"])
@require_mt5_connection
@swag_from(
    {
        "tags": ["State"],
        "summary": "Account, positions, and orders in one request",
        "description": (
            "Coalesces /account, /get_positions, and /orders into a single "
            "request so the trading engine's bar-close sync pays one round-trip "
            "and one MT5 lock acquisition instead of three. All-or-nothing: if "
            "any broker read returns no data the whole request fails with 503. "
            "Account money fields (equity, margin, profit) are always live — "
            "never cached — because the drawdown circuit breaker depends on them."
        ),
        "responses": {
            200: {"description": "Snapshot retrieved successfully."},
            503: {"description": "MT5 unavailable or a broker read failed."},
        },
    }
)
def get_state():
    """
    Get Account + Positions + Orders Snapshot
    ---
    description: One consistent view of account, open positions, and pending orders.
    """
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return _connection_error("account info")

        positions = mt5.positions_get()
        if positions is None:
            return _connection_error("positions")

        orders = mt5.orders_get()
        if orders is None:
            return _connection_error("orders")

        account = account_info._asdict()
        account["terminal_trade_allowed"] = _get_terminal_trade_allowed()

        positions_list = [
            broker_clock.normalize_mt5_dict(pos._asdict()) for pos in positions
        ]

        orders_list = []
        for order in orders:
            order_dict = broker_clock.normalize_mt5_dict(order._asdict())
            order_dict["type_str"] = ORDER_TYPE_TO_STRING.get(
                order.type, f"UNKNOWN_{order.type}"
            )
            orders_list.append(order_dict)

        return jsonify(
            {
                "account": account,
                "positions": positions_list,
                "orders": {"total": len(orders_list), "orders": orders_list},
            }
        )

    except Exception as e:
        return internal_error_response("get_state", e)
