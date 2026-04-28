"""Settings for the Reachy Assistant."""

import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Settings for the Reachy Assistant."""

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="RA_")

    reachy_api_url: str = "http://localhost"
    """Address of the Reachy API. By default, it is set to `http://localhost`."""
    reachy_api_port: int = 8790
    """Port of the Reachy API. By default, it is set to `8790`."""
    face_tracking_enabled: bool = False
    """Whether to enable face tracking. Enabled by default."""
    antenna_enabled: bool = True
    """Whether to enable the antenna. Enabled by default."""

    @property
    def custom_app_url(self) -> str:
        """Custom URL for the app. It is constructed from the `reachy_api_url` and `reachy_api_port` settings."""
        return f"{self.reachy_api_url}:{self.reachy_api_port}/"
