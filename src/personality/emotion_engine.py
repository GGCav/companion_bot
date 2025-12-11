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


        self.current_emotion = EmotionState(self.personality_config['default_state'])
        self.emotion_intensity = 0.5
        self.energy_level = self.personality_config['traits']['energy_level']


        self.emotion_scores: Dict[EmotionState, float] = {
            emotion: 0.0 for emotion in EmotionState
        }
        self.emotion_scores[self.current_emotion] = 1.0


        self.last_interaction_time = time.time()
        self.last_update_time = time.time()


        self.traits = self.personality_config['traits']

        logger.info(f"Emotion engine initialized, default state: {self.current_emotion.value}")

    def update(self):
        """Update emotional state based on time and dynamics"""
        current_time = time.time()
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time


        decay_rate = self.personality_config['dynamics']['emotion_decay_rate']
        for emotion in EmotionState:
            if emotion != self.current_emotion:
                self.emotion_scores[emotion] = max(0.0, self.emotion_scores[emotion] - decay_rate * delta_time)


        time_since_interaction = current_time - self.last_interaction_time
        if time_since_interaction > 30:
            loneliness_rate = self.personality_config['dynamics']['loneliness_increase_rate']
            self.add_emotion(EmotionState.LONELY, loneliness_rate * time_since_interaction)


        energy_drain = self.personality_config['dynamics']['energy_drain_rate']
        self.energy_level = max(0.1, self.energy_level - energy_drain * delta_time)


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

    def set_emotion_from_llm(self, emotion_str: str, intensity: float = 0.8):
        """
        Set emotion based on LLM's choice
        This is the new primary way to update emotions - the LLM decides the emotion

        Args:
            emotion_str: Emotion name (e.g., "happy", "excited")
            intensity: Emotion intensity (0-1), defaults to 0.8
        """
        self.last_interaction_time = time.time()


        try:
            emotion = EmotionState(emotion_str.lower())
        except ValueError:
            logger.warning(f"Invalid emotion '{emotion_str}', defaulting to happy")
            emotion = EmotionState.HAPPY



        for e in EmotionState:
            if e == emotion:
                self.emotion_scores[e] = intensity
            else:

                self.emotion_scores[e] = max(0.0, self.emotion_scores[e] * 0.3)


        self._update_primary_emotion()

        logger.info(f"Emotion set from LLM: {emotion.value} (intensity: {intensity:.2f})")

    def process_emotion_sequence(self, emotion_list: list):
        """
        Process a sequence of emotions from multi-emotion LLM response

        The final emotion in the sequence becomes dominant, but earlier emotions
        contribute with decreasing weight to create a natural emotional blend.

        Example:
            ["excited", "curious", "happy"]
            → excited: 0.3, curious: 0.5, happy: 0.8 (final is strongest)

        Args:
            emotion_list: List of emotion strings in sequential order
        """
        if not emotion_list:
            logger.warning("Empty emotion sequence, no update")
            return

        self.last_interaction_time = time.time()


        for e in EmotionState:
            self.emotion_scores[e] = max(0.0, self.emotion_scores[e] * 0.2)


        num_emotions = len(emotion_list)
        for i, emotion_str in enumerate(emotion_list):

            try:
                emotion = EmotionState(emotion_str.lower())
            except ValueError:
                logger.warning(f"Invalid emotion '{emotion_str}' in sequence, skipping")
                continue



            base_intensity = 0.3
            max_intensity = 0.8
            if num_emotions > 1:
                position_weight = i / (num_emotions - 1)
                intensity = base_intensity + (max_intensity - base_intensity) * position_weight
            else:
                intensity = max_intensity


            self.emotion_scores[emotion] = max(
                self.emotion_scores[emotion],
                intensity
            )


        self._update_primary_emotion()

        logger.info(f"Processed emotion sequence: {' → '.join(emotion_list)} (final: {self.current_emotion.value})")

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
