"""
Touch Sensor Handler
Manages capacitive touch sensors with debouncing
"""

import RPi.GPIO as GPIO
import time
import threading
import logging
from typing import Dict, Callable, Optional

logger = logging.getLogger(__name__)


class TouchSensor:
    """Handles multiple touch sensors with event callbacks"""

    def __init__(self, config: dict):
        """Initialize touch sensors"""
        self.config = config
        self.touch_config = config['sensors']['touch']

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Touch sensor pins
        self.pins = self.touch_config['pins']
        self.debounce_time = self.touch_config['debounce_time']
        self.long_press_duration = self.touch_config['long_press_duration']

        # State tracking
        self.touch_states: Dict[str, bool] = {}
        self.touch_start_times: Dict[str, float] = {}
        self.callbacks: Dict[str, list] = {
            'press': [],
            'release': [],
            'long_press': []
        }

        # Initialize pins
        for location, pin in self.pins.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.touch_states[location] = False
            self.touch_start_times[location] = 0

        # Monitoring thread
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

        logger.info(f"Touch sensors initialized on pins: {self.pins}")

    def start_monitoring(self):
        """Start monitoring touch sensors"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Touch sensor monitoring started")

    def stop_monitoring(self):
        """Stop monitoring touch sensors"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("Touch sensor monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        polling_rate = self.config['sensors']['polling_rate']
        sleep_time = 1.0 / polling_rate

        while self.is_monitoring:
            for location, pin in self.pins.items():
                self._check_sensor(location, pin)
            time.sleep(sleep_time)

    def _check_sensor(self, location: str, pin: int):
        """Check individual sensor state"""
        current_state = GPIO.input(pin)
        previous_state = self.touch_states[location]

        # State changed
        if current_state != previous_state:
            time.sleep(self.debounce_time)  # Debounce
            current_state = GPIO.input(pin)  # Re-read after debounce

            if current_state != previous_state:
                self.touch_states[location] = current_state

                if current_state:  # Pressed
                    self.touch_start_times[location] = time.time()
                    self._trigger_callbacks('press', location)
                    logger.debug(f"Touch pressed: {location}")
                else:  # Released
                    press_duration = time.time() - self.touch_start_times[location]
                    if press_duration >= self.long_press_duration:
                        self._trigger_callbacks('long_press', location)
                        logger.debug(f"Long press: {location} ({press_duration:.1f}s)")
                    self._trigger_callbacks('release', location)
                    logger.debug(f"Touch released: {location}")

    def _trigger_callbacks(self, event_type: str, location: str):
        """Trigger registered callbacks for event"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(location)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def on_press(self, callback: Callable[[str], None]):
        """Register callback for touch press"""
        self.callbacks['press'].append(callback)

    def on_release(self, callback: Callable[[str], None]):
        """Register callback for touch release"""
        self.callbacks['release'].append(callback)

    def on_long_press(self, callback: Callable[[str], None]):
        """Register callback for long press"""
        self.callbacks['long_press'].append(callback)

    def is_touched(self, location: str) -> bool:
        """Check if location is currently touched"""
        return self.touch_states.get(location, False)

    def cleanup(self):
        """Clean up GPIO resources"""
        self.stop_monitoring()
        GPIO.cleanup()
        logger.info("Touch sensor cleanup complete")
