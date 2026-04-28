"""Scraper for Create-X upcoming events calendar."""

import datetime
import logging
from typing import Final
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from reachy_assistant.services.calendars import scraper
from reachy_assistant.services.calendars.event import CalendarEvent
from reachy_assistant.services.calendars.scheduler import CalendarScheduler, CalendarSchedulerConfig
from reachy_assistant.services.registry import CronJobEntry, cron_job
from reachy_assistant.services.status import ServiceStatus

LOGGER: logging.Logger = logging.getLogger(__name__)
URL: Final[str] = "https://create-x.gatech.edu/news-events-publications/upcoming-events"


class Scraper(scraper.Scraper):
    """Scraper for Create-X upcoming events."""

    def scrape_calendar(self) -> set[CalendarEvent]:
        """Scrape the Create-X upcoming events page and return a set of CalendarEvent.

        Returns:
            Set of CalendarEvent objects, sorted by date.

        Raises:
            requests.RequestException: on network failure.
        """
        response = requests.get(URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        events: set[CalendarEvent] = set()

        # Target the view-content-wrap div which contains event cards
        content_wrap = soup.select_one("div.view-content-wrap")
        if not content_wrap:
            LOGGER.error("Could not find event container on the page.")
            return set()

        # Each event is in a structured card with date on left, title/time on right
        months = {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}

        # Find event containers - look for divs with month text
        for element in content_wrap.find_all():
            text = element.get_text(strip=True)
            if not any(month in text for month in months):
                continue

            # Extract month/day/year from the date box
            month = None
            day = None
            year = None
            time_str = None
            title = None
            link = None
            lines = [line.strip() for line in element.get_text("\n", strip=True).splitlines() if line.strip()]

            for i, line in enumerate(lines):
                if line in months:
                    month = line
                    if i + 1 < len(lines):
                        day = lines[i + 1]
                    if i + 2 < len(lines):
                        year = lines[i + 2]
                    if i + 3 < len(lines):
                        title = lines[i + 3]
                    if i + 4 < len(lines):
                        time_str = lines[i + 4]
                    break

            if not (month and day and year and title):
                continue

            # Find the title link within or near this element
            link = element.find("a", href=True)
            datetime_str = f"{month} {day} {year} {time_str}"
            # Parse into naive datetime
            dt_naive = datetime.datetime.strptime(datetime_str, "%B %d %Y %I:%M %p")  # noqa: DTZ007
            # Attach Eastern timezone
            dt_eastern = dt_naive.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=-5)))

            events.add(
                CalendarEvent(
                    id=f"{title}-{month}-{day}-{year}-{time_str}",
                    date=f"{month} {day}, {year}",
                    semester="",
                    year=int(year),
                    category="Create-X",
                    event=title,
                    link=urljoin("https://create-x.gatech.edu", link.get("href")) if link else None,  # pyright: ignore[reportArgumentType]
                    start_date=dt_eastern,
                    end_date=dt_eastern,
                )
            )

        return events


@cron_job(name="creative_x_calendar")
def _register() -> CronJobEntry | None:
    """Register the Creative-X calendar scraper job.

    Returns None if calendar_enabled is False, otherwise returns a
    CronJobEntry with the configured scheduler and status.
    """
    from reachy_assistant.services.calendars import get_calendar_store  # noqa: PLC0415

    settings = CalendarSchedulerConfig()
    if not settings.calendar_enabled:
        return None

    status = ServiceStatus(name="creative_x_calendar", enabled=True)
    store = get_calendar_store(settings.calendar_db_path)
    scheduler = CalendarScheduler(
        store=store,
        scraper=Scraper(),
        interval_seconds=settings.calendar_interval_seconds,
        status=status,
    )
    return CronJobEntry(name="creative_x_calendar", scheduler=scheduler, status=status, config=settings)
