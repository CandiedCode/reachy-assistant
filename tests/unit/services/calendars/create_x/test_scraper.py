"""Unit tests for Create-X calendar scraper."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from reachy_assistant.services.calendars.create_x.scraper import Scraper


@pytest.fixture
def scraper() -> Scraper:
    """Create a Scraper instance for testing.

    Returns:
        Scraper: A new Scraper instance.
    """
    return Scraper()


class TestScraperDateTimeParsing:
    """Test datetime parsing and timezone handling."""

    @patch("requests.get")
    def test_scraper_parses_datetime_correctly(self, mock_get: MagicMock, scraper: Scraper) -> None:
        """Test scraper correctly parses datetime strings.

        Args:
            mock_get: Mocked requests.get function.
            scraper: Scraper fixture instance.

        Returns:
            None
        """
        html_content = """
        <html>
            <body>
                <div class='view-content-wrap'>
                    <div>
                        July
                        4
                        2026
                        Independence Day
                        02:30 PM
                        <a href='/event'>Link</a>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_get.return_value = mock_response

        events = scraper.scrape_calendar()
        event = events.pop()

        # Check datetime fields exist and are datetime objects
        assert event.start_date is not None and event.end_date is not None
        assert isinstance(event.start_date, datetime.datetime) and isinstance(event.end_date, datetime.datetime)

    @patch("requests.get")
    def test_scraper_uses_eastern_timezone(self, mock_get: MagicMock, scraper: Scraper) -> None:
        """Test scraper uses Eastern timezone for dates.

        Args:
            mock_get: Mocked requests.get function.
            scraper: Scraper fixture instance.

        Returns:
            None
        """
        html_content = """
        <html>
            <body>
                <div class='view-content-wrap'>
                    <div>
                        August
                        15
                        2026
                        Summer Event
                        06:00 PM
                        <a href='/event'>Link</a>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_get.return_value = mock_response

        events = scraper.scrape_calendar()
        event = events.pop()

        # Eastern timezone is UTC-5
        expected_offset = datetime.timedelta(hours=-5)
        assert event.start_date.tzinfo is not None
        assert event.start_date.utcoffset() == expected_offset

    @pytest.mark.parametrize(
        "time_str,expected_hour,expected_minute",
        [
            ("12:00 AM", 0, 0),  # Midnight
            ("01:00 AM", 1, 0),
            ("12:00 PM", 12, 0),  # Noon
            ("01:00 PM", 13, 0),
            ("11:59 PM", 23, 59),
        ],
    )
    @patch("requests.get")
    def test_scraper_parses_various_times(
        self, mock_get: MagicMock, scraper: Scraper, time_str: str, expected_hour: int, expected_minute: int
    ) -> None:
        """Test scraper correctly parses various time formats."""
        html_content = f"""
        <html>
            <body>
                <div class='view-content-wrap'>
                    <div>
                        September
                        1
                        2026
                        Time Test
                        {time_str}
                        <a href='/event'>Link</a>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html_content
        mock_get.return_value = mock_response

        events = scraper.scrape_calendar()
        if len(events) > 0:
            event = events.pop()
            assert event.start_date.hour == expected_hour
            assert event.start_date.minute == expected_minute
