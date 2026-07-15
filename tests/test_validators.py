"""Unit tests for bot.validators. No network access required."""

import unittest

from bot.exceptions import ValidationError
from bot.validators import (
    validate_order_params,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
    validate_time_in_force,
)


class TestValidateSymbol(unittest.TestCase):
    def test_accepts_and_normalizes_valid_symbol(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")

    def test_rejects_empty_symbol(self):
        with self.assertRaises(ValidationError):
            validate_symbol("")

    def test_rejects_symbol_with_invalid_characters(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BTC-USDT")


class TestValidateSide(unittest.TestCase):
    def test_accepts_buy_and_sell(self):
        self.assertEqual(validate_side("buy"), "BUY")
        self.assertEqual(validate_side("SELL"), "SELL")

    def test_rejects_invalid_side(self):
        with self.assertRaises(ValidationError):
            validate_side("HOLD")


class TestValidateOrderType(unittest.TestCase):
    def test_accepts_known_types(self):
        for t in ("market", "LIMIT", "Stop_Limit"):
            self.assertIn(validate_order_type(t), {"MARKET", "LIMIT", "STOP_LIMIT"})

    def test_rejects_unknown_type(self):
        with self.assertRaises(ValidationError):
            validate_order_type("OCO")


class TestValidateQuantity(unittest.TestCase):
    def test_accepts_positive_number(self):
        self.assertEqual(validate_quantity("0.01"), 0.01)

    def test_rejects_zero_or_negative(self):
        with self.assertRaises(ValidationError):
            validate_quantity("0")
        with self.assertRaises(ValidationError):
            validate_quantity("-1")

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValidationError):
            validate_quantity("abc")


class TestValidatePrice(unittest.TestCase):
    def test_market_order_ignores_price(self):
        self.assertIsNone(validate_price(None, "MARKET"))

    def test_limit_order_requires_price(self):
        with self.assertRaises(ValidationError):
            validate_price(None, "LIMIT")

    def test_limit_order_accepts_valid_price(self):
        self.assertEqual(validate_price("25000.5", "LIMIT"), 25000.5)


class TestValidateStopPrice(unittest.TestCase):
    def test_non_stop_limit_ignores_stop_price(self):
        self.assertIsNone(validate_stop_price(None, "LIMIT"))

    def test_stop_limit_requires_stop_price(self):
        with self.assertRaises(ValidationError):
            validate_stop_price(None, "STOP_LIMIT")

    def test_stop_limit_accepts_valid_stop_price(self):
        self.assertEqual(validate_stop_price("24000", "STOP_LIMIT"), 24000.0)


class TestValidateTimeInForce(unittest.TestCase):
    def test_defaults_to_gtc(self):
        self.assertEqual(validate_time_in_force(""), "GTC")

    def test_rejects_invalid_value(self):
        with self.assertRaises(ValidationError):
            validate_time_in_force("BAD")


class TestValidateOrderParams(unittest.TestCase):
    def test_full_market_order(self):
        result = validate_order_params("btcusdt", "buy", "market", "0.01")
        self.assertEqual(result["symbol"], "BTCUSDT")
        self.assertIsNone(result["price"])
        self.assertIsNone(result["time_in_force"])

    def test_full_limit_order(self):
        result = validate_order_params(
            "ethusdt", "sell", "limit", "1.5", price="3000", time_in_force="GTC"
        )
        self.assertEqual(result["price"], 3000.0)
        self.assertEqual(result["time_in_force"], "GTC")

    def test_limit_order_missing_price_raises(self):
        with self.assertRaises(ValidationError):
            validate_order_params("ethusdt", "sell", "limit", "1.5")


if __name__ == "__main__":
    unittest.main()
