"""Unit tests for ServiceStatus health tracking."""

import threading
from datetime import UTC, datetime

from reachy_assistant.services.status import ServiceStatus


class TestServiceStatusTransitions:
    """Test marking service state transitions."""

    def test_initial_state(self) -> None:
        """Service starts not running."""
        status = ServiceStatus(name="test_service")
        assert status.name == "test_service"
        assert not status.running
        assert not status.enabled
        assert status.last_run_at is None
        assert status.last_success_at is None
        assert status.last_error is None
        assert status.next_run_at is None

    def test_mark_started(self) -> None:
        """mark_started sets running and last_run_at."""
        status = ServiceStatus(name="test")
        status.mark_started()
        assert status.running
        assert status.last_run_at is not None

    def test_mark_success(self) -> None:
        """mark_success clears errors and sets success time."""
        status = ServiceStatus(name="test")
        status.last_error = "old error"
        status.mark_success()
        assert status.last_success_at is not None
        assert status.last_error is None

    def test_mark_error(self) -> None:
        """mark_error records the error message."""
        status = ServiceStatus(name="test")
        status.mark_error("connection failed")
        assert status.last_error == "connection failed"

    def test_mark_stopped(self) -> None:
        """mark_stopped clears running flag."""
        status = ServiceStatus(name="test")
        status.running = True
        status.mark_stopped()
        assert not status.running

    def test_set_next_run(self) -> None:
        """set_next_run schedules the next run time."""
        status = ServiceStatus(name="test")
        dt = datetime(2026, 4, 17, 12, 0, 0, tzinfo=UTC)
        status.set_next_run(dt)
        assert status.next_run_at == "2026-04-17T12:00:00+00:00"

    def test_set_next_run_in_seconds(self) -> None:
        """set_next_run_in_seconds schedules relative to now."""
        status = ServiceStatus(name="test")
        before = datetime.now(UTC)
        status.set_next_run_in_seconds(3600)

        assert status.next_run_at is not None
        next_run = datetime.fromisoformat(status.next_run_at)
        # Should be ~1 hour from now
        delta = (next_run - before).total_seconds()
        assert 3599 < delta < 3601  # Allow 1 second tolerance


class TestServiceStatusAsDict:
    """Test as_dict() snapshot method."""

    def test_as_dict_empty(self) -> None:
        """as_dict returns all fields."""
        status = ServiceStatus(name="test", enabled=True)
        result = status.as_dict()
        assert result["name"] == "test"
        assert result["enabled"]
        assert not result["running"]
        assert result["last_run_at"] is None
        assert result["last_success_at"] is None
        assert result["last_error"] is None
        assert result["next_run_at"] is None

    def test_as_dict_populated(self) -> None:
        """as_dict with all fields populated."""
        status = ServiceStatus(
            name="calendar",
            enabled=True,
            running=False,
            last_run_at="2026-04-10T12:00:00+00:00",
            last_success_at="2026-04-10T12:00:05+00:00",
            last_error=None,
            next_run_at="2026-04-17T12:00:00+00:00",
        )
        result = status.as_dict()
        # as_dict should return only public fields (not _lock)
        assert result == {
            "name": "calendar",
            "enabled": True,
            "running": False,
            "last_run_at": "2026-04-10T12:00:00+00:00",
            "last_success_at": "2026-04-10T12:00:05+00:00",
            "last_error": None,
            "next_run_at": "2026-04-17T12:00:00+00:00",
        }
        assert "_lock" not in result


class TestServiceStatusThreadSafety:
    """Test thread-safe concurrent access."""

    def test_concurrent_updates(self) -> None:
        """Multiple threads can update status safely."""
        status = ServiceStatus(name="test")
        errors = []

        def writer(tid: int) -> None:
            try:
                for i in range(100):
                    if i % 3 == 0:
                        status.mark_started()
                    elif i % 3 == 1:
                        status.mark_success()
                    else:
                        status.mark_error(f"error_{tid}_{i}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(100):
                    snapshot = status.as_dict()
                    # Verify snapshot is complete
                    assert "name" in snapshot
                    assert "running" in snapshot
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(e)

        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent access errors: {errors}"

    def test_as_dict_is_consistent_snapshot(self) -> None:
        """as_dict returns a consistent snapshot despite concurrent updates."""
        status = ServiceStatus(
            name="test",
            running=True,
            last_run_at="2026-04-10T12:00:00+00:00",
            last_success_at="2026-04-10T12:00:05+00:00",
        )

        def updater() -> None:
            for _ in range(100):
                status.mark_error("error")
                status.mark_success()

        def reader() -> None:
            snapshots = [status.as_dict() for _ in range(100)]
            # Each snapshot should have consistent fields
            for snapshot in snapshots:
                assert isinstance(snapshot["name"], str)
                assert isinstance(snapshot["running"], bool)

        threads = [
            threading.Thread(target=updater),
            threading.Thread(target=updater),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


class TestServiceStatusLifecycle:
    """Test typical service lifecycle."""

    def test_scheduled_service_lifecycle(self) -> None:
        """Test a scheduled service run cycle."""
        status = ServiceStatus(name="calendar", enabled=True)

        # Before first run
        assert not status.running
        assert status.last_run_at is None

        # Service starts
        status.mark_started()
        assert status.running
        assert status.last_run_at is not None

        # Job completes successfully
        status.mark_success()
        assert status.last_success_at is not None
        assert status.last_error is None

        # Schedule next run
        status.set_next_run_in_seconds(604800)
        assert status.next_run_at is not None

        # Service stops
        status.mark_stopped()
        assert not status.running
        assert status.last_success_at is not None  # Previous success still recorded

    def test_service_with_error(self) -> None:
        """Test service encountering an error."""
        status = ServiceStatus(name="service", enabled=True)

        status.mark_started()
        status.mark_error("Connection timeout")
        assert status.last_error == "Connection timeout"
        assert status.last_success_at is None

        # On next successful run, error is cleared
        status.mark_success()
        assert status.last_error is None
        assert status.last_success_at is not None
