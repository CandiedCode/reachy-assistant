"""Scraper for GaTech future academic calendar."""

import datetime
import logging
from typing import Any, Final

import requests

from reachy_assistant.services.calendars.gatech.event import CalendarEvent

LOGGER = logging.getLogger(__name__)
MAIN_URL: Final[str] = "https://registrar.gatech.edu/future-academic-calendar"
API_URL: Final[str] = "https://registrar.gatech.edu/calevents/proxy"
REQUEST_TIMEOUT_SECONDS: Final[int] = 30


class RecordExtractionError(ValueError):
    """Raised when unable to extract records from API response."""

    def __init__(self) -> None:
        super().__init__("Could not find record list in API response.")


def scrape_calendar(excluded_categories: list[str] | None = None) -> list[CalendarEvent]:
    """Scrape the GaTech academic calendar and return filtered events.

    Fetches events from the official GaTech calendar API endpoint.

    Args:
        excluded_categories: List of categories to exclude from results.

    Returns:
        List of CalendarEvent objects, sorted by (year, weight).

    Raises:
        requests.RequestException: on network failure.
        ValueError: if the API response structure is unexpected.
    """
    session = requests.Session()

    browser_headers: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    # We need cookies from the main page to access the API
    main_response = session.get(MAIN_URL, headers=browser_headers, timeout=REQUEST_TIMEOUT_SECONDS)
    main_response.raise_for_status()

    api_headers = {
        **browser_headers,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": MAIN_URL,
        "X-Requested-With": "XMLHttpRequest",
    }

    current_year = datetime.datetime.now(datetime.UTC).year
    next_year = current_year + 1

    params = {
        "year": f"{current_year}-{next_year}",
        "status": "future",
    }

    LOGGER.info("Fetching calendar data from API endpoint")
    api_response = session.get(API_URL, params=params, headers=api_headers, timeout=REQUEST_TIMEOUT_SECONDS)
    api_response.raise_for_status()

    data = api_response.json()
    records = _extract_records(data)
    events = _parse_calendar_records(records, excluded_categories)

    LOGGER.info(
        "Scraped %d events from GaTech calendar (excluded %d categories)",
        len(events),
        len(excluded_categories) if excluded_categories else 0,
    )
    return events


def _extract_records(data: list | dict[str, Any]) -> list[dict]:
    """Extract the record list from the API response.

    Handles various response structures.

    Args:
        data: Parsed JSON response from the API.

    Returns:
        List of record dictionaries.

    Raises:
        ValueError: if no record list is found in the response.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data["data"]

    raise RecordExtractionError


def _parse_calendar_records(records: list[dict], excluded_categories: list[str] | None) -> list[CalendarEvent]:
    """Parse calendar records from the API response.

    Args:
        records: List of record dictionaries from the API.
        excluded_categories: Categories to filter out.

    Returns:
        List of CalendarEvent objects, sorted by (year, weight).
    """
    events = []

    for record in records:
        if not isinstance(record, dict):
            continue

        try:
            event = CalendarEvent.model_validate(record)

            # Skip excluded categories
            if excluded_categories and event.category in excluded_categories:
                continue

            events.append(event)
        except (ValueError, TypeError) as e:
            LOGGER.warning("Failed to parse event record: %s (error: %s)", record, e)
            continue

    return sorted(events, key=lambda e: (e.year, e.weight))
