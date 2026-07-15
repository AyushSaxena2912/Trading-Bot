# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

This is a small Python CLI tool that places MARKET and LIMIT orders on the
Binance Futures Testnet (USDT-M). Built for the "Simplified Trading Bot"
assignment.

## What it does

- Places MARKET and LIMIT orders, both BUY and SELL.
- Bonus: also supports a third order type, STOP_LIMIT.
- Bonus: has an interactive mode (just run `python cli.py` with no flags)
  in addition to the normal `--flag` style usage.
- Validates all input (symbol, side, quantity, price, etc.) before making
  any API call, so you get a clear error message instead of a random
  Binance error code.
- Logs every request/response/error to `logs/trading_bot.log`.

## Project structure

```
trading_bot/
  bot/
    __init__.py
    client.py           # talks to Binance (signing requests, sending them)
    orders.py            # order placement logic
    validators.py        # checks user input before we call the API
    logging_config.py    # sets up the log file + console logging
    exceptions.py         # custom exception types
  tests/
    test_validators.py   # unit tests for validators.py
  cli.py                 # the actual CLI you run
  logs/
    trading_bot.log       # gets created when you run the bot
  requirements.txt
  .env.example
  README.md
```

This basically follows the structure suggested in the assignment, just with
a couple of extra files (`exceptions.py`, `tests/`) that made the code
easier to work with.

## Setup

### 1. Get a Binance Futures Testnet account + API key

1. Go to `testnet.binancefuture.com` and log in with GitHub or Google (you
   don't need a real Binance account for this).
2. You'll probably get redirected to a page that says "Demo Trading" —
   that's the same thing, Binance just renamed the UI for it at some point.
   Click through to start demo trading.
3. Find API Management (usually under the account icon) and create a new
   API key. Pick "System generated" when it asks (that's the normal
   HMAC key/secret pair, not the RSA/Ed25519 option).
4. Copy the API Key and Secret Key somewhere safe — the secret is only
   shown once.

Your testnet account comes with a chunk of fake USDT (a few thousand) to
trade with, so no real money is ever involved.

Note: I noticed the API also works fine on `demo-fapi.binance.com`, which
seems to be where Binance is slowly moving this. This bot defaults to the
URL given in the assignment (`testnet.binancefuture.com`), but you can
switch it via `BINANCE_BASE_URL` in your `.env` if that one ever stops
working.

### 2. Install dependencies

```bash
cd trading_bot
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add your API keys

```bash
cp .env.example .env
```

Then open `.env` and paste in your key/secret:

```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

## Running it

**Market order:**

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

**Limit order:**

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 60000
```

**Stop-limit order (bonus):**

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.01 --price 58000 --stop-price 58500
```

There's also `--time-in-force` (GTC/IOC/FOK, defaults to GTC) and
`--base-url` if you want to override the API host.

**Interactive mode** — just run it without any flags and it'll walk you
through it step by step:

```bash
python cli.py
```

```
============================================================
 Simplified Trading Bot - Binance Futures Testnet
============================================================
Interactive mode. Press Ctrl+C at any time to cancel.

Symbol (e.g. BTCUSDT): btcusdt
Side ['BUY', 'SELL']: buy
Order type ['LIMIT', 'MARKET', 'STOP_LIMIT']: market
Quantity: 0.01

Submit this order to the testnet? [y/N]: y
```

### Example output

This is actual output from a market order I placed while testing this:

```
Order Request
-------------
  Symbol: BTCUSDT
  Side: BUY
  Type: MARKET
  Quantity: 0.01

Order Response
--------------
  Order ID: 21859761148
  Status: NEW
  Executed Qty: 0.0000
  Price: 0.00
  Stop Price: 0.00
  Time In Force: GTC

SUCCESS: Order placed on Binance Futures Testnet.
```

One thing worth knowing: the testnet sometimes returns `status: NEW` right
away for a market order even though it fills a split second later. If you
check the order again right after (GET /fapi/v1/order) it'll show `FILLED`
with a proper `avgPrice`. Not a bug, just testnet being a little slow to
report the fill in the initial response.

If something goes wrong, you'll get a `FAILED: ...` message and a non-zero
exit code — 2 for bad input, 3 for a Binance rejection, 4 for network
issues.

## Logs

Everything gets written to `logs/trading_bot.log` — the order details, the
exact request sent to Binance, the raw response, and any errors. The
signature param is redacted before logging (no point exposing it, and it's
useless without the secret key anyway). File rotates at 2MB so it doesn't
grow forever.

The log file included with this submission has real runs against the
testnet: one MARKET order, one LIMIT order, one STOP_LIMIT order, and one
example of a rejected/invalid input to show the validation working.

## Running the tests

```bash
python -m unittest discover -s tests -v
```

These just test the validation logic (no network calls needed).

## Assumptions / notes

- Used the base URL from the assignment (`testnet.binancefuture.com`) by
  default, with an env var override in case it changes later.
- Only using USDT-M futures endpoints, since that's what the assignment
  asked for.
- Assumed one-way position mode (the default for testnet accounts). Hedge
  mode would need an extra `positionSide` param which I didn't add since
  it's out of scope here.
- For STOP_LIMIT, Binance changed how conditional orders work back in Dec
  2025 — they now need to go through a separate `/fapi/v1/algoOrder`
  endpoint instead of the regular order endpoint. I only found this out
  because my first attempt at a stop order failed with error -4120, so I
  went and fixed the client to use the right endpoint. MARKET and LIMIT
  orders aren't affected by this.
- Didn't duplicate Binance's own quantity/price precision rules
  (stepSize/tickSize) on the client side — if you send something Binance
  doesn't like, it'll just tell you and the bot prints that message.
- No retry/backoff logic — this is a simple bot for testnet use, not meant
  to survive rate limits or flaky connections gracefully.
