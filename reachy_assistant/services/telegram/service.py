"""Telegram service orchestrator."""

import logging
import threading
from typing import TYPE_CHECKING

from reachy_assistant.services.telegram.bot import TelegramBotScheduler
from reachy_assistant.services.telegram.command import build_command_registry
from reachy_assistant.services.telegram.settings import TelegramSettings

if TYPE_CHECKING:
    from reachy_assistant.services.jobs import Jobs

LOGGER = logging.getLogger(__name__)


class TelegramService:
    """Manages Telegram bot initialization and lifecycle.

    Orchestrates the same way as Jobs: initialize, then call start/stop
    with the application's stop_event.
    """

    def __init__(self, jobs: "Jobs") -> None:
        """Initialize the Telegram service.

        Args:
            jobs: The Jobs registry for command dependency injection.
        """
        self._jobs = jobs
        self._bot: TelegramBotScheduler | None = None

    def start(self, stop_event: threading.Event) -> None:
        """Start the Telegram bot if enabled.

        Args:
            stop_event: threading.Event to signal shutdown.
        """
        settings = TelegramSettings()
        if not settings.telegram_enabled:
            LOGGER.debug("Telegram service is disabled")
            return

        commands = build_command_registry(self._jobs)
        self._bot = TelegramBotScheduler(
            token=settings.telegram_token.get_secret_value(),
            commands=commands,
            allowed_users=settings.telegram_allowed_users,
        )
        self._bot.start(stop_event)

    def stop(self) -> None:
        """Stop the Telegram bot gracefully."""
        if self._bot:
            self._bot.stop()
