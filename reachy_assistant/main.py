import threading
import time

from reachy_mini import ReachyMini, ReachyMiniApp

from reachy_assistant import settings
from reachy_assistant.services.jobs import Jobs


class ReachyAssistant(ReachyMiniApp):
    settings = settings.Settings()
    custom_app_url = settings.custom_app_url

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event):

        # Get the configured Jobs and start them
        jobs = Jobs()
        jobs.start(stop_event)

        # type narrowing
        assert self.settings_app is not None, "Settings app is not initialized"

        # Service status endpoint
        @self.settings_app.get("/status/services")
        def get_service_statuses():
            """Return the status of all registered services.

            Returns:
                A list of service status dictionaries, one for each registered job.
            """
            cron_statuses = [s.as_dict() for s in jobs.statuses]
            return {"services": cron_statuses}

        @self.settings_app.get("/status/services/{service_name}")
        def get_service_status(service_name: str):
            """Return the status of a specific service by name.

            Args:
                service_name: The name of the service to query (e.g. "gatech_calendar")

            Returns:
                A dictionary representing the status of the specified service, or None if not found.
            """
            status = jobs.status(service_name)
            return {"status": status.as_dict() if status else None}

        # Main control loop
        while not stop_event.is_set():
            time.sleep(0.02)


if __name__ == "__main__":
    app = ReachyAssistant()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()
