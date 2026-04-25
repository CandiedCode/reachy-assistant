import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="RA_")

    reachy_api_url: str = "http://localhost"
    """Address of the Reachy API. By default, it is set to `http://localhost`."""
    reachy_api_port: int = 8790
    """Port of the Reachy API. By default, it is set to `8790`."""
