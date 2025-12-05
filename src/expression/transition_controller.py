"""
Transition Controller for Emotion Expression Pipeline
Manages smooth cross-fade transitions between emotions
"""

import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TransitionController:
    """
    Manages smooth transitions between emotions using alpha blending
    Tracks transition progress over time for interpolation
    """

    def __init__(self):
        """Initialize transition controller"""
        self.is_active = False
        self.from_emotion: Optional[str] = None
        self.to_emotion: Optional[str] = None
        self.duration: float = 0.5  # Default transition duration
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.alpha: float = 0.0  # Current blend factor (0.0 to 1.0)

    def start_transition(self, from_emotion: str, to_emotion: str, duration: float = 0.5):
        """
        Start a new emotion transition

        Args:
            from_emotion: Current emotion to transition from
            to_emotion: Target emotion to transition to
            duration: Transition duration in seconds
        """
        self.from_emotion = from_emotion
        self.to_emotion = to_emotion
        self.duration = max(0.1, duration)  # Minimum 0.1s duration
        self.start_time = time.time()
        self.elapsed_time = 0.0
        self.alpha = 0.0
        self.is_active = True

        logger.debug(f"Transition started: {from_emotion} → {to_emotion} ({duration}s)")

    def update(self, delta_time: float) -> Tuple[str, str, float]:
        """
        Update transition progress

        Args:
            delta_time: Time elapsed since last update (seconds)

        Returns:
            Tuple of (from_emotion, to_emotion, alpha)
            alpha: 0.0 = show from_emotion, 1.0 = show to_emotion
        """
        if not self.is_active:
            return (self.from_emotion or 'happy', self.to_emotion or 'happy', 1.0)

        self.elapsed_time += delta_time

        # Linear interpolation
        self.alpha = min(1.0, self.elapsed_time / self.duration)

        # Check if transition complete
        if self.alpha >= 1.0:
            self.is_active = False
            self.from_emotion = self.to_emotion  # Update current emotion
            logger.debug(f"Transition complete: now showing {self.to_emotion}")

        return (self.from_emotion, self.to_emotion, self.alpha)

    def is_transitioning(self) -> bool:
        """
        Check if transition is currently in progress

        Returns:
            True if transitioning, False otherwise
        """
        return self.is_active

    def skip_to_end(self):
        """Skip to end of transition instantly"""
        if self.is_active:
            self.alpha = 1.0
            self.is_active = False
            self.from_emotion = self.to_emotion
            logger.debug(f"Transition skipped to end: {self.to_emotion}")

    def get_current_emotion(self) -> str:
        """
        Get the current emotion (from or to depending on transition state)

        Returns:
            Current emotion name
        """
        if self.is_active and self.alpha >= 0.5:
            # Past halfway point - consider target emotion as current
            return self.to_emotion or 'happy'
        else:
            return self.from_emotion or 'happy'

    def get_progress(self) -> float:
        """
        Get transition progress

        Returns:
            Progress from 0.0 to 1.0
        """
        return self.alpha
