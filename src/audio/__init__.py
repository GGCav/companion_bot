"""
Audio module for Companion Bot
Handles mini microphone input, voice activity detection, and audio output
"""

from .audio_input import AudioInput
from .audio_output import AudioOutput
from .voice_detector import VoiceActivityDetector

__all__ = ['AudioInput', 'AudioOutput', 'VoiceActivityDetector']
