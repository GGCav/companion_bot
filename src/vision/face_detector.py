"""
Face Detection using MediaPipe and OpenCV
Optimized for Pi Camera v2
Pending implementation
"""

import cv2
import mediapipe as mp
import numpy as np
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class FaceDetector:
    """Detects faces in camera frames"""

    def __init__(self, config: dict):
        """Initialize face detector"""
        self.config = config
        self.face_config = config['vision']['face']
        self.processing_config = config['vision']['processing']


        self.mp_face_detection = mp.solutions.face_detection
        self.detector = self.mp_face_detection.FaceDetection(
            min_detection_confidence=self.processing_config['min_detection_confidence']
        )


        self.haar_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        self.use_mediapipe = True
        logger.info("Face detector initialized")

    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in frame

        Args:
            frame: BGR image

        Returns:
            List of face bounding boxes [(x, y, w, h), ...]
        """
        if self.use_mediapipe:
            try:
                return self._detect_mediapipe(frame)
            except Exception as e:
                logger.warning(f"MediaPipe detection failed: {e}, using Haar Cascade")
                self.use_mediapipe = False

        return self._detect_haar(frame)

    def _detect_mediapipe(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using MediaPipe"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.detector.process(rgb_frame)

        faces = []
        if results.detections:
            h, w = frame.shape[:2]
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                faces.append((x, y, width, height))

        return faces

    def _detect_haar(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using Haar Cascade"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.haar_cascade.detectMultiScale(gray, 1.1, 4)
        return [tuple(face) for face in faces]

    def draw_faces(self, frame: np.ndarray, faces: List[Tuple[int, int, int, int]]) -> np.ndarray:
        """Draw bounding boxes around detected faces"""
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return frame

    def cleanup(self):
        """Clean up resources"""
        self.detector.close()
        logger.info("Face detector cleanup complete")
