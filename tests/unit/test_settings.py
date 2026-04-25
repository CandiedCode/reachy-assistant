"""Unit tests for reachy_assistant.settings module."""

import pytest
from pydantic import ValidationError

from reachy_assistant.settings import Settings

DEFAULTS = {
    "reachy_api_url": "http://localhost",
    "reachy_api_port": 8790,
}

class TestSettingsDefaults:
    """Test default values for Settings."""

    @pytest.mark.parametrize(
        "attribute,expected_value",
        [
            ("reachy_api_url", "http://localhost"),
            ("reachy_api_port", 8790),
        ],
    )
    def test_defaults(self, attribute: str, expected_value: str | int) -> None:
        """Test default values for all settings attributes."""
        settings = Settings()
        assert getattr(settings, attribute) == expected_value


class TestSettingsEnvironmentVariables:
    """Test loading settings from environment variables."""

    @pytest.mark.parametrize(
        "env_var,env_value,attribute,expected_value",
        [
            ("RA_REACHY_API_URL", "http://192.168.1.100", "reachy_api_url", "http://192.168.1.100"),
            ("RA_REACHY_API_PORT", "9000", "reachy_api_port", 9000),
        ],
    )
    def test_load_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        env_var: str,
        env_value: str,
        attribute: str,
        expected_value: str | int,
    ) -> None:
        """Test loading settings from environment variables with RA_ prefix."""
        monkeypatch.setenv(env_var, env_value)
        settings = Settings()
        assert getattr(settings, attribute) == expected_value


class TestSettingsValidation:
    """Test field validation for Settings."""

    def test_api_port_type_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that API port must be an integer."""
        monkeypatch.setenv("RA_REACHY_API_PORT", "not_a_number")
        with pytest.raises(ValidationError):
            Settings()


class TestSettingsIntegration:
    """Integration tests for Settings with multiple environment variables."""

    def test_load_all_settings_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading all settings from environment variables."""
        monkeypatch.setenv("RA_REACHY_API_URL", "http://10.0.0.1")
        monkeypatch.setenv("RA_REACHY_API_PORT", "8000")
        settings = Settings()
        assert settings.reachy_api_url == "http://10.0.0.1"
        assert settings.reachy_api_port == 8000

    def test_partial_env_vars_use_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that unset environment variables use defaults."""
        monkeypatch.delenv("RA_REACHY_API_URL", raising=False)
        monkeypatch.delenv("RA_REACHY_API_PORT", raising=False)
        settings = Settings()
        assert settings.reachy_api_url == "http://localhost"
        assert settings.reachy_api_port == 8790


class TestSettingsDirectInstantiation:
    """Test direct instantiation of Settings with keyword arguments."""

    @pytest.mark.parametrize(
        "kwargs,expected_values",
        [
            (
                {
                    "reachy_api_url": "http://custom.local",
                    "reachy_api_port": 5000,
                },
                {
                    "reachy_api_url": "http://custom.local",
                    "reachy_api_port": 5000,
                },
            ),
            (
                {"reachy_api_port": 3000},
                {
                    "reachy_api_url": "http://localhost",
                    "reachy_api_port": 3000,
                },
            ),
        ],
        ids=["all_custom_values", "partial_custom_values"],
    )
    def test_instantiate_with_values(
        self,
        kwargs: dict,
        expected_values: dict,
    ) -> None:
        """Test creating settings with custom and default values."""
        settings = Settings(**kwargs)
        for attr, expected_value in expected_values.items():
            assert getattr(settings, attr) == expected_value
