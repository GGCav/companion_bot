"""
Expression Module
Manages visual expressions and physical movements
"""

from .emotion_display import EmotionDisplay
from .display_renderer import DisplayRenderer
from .transition_controller import TransitionController

__all__ = [
    'EmotionDisplay',
    'DisplayRenderer',
    'TransitionController'
]
