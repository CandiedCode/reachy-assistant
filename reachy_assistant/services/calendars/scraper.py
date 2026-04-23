"""Scraper abstract module for calendars."""

import abc

from reachy_assistant.services.calendars.event import CalendarEvent


class Scraper(abc.ABC):
    """Base scraper class for academic calendars."""

    @abc.abstractmethod
    def scrape_calendar(self) -> set[CalendarEvent]:
        """Scrape the calendar and return a set of events.

        This method should be implemented by subclasses to fetch and parse
        calendar data from specific sources.

        Returns:
            Set of CalendarEvent objects.

        Raises:
            NotImplementedError: if the method is not implemented by a subclass.
            Exception: for any scraping or parsing errors.
        """
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)
