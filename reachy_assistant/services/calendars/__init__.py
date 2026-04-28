"""Calendar cronjob services."""

from pathlib import Path

from reachy_assistant.services.calendars import create_x, event, gatech, hive, scheduler, store
from reachy_assistant.services.calendars.store import CalendarStore

_calendar_store: CalendarStore | None = None


def get_calendar_store(db_path: str | Path) -> CalendarStore:
    """Get or create the shared CalendarStore instance.

    Args:
        db_path: Path to the calendar database file.

    Returns:
        CalendarStore: The shared store instance.
    """
    global _calendar_store  # noqa: PLW0603
    if _calendar_store is None:
        _calendar_store = CalendarStore(Path(db_path) if isinstance(db_path, str) else db_path)
    return _calendar_store


__all__ = ["create_x", "event", "gatech", "get_calendar_store", "hive", "scheduler", "store"]
