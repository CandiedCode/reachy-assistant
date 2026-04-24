"""Background scheduler for the GaTech calendar scraper."""

import logging
from pathlib import Path

import pydantic
import pydantic_settings

from reachy_assistant.services.calendars.scraper import Scraper
from reachy_assistant.services.calendars.store import CalendarStore
from reachy_assistant.services.scheduler import BaseScheduler
from reachy_assistant.services.status import ServiceStatus

logger = logging.getLogger(__name__)

ONE_WEEK_SECONDS = 7 * 24 * 60 * 60


class CalendarScheduler(BaseScheduler):
    """Runs the GaTech calendar scraper on a recurring schedule.

    The scraper runs immediately on start, then repeats at the specified interval.
    It integrates with the main app's threading.Event stop signal.
    """

    def __init__(
        self,
        store: CalendarStore,
        scraper: Scraper,
        interval_seconds: int,
        status: ServiceStatus,
    ) -> None:
        """Initialize the scheduler.

        Args:
            store: CalendarStore instance for persisting events.
            scraper: Scraper instance to use for scraping the calendar.
            interval_seconds: How often to run the scraper.
            status: ServiceStatus for health tracking.
        """
        super().__init__(interval_seconds, status)
        self._store = store
        self._scraper = scraper

    @property
    def store(self) -> CalendarStore:
        """Return the store instance for direct access."""
        return self._store

    def _run_job(self) -> None:
        """Execute one scrape cycle."""
        self._status.mark_started()
        try:
            events = self._scraper.scrape_calendar()
            added = self._store.merge_and_save(events)
            self._status.mark_success()
            logger.info(
                "Calendar sync complete: %d new events, %d total scraped",
                added,
                len(events),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self._status.mark_error(str(e))
            logger.exception("Calendar scrape failed")


class CalendarSchedulerConfig(pydantic.BaseModel):
    """Configuration for the calendar scheduler."""

    model_config = pydantic_settings.SettingsConfigDict(env_prefix="RA_GTC_")

    calendar_enabled: bool = True
    """Whether to enable the calendar scraper job. Enabled by default."""
    calendar_db_path: Path = Path("data/reachy_assistant.db")
    """Path to the SQLite database file for storing calendar events."""
    calendar_interval_seconds: int = ONE_WEEK_SECONDS
    """Interval in seconds between calendar scraper runs."""
    calendar_excluded_categories: list[str] = ["Readmission", "Thesis", "Faculty"]
    """List of event categories to exclude from results."""
