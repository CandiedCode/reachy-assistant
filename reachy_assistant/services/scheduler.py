"""Base class for all recurring background job schedulers."""

import abc
import logging
import threading

from reachy_assistant.services.status import ServiceStatus

LOGGER = logging.getLogger(__name__)


class BaseScheduler(abc.ABC):
    """Abstract base for all recurring schedulers."""

    def __init__(self, interval_seconds: int, status: ServiceStatus) -> None:
        """Initialize the scheduler.

        Args:
            interval_seconds: How often to run the job (in seconds).
            status: ServiceStatus for health tracking.
        """
        self._interval = interval_seconds
        self._status = status
        self._timer: threading.Timer | None = None

    def start(self, stop_event: threading.Event) -> None:
        """Start the scheduler.

        Runs the job immediately, then schedules recurring runs.

        Args:
            stop_event: threading.Event that signals when to stop scheduling.
        """
        LOGGER.info("%s starting (interval=%ds)", self.__class__.__name__, self._interval)
        self._schedule_next(stop_event)

    def stop(self) -> None:
        """Stop the scheduler and cancel any pending timer."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        LOGGER.info("%s stopped", self.__class__.__name__)

    def _schedule_next(self, stop_event: threading.Event) -> None:
        """Run the job and schedule the next run.

        Args:
            stop_event: Stop signal from the main app.
        """
        if stop_event.is_set():
            return

        self._run_job()

        if not stop_event.is_set():
            self._status.set_next_run_in_seconds(self._interval)
            self._timer = threading.Timer(self._interval, self._schedule_next, args=(stop_event,))
            self._timer.daemon = True
            self._timer.start()

    @abc.abstractmethod
    def _run_job(self) -> None:
        """Execute one job cycle."""
