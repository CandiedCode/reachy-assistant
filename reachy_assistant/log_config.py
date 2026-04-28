"""Logging configuration for Reachy Assistant."""

import logging


def configure_logging() -> None:
    """Configure the root logger with basic settings."""
    # Force set the root logger level - basicConfig() may have already been called
    logging.root.setLevel(logging.INFO)

    # Ensure we have a handler
    if not logging.root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logging.root.addHandler(handler)
