"""Unit tests for the Jobs orchestrator."""

import threading
from collections.abc import Callable

import pytest

from reachy_assistant.services.jobs import Jobs
from reachy_assistant.services.registry import CronJobEntry, Startable
from reachy_assistant.services.status import ServiceStatus

type BuildRegistry = Callable[[list[CronJobEntry]], Callable[[], list[CronJobEntry]]]


class MockScheduler:
    """Mock scheduler implementing Startable protocol."""

    def __init__(self, name: str = "mock") -> None:
        """Initialize the mock scheduler.

        Args:
            name: Optional name for identification in tests.
        """
        self.name = name
        self.start_called = False
        self.stop_called = False
        self.start_stop_event = None

    def start(self, stop_event: threading.Event) -> None:
        """Simulate starting the scheduler."""
        self.start_called = True
        self.start_stop_event = stop_event

    def stop(self) -> None:
        """Simulate stopping the scheduler."""
        self.stop_called = True


def create_test_job(job_name: str, enabled: bool = True) -> tuple[MockScheduler, "ServiceStatus", CronJobEntry]:
    """Create a test job with MockScheduler, ServiceStatus, and CronJobEntry.

    Args:
        job_name: The name of the job.
        enabled: Whether the job is enabled (default: True).

    Returns:
        Tuple of (scheduler, status, entry).
    """
    scheduler = MockScheduler(job_name)
    status = ServiceStatus(name=f"{job_name}_status", enabled=enabled)
    entry = CronJobEntry(name=job_name, scheduler=scheduler, status=status)
    return scheduler, status, entry


@pytest.fixture
def mock_build_registry(monkeypatch: pytest.MonkeyPatch) -> BuildRegistry:
    """Fixture to mock build_registry for isolated Jobs tests."""

    def _mock_build(entries: list[CronJobEntry]) -> Callable[[], list[CronJobEntry]]:
        def mock_fn() -> list[CronJobEntry]:
            return entries

        monkeypatch.setattr(
            "reachy_assistant.services.jobs.build_registry",
            mock_fn,
        )
        return mock_fn

    return _mock_build


class TestJobsInitialization:
    """Test Jobs initialization and discovery."""

    def test_jobs_init_calls_build_registry(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.__init__ calls build_registry."""
        mock_build_registry([])
        jobs = Jobs()
        assert jobs.entries == []

    def test_jobs_discovers_enabled_jobs(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs stores entries returned by build_registry."""
        _, _, entry1 = create_test_job("job1")
        _, _, entry2 = create_test_job("job2")

        mock_build_registry([entry1, entry2])
        jobs = Jobs()

        assert [entry.name for entry in jobs.entries] == ["job1", "job2"]

    def test_jobs_empty_when_no_enabled_jobs(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs has no entries when all jobs are disabled."""
        mock_build_registry([])
        jobs = Jobs()
        assert jobs.entries == []


class TestJobsStart:
    """Test starting all jobs."""

    def test_start_calls_all_schedulers(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.start() calls start() on every scheduler."""
        scheduler1, _, entry1 = create_test_job("job1")
        scheduler2, _, entry2 = create_test_job("job2")

        mock_build_registry([entry1, entry2])
        jobs = Jobs()
        stop_event = threading.Event()

        jobs.start(stop_event)

        assert scheduler1.start_called
        assert scheduler2.start_called
        assert scheduler1.start_stop_event is stop_event
        assert scheduler2.start_stop_event is stop_event

    def test_start_with_no_jobs(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.start() succeeds even with no jobs."""
        mock_build_registry([])
        jobs = Jobs()
        stop_event = threading.Event()

        # Should not raise
        jobs.start(stop_event)


class TestJobsStop:
    """Test stopping all jobs."""

    def test_stop_calls_all_schedulers(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.stop() calls stop() on every scheduler."""
        scheduler1, _, entry1 = create_test_job("job1")
        scheduler2, _, entry2 = create_test_job("job2")

        mock_build_registry([entry1, entry2])
        jobs = Jobs()

        jobs.stop()

        assert scheduler1.stop_called
        assert scheduler2.stop_called

    def test_stop_with_no_jobs(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.stop() succeeds even with no jobs."""
        mock_build_registry([])
        jobs = Jobs()

        # Should not raise
        jobs.stop()

    def test_stop_gracefully_handles_missing_stop_method(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.stop() gracefully skips schedulers without stop() method."""

        class NoStopScheduler(Startable):
            def start(self, stop_event: threading.Event) -> None:
                """Mock start method."""

        scheduler = NoStopScheduler()
        status = ServiceStatus(name="job_status", enabled=True)
        # Using cast to bypass the protocol check for this test case
        entry = CronJobEntry(
            name="job",
            scheduler=scheduler,
            status=status,  # type: ignore[arg-type]
        )

        mock_build_registry([entry])
        jobs = Jobs()

        jobs.stop()


class TestJobsStatuses:
    """Test the statuses property."""

    def test_statuses_returns_all_status_objects(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.statuses returns a list of all ServiceStatus objects."""
        _, status1, entry1 = create_test_job("job1", enabled=True)
        _, status2, entry2 = create_test_job("job2", enabled=False)

        mock_build_registry([entry1, entry2])
        jobs = Jobs()

        statuses = jobs.statuses
        assert statuses == [status1, status2]

    def test_statuses_empty_when_no_jobs(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.statuses returns empty list when no jobs are registered."""
        mock_build_registry([])
        jobs = Jobs()
        assert jobs.statuses == []

    def test_statuses_for_api_response(self, mock_build_registry: BuildRegistry) -> None:
        """Statuses can be serialized for API response."""
        _, _, entry = create_test_job("job")

        mock_build_registry([entry])
        jobs = Jobs()

        # Should be able to call as_dict() on each status
        status_dicts = [s.as_dict() for s in jobs.statuses]
        assert status_dicts[0]["name"] == "job_status"
        assert status_dicts[0]["enabled"] is True


class TestJobsGetScheduler:
    """Test scheduler lookup by name."""

    def test_get_scheduler_by_name(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.get_scheduler(name) returns the scheduler for that job."""
        scheduler1, _, entry1 = create_test_job("job1")
        scheduler2, _, entry2 = create_test_job("job2")

        mock_build_registry([entry1, entry2])
        jobs = Jobs()

        assert jobs.get_scheduler("job1") is scheduler1
        assert jobs.get_scheduler("job2") is scheduler2

    def test_get_scheduler_returns_none_for_missing(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.get_scheduler(name) returns None if job not found."""
        _, _, entry = create_test_job("job1")

        mock_build_registry([entry])
        jobs = Jobs()

        assert jobs.get_scheduler("nonexistent") is None

    def test_get_scheduler_with_no_jobs(self, mock_build_registry: BuildRegistry) -> None:
        """Jobs.get_scheduler() returns None when no jobs exist."""
        mock_build_registry([])
        jobs = Jobs()
        assert jobs.get_scheduler("any_name") is None


class TestJobsIntegration:
    """Integration tests for Jobs with multiple operations."""

    def test_full_lifecycle(self, mock_build_registry: BuildRegistry) -> None:
        """Full job lifecycle: init -> start -> stop."""
        scheduler, _, entry = create_test_job("test_job")

        mock_build_registry([entry])
        jobs = Jobs()

        stop_event = threading.Event()
        jobs.start(stop_event)
        assert scheduler.start_called

        jobs.stop()
        assert scheduler.stop_called

    def test_multiple_jobs_independent_control(self, mock_build_registry: BuildRegistry) -> None:
        """Multiple jobs can be started and stopped independently."""
        job_data = [create_test_job(f"job{i}") for i in range(3)]
        schedulers = [s for s, _, _ in job_data]
        entries = [e for _, _, e in job_data]

        mock_build_registry(entries)
        jobs = Jobs()
        stop_event = threading.Event()

        jobs.start(stop_event)
        for scheduler in schedulers:
            assert scheduler.start_called

        jobs.stop()
        for scheduler in schedulers:
            assert scheduler.stop_called
