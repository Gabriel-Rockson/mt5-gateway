import logging

import MetaTrader5 as mt5
from flask import g, jsonify

logger = logging.getLogger(__name__)


def _get_request_id():
    return getattr(g, 'request_id', None)


def mt5_error_response(operation, result):
    """
    Build error response for MT5 operation failures.

    Args:
        operation: Description of the operation that failed
        result: MT5 result object from order_send or similar

    Returns:
        tuple: (jsonify response, status_code)
    """
    request_id = _get_request_id()

    error_code, error_str = mt5.last_error()

    is_connection_error = (
        error_code in [10004, 10005, 10006] or
        result.retcode in [10018, 10019, 10020]
    )

    if is_connection_error:
        status_code = 503
        error_type = "connection_error"
    else:
        status_code = 400
        error_type = "mt5_rejected"

    response = {
        "error": f"{operation} failed: {result.comment}",
        "error_type": error_type,
        "mt5_error": {
            "retcode": result.retcode,
            "comment": result.comment,
            "error_code": error_code,
            "error_string": error_str
        }
    }

    if request_id:
        response["request_id"] = request_id

    logger.error(f"MT5 error: {operation}", extra={
        "operation": operation,
        "retcode": result.retcode,
        "error_code": error_code,
        "request_id": request_id
    })

    return jsonify(response), status_code


def internal_error_response(operation, exception):
    """
    Build error response for internal server errors.

    Args:
        operation: Description of what was being attempted
        exception: The exception that occurred

    Returns:
        tuple: (jsonify response, 500)
    """
    request_id = _get_request_id()

    response = {
        "error": "Internal server error",
        "operation": operation,
        "detail": str(exception)
    }

    if request_id:
        response["request_id"] = request_id

    logger.exception(f"Internal error during {operation}", extra={
        "operation": operation,
        "request_id": request_id
    })

    return jsonify(response), 500


def validation_error_response(message, details=None):
    """
    Build error response for request validation failures.

    Args:
        message: Human-readable error message
        details: Optional dict with additional validation error details

    Returns:
        tuple: (jsonify response, 400)
    """
    request_id = _get_request_id()

    response = {
        "error": message,
        "error_type": "validation_error"
    }

    if details:
        response["details"] = details

    if request_id:
        response["request_id"] = request_id

    logger.warning(f"Validation error: {message}", extra={
        "request_id": request_id,
        "details": details
    })

    return jsonify(response), 400


def not_found_response(resource, identifier=None):
    """
    Build error response for resource not found.

    Args:
        resource: Type of resource (e.g., "symbol", "position")
        identifier: Optional identifier of the missing resource

    Returns:
        tuple: (jsonify response, 404)
    """
    request_id = _get_request_id()

    if identifier:
        message = f"{resource.capitalize()} not found: {identifier}"
    else:
        message = f"{resource.capitalize()} not found"

    response = {
        "error": message,
        "error_type": "not_found"
    }

    if request_id:
        response["request_id"] = request_id

    return jsonify(response), 404
