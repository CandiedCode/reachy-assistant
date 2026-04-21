"""Global registry for interval-based cron jobs.

Usage
-----
To register a new cron job, create a factory function that returns a CronJobEntry with the configured scheduler and status. Decorate the
function with @cron_job(name=...) to add it to the registry. The factory will be called later by Jobs.__init__,
allowing it to conditionally enable/disable the job and configure its parameters.

    @cron_job(name="my_job")
    def _register() -> CronJobEntry | None:
        if not settings.my_job_enabled:
            return None
        status = ServiceStatus(name="my_job", enabled=True)
        scheduler = MyScheduler(..., status=status)
        return CronJobEntry(name="my_job", scheduler=scheduler, status=status)

jobs.py imports the service module (which runs the decorator), then calls
build_registry to instantiate all registered jobs.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pydantic

from reachy_assistant.models.service_status import ServiceStatus

LOGGER = logging.getLogger(__name__)


@runtime_checkable
class Startable(Protocol):
    """Any scheduler with start/stop lifecycle methods."""

    def start(self, stop_event: threading.Event) -> None:
        """Start the scheduler, using the provided stop_event to know when to stop.

        Args:
            stop_event: A threading.Event that will be set when the scheduler should stop.
        """

    def stop(self) -> None:
        """Stop the scheduler."""


@dataclass
class CronJobEntry:
    """A registered cron job with its scheduler and status."""

    name: str
    scheduler: Startable
    status: ServiceStatus
    config: pydantic.BaseModel | None = None


# Module-level registry of (name, factory_fn) pairs — populated by @cron_job decorators.
_FACTORY_REGISTRY: list[tuple[str, Callable[[], CronJobEntry | None]]] = []


def cron_job(name: str) -> Callable:
    """Register a factory function in the job registry.

    The decorated function must take no arguments and return either a CronJobEntry, to enable the job, or None, to disable it.
    The system calls the factory later—during build_registry() inside Jobs.__init__—not at decoration time.

    Args:
        name: Human-readable job name used in log messages and status keys.

    Returns:
        A decorator that appends the factory to _FACTORY_REGISTRY and
        returns the function unchanged (so it can still be called directly).

    Example:
        @cron_job(name="gatech_calendar")
        def _register() -> CronJobEntry | None: ...
    """

    def decorator(factory_fn: Callable[[], CronJobEntry | None]) -> Callable[[], CronJobEntry | None]:
        """Append the factory function to the registry and return it unchanged.

        Args:
            factory_fn: The function being decorated, which takes no arguments and returns CronJobEntry or None.

        Returns:
            The same factory function, unmodified, so it can still be called directly if needed.
        """
        _FACTORY_REGISTRY.append((name, factory_fn))
        return factory_fn

    return decorator


def build_registry() -> list[CronJobEntry]:
    """Instantiate all registered factories.

    Called once by Jobs.__init__. Each factory is called in order; disabled
    jobs (returning None) are skipped.

    Returns:
        List of CronJobEntry for all enabled jobs.
    """
    entries: list[CronJobEntry] = []

    for name, factory_fn in _FACTORY_REGISTRY:
        LOGGER.debug("Building cron job '%s' using factory %s", name, factory_fn)
        entry = factory_fn()
        if entry is not None:
            entries.append(entry)
        else:
            LOGGER.info("Cron job '%s' is disabled by its factory; skipping", name)
    return entries


def list_cron_jobs_info() -> None:
    """Instantiate all registered factories.

    Called once by Jobs.__init__. Each factory is called in order; disabled
    jobs (returning None) are skipped.

    Returns:
        List of CronJobEntry for all enabled jobs.
    """
    for name, factory_fn in _FACTORY_REGISTRY:
        entry = factory_fn()
        if entry is not None:
            print(f"Cron job '{name}': enabled with scheduler {entry.scheduler} and status {entry.status}")
            print_expected_env_vars(entry.config.__class__) if entry.config else None


def print_expected_env_vars(settings: type[pydantic.BaseModel]) -> None:
    """Print expected environment variable names based on the provided settings model.

    Args:
        settings: A Pydantic settings model class.
    """
    config = settings.model_config
    prefix = config.get("env_prefix", "") or ""

    for name, field in settings.model_fields.items():
        env_names = []

        # Pydantic sometimes stores env overrides here
        if isinstance(field.json_schema_extra, dict) and "env_names" in field.json_schema_extra:
            env_names = field.json_schema_extra["env_names"]
        elif field.alias:
            env_names = [field.alias]
        else:
            env_names = [name]

        if isinstance(env_names, (list, dict)):
            for env in env_names:
                print(f"{prefix}{env}".upper())
