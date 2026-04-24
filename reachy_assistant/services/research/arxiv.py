"""Scheduled scraper for top crypto and security papers from arXiv."""

import logging
from typing import Final

import requests

from reachy_assistant.services.registry import CronJobEntry, cron_job
from reachy_assistant.services.scheduler import BaseScheduler
from reachy_assistant.services.status import ServiceStatus

LOGGER = logging.getLogger(__name__)

ONE_DAY_SECONDS: Final[int] = 24 * 60 * 60
ARXIV_API_URL: Final[str] = (
    "https://export.arxiv.org/api/query?search_query=(cat:cs.CR+OR+cat:cs.CY)&sortBy=submittedDate&sortOrder=descending&max_results=20"
)
REQUEST_TIMEOUT_SECONDS: Final[int] = 30


class ArxivScheduler(BaseScheduler):
    """Runs the arXiv paper scraper on a daily schedule."""

    def __init__(self, interval_seconds: int, status: ServiceStatus) -> None:
        """Initialize the scheduler.

        Args:
            interval_seconds: How often to run the scraper.
            status: ServiceStatus for health tracking.
        """
        super().__init__(interval_seconds, status)

    def _run_job(self) -> None:
        """Fetch the latest crypto and security papers from arXiv."""
        self._status.mark_started()
        try:
            response = requests.get(ARXIV_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            LOGGER.info("Successfully fetched top 20 crypto/security papers from arXiv")
            self._status.mark_success()
        except requests.RequestException as e:
            self._status.mark_error(str(e))
            LOGGER.exception("Failed to fetch arXiv papers")


@cron_job(name="arxiv_papers")
def _register() -> CronJobEntry:
    """Register the arXiv papers scraper job.

    Returns:
        CronJobEntry with the configured scheduler and status.
    """
    status = ServiceStatus(name="arxiv_scheduler", enabled=True)
    scheduler = ArxivScheduler(interval_seconds=ONE_DAY_SECONDS, status=status)
    return CronJobEntry(name="arxiv_papers", scheduler=scheduler, status=status)
