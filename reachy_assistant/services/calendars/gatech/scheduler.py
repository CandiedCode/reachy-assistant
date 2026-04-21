"""Background scheduler for the GaTech calendar scraper."""

import logging
import threading
from collections.abc import Callable
from pathlib import Path

import pydantic
import pydantic_settings

from reachy_assistant.models.service_status import ServiceStatus
from reachy_assistant.services.calendars.gatech import scraper
from reachy_assistant.services.calendars.store import CalendarStore
from reachy_assistant.services.registry import CronJobEntry, cron_job

logger = logging.getLogger(__name__)

ONE_WEEK_SECONDS = 7 * 24 * 60 * 60


class CalendarScheduler:
    """Runs the GaTech calendar scraper on a recurring schedule.

    The scraper runs immediately on start, then repeats at the specified interval.
    It integrates with the main app's threading.Event stop signal.
    """

    def __init__(
        self,
        store: CalendarStore,
        scraper_fn: Callable[[list[str] | None], list],
        interval_seconds: int = ONE_WEEK_SECONDS,
        excluded_categories: list[str] | None = None,
        status: ServiceStatus | None = None,
    ) -> None:
        """Initialize the scheduler.

        Args:
            store: CalendarStore instance for persisting events.
            scraper_fn: Function to call to scrape calendar. Should accept excluded_categories.
            interval_seconds: How often to run the scraper (default: 1 week).
            excluded_categories: List of categories to exclude from results.
            status: Optional ServiceStatus for health tracking.
        """
        self._store = store
        self._scraper_fn = scraper_fn
        self._interval = interval_seconds
        self._excluded_categories = excluded_categories
        self._status = status
        self._timer: threading.Timer | None = None

    @property
    def store(self) -> CalendarStore:
        """Return the store instance for direct access."""
        return self._store

    def start(self, stop_event: threading.Event) -> None:
        """Start the scheduler.

        Runs the scraper immediately, then schedules recurring runs.

        Args:
            stop_event: threading.Event that signals when to stop scheduling.
        """
        logger.info("CalendarScheduler starting (interval=%ds)", self._interval)
        self._schedule_next(stop_event)

    def stop(self) -> None:
        """Stop the scheduler and cancel any pending timer."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        logger.info("CalendarScheduler stopped")

    def _schedule_next(self, stop_event: threading.Event) -> None:
        """Run the job and schedule the next run.

        Args:
            stop_event: Stop signal from the main app.
        """
        if stop_event.is_set():
            return

        # Run the scraper in this thread (the timer thread)
        self._run_job()

        # Schedule the next run
        if not stop_event.is_set():
            if self._status:
                self._status.set_next_run_in_seconds(self._interval)
            self._timer = threading.Timer(self._interval, self._schedule_next, args=(stop_event,))
            self._timer.daemon = True
            self._timer.start()

    def _run_job(self) -> None:
        """Execute one scrape cycle."""
        if self._status:
            self._status.mark_started()
        try:
            events = self._scraper_fn(self._excluded_categories)
            added = self._store.merge_and_save(events, self._excluded_categories)
            if self._status:
                self._status.mark_success()
            logger.info(
                "Calendar sync complete: %d new events, %d total scraped",
                added,
                len(events),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            if self._status:
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


@cron_job(name="gatech_calendar")
def _register() -> CronJobEntry | None:
    """Register the GaTech calendar scraper job.

    Returns None if calendar_enabled is False, otherwise returns a
    CronJobEntry with the configured scheduler and status.
    """
    settings = CalendarSchedulerConfig()
    if not settings.calendar_enabled:
        return None

    status = ServiceStatus(name="calendar_scheduler", enabled=True)
    store = CalendarStore(settings.calendar_db_path)
    scheduler = CalendarScheduler(
        store=store,
        scraper_fn=scraper.scrape_calendar,
        interval_seconds=settings.calendar_interval_seconds,
        excluded_categories=settings.calendar_excluded_categories,
        status=status,
    )
    return CronJobEntry(name="gatech_calendar", scheduler=scheduler, status=status, config=settings)
