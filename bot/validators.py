"""Input validation for order parameters.

Checking everything here before we ever hit the network means bad input
fails fast with an actual useful message, instead of wasting an API call
and getting back some cryptic Binance error code.
"""

import re
from typing import Optional

from .exceptions import ValidationError

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK"}

_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


def validate_symbol(symbol: str) -> str:
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not _SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected an uppercase alphanumeric "
            "trading pair, e.g. BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side or not isinstance(side, str):
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type or not isinstance(order_type, str):
        raise ValidationError("Order type is required (MARKET, LIMIT or STOP_LIMIT).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {quantity}.")
    return quantity


def validate_price(price, order_type: str) -> Optional[float]:
    """Required for LIMIT/STOP_LIMIT, doesn't matter for MARKET."""
    if order_type == "MARKET":
        return None

    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError(f"Price must be greater than 0, got {price}.")
    return price


def validate_stop_price(stop_price, order_type: str) -> Optional[float]:
    """Only STOP_LIMIT needs this one."""
    if order_type != "STOP_LIMIT":
        return None

    if stop_price is None:
        raise ValidationError("Stop price is required for STOP_LIMIT orders.")
    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'.")
    if stop_price <= 0:
        raise ValidationError(f"Stop price must be greater than 0, got {stop_price}.")
    return stop_price


def validate_time_in_force(time_in_force: str) -> str:
    if not time_in_force:
        return "GTC"
    time_in_force = time_in_force.strip().upper()
    if time_in_force not in VALID_TIME_IN_FORCE:
        raise ValidationError(
            f"Invalid time in force '{time_in_force}'. Must be one of "
            f"{sorted(VALID_TIME_IN_FORCE)}."
        )
    return time_in_force


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    stop_price=None,
    time_in_force: str = "GTC",
) -> dict:
    """Runs all the individual validators and returns the cleaned-up values.

    Stops at whichever check fails first and raises ValidationError.
    """
    order_type = validate_order_type(order_type)
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": order_type,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
        "stop_price": validate_stop_price(stop_price, order_type),
        "time_in_force": validate_time_in_force(time_in_force) if order_type != "MARKET" else None,
    }
