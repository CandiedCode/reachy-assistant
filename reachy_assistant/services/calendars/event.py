"""Pydantic model for a GaTech academic calendar event."""

import datetime

import pydantic


class CalendarEvent(pydantic.BaseModel):
    """A calendar event from the GaTech academic calendar."""

    id: str
    """Numeric event ID from the page (deduplication key)."""
    date: str
    """Raw date string as scraped (e.g., "January 20 (Tue)")."""
    semester: str
    """Semester code (e.g., "5F", "5M", "8")."""
    year: int
    """Academic year (e.g., 2026)."""
    category: str
    """Event category (e.g., "Classes", "Holiday", "Registration")."""
    event: str
    """Event description (HTML-stripped text)."""
    weight: int
    """Ordering weight from the page (for sorting within a year)."""
    _scraped_at: datetime.datetime = datetime.datetime.now(datetime.UTC)
    """ISO 8601 UTC timestamp when this event was scraped."""
    _parsed_dates: tuple[datetime.date, datetime.date | None] | None = None
