"""Centralized logging configuration using Rich."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

console = Console(stderr=True)


def setup_logger(name: str = "tracecleaner", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a Rich-powered logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)
    handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    handler.setLevel(level)
    fmt = logging.Formatter("%(message)s", datefmt="[%X]")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


log = setup_logger()
