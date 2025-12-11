"""
Face Recognition for user identification
Stores and recognizes known users
"""

import cv2
import numpy as np
import pickle
import logging
from pathlib import Path
from typing import Optional, Dict, List
import face_recognition

logger = logging.getLogger(__name__)


class FaceRecognizer:
    """Recognizes known faces and manages user encodings"""

    def __init__(self, config: dict):
        """Initialize face recognizer"""
        self.config = config
        self.face_config = config['vision']['face']
        self.encodings_file = Path("data/face_encodings.pkl")


        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.known_user_ids: List[int] = []

        self._load_encodings()
        logger.info(f"Face recognizer initialized with {len(self.known_names)} known faces")

    def recognize(self, frame: np.ndarray, face_bbox: tuple) -> Optional[Dict]:
        """
        Recognize face in bounding box

        Args:
            frame: BGR image
            face_bbox: (x, y, w, h) bounding box

        Returns:
            Dict with {'user_id', 'name', 'confidence'} or None
        """
        if not self.known_encodings:
            return None

        x, y, w, h = face_bbox
        face_crop = frame[y:y+h, x:x+w]
        rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

        try:

            encodings = face_recognition.face_encodings(rgb_face)
            if not encodings:
                return None

            encoding = encodings[0]


            distances = face_recognition.face_distance(self.known_encodings, encoding)

            if len(distances) == 0:
                return None

            min_distance_idx = np.argmin(distances)
            min_distance = distances[min_distance_idx]


            if min_distance < self.face_config['recognition_threshold']:
                return {
                    'user_id': self.known_user_ids[min_distance_idx],
                    'name': self.known_names[min_distance_idx],
                    'confidence': 1.0 - min_distance
                }

        except Exception as e:
            logger.error(f"Recognition error: {e}")

        return None

    def add_face(self, frame: np.ndarray, face_bbox: tuple, name: str, user_id: int):
        """
        Add new face to known faces

        Args:
            frame: BGR image
            face_bbox: (x, y, w, h) bounding box
            name: User name
            user_id: User ID
        """
        x, y, w, h = face_bbox
        face_crop = frame[y:y+h, x:x+w]
        rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

        try:
            encodings = face_recognition.face_encodings(rgb_face)
            if encodings:
                self.known_encodings.append(encodings[0])
                self.known_names.append(name)
                self.known_user_ids.append(user_id)
                self._save_encodings()
                logger.info(f"Added face for {name} (ID: {user_id})")

        except Exception as e:
            logger.error(f"Failed to add face: {e}")

    def _load_encodings(self):
        """Load face encodings from file"""
        if self.encodings_file.exists():
            try:
                with open(self.encodings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.known_encodings = data['encodings']
                    self.known_names = data['names']
                    self.known_user_ids = data['user_ids']
                logger.info("Face encodings loaded")
            except Exception as e:
                logger.error(f"Failed to load encodings: {e}")

    def _save_encodings(self):
        """Save face encodings to file"""
        self.encodings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                'encodings': self.known_encodings,
                'names': self.known_names,
                'user_ids': self.known_user_ids
            }
            with open(self.encodings_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info("Face encodings saved")
        except Exception as e:
            logger.error(f"Failed to save encodings: {e}")

    def cleanup(self):
        """Clean up resources"""
        self._save_encodings()
        logger.info("Face recognizer cleanup complete")
