"""Reachy Assistant package."""

import logging
import sys

# Ensure root logger has a handler for reachy_assistant logs
# Do this even if handlers exist, to ensure we always have output
root_logger = logging.getLogger()
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
