"""
Sensors module for Companion Bot
Handles touch sensors, proximity sensors, and PIR motion detection
"""

from .touch_sensor import TouchSensor
from .proximity_sensor import ProximitySensor

__all__ = ['TouchSensor', 'ProximitySensor']
