"""Custom exceptions for the bot.

Splitting these out instead of just raising plain Exception/ValueError
everywhere makes it way easier for the CLI to show the right message and
exit code depending on what actually went wrong.
"""


class TradingBotError(Exception):
    """Base class - catch this if you just want to catch anything we raise on purpose."""


class ValidationError(TradingBotError):
    """User typed something wrong (bad symbol, missing price, etc)."""


class BinanceAPIError(TradingBotError):
    """Binance didn't like the request and sent back an error.

    Attributes:
        status_code: the HTTP status code
        binance_code: Binance's own error code (e.g. -1121)
        binance_message: whatever message Binance gave us
    """

    def __init__(self, message, status_code=None, binance_code=None, binance_message=None):
        super().__init__(message)
        self.status_code = status_code
        self.binance_code = binance_code
        self.binance_message = binance_message


class NetworkError(TradingBotError):
    """Couldn't even reach Binance - timeout, no internet, DNS issue, etc."""
