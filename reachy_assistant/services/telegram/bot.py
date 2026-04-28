"""Telegram bot service with async event handling."""

import asyncio
import logging
import threading
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from reachy_assistant.services.telegram.command import BotCommandEntry

LOGGER = logging.getLogger(__name__)


class TelegramBotScheduler:
    """Runs a Telegram bot in a background thread."""

    def __init__(
        self,
        token: str,
        commands: list[BotCommandEntry],
        allowed_users: list[int] | None = None,
    ) -> None:
        """Initialize the Telegram bot scheduler.

        Args:
            token: Telegram Bot API token.
            commands: List of registered bot commands.
            allowed_users: List of allowed user IDs. Empty/None means all users allowed.
        """
        self._token = token
        self._commands = commands
        self._allowed_users = allowed_users or []
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._application: Application | None = None
        self._stop_event: threading.Event | None = None

    def start(self, stop_event: threading.Event) -> None:
        """Start the bot in a background thread.

        Args:
            stop_event: threading.Event to signal shutdown.
        """
        self._stop_event = stop_event
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True)
        self._thread.start()
        LOGGER.info("Telegram bot started in background thread")

    def stop(self) -> None:
        """Stop the bot gracefully."""
        if self._application and self._loop:
            asyncio.run_coroutine_threadsafe(self._application.stop(), self._loop)
        LOGGER.info("Telegram bot stopped")

    def _run(self, stop_event: threading.Event) -> None:
        """Run the bot event loop in a dedicated thread.

        Args:
            stop_event: Signal to stop the bot.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_async(stop_event))
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Telegram bot encountered an error")
        finally:
            self._loop.close()

    async def _run_async(self, stop_event: threading.Event) -> None:
        """Async main loop for the bot.

        Args:
            stop_event: Signal to stop the bot.
        """
        self._application = Application.builder().token(self._token).build()

        for cmd in self._commands:
            handler = self._wrap_handler(cmd.handler)
            self._application.add_handler(CommandHandler(cmd.name, handler))

        async with self._application:
            await self._application.start()
            if self._application.updater:
                await self._application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

                LOGGER.info("Telegram bot polling started with %d commands", len(self._commands))

                while not stop_event.is_set():  # noqa: ASYNC110
                    await asyncio.sleep(0.5)

                await self._application.updater.stop()
            await self._application.stop()

        LOGGER.info("Telegram bot polling stopped")

    def _wrap_handler(self, handler: Any) -> Any:
        """Wrap a command handler to add authorization checks.

        Args:
            handler: The command handler to wrap.

        Returns:
            Wrapped handler with auth checks.
        """

        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if not self._check_auth(update) and update.message is not None:
                await update.message.reply_text("❌ You are not authorized to use this command.")
                return
            await handler(update, context)

        return wrapped

    def _check_auth(self, update: Update) -> bool:
        """Check if user is authorized.

        Args:
            update: The Telegram update.

        Returns:
            True if authorized, False otherwise.
        """
        if not self._allowed_users:
            return True
        return update.effective_user is not None and update.effective_user.id in self._allowed_users
