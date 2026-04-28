"""Unit tests for reachy_assistant.main module."""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from reachy_mini import ReachyMini

from reachy_assistant.main import ReachyAssistant
from reachy_assistant.services.jobs import Jobs
from reachy_assistant.settings import Settings


@pytest.fixture
def stop_event() -> threading.Event:
    """Create a threading.Event for testing.

    Returns:
        threading.Event: A new stop event.
    """
    return threading.Event()


@pytest.fixture
def mock_reachy_mini() -> MagicMock:
    """Create a mock ReachyMini instance.

    Returns:
        MagicMock: A mocked ReachyMini instance.
    """
    return MagicMock(spec=ReachyMini)


@pytest.fixture
def mock_settings_app() -> MagicMock:
    """Create a mock FastAPI settings app.

    Returns:
        MagicMock: A mocked FastAPI app instance.
    """
    return MagicMock(spec=FastAPI)


class TestReachyAssistantBasics:
    """Test basic ReachyAssistant functionality."""

    def test_reachy_assistant_instantiation(self) -> None:
        """Verify ReachyAssistant can be instantiated."""
        app = ReachyAssistant()
        assert app is not None
        assert isinstance(app, ReachyAssistant)

    def test_reachy_assistant_has_settings(self) -> None:
        """Verify ReachyAssistant has settings attribute.

        Returns:
            None
        """
        app = ReachyAssistant()
        assert hasattr(app, "settings")
        assert isinstance(app.settings, Settings)

    def test_reachy_assistant_has_custom_app_url(self) -> None:
        """Verify ReachyAssistant has custom_app_url attribute.

        Returns:
            None
        """
        app = ReachyAssistant()
        assert hasattr(app, "custom_app_url")
        assert isinstance(app.custom_app_url, str)

    def test_custom_app_url_format(self) -> None:
        """Verify custom_app_url has correct format.

        Returns:
            None
        """
        app = ReachyAssistant()
        assert app.custom_app_url.startswith("http://")
        assert app.custom_app_url.endswith("/")


class TestReachyAssistantRun:
    """Test ReachyAssistant.run method."""

    @patch("reachy_assistant.main.Jobs")
    def test_run_creates_jobs_instance(self, mock_jobs_class: MagicMock, mock_reachy_mini: MagicMock, stop_event: threading.Event) -> None:
        """Verify run() creates a Jobs instance.

        Args:
            mock_jobs_class: Mocked Jobs class.
            mock_reachy_mini: Mocked ReachyMini instance.
            stop_event: threading.Event for stopping the app.
        """
        mock_jobs = MagicMock(spec=Jobs)
        mock_jobs_class.return_value = mock_jobs

        app = ReachyAssistant()
        app.settings_app = MagicMock(spec=FastAPI)

        stop_event.set()  # Set immediately to exit loop
        app.run(mock_reachy_mini, stop_event)

        mock_jobs_class.assert_called_once()

    @patch("reachy_assistant.main.Jobs")
    def test_run_starts_jobs(self, mock_jobs_class: MagicMock, mock_reachy_mini: MagicMock, stop_event: threading.Event) -> None:
        """Verify run() calls jobs.start().

        Args:
            mock_jobs_class: Mocked Jobs class.
            mock_reachy_mini: Mocked ReachyMini instance.
            stop_event: threading.Event for stopping the app.
        """
        mock_jobs = MagicMock(spec=Jobs)
        mock_jobs_class.return_value = mock_jobs

        app = ReachyAssistant()
        app.settings_app = MagicMock(spec=FastAPI)

        stop_event.set()
        app.run(mock_reachy_mini, stop_event)

        mock_jobs.start.assert_called_once_with(stop_event)

    @patch("reachy_assistant.main.Jobs")
    def test_run_includes_routers(self, mock_jobs_class: MagicMock, mock_reachy_mini: MagicMock, stop_event: threading.Event) -> None:
        """Verify run() calls jobs.include_routers().

        Args:
            mock_jobs_class: Mocked Jobs class.
            mock_reachy_mini: Mocked ReachyMini instance.
            stop_event: threading.Event for stopping the app.
        """
        mock_jobs = MagicMock(spec=Jobs)
        mock_jobs_class.return_value = mock_jobs

        app = ReachyAssistant()
        mock_settings_app = MagicMock(spec=FastAPI)
        app.settings_app = mock_settings_app

        stop_event.set()
        app.run(mock_reachy_mini, stop_event)

        mock_jobs.include_routers.assert_called_once_with(mock_settings_app)

    @patch("reachy_assistant.main.Jobs")
    def test_run_checks_settings_app_is_not_none(self, mock_reachy_mini: MagicMock, stop_event: threading.Event) -> None:
        """Verify run() asserts settings_app is not None.

        Args:
            mock_jobs_class: Mocked Jobs class.
            mock_reachy_mini: Mocked ReachyMini instance.
            stop_event: threading.Event for stopping the app.
        """
        app = ReachyAssistant()
        app.settings_app = None

        stop_event.set()
        with pytest.raises(AssertionError, match="Settings app is not initialized"):
            app.run(mock_reachy_mini, stop_event)

    @patch("reachy_assistant.main.Jobs")
    def test_run_loops_until_stop_event_set(
        self, mock_jobs_class: MagicMock, mock_reachy_mini: MagicMock, stop_event: threading.Event
    ) -> None:
        """Verify run() loops until stop_event is set.

        Args:
            mock_jobs_class: Mocked Jobs class.
            mock_reachy_mini: Mocked ReachyMini instance.
            stop_event: threading.Event for stopping the app.
        """
        mock_jobs = MagicMock(spec=Jobs)
        mock_jobs_class.return_value = mock_jobs

        app = ReachyAssistant()
        app.settings_app = MagicMock(spec=FastAPI)

        # Set stop_event in a separate thread after a short delay
        def stop_after_delay() -> None:
            time.sleep(0.05)
            stop_event.set()

        stop_thread = threading.Thread(target=stop_after_delay, daemon=True)
        stop_thread.start()

        start_time = time.time()
        app.run(mock_reachy_mini, stop_event)
        elapsed = time.time() - start_time

        # Should have run for at least the delay time
        assert elapsed >= 0.05
        assert stop_event.is_set()
