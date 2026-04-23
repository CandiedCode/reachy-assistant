"""Unit tests for the cron job registry and decorator."""

import threading
import types

import pytest

from reachy_assistant.services import registry
from reachy_assistant.services.registry import CronJobEntry, Startable, build_registry, cron_job
from reachy_assistant.services.status import ServiceStatus


class MockScheduler:
    """Mock scheduler that implements the Startable protocol."""

    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self, stop_event: threading.Event) -> None:  # noqa: ARG002 # pylint: disable=unused-argument
        """Simulate starting the scheduler.

        Args:
            stop_event: A threading.Event that would signal when to stop (not used in this mock).
        """
        self.started = True

    def stop(self) -> None:
        """Simulate stopping the scheduler."""
        self.stopped = True


@pytest.fixture(scope="function")
def clean_registry(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Clear the global factory registry before each test."""
    monkeypatch.setattr(registry, "_FACTORY_REGISTRY", [])
    return registry


@pytest.mark.usefixtures("clean_registry")
class TestCronJobDecorator:
    """Test the @cron_job decorator registration."""

    def test_decorator_registers_factory(self) -> None:
        """@cron_job adds the factory to the registry."""

        @cron_job(name="test_job")
        def _register() -> CronJobEntry | None:
            return None

        assert len(registry._FACTORY_REGISTRY) == 1
        name, factory = registry._FACTORY_REGISTRY[0]
        assert name == "test_job"
        assert factory is _register

    def test_decorator_returns_function_unchanged(self) -> None:
        """The decorated function is still callable."""

        @cron_job(name="test_job")
        def _register() -> CronJobEntry | None:
            return None

        # Should be able to call the function directly
        result = _register()
        assert result is None

    def test_multiple_decorators_register_multiple_factories(self) -> None:
        """Multiple @cron_job decorators all register."""

        @cron_job(name="job1")
        def _register1() -> CronJobEntry | None:
            return None

        @cron_job(name="job2")
        def _register2() -> CronJobEntry | None:
            return None

        assert len(registry._FACTORY_REGISTRY) == 2
        names = [name for name, _ in registry._FACTORY_REGISTRY]
        assert names == ["job1", "job2"]


@pytest.mark.usefixtures("clean_registry")
class TestBuildRegistry:
    """Test the build_registry function."""

    def test_build_registry_enabled_job(self) -> None:
        """build_registry calls the factory and returns the entry."""

        @cron_job(name="test_job")
        def _register() -> CronJobEntry | None:
            scheduler = MockScheduler()
            status = ServiceStatus(name="test_job", enabled=True)
            return CronJobEntry(name="test_job", scheduler=scheduler, status=status)

        entries = build_registry()
        assert len(entries) == 1
        assert entries[0].name == "test_job"
        assert isinstance(entries[0].scheduler, MockScheduler)

    def test_build_registry_disabled_job(self) -> None:
        """build_registry skips factories that return None."""

        @cron_job(name="disabled_job")
        def _register() -> CronJobEntry | None:
            return None

        entries = build_registry()
        assert len(entries) == 0

    def test_build_registry_mixed_enabled_disabled(self) -> None:
        """build_registry returns only enabled jobs."""

        @cron_job(name="enabled")
        def _register_enabled() -> CronJobEntry | None:
            scheduler = MockScheduler()
            status = ServiceStatus(name="enabled", enabled=True)
            return CronJobEntry(name="enabled", scheduler=scheduler, status=status)

        @cron_job(name="disabled")
        def _register_disabled() -> CronJobEntry | None:
            return None

        entries = build_registry()
        assert len(entries) == 1
        assert entries[0].name == "enabled"

    def test_build_registry_calls_factories_with_no_args(self) -> None:
        """build_registry calls each factory with no arguments."""
        call_count = []

        @cron_job(name="test")
        def _register() -> CronJobEntry | None:
            call_count.append(1)
            return None

        build_registry()
        assert len(call_count) == 1

    def test_build_registry_factory_internal_config(self) -> None:
        """Factory can instantiate its own config to decide enable/disable."""

        @cron_job(name="conditional")
        def _register() -> CronJobEntry | None:
            should_enable = True
            if not should_enable:
                return None
            scheduler = MockScheduler()
            status = ServiceStatus(name="conditional", enabled=True)
            return CronJobEntry(name="conditional", scheduler=scheduler, status=status)

        # Factory can choose to return None (disabled) or a CronJobEntry (enabled)
        entries = build_registry()
        assert len(entries) == 1


class TestStartableProtocol:
    """Test the Startable protocol."""

    def test_startable_protocol_runtime_check(self) -> None:
        """Objects with start() and stop() methods are Startable."""
        mock = MockScheduler()
        assert isinstance(mock, Startable)

    def test_startable_protocol_requires_both_methods(self) -> None:
        """Objects missing start() or stop() are not Startable."""

        class PartialScheduler:
            """Mocks a scheduler that only has start() but not stop()."""
            def start(self, stop_event: threading.Event) -> None:
                """Simulate starting the scheduler."""

        partial = PartialScheduler()
        assert not isinstance(partial, Startable)


class TestCronJobEntry:
    """Test the CronJobEntry dataclass."""

    def test_entry_creation(self) -> None:
        """CronJobEntry stores name, scheduler, and status."""
        scheduler = MockScheduler()
        status = ServiceStatus(name="test", enabled=True)
        entry = CronJobEntry(name="test_job", scheduler=scheduler, status=status)

        assert entry.name == "test_job"
        assert entry.scheduler is scheduler
        assert entry.status is status

    def test_entry_scheduler_implements_startable(self) -> None:
        """Entry's scheduler must be Startable."""
        scheduler = MockScheduler()
        status = ServiceStatus(name="test", enabled=True)
        entry = CronJobEntry(name="test", scheduler=scheduler, status=status)

        assert hasattr(entry.scheduler, "start")
        assert hasattr(entry.scheduler, "stop")
