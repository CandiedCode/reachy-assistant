"""FastAPI router for calendar events API."""

import logging

from fastapi import APIRouter, Query

from reachy_assistant.services import calendars

LOGGER = logging.getLogger(__name__)


def build_router(db_path: str) -> APIRouter:
    """Build a FastAPI router for calendar event queries.

    Args:
        db_path: Path to the database file for the calendar store.

    Returns:
        APIRouter with calendar event endpoints.
    """
    router = APIRouter()
    store = calendars.get_calendar_store(db_path)

    @router.get("/events")
    def get_events(days: int = Query(7, ge=1, le=365)) -> dict:
        """Get calendar events in the next N days.

        Args:
            days: Number of days to look ahead (1-365, default 7).

        Returns:
            Dictionary with days, count, and list of events.
        """
        events = store.get_events_in_next_days(days)
        return {
            "days": days,
            "count": len(events),
            "events": [
                {
                    "id": event.id,
                    "event": event.event,
                    "category": event.category,
                    "start_date": event.start_date.isoformat() if event.start_date else None,
                    "end_date": event.end_date.isoformat() if event.end_date else None,
                    "link": event.link,
                }
                for event in events
            ],
        }

    return router
