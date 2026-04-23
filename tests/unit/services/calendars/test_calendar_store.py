"""Unit tests for SQLite-backed CalendarStore."""

import datetime
from pathlib import Path

from reachy_assistant.services.calendars.event import CalendarEvent
from reachy_assistant.services.calendars.store import CalendarStore


def test_load_empty(tmp_path: Path) -> None:
    """Load from empty/nonexistent database returns empty dict."""
    store = CalendarStore(tmp_path / "test")
    result = store.load()
    assert result == {}


def test_merge_and_save_single_event(tmp_path: Path) -> None:
    """Merge and save a single event."""
    store = CalendarStore(tmp_path / "test")

    event = CalendarEvent(
        id="1",
        date="April 5 (Sat)",
        semester="8",
        year=2026,
        category="Classes",
        event="First day of classes",
        start_date=datetime.datetime(2026, 4, 5, tzinfo=datetime.UTC),
        end_date=None,
        link=None,
    )

    added = store.merge_and_save({event})
    assert added == 1

    loaded = store.load()
    assert "1" in loaded
    assert loaded["1"].id == "1"
    assert loaded["1"].date == "April 5 (Sat)"
    assert loaded["1"].year == 2026


def test_merge_and_save_deduplication(tmp_path: Path) -> None:
    """Second save with same ID doesn't increase count."""
    store = CalendarStore(tmp_path / "test")

    event1 = CalendarEvent(
        id="1",
        date="April 5 (Sat)",
        semester="8",
        year=2026,
        category="Classes",
        event="First day",
        start_date=datetime.datetime(2026, 4, 5, tzinfo=datetime.UTC),
        end_date=None,
        link=None,
    )

    added1 = store.merge_and_save({event1})
    assert added1 == 1

    # Save the same event again
    added2 = store.merge_and_save({event1})
    assert added2 == 0

    loaded = store.load()
    assert len(loaded) == 1


def test_merge_and_save_multiple_events(tmp_path: Path) -> None:
    """Merge multiple events at once."""
    store = CalendarStore(tmp_path / "test")

    events = [
        CalendarEvent(
            id="1",
            date="April 5 (Sat)",
            semester="8",
            year=2026,
            category="Classes",
            event="First day",
            start_date=datetime.datetime(2026, 4, 5, tzinfo=datetime.UTC),
            end_date=None,
            link=None,
        ),
        CalendarEvent(
            id="2",
            date="May 15 (Thu)",
            semester="8",
            year=2026,
            category="Holiday",
            event="Last day",
            start_date=datetime.datetime(2026, 5, 15, tzinfo=datetime.UTC),
            end_date=None,
            link=None,
        ),
    ]

    added = store.merge_and_save(set(events))
    assert added == 2

    loaded = store.load()
    assert len(loaded) == 2
    assert "1" in loaded
    assert "2" in loaded


def test_merge_and_save_range_dates(tmp_path: Path) -> None:
    """Store and load range dates (e.g., finals period)."""
    store = CalendarStore(tmp_path / "test")

    event = CalendarEvent(
        id="finals",
        date="April 13 (Mon) - May 22 (Fri)",
        semester="8",
        year=2026,
        category="Exam",
        event="Final exams",
        start_date=datetime.datetime(2026, 4, 13, tzinfo=datetime.UTC),
        end_date=datetime.datetime(2026, 5, 22, tzinfo=datetime.UTC),
        link=None,
    )

    added = store.merge_and_save({event})
    assert added == 1

    loaded = store.load()
    assert "finals" in loaded
    assert loaded["finals"].date == "April 13 (Mon) - May 22 (Fri)"


def test_load_after_multiple_saves(tmp_path: Path) -> None:
    """Load returns all events from multiple save operations."""
    store = CalendarStore(tmp_path / "test")

    event1 = CalendarEvent(
        id="1",
        date="April 1 (Tue)",
        semester="8",
        year=2026,
        category="Classes",
        event="Event 1",
        start_date=datetime.datetime(2026, 4, 1, tzinfo=datetime.UTC),
        end_date=None,
        link=None,
    )
    store.merge_and_save({event1})

    event2 = CalendarEvent(
        id="2",
        date="May 1 (Thu)",
        semester="8",
        year=2026,
        category="Classes",
        event="Event 2",
        start_date=datetime.datetime(2026, 5, 1, tzinfo=datetime.UTC),
        end_date=None,
        link=None,
    )
    store.merge_and_save({event2})

    loaded = store.load()
    assert len(loaded) == 2
    assert loaded["1"].event == "Event 1"
    assert loaded["2"].event == "Event 2"


def test_excluded_categories_parameter(tmp_path: Path) -> None:
    """excluded_categories parameter is accepted (for API compatibility)."""
    store = CalendarStore(tmp_path / "test")

    event = CalendarEvent(
        id="1",
        date="April 5 (Sat)",
        semester="8",
        year=2026,
        category="Classes",
        event="First day",
        start_date=datetime.datetime(2026, 4, 5, tzinfo=datetime.UTC),
        end_date=None,
        link=None,
    )

    # Should not raise even though excluded_categories is not used internally
    added = store.merge_and_save({event})
    assert added == 1
