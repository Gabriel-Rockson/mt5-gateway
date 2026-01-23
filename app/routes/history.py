import logging
from datetime import datetime

import MetaTrader5 as mt5
from decorators import require_mt5_connection
from errors import (
    internal_error_response,
    not_found_response,
    validation_error_response,
)
from flasgger import swag_from
from flask import Blueprint, jsonify, request
from lib import get_deal_from_ticket, get_order_from_ticket

history_bp = Blueprint("history", __name__)
logger = logging.getLogger(__name__)


@history_bp.route("/get_deal_from_ticket", methods=["GET"])
@require_mt5_connection
@swag_from(
    {
        "tags": ["History"],
        "parameters": [
            {
                "name": "ticket",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "Position ticket number to retrieve deal information.",
            }
        ],
        "responses": {
            200: {
                "description": "Deal information retrieved successfully.",
                "schema": {"$ref": "#/definitions/DealInfo"},
            },
            400: {"description": "Invalid ticket format."},
            404: {"description": "Failed to get deal information."},
            500: {"description": "Internal server error."},
        },
    }
)
def get_deal_from_ticket_endpoint():
    """
    Get Deal Information from Position Ticket
    ---
    description: Retrieve deal information associated with a specific position ticket number.
    """
    try:
        ticket = request.args.get("ticket")
        if not ticket:
            return validation_error_response("Ticket parameter is required")

        try:
            ticket = int(ticket)
        except ValueError:
            return validation_error_response("Invalid ticket format")

        deal = get_deal_from_ticket(ticket)
        if deal is None:
            return not_found_response("deal", ticket)

        return jsonify(deal)

    except Exception as e:
        return internal_error_response("get_deal_from_ticket", e)


@history_bp.route("/get_order_from_ticket", methods=["GET"])
@require_mt5_connection
@swag_from(
    {
        "tags": ["History"],
        "parameters": [
            {
                "name": "ticket",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "Ticket number to retrieve order information.",
            }
        ],
        "responses": {
            200: {
                "description": "Order information retrieved successfully.",
                "schema": {"$ref": "#/definitions/HistoryOrder"},
            },
            400: {"description": "Invalid ticket format."},
            404: {"description": "Failed to get order information."},
            500: {"description": "Internal server error."},
        },
    }
)
def get_order_from_ticket_endpoint():
    """
    Get Order Information from Ticket
    ---
    description: Retrieve order information associated with a specific ticket number.
    """
    try:
        ticket = request.args.get("ticket")
        if not ticket:
            return validation_error_response("Ticket parameter is required")

        try:
            ticket = int(ticket)
        except ValueError:
            return validation_error_response("Invalid ticket format")

        order = get_order_from_ticket(ticket)
        if order is None:
            return not_found_response("order", ticket)

        return jsonify(order)

    except Exception as e:
        return internal_error_response("get_order_from_ticket", e)


@history_bp.route("/history_deals_get", methods=["GET"])
@require_mt5_connection
@swag_from(
    {
        "tags": ["History"],
        "parameters": [
            {
                "name": "from_date",
                "in": "query",
                "type": "string",
                "required": True,
                "format": "date-time",
                "description": "Start date in ISO format.",
            },
            {
                "name": "to_date",
                "in": "query",
                "type": "string",
                "required": True,
                "format": "date-time",
                "description": "End date in ISO format.",
            },
            {
                "name": "position",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "Position number to filter deals.",
            },
        ],
        "responses": {
            200: {
                "description": "Deals history retrieved successfully.",
                "schema": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/DealInfo"},
                },
            },
            400: {"description": "Invalid parameter format or missing parameters."},
            404: {"description": "Failed to get deals history."},
            500: {"description": "Internal server error."},
        },
    }
)
def history_deals_get_endpoint():
    """
    Get Deals History
    ---
    description: Retrieve historical deals within a specified date range for a particular position.
    """
    try:
        from_date = request.args.get("from_date")
        to_date = request.args.get("to_date")
        position = request.args.get("position")

        if not all([from_date, to_date, position]):
            return validation_error_response(
                "from_date, to_date, and position parameters are required"
            )

        try:
            from_date = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            to_date = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            position = int(position)
        except ValueError as e:
            return validation_error_response(f"Invalid parameter format: {str(e)}")

        if from_date >= to_date:
            return validation_error_response("from_date must be before to_date")

        from_timestamp = int(from_date.timestamp())
        to_timestamp = int(to_date.timestamp())
        deals = mt5.history_deals_get(from_timestamp, to_timestamp, position=position)

        if deals is None:
            return not_found_response("deals history", position)

        deals_list = [deal._asdict() for deal in deals]
        return jsonify(deals_list)

    except Exception as e:
        return internal_error_response("history_deals_get", e)


@history_bp.route("/history_orders_get", methods=["GET"])
@require_mt5_connection
@swag_from(
    {
        "tags": ["History"],
        "parameters": [
            {
                "name": "ticket",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "Ticket number to retrieve orders history.",
            }
        ],
        "responses": {
            200: {
                "description": "Orders history retrieved successfully.",
                "schema": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/HistoryOrder"},
                },
            },
            400: {"description": "Invalid ticket format or missing parameter."},
            404: {"description": "Failed to get orders history."},
            500: {"description": "Internal server error."},
        },
    }
)
def history_orders_get_endpoint():
    """
    Get Orders History
    ---
    description: Retrieve historical orders associated with a specific ticket number.
    """
    try:
        ticket = request.args.get("ticket")
        if not ticket:
            return validation_error_response("Ticket parameter is required")

        try:
            ticket = int(ticket)
        except ValueError:
            return validation_error_response("Invalid ticket format")

        orders = mt5.history_orders_get(ticket=ticket)
        if orders is None:
            return not_found_response("orders history", ticket)

        orders_list = [order._asdict() for order in orders]
        return jsonify(orders_list)

    except Exception as e:
        return internal_error_response("history_orders_get", e)

