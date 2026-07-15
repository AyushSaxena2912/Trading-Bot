"""Order placement logic - this is the glue between the CLI and the API client.

Takes whatever the user typed in, validates it, figures out which Binance
endpoint/params to use, and hands back a simple dict the CLI can print.
"""

from typing import Any, Dict

from .client import BinanceFuturesClient
from .exceptions import BinanceAPIError, NetworkError
from .logging_config import get_logger
from .validators import validate_order_params

logger = get_logger()

# our CLI names -> what Binance actually calls the order type
_ORDER_TYPE_MAP = {
    "MARKET": "MARKET",
    "LIMIT": "LIMIT",
    "STOP_LIMIT": "STOP",  # this is Binance's price+stopPrice stop order
}

# STOP_LIMIT has to go through the newer Algo Order endpoint now (Binance
# migrated conditional orders there in Dec 2025), otherwise you get -4120.
_ALGO_ORDER_TYPES = {"STOP_LIMIT"}

_RESULT_FIELDS = [
    "orderId",
    "algoId",
    "symbol",
    "status",
    "algoStatus",
    "side",
    "type",
    "origQty",
    "executedQty",
    "avgPrice",
    "price",
    "stopPrice",
    "triggerPrice",
    "timeInForce",
    "updateTime",
]


class OrderManager:
    """Handles placing orders on Binance Futures (Testnet by default)."""

    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity,
        price=None,
        stop_price=None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """Validates everything, sends the order, and returns the result.

        Returns a dict with `request` (what got sent), `response` (raw
        Binance reply), and `summary` (just the fields the CLI cares about
        printing). Can raise ValidationError / BinanceAPIError / NetworkError.
        """
        params = validate_order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )

        binance_type = _ORDER_TYPE_MAP[params["order_type"]]
        is_algo = params["order_type"] in _ALGO_ORDER_TYPES

        request_payload = {
            "symbol": params["symbol"],
            "side": params["side"],
            "type": binance_type,
            "quantity": params["quantity"],
            "price": params["price"],
            "timeInForce": params["time_in_force"],
        }
        if is_algo:
            # algoOrder calls it triggerPrice instead of stopPrice, no idea why
            request_payload["triggerPrice"] = params["stop_price"]
        else:
            request_payload["stopPrice"] = params["stop_price"]

        logger.info(
            "Placing order: symbol=%s side=%s type=%s quantity=%s price=%s stop_price=%s "
            "(via %s endpoint)",
            params["symbol"],
            params["side"],
            params["order_type"],
            params["quantity"],
            params["price"],
            params["stop_price"],
            "algoOrder" if is_algo else "order",
        )

        try:
            if is_algo:
                response = self.client.new_algo_order(**request_payload)
            else:
                response = self.client.new_order(**request_payload)
        except (BinanceAPIError, NetworkError):
            logger.exception("Order placement failed for %s", params["symbol"])
            raise

        logger.info(
            "Order accepted: orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId") or response.get("algoId"),
            response.get("status") or response.get("algoStatus"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )

        summary = {field: response.get(field) for field in _RESULT_FIELDS}

        return {
            "request": {**request_payload, "orderTypeRequested": params["order_type"]},
            "response": response,
            "summary": summary,
        }

    def place_market_order(self, symbol: str, side: str, quantity) -> Dict[str, Any]:
        return self.place_order(symbol=symbol, side=side, order_type="MARKET", quantity=quantity)

    def place_limit_order(
        self, symbol: str, side: str, quantity, price, time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
        )

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity,
        price,
        stop_price,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type="STOP_LIMIT",
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )
