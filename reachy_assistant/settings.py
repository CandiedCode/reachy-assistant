from typing import Literal

import pydantic
import pydantic_settings
from reachy_mini.media import media_manager


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="RA_")

    reachy_api_url: str = "http://localhost"
    """Address of the Reachy API. By default, it is set to `http://localhost`."""
    reachy_api_port: int = 8790
    """Port of the Reachy API. By default, it is set to `8790`."""
    request_media_backend: Literal["no_media", "local", "webrtc", "auto"] | None = "auto"
    """Media backend to request for the app."""

    @pydantic.field_validator("request_media_backend", mode="after")
    @classmethod
    def _validate_request_media_backend(cls, value: str | None) -> str | None:
        if value in ("default", "auto"):
            return value

        for backend in media_manager.MediaBackend.__members__.values():
            if value == backend.value:
                return backend.value
        raise ValueError(f"Invalid media backend '{value}'. Available backends: {list(media_manager.MediaBackend.__members__.keys())}")
