"""Telegram bot settings."""

import pydantic
import pydantic_settings


class TelegramSettings(pydantic_settings.BaseSettings):
    """Configuration for the Telegram bot service."""

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="RA_TG_")

    telegram_enabled: bool = False
    """Whether to enable the Telegram bot. Disabled by default."""
    telegram_token: pydantic.SecretStr = pydantic.SecretStr("")
    """Telegram Bot API token from BotFather."""
    telegram_allowed_users: list[int] = []
    """List of allowed Telegram user IDs. Empty list means all users are allowed."""
