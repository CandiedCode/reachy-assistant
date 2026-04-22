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
    link: str | None
    """URL link to the event page."""
    parsed_dates: tuple[datetime.datetime, datetime.datetime | None] | None = None
    """Parsed start/end dates for the event, populated after validation."""
    _scraped_at: datetime.datetime = datetime.datetime.now(datetime.UTC)
    """ISO 8601 UTC timestamp when this event was scraped."""

    def __hash__(self) -> int:
        """Hash based on the unique event ID for deduplication."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on the unique event ID.

        Args:
            other: Another object to compare against.

        Returns:
            True if the other object is a CalendarEvent with the same ID, False otherwise.
        """
        if not isinstance(other, CalendarEvent):
            return False
        return self.id == other.id
