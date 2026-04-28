"""Pydantic model for a GaTech academic calendar event."""

import datetime
import re
from typing import Final, Self

import pydantic

from reachy_assistant.services.calendars import event


class CalendarEvent(event.CalendarEvent):
    """A calendar event from the GaTech academic calendar."""

    _DAY_OF_WEEK = re.compile(r"\s*\([A-Za-z]+\)")
    _DATE_PARTS_COUNT: Final[int] = 2

    def _parse_date(self, raw_date: str, year: int) -> datetime.datetime:
        """Parse a date string with day-of-week suffix.

        Args:
            raw_date: e.g. "January 20 (Tue)"
            year: academic year (e.g., 2026)

        Returns:
            datetime object

        Raises:
            ValueError: if parsing fails
        """
        clean_date = self._DAY_OF_WEEK.sub("", raw_date).strip()
        dt = datetime.datetime.strptime(f"{clean_date} {year}", "%B %d %Y").replace(tzinfo=datetime.UTC)
        return dt

    def parse_event_dates(self) -> tuple[datetime.datetime, datetime.datetime]:
        """Parse an event's date range.

        Returns:
            Tuple of (start_date, end_date). For single-day events, start_date and end_date will be the same.

        Raises:
            ValueError: if parsing fails
        """
        parts = [p.strip() for p in self.date.split(" - ", 1)]
        start_date = self._parse_date(parts[0], self.year)
        end_date = self._parse_date(parts[1], self.year) if len(parts) == self._DATE_PARTS_COUNT else start_date
        return start_date, end_date

    @pydantic.model_validator(mode="after")
    def _parse_dates(self) -> Self:
        self.start_date, self.end_date = self.parse_event_dates()
        return self
