"""Bot command registry for plugin-style command registration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass
class BotCommandEntry:
    """A registered bot command with its handler."""

    name: str
    """Command name (e.g., 'papers')."""
    description: str
    """Command description shown in help."""
    handler: Callable
    """Async handler function for the command."""


_COMMAND_REGISTRY: list[tuple[str, Callable[[Any], BotCommandEntry | None]]] = []


def bot_command(name: str) -> Callable:
    """Register a factory function in the bot command registry.

    The decorated function receives a `Jobs` instance and returns a `BotCommandEntry` or None.

    Args:
        name: Command name (e.g., 'papers').

    Returns:
        A decorator that appends the factory to the registry.

    Example:
        @bot_command(name="papers")
        def _register(jobs: Jobs) -> BotCommandEntry:
            ...
    """

    def decorator(factory_fn: Callable[[Any], BotCommandEntry | None]) -> Callable[[Any], BotCommandEntry | None]:
        _COMMAND_REGISTRY.append((name, factory_fn))
        return factory_fn

    return decorator


def build_command_registry(jobs: Any) -> list[BotCommandEntry]:
    """Instantiate all registered command factories.

    Args:
        jobs: The Jobs instance for dependency injection.

    Returns:
        List of enabled BotCommandEntry instances.
    """
    entries: list[BotCommandEntry] = []

    for name, factory_fn in _COMMAND_REGISTRY:
        LOGGER.debug("Building bot command '%s' using factory %s", name, factory_fn)
        entry = factory_fn(jobs)
        if entry is not None:
            entries.append(entry)
        else:
            LOGGER.info("Bot command '%s' is disabled by its factory; skipping", name)

    return entries
