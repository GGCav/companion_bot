"""
Emotion Engine
State machine for managing emotional states and transitions
"""

import time
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionState(Enum):
    """Available emotion states"""
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CURIOUS = "curious"
    SLEEPY = "sleepy"
    LONELY = "lonely"
    PLAYFUL = "playful"
    SCARED = "scared"
    ANGRY = "angry"
    LOVING = "loving"
    BORED = "bored"
    SURPRISED = "surprised"


class EmotionEngine:
    """Manages emotional state and personality dynamics"""

    def __init__(self, config: dict):
        """Initialize emotion engine"""
        self.config = config
        self.personality_config = config['personality']

        # Current state
        self.current_emotion = EmotionState(self.personality_config['default_state'])
        self.emotion_intensity = 0.5  # 0-1
        self.energy_level = self.personality_config['traits']['energy_level']

        # Emotion scores (multiple emotions can be active)
        self.emotion_scores: Dict[EmotionState, float] = {
            emotion: 0.0 for emotion in EmotionState
        }
        self.emotion_scores[self.current_emotion] = 1.0

        # Timers
        self.last_interaction_time = time.time()
        self.last_update_time = time.time()

        # Personality traits
        self.traits = self.personality_config['traits']

        logger.info(f"Emotion engine initialized, default state: {self.current_emotion.value}")

    def update(self):
        """Update emotional state based on time and dynamics"""
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time

        # Apply emotion decay
        decay_rate = self.personality_config['dynamics']['emotion_decay_rate']
        for emotion in EmotionState:
            if emotion != self.current_emotion:
                self.emotion_scores[emotion] = max(0.0, self.emotion_scores[emotion] - decay_rate * delta_time)

        # Check for loneliness
        time_since_interaction = current_time - self.last_interaction_time
        if time_since_interaction > 30:  # 30 seconds
            loneliness_rate = self.personality_config['dynamics']['loneliness_increase_rate']
            self.add_emotion(EmotionState.LONELY, loneliness_rate * time_since_interaction)

        # Energy drain
        energy_drain = self.personality_config['dynamics']['energy_drain_rate']
        self.energy_level = max(0.1, self.energy_level - energy_drain * delta_time)

        # Update primary emotion based on highest score
        self._update_primary_emotion()

    def add_emotion(self, emotion: EmotionState, amount: float):
        """Add emotional response"""
        self.emotion_scores[emotion] = min(1.0, self.emotion_scores[emotion] + amount)
        self._update_primary_emotion()

    def on_touch(self, location: str):
        """Handle touch event"""
        self.last_interaction_time = time.time()
        boost = self.personality_config['dynamics']['touch_happiness_boost']
        self.add_emotion(EmotionState.HAPPY, boost)
        self.add_emotion(EmotionState.LOVING, boost * 0.5)
        logger.info(f"Touch received at {location}")

    def on_voice_interaction(self):
        """Handle voice interaction"""
        self.last_interaction_time = time.time()
        boost = self.personality_config['dynamics']['voice_interaction_boost']
        self.add_emotion(EmotionState.HAPPY, boost)
        self.add_emotion(EmotionState.EXCITED, boost * 0.3)

    def on_face_recognized(self, user_name: str):
        """Handle face recognition"""
        self.last_interaction_time = time.time()
        boost = self.personality_config['dynamics']['face_recognition_boost']
        self.add_emotion(EmotionState.HAPPY, boost)
        self.add_emotion(EmotionState.EXCITED, boost * 0.5)
        logger.info(f"Recognized {user_name}")

    def _update_primary_emotion(self):
        """Update primary emotion based on scores"""
        max_emotion = max(self.emotion_scores.items(), key=lambda x: x[1])
        self.current_emotion = max_emotion[0]
        self.emotion_intensity = max_emotion[1]

    def get_emotion(self) -> str:
        """Get current primary emotion"""
        return self.current_emotion.value

    def get_emotion_data(self) -> Dict:
        """Get full emotion state data"""
        return {
            'emotion': self.current_emotion.value,
            'intensity': self.emotion_intensity,
            'energy': self.energy_level,
            'scores': {e.value: score for e, score in self.emotion_scores.items()}
        }
