"""Thread-safe health status tracking for background services."""

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass
class ServiceStatus:
    """Health status of a background service.

    Thread-safe status tracking for services running in background threads.
    The main app thread reads via as_dict(); background threads write via mark_* methods.
    """

    name: str
    """Unique service name (e.g., 'calendar_scheduler', 'face_tracker')."""
    enabled: bool = False
    """Whether this service is configured to run."""
    running: bool = False
    """Whether the service thread is currently active."""
    last_run_at: str | None = None
    """ISO 8601 timestamp when the service last started a job/frame."""
    last_success_at: str | None = None
    """ISO 8601 timestamp when the service last completed successfully."""
    last_error: str | None = None
    """Error message from the last failure, if any."""
    next_run_at: str | None = None
    """ISO 8601 timestamp of next scheduled run (for scheduled services only)."""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def mark_started(self) -> None:
        """Mark the service as started (job/frame processing beginning)."""
        with self._lock:
            self.running = True
            self.last_run_at = datetime.now(UTC).isoformat()

    def mark_success(self) -> None:
        """Mark the last job/cycle as successful."""
        with self._lock:
            self.last_success_at = datetime.now(UTC).isoformat()
            self.last_error = None

    def mark_error(self, error: str) -> None:
        """Record an error that occurred during execution."""
        with self._lock:
            self.last_error = error

    def mark_stopped(self) -> None:
        """Mark the service as stopped."""
        with self._lock:
            self.running = False

    def set_next_run(self, dt: datetime) -> None:
        """Set the next scheduled run time (for scheduled services).

        Args:
            dt: datetime object with timezone info (typically UTC)
        """
        with self._lock:
            self.next_run_at = dt.isoformat()

    def set_next_run_in_seconds(self, seconds: int) -> None:
        """Set the next scheduled run time relative to now.

        Args:
            seconds: how many seconds from now to schedule next run
        """
        next_dt = datetime.now(UTC) + timedelta(seconds=seconds)
        self.set_next_run(next_dt)

    def as_dict(self) -> dict:
        """Return a snapshot of the status as a dictionary.

        Thread-safe snapshot for API responses.

        Returns:
            Dictionary with all status fields.
        """
        with self._lock:
            return {
                "name": self.name,
                "enabled": self.enabled,
                "running": self.running,
                "last_run_at": self.last_run_at,
                "last_success_at": self.last_success_at,
                "last_error": self.last_error,
                "next_run_at": self.next_run_at,
            }
