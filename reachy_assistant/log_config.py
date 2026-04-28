"""Logging configuration for Reachy Assistant."""

import logging


def configure_logging() -> None:
    """Configure the root logger with basic settings."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
