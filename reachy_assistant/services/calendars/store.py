"""Read/write calendar events to SQLite with Alembic migrations."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from reachy_assistant.services.calendars.event import CalendarEvent

LOGGER = logging.getLogger(__name__)


class CalendarStore:
    """Manages persistent storage of calendar events in SQLite."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize the calendar store.

        Args:
            storage_path: Path to the SQLite database file.
        """
        db_path = Path(storage_path).with_suffix(".db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{db_path.resolve()}"
        self._engine = create_engine(db_url)
        self._run_migrations()

    def _run_migrations(self) -> None:
        """Run pending Alembic migrations on startup."""
        try:
            # Find alembic.ini in project root
            alembic_ini = Path(__file__).parent.parent.parent.parent / "alembic.ini"
            if not alembic_ini.exists():
                LOGGER.warning("alembic.ini not found, skipping migrations")
                return

            cfg = Config(str(alembic_ini))
            cfg.set_main_option("sqlalchemy.url", str(self._engine.url))
            command.upgrade(cfg, "head")
            LOGGER.info("Alembic migrations completed successfully")
        except Exception:  # pylint: disable=broad-exception-caught
            LOGGER.exception("Failed to run Alembic migrations")
            raise

    def load(self) -> dict[str, CalendarEvent]:
        """Load all stored calendar events.

        Returns:
            A dictionary keyed by event `id`. Empty dict if table doesn't exist.
        """
        try:
            with self._engine.connect() as conn:
                query = text(
                    """
                    SELECT id, date, semester, year, category, event, start_date, end_date, link
                    FROM calendar_events
                    """
                )
                rows = conn.execute(query).mappings().all()
            return {row["id"]: CalendarEvent.model_validate(dict(row)) for row in rows}
        except Exception as e:  # noqa: BLE001 pylint: disable=broad-exception-caught
            LOGGER.warning("Calendar store load failed: %s", e, exc_info=True)
            return {}

    def merge_and_save(
        self,
        new_events: set[CalendarEvent],
    ) -> int:
        """Merge new events into the store and save to database.

        New events take precedence over existing events with the same id (for corrections).

        Args:
            new_events: Set of calendar events to merge in.
            excluded_categories: Optional list of categories to exclude (currently unused).

        Returns:
            Number of net-new events added (after deduplication).
        """
        before = self._count()

        with self._engine.begin() as conn:
            for ev in new_events:
                conn.execute(
                    text(
                        """
                        INSERT OR REPLACE INTO calendar_events
                            (id, date, semester, year, category, event, start_date, end_date, link, scraped_at)
                        VALUES (:id, :date, :semester, :year, :category, :event, :start_date, :end_date, :link, :scraped_at)
                        """
                    ),
                    {
                        **ev.model_dump(),
                        "scraped_at": datetime.now(UTC).isoformat(),
                    },
                )

        after = self._count()
        added = after - before

        LOGGER.info(
            "Calendar store saved: %d total events (added %d new)",
            after,
            added,
        )

        return added

    def _count(self) -> int:
        """Count total events in the store."""
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM calendar_events"))
                return result.scalar() or 0
        except Exception:  # noqa: BLE001 pylint: disable=broad-exception-caught
            return 0
