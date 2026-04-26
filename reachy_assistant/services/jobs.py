"""Job orchestrator — discovers and starts all registered cron jobs."""

import threading

from fastapi import FastAPI

from reachy_assistant.services.registry import CronJobEntry, Startable, build_registry
from reachy_assistant.services.status import ServiceStatus


class Jobs:
    """Manages discovery and startup of all registered cron jobs.

    Jobs are registered via the @cron_job decorator and auto-discovered
    by importing their service modules. The registry is instantiated once
    per Jobs instance.
    """

    def __init__(self) -> None:
        """Initialize and discover all registered jobs."""
        self._entries: list[CronJobEntry] = build_registry()

    @property
    def entries(self) -> list[CronJobEntry]:
        """Return the list of registered CronJobEntry objects."""
        return self._entries

    @property
    def statuses(self) -> list[ServiceStatus]:
        """Return ServiceStatus objects for all registered jobs."""
        return [entry.status for entry in self._entries]

    def status(self, service_name: str) -> ServiceStatus | None:
        """Return the ServiceStatus object for a specific job.

        Args:
            service_name: The job name as passed to @cron_job(name=...).

        Returns:
            The ServiceStatus object for the specified job, or None if not found.
        """
        entry = next((entry for entry in self._entries if entry.name == service_name), None)
        return entry.status if entry else None

    def get_scheduler(self, name: str) -> Startable | None:
        """Get a specific scheduler by job name.

        Args:
            name: The job name as passed to @cron_job(name=...).

        Returns:
            The Startable scheduler instance, or None if not found.
        """
        return next((entry.scheduler for entry in self._entries if entry.name == name), None)

    def start(self, stop_event: threading.Event) -> None:
        """Start all registered jobs.

        Args:
            stop_event: threading.Event to signal when to stop scheduled jobs.
        """
        for entry in self._entries:
            entry.scheduler.start(stop_event)

    def stop(self) -> None:
        """Stop all jobs."""
        for entry in self._entries:
            if hasattr(entry.scheduler, "stop"):
                entry.scheduler.stop()

    def include_routers(self, app: FastAPI) -> None:
        """Include each service's optional APIRouter into the given FastAPI app.

        Each router is mounted under /services/<name>/ with a matching tag so
        routes are grouped in the auto-generated OpenAPI docs.

        Args:
            app: The FastAPI application (self.settings_app in main.py).
        """
        for entry in self._entries:
            if entry.router is not None:
                app.include_router(
                    entry.router,
                    prefix=f"/services/{entry.name}",
                    tags=[entry.name],
                )
