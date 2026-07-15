"""Logging setup for the whole app, all in one place.

Writes everything (requests, responses, errors) to a rotating log file so
it doesn't grow forever. Console just shows INFO and above so it's not
spammy while you're using the CLI, but the file has the full DEBUG detail
if you need to dig into what actually got sent/received.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

_LOGGER_NAME = "trading_bot"
_configured = False


def setup_logging(log_file: Path = LOG_FILE, console_level: int = logging.INFO) -> logging.Logger:
    """Sets up the shared logger and returns it.

    Fine to call this more than once - it only actually sets up the
    handlers the first time, after that it just returns the same logger.
    """
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)

    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    return logger


def get_logger() -> logging.Logger:
    """Shortcut so other modules don't have to import setup_logging directly."""
    return setup_logging()
