"""YOLO-based face detection service running in a background thread."""

import logging
from pathlib import Path

import numpy as np
import numpy.typing as npt
from reachy_mini import ReachyMini
from ultralytics import YOLO

LOGGER = logging.getLogger(__name__)


class FaceTracker:
    """Detects faces in camera frames using YOLO and updates shared state.

    Runs face detection in a background daemon thread. On each frame:
    1. Captures frame from Reachy camera
    2. Runs YOLO inference
    3. Finds the face with highest confidence
    4. Updates FaceTrackingState with pixel coordinates
    """

    FACE_CLASS_ID = 0

    def __init__(
        self,
        reachy_mini: ReachyMini,
        model_name: str,
        confidence_threshold: float = 0.5,
    ) -> None:
        """Initialize the face tracker.

        Args:
            reachy_mini: ReachyMini instance for camera access.
            model_name: YOLO model to use.
            confidence_threshold: Minimum confidence to report detection.
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.reachy_mini = reachy_mini
        self.max_retries = 5
        self.frame_height, self.frame_width = self.get_frame_size(reachy_mini)
        self.x_center = (self.frame_width / 2) if self.frame_width > 0 else 0
        self.y_center = (self.frame_height / 2) if self.frame_height > 0 else 0
        self.model = self._load_model()

    def get_frame_size(self, reachy_mini: ReachyMini) -> tuple[int, int]:
        """Get the frame width and height from the Reachy camera.

        Args:
            reachy_mini: ReachyMini instance to access the camera.

        Returns:
            Tuple of (frame_height, frame_width) if successful, otherwise (0, 0).
        """
        frame = reachy_mini.media.get_frame()
        if frame is not None:
            height, width = frame.shape[:2]
            LOGGER.info("Camera frame size: width=%d height=%d", width, height)
            return height, width

        LOGGER.warning("Unable to get frame size from Reachy camera")
        return 0, 0

    def _load_model(self) -> YOLO | None:
        """Load the YOLO model and downloads if needed."""
        LOGGER.info("Loading YOLO model: %s", self.model_name)

        path = Path("yolo26n_ncnn_model")
        # If we have already exported the NCNN model use this
        if path.is_dir():
            model = YOLO("yolo26n_ncnn_model", task="detect")
        # else create it by exporting the format to ncnn
        # See https://docs.ultralytics.com/guides/raspberry-pi/ for more information
        else:
            model = YOLO(self.model_name, task="detect")
            model.export(format="ncnn")  # creates 'yolo26n_ncnn_model'
            model = YOLO("yolo26n_ncnn_model", task="detect")

        return model

    def get_center(self, bbox: npt.NDArray[np.float32]) -> tuple[float, float]:
        """Calculate the center of a bounding box.

        Args:
            bbox: Bounding box in the format [x1, y1, x2, y2].

        Returns:
            Tuple of (cx, cy) representing the center coordinates of the bounding box.
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        return cx, cy

    def create_head_pose(self, cx: float, cy: float) -> tuple[float, float]:
        """Create a head pose dict based on face position vis proportional controller.

        Args:
            cx: X coordinate of the face center.
            cy: Y coordinate of the face center.

        Returns:
            Tuple of (target_yaw, target_pitch) representing the desired head pose angles.
        """
        face_tracking_kp = 35.0  # proportional gain
        error_u = (cx - self.frame_width / 2) / (self.frame_width / 2)  # face from the center horizontally
        error_v = (cy - self.frame_height / 2) / (self.frame_height / 2)  # face from the center vertically

        target_yaw = -face_tracking_kp * error_u  # turn in opposite direction of error, negative sign, let and right movement
        target_pitch = face_tracking_kp * error_v  # turn in opposite direction of error, negative sign, up and down movement
        return target_yaw, target_pitch

    def predict(self, frame: npt.NDArray[np.uint8] | None) -> tuple[float, float]:
        """Run YOLO inference on the given frame and return head pose if a face is detected.

        Args:
            frame: Image frame from the camera.

        Returns:
            Tuple of (yaw, pitch) representing the head pose if a face is detected, otherwise None.
        """
        if self.model is None:
            LOGGER.warning("Model not loaded")
            return 0, 0

        if frame is None:
            LOGGER.warning("No frame provided for prediction")
            return 0, 0

        # perform inferencing on image frame, scale image size down for an optimization
        results = self.model(source=frame, imgsz=640)

        # iterate over the results per class
        for r in results:
            if r.boxes is None:
                LOGGER.warning("No boxes in result")
                continue

            # get the class id's
            class_ids = r.boxes.cls.cpu().numpy()
            # filter to faces only
            mask = class_ids == self.FACE_CLASS_ID

            if not np.any(mask):
                LOGGER.info("No faces detected in this frame")
                continue

            # confidences for each detection
            confidences = r.boxes.conf.cpu().numpy()

            # get the id of the face with the highest confidence score
            idx = confidences[mask].argmax()
            confidence = confidences[mask][idx]
            LOGGER.debug("Highest face confidence: %f (threshold: %f)", confidence, self.confidence_threshold)

            # if the face has met the minimum confidence threshold
            if confidence >= self.confidence_threshold:
                cx, cy = self.get_center(r.boxes.xyxy.cpu().numpy()[mask][idx])
                head_pose = self.create_head_pose(cx, cy)
                return head_pose

        return 0, 0
