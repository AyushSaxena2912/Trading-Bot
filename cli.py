#!/usr/bin/env python3
"""CLI entry point for the trading bot.

Two ways to run it:

1. Pass flags directly, good for scripting:

    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

2. Just run it with no flags and it drops into an interactive prompt:

    python cli.py
"""

import argparse
import os
import sys

from bot.client import DEFAULT_BASE_URL, BinanceFuturesClient
from bot.exceptions import BinanceAPIError, NetworkError, TradingBotError, ValidationError
from bot.logging_config import get_logger
from bot.orders import OrderManager
from bot.validators import (
    VALID_ORDER_TYPES,
    VALID_SIDES,
    VALID_TIME_IN_FORCE,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", choices=sorted(VALID_SIDES), help="BUY or SELL")
    parser.add_argument(
        "--type",
        dest="order_type",
        choices=sorted(VALID_ORDER_TYPES),
        help="MARKET, LIMIT, or STOP_LIMIT",
    )
    parser.add_argument("--quantity", help="Order quantity, e.g. 0.01")
    parser.add_argument("--price", help="Limit price (required for LIMIT / STOP_LIMIT)")
    parser.add_argument(
        "--stop-price", dest="stop_price", help="Stop trigger price (required for STOP_LIMIT)"
    )
    parser.add_argument(
        "--time-in-force",
        dest="time_in_force",
        default="GTC",
        choices=sorted(VALID_TIME_IN_FORCE),
        help="Time in force for LIMIT/STOP_LIMIT orders (default: GTC)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BINANCE_BASE_URL", DEFAULT_BASE_URL),
        help=f"Futures API base URL (default: {DEFAULT_BASE_URL})",
    )
    return parser


def _print_summary(title: str, rows: dict) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in rows.items():
        if value is None:
            continue
        print(f"  {key}: {value}")


def print_request_summary(symbol, side, order_type, quantity, price, stop_price, time_in_force):
    _print_summary(
        "Order Request",
        {
            "Symbol": symbol,
            "Side": side,
            "Type": order_type,
            "Quantity": quantity,
            "Price": price,
            "Stop Price": stop_price,
            "Time In Force": time_in_force if order_type != "MARKET" else None,
        },
    )


def print_response_summary(result: dict) -> None:
    summary = result["summary"]
    _print_summary(
        "Order Response",
        {
            "Order ID": summary.get("orderId") or summary.get("algoId"),
            "Status": summary.get("status") or summary.get("algoStatus"),
            "Executed Qty": summary.get("executedQty"),
            "Avg Price": summary.get("avgPrice"),
            "Price": summary.get("price"),
            "Stop Price": summary.get("stopPrice") or summary.get("triggerPrice"),
            "Time In Force": summary.get("timeInForce"),
        },
    )


def get_credentials() -> tuple:
    api_key = os.environ.get("BINANCE_API_KEY")
    api_secret = os.environ.get("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        print(
            "ERROR: Missing credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
            "as environment variables (or in a .env file). See .env.example.",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key, api_secret


def run_order(args) -> int:
    """Validates and places one order based on args, returns an exit code."""
    try:
        symbol = validate_symbol(args.symbol)
        side = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity = validate_quantity(args.quantity)
        price = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValidationError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        logger.warning("Validation failed: %s", exc)
        return 2

    api_key, api_secret = get_credentials()

    print_request_summary(
        symbol, side, order_type, quantity, price, stop_price, args.time_in_force
    )

    try:
        client = BinanceFuturesClient(api_key, api_secret, base_url=args.base_url)
        manager = OrderManager(client)
        result = manager.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        print(f"\nFAILED: Invalid input - {exc}", file=sys.stderr)
        return 2
    except BinanceAPIError as exc:
        print(f"\nFAILED: Binance rejected the order - {exc}", file=sys.stderr)
        return 3
    except NetworkError as exc:
        print(f"\nFAILED: Network error - {exc}", file=sys.stderr)
        return 4
    except TradingBotError as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        return 1

    print_response_summary(result)
    print("\nSUCCESS: Order placed on Binance Futures Testnet.")
    return 0


# -- Interactive mode, keeps asking until you give it valid input ---------


def _prompt(label, validator, *validator_args):
    """Keeps asking until the input passes validation."""
    while True:
        raw = input(f"{label}: ").strip()
        try:
            return validator(raw, *validator_args) if validator_args else validator(raw)
        except ValidationError as exc:
            print(f"  -> {exc} Try again.")


def interactive_mode(default_base_url: str) -> int:
    print("=" * 60)
    print(" Simplified Trading Bot - Binance Futures Testnet")
    print("=" * 60)
    print("Interactive mode. Press Ctrl+C at any time to cancel.\n")

    try:
        symbol = _prompt("Symbol (e.g. BTCUSDT)", validate_symbol)
        side = _prompt(f"Side {sorted(VALID_SIDES)}", validate_side)
        order_type = _prompt(f"Order type {sorted(VALID_ORDER_TYPES)}", validate_order_type)
        quantity = _prompt("Quantity", validate_quantity)

        price = None
        stop_price = None
        time_in_force = "GTC"
        if order_type in ("LIMIT", "STOP_LIMIT"):
            price = _prompt("Price", validate_price, order_type)
            time_in_force = _prompt(
                f"Time in force {sorted(VALID_TIME_IN_FORCE)} [GTC]", _optional_tif
            )
        if order_type == "STOP_LIMIT":
            stop_price = _prompt("Stop price", validate_stop_price, order_type)

        confirm = input("\nSubmit this order to the testnet? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130

    class _Args:
        pass

    args = _Args()
    args.symbol = symbol
    args.side = side
    args.order_type = order_type
    args.quantity = quantity
    args.price = price
    args.stop_price = stop_price
    args.time_in_force = time_in_force
    args.base_url = default_base_url
    return run_order(args)


def _optional_tif(raw):
    if not raw:
        return "GTC"
    from bot.validators import validate_time_in_force

    return validate_time_in_force(raw)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    has_order_args = any([args.symbol, args.side, args.order_type, args.quantity])

    if not has_order_args:
        return interactive_mode(args.base_url)

    missing = [
        name
        for name, value in (
            ("--symbol", args.symbol),
            ("--side", args.side),
            ("--type", args.order_type),
            ("--quantity", args.quantity),
        )
        if not value
    ]
    if missing:
        parser.error(f"Missing required argument(s): {', '.join(missing)}")

    return run_order(args)


if __name__ == "__main__":
    sys.exit(main())
