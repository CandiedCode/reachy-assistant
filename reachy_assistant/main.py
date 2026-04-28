"""Main entry point for the Reachy Assistant app."""

import logging
import threading
import time

from reachy_mini import ReachyMini, ReachyMiniApp
from reachy_mini.utils import create_head_pose

from reachy_assistant import settings, tracker
from reachy_assistant.log_config import configure_logging
from reachy_assistant.services.jobs import Jobs

configure_logging()
LOGGER = logging.getLogger(__name__)


class ReachyAssistant(ReachyMiniApp):
    """Reachy Personal Asisstant App."""

    settings = settings.Settings()
    custom_app_url = settings.custom_app_url

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        """Run main entry point for the Reachy Assistant app.

        Args:
            reachy_mini: The ReachyMini instance provided by the framework.
            stop_event: A threading.Event that will be set when the app should stop.
        """

        # type narrowing
        assert self.settings_app is not None, "Settings app is not initialized"
        face_tracker = tracker.FaceTracker(reachy_mini, model_name="yolov8n-face.pt", confidence_threshold=0.5)

        # Get the configured Jobs and start them
        jobs = Jobs()
        jobs.start(stop_event)
        jobs.include_routers(self.settings_app)

        # Main control loop
        while not stop_event.is_set():
            yaw, pitch = face_tracker.predict(frame=reachy_mini.media.get_frame())
            head_pose = create_head_pose(yaw=yaw, pitch=pitch, degrees=True)
            reachy_mini.set_target(head=head_pose)
            time.sleep(0.02)


if __name__ == "__main__":
    app = ReachyAssistant()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()
