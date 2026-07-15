"""Wrapper around the Binance Futures (USDT-M) REST API.

Basically all the HTTP + signing stuff lives here so the rest of the app
(orders.py, cli.py) doesn't have to care about it. If Binance ever changes
something on their end, this is the only file that should need edits.
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .exceptions import BinanceAPIError, NetworkError
from .logging_config import get_logger

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
DEFAULT_RECV_WINDOW = 5000
MAX_LOGGED_BODY_CHARS = 2000  # /account returns a huge blob, don't dump all of it in the log

logger = get_logger()


class BinanceFuturesClient:
    """Small signed REST client for Binance USDT-M Futures.

    Points at the Futures Testnet by default. If you need to hit a
    different host (prod, or Binance's other demo host
    demo-fapi.binance.com), just pass base_url - nothing else changes.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ):
        if not api_key or not api_secret:
            raise BinanceAPIError(
                "Missing API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
                "(see .env.example)."
            )
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.recv_window = recv_window
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})

    # -- low level stuff -----------------------------------------------

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params)
        signature = hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256)
        return signature.hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = dict(params or {})
        url = f"{self.base_url}{path}"

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(params)

        logger.debug(
            "API request -> %s %s | params=%s",
            method,
            url,
            _redact(params),
        )

        try:
            response = self._session.request(
                method, url, params=params, timeout=self.timeout
            )
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout calling %s %s: %s", method, url, exc)
            raise NetworkError(f"Request to Binance timed out after {self.timeout}s.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network/connection error calling %s %s: %s", method, url, exc)
            raise NetworkError(
                "Could not connect to Binance Futures Testnet. Check your internet "
                "connection and the base URL."
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error calling %s %s: %s", method, url, exc)
            raise NetworkError(f"Unexpected network error: {exc}") from exc

        logger.debug(
            "API response <- %s %s | status=%s body=%s",
            method,
            url,
            response.status_code,
            _truncate(response.text),
        )

        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: requests.Response) -> Dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.ok:
            return payload

        binance_code = payload.get("code")
        binance_message = payload.get("msg", response.text)
        logger.error(
            "Binance API error: http_status=%s code=%s msg=%s",
            response.status_code,
            binance_code,
            binance_message,
        )
        raise BinanceAPIError(
            f"Binance API error {binance_code}: {binance_message}",
            status_code=response.status_code,
            binance_code=binance_code,
            binance_message=binance_message,
        )

    # -- public endpoints (no auth needed) -------------------------------

    def ping(self) -> Dict[str, Any]:
        """Just hits the ping endpoint, useful for checking connectivity."""
        return self._request("GET", "/fapi/v1/ping")

    def get_exchange_info(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    # -- signed endpoints (need api key + secret) ------------------------

    def get_account(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def new_order(self, **params: Any) -> Dict[str, Any]:
        """Places a regular order via POST /fapi/v1/order.

        We drop any None values before sending so callers (orders.py) can
        just pass every field they have and not worry about which ones
        apply to MARKET vs LIMIT.
        """
        clean_params = {k: v for k, v in params.items() if v is not None}
        return self._request("POST", "/fapi/v1/order", params=clean_params, signed=True)

    def new_algo_order(self, **params: Any) -> Dict[str, Any]:
        """Places a conditional order (STOP, TAKE_PROFIT, etc).

        Binance moved these order types to a separate Algo Order endpoint
        in Dec 2025 - hitting the regular /fapi/v1/order endpoint with a
        STOP type now just gives you back error -4120. Found this out the
        hard way while testing, so routing it here instead.
        """
        clean_params = {k: v for k, v in params.items() if v is not None}
        clean_params.setdefault("algoType", "CONDITIONAL")
        return self._request("POST", "/fapi/v1/algoOrder", params=clean_params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )


def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Makes a copy of the params with the signature blanked out, for logging."""
    redacted = dict(params)
    if "signature" in redacted:
        redacted["signature"] = "***REDACTED***"
    return redacted


def _truncate(text: str, limit: int = MAX_LOGGED_BODY_CHARS) -> str:
    """Some responses (looking at you, /account) are massive - trim them for the log file."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... (truncated, {len(text)} chars total)"
