import time

from broker_clock import broker_clock
from flasgger import swag_from
from flask import Blueprint, jsonify

from mt5_connection import MT5Connection

health_bp = Blueprint('health', __name__)

_start_time = time.time()


@health_bp.route('/health')
@swag_from({
    'tags': ['Health'],
    'responses': {
        200: {
            'description': 'Health check successful',
            'schema': {
                '$ref': '#/definitions/HealthResponse'
            }
        }
    }
})
def health_check():
    """
    Full Health Check
    ---
    description: Comprehensive health check including MT5 connection validation.
    """
    conn = MT5Connection.get_instance()
    uptime = time.time() - _start_time

    # Answer from cached connection state only. /health is exempt from the MT5
    # serialization middleware (it holds no api_lock), so calling into the
    # non-thread-safe MetaTrader5 module here would race the broker_clock probe
    # thread and in-flight order_send calls. The login is cached at connect time.
    response = {
        "status": "healthy",
        "mt5_status": conn.get_status().value,
        "uptime_seconds": round(uptime, 2),
        "mt5_account": conn.get_account_login() if conn.is_connected() else None,
        "last_error": conn.get_last_error(),
    }

    return jsonify(response), 200


@health_bp.route('/health/ready')
@swag_from({
    'tags': ['Health'],
    'responses': {
        200: {
            'description': 'Service is ready',
            'schema': {
                '$ref': '#/definitions/ReadinessResponse'
            }
        },
        503: {
            'description': 'Service not ready (MT5 disconnected)',
            'schema': {
                '$ref': '#/definitions/ReadinessResponse'
            }
        }
    }
})
def ready_check():
    """
    Readiness Check
    ---
    description: Kubernetes-style readiness probe. Returns 503 if MT5 is unavailable.
    """
    conn = MT5Connection.get_instance()

    if conn.is_connected():
        return jsonify({
            "status": "ready",
            "mt5_status": conn.get_status().value
        }), 200
    else:
        return jsonify({
            "status": "not_ready",
            "mt5_status": conn.get_status().value,
            "error": conn.get_last_error()
        }), 503


@health_bp.route('/broker_clock')
@swag_from({
    'tags': ['Health'],
    'responses': {
        200: {
            'description': 'Broker server clock state — the IANA timezone the gateway has '
                           'identified for the broker server, and the corresponding signed '
                           'UTC offset (seconds) at the current moment. Downstream consumers '
                           "use this to know what 'Server time' means for this gateway."
        }
    }
})
def broker_clock_info():
    """
    Broker Clock State
    ---
    description: Returns the broker server's IANA timezone and current UTC offset.
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    tz_name = broker_clock.timezone
    if tz_name == "UTC":
        offset = 0
    else:
        off = ZoneInfo(tz_name).utcoffset(datetime.now(tz=timezone.utc))
        offset = int(off.total_seconds()) if off is not None else 0
    return jsonify({
        "timezone": tz_name,
        "offset_seconds": offset,
    }), 200


@health_bp.route('/health/live')
@swag_from({
    'tags': ['Health'],
    'responses': {
        200: {
            'description': 'Service is alive',
            'schema': {
                '$ref': '#/definitions/LivenessResponse'
            }
        }
    }
})
def liveness_check():
    """
    Liveness Check
    ---
    description: Kubernetes-style liveness probe. Always returns 200 if process is running.
    """
    return jsonify({"status": "alive"}), 200