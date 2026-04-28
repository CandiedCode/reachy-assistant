"""Main entry point for the Reachy Assistant app."""

import logging
import threading
import time

from reachy_mini import ReachyMini, ReachyMiniApp
from reachy_mini.utils import create_head_pose

from reachy_assistant import settings, tracker
from reachy_assistant.services.jobs import Jobs

LOGGER = logging.getLogger(__name__)


class ReachyAssistant(ReachyMiniApp):
    """Reachy Personal Assistant App."""

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

        face_tracker = (
            tracker.FaceTracker(reachy_mini, model_name="yolov8n-face.pt", confidence_threshold=0.5)
            if self.settings.face_tracking_enabled
            else None
        )

        # Get the configured Jobs and start them
        jobs = Jobs()
        jobs.start(stop_event)
        jobs.include_routers(self.settings_app)

        # run face detection every 5th frame (~10 Hz)
        frame_count = 0
        last_yaw, last_pitch = 0, 0

        # Main control loop
        while not stop_event.is_set():
            frame_count += 1
            if frame_count % 5 == 0 and face_tracker is not None:
                last_yaw, last_pitch = face_tracker.predict(frame=reachy_mini.media.get_frame())
                head_pose = create_head_pose(yaw=last_yaw, pitch=last_pitch, degrees=True)

                reachy_mini.set_target(head=head_pose)

            time.sleep(0.02)


if __name__ == "__main__":
    app = ReachyAssistant()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()
