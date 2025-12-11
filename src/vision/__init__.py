"""
Vision module for Companion Bot
Handles Pi Camera v2 input, face detection, and object tracking
Pending implementation
"""

from .camera import Camera
from .face_detector import FaceDetector
from .face_recognizer import FaceRecognizer

__all__ = ['Camera', 'FaceDetector', 'FaceRecognizer']
