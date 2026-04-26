"""YOLO-based face detection service running in a background thread."""

import logging
import threading

import numpy as np
from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose
from ultralytics import YOLO
from pathlib import Path
import numpy as np
import numpy.typing as npt

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
        self.model = None
        self.thread: threading.Thread | None = None
        self.reachy_mini = reachy_mini
        self.max_retries = 5
        self.frame_height, self.frame_width = self.get_frame_size(reachy_mini)
        self.x_center = (self.frame_width / 2) if self.frame_width > 0 else 0
        self.y_center = (self.frame_height / 2) if self.frame_height > 0 else 0
        self._load_model()  # Load model synchronously during initialization

    def get_frame_size(self, reachy_mini: ReachyMini) -> tuple[int, int]:
        """Get the frame width and height from the Reachy camera."""
        frame = reachy_mini.media.get_frame()
        if frame is not None:
            height, width = frame.shape[:2]
            LOGGER.info("Camera frame size: width=%d height=%d", width, height)
            return height, width

        LOGGER.warning("Unable to get frame size from Reachy camera")
        return 0, 0

    def _load_model(self) -> None:
        """Load the YOLO model and downloads if needed."""
        LOGGER.info("Loading YOLO model: %s", self.model_name)

        path = Path("yolo26n_ncnn_model")
        if path.is_dir():
            self.model = YOLO("yolo26n_ncnn_model")
        else:
            model = YOLO(self.model_name, task="detect")
            model.export(format="ncnn")  # creates 'yolo26n_ncnn_model'
            self.model = YOLO("yolo26n_ncnn_model", task="detect")

    def start(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        """Start the face tracker in a background thread.

        Args:
            reachy_mini: ReachyMini instance (for media.get_frame).
            stop_event: threading.Event to signal shutdown.
        """
        LOGGER.info(
            "Starting FaceTrackerService with model: %s threshold: %.2f",
            self.model_name,
            self.confidence_threshold,
        )

        if self.model is None:
            LOGGER.error("Model failed to load. Face tracking is disabled")
            return

        self.thread = threading.Thread(target=self._run, args=(reachy_mini, stop_event), daemon=True)
        self.thread.start()
        LOGGER.info("FaceTracker Service thread started")

    def get_center(self, bbox: npt.NDArray[np.float32]) -> tuple[float, float]:
        """Calculate the center of a bounding box."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        return cx, cy

    def stop(self) -> None:
        """Stop the face tracker."""
        if self.thread is not None and self.thread.is_alive():
            LOGGER.info("Stopping FaceTracker Service")
            # Thread will exit naturally when stop_event is set
            # Just wait a moment for graceful shutdown
            self.thread.join(timeout=2.0)
        self._cleanup()

    def create_head_pose(self, cx: float, cy: float) -> tuple[float, float]:
        """Create a head pose dict based on face position vis proportional controller."""
        face_tracking_kp = 15.0 # proportional gain
        error_u = (cx - self.frame_width / 2) / (self.frame_width / 2) # how far is the face from the center horizontally
        error_v = (cy - self.frame_height / 2) / (self.frame_height / 2) # how far is the face from the center vertically

        # dead zone
        if abs(error_u) < 0.05:
            error_u = 0
        if abs(error_v) < 0.05:
            error_v = 0

        target_yaw = -face_tracking_kp * error_u # turn in opposite direction of error (negative sign) let and right movement
        target_pitch = -face_tracking_kp * error_v # turn in opposite direction of error (negative sign) up and down movement
        return target_yaw, target_pitch

    def predict(self, frame: npt.NDArray[np.uint8]):
        results = self.model(frame)
        for r in results:
            if r.boxes is None:
                continue
            class_ids = r.boxes.cls.cpu().numpy()
            confidences = r.boxes.conf.cpu().numpy()
            # filter to faces only
            mask = class_ids == self.FACE_CLASS_ID

            if not np.any(mask):
                continue

            print(class_ids[mask])
            print(confidences[mask])
            idx = confidences[mask].argmax()
            print(idx)

            if confidences[mask][idx] >= self.confidence_threshold:
                print("Face detected with confidence:", confidences[mask][idx])
                cx, cy = self.get_center(r.boxes.xyxy.cpu().numpy()[mask][idx])
                head_pose = self.create_head_pose(cx, cy)
                # self.reachy_mini.set_target(head=head_pose)
                self.reachy_mini.look_at_image(cx, cy, duration=0.3)



    def _run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        """Capture frames and run face detection.

        Args:
            reachy_mini: ReachyMini instance.
            stop_event: Stop signal from main app.
        """
        # Safety check (should not happen if start() succeeded)
        if self.model is None:
            LOGGER.error("Model is None in _run(), face tracking disabled")
            return

        frame_count = 0

        while not stop_event.is_set() and self.max_retries > 0:
            try:
                # Try to get frame from Reachy camera first
                frame = reachy_mini.media.get_frame()
            except Exception: # pylint: disable=broad-except
                LOGGER.exception("Failed to get frame from Reachy camera")
                self.max_retries -= 1
                continue

            if frame is None:
                LOGGER.exception("No frame received from Reachy camera")
                self.max_retries -= 1
                continue

            try:
                results = self.model(frame, verbose=False)
            except Exception as e: # pylint: disable=broad-except
                LOGGER.exception("Model inference failed")
                self.max_retries -= 1
                continue

            # Extract detections
            face_detected = False
            best_confidence = 0.0
            best_cx = self.x_center
            best_cy = self.y_center

            if results and len(results) > 0:
                boxes = results[0].boxes
                if boxes is not None and len(boxes) > 0:
                    # Filter for 'person' class (index 0 in COCO dataset)
                    # Get class indices if available
                    if hasattr(boxes, "cls"):
                        class_ids = boxes.cls.cpu().numpy()
                        confidences = boxes.conf.cpu().numpy()

                        # Find person with highest confidence
                        person_mask = class_ids == 0  # 0 = person class
                        if np.any(person_mask):
                            person_confidence = confidences[person_mask]
                            person_idx_in_filtered = np.argmax(person_confidence)

                            # Map back to original index
                            all_person_indices = np.where(person_mask)[0]
                            best_idx = all_person_indices[person_idx_in_filtered]
                            best_confidence = float(confidences[best_idx])

                            # Only report if above threshold
                            if best_confidence >= self.confidence_threshold:
                                # Get bounding box
                                box = boxes.xyxy[best_idx].cpu().numpy()
                                x1, y1, x2, y2 = box

                                # Compute centroid
                                best_cx = (x1 + x2) / 2.0
                                best_cy = (y1 + y2) / 2.0
                                face_detected = True
                    else:
                        # Fallback: just use highest confidence detection
                        confidences = boxes.conf.cpu().numpy()
                        if len(confidences) > 0:
                            best_idx = np.argmax(confidences)
                            best_confidence = float(confidences[best_idx])

                            if best_confidence >= self.confidence_threshold:
                                box = boxes.xyxy[best_idx].cpu().numpy()
                                x1, y1, x2, y2 = box
                                best_cx = (x1 + x2) / 2.0
                                best_cy = (y1 + y2) / 2.0
                                face_detected = True


            self.move_reachy(face_detected, best_cx, best_cy, self.reachy_mini)


    def move_reachy(self, face_detected: bool, cx: float, cy: float, reachy_mini: ReachyMini) -> None:
        if face_detected:
            face_tracking_kp = 25.0
            error_u = (cx - self.frame_width / 2) / (self.frame_width / 2)
            error_v = (cy - self.frame_height / 2) / (self.frame_height / 2)
            target_yaw = -face_tracking_kp * error_u
            target_pitch = -face_tracking_kp * error_v
            head_pose = create_head_pose(yaw=target_yaw, pitch=target_pitch, degrees=True)
        else:
            head_pose = create_head_pose()  # Neutral pose when no face detected

        reachy_mini.set_target(head=head_pose)

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self.model is not None:
            LOGGER.info("Unloading YOLO model")
            # YOLO cleanup if needed
            self.model = None
