"""
Proximity and Motion Sensors
Handles ultrasonic and PIR sensors
"""

import RPi.GPIO as GPIO
import time
import logging

logger = logging.getLogger(__name__)


class ProximitySensor:
    """Handles ultrasonic proximity sensor"""

    def __init__(self, config: dict):
        """Initialize proximity sensor"""
        self.config = config
        self.proximity_config = config['sensors']['proximity']
        self.ultrasonic_config = self.proximity_config['ultrasonic']

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.trigger_pin = self.ultrasonic_config['trigger_pin']
        self.echo_pin = self.ultrasonic_config['echo_pin']
        self.max_distance = self.ultrasonic_config['max_distance']
        self.threshold = self.ultrasonic_config['detection_threshold']

        # Setup pins
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)

        logger.info(f"Proximity sensor initialized (trigger: {self.trigger_pin}, echo: {self.echo_pin})")

    def get_distance(self) -> float:
        """
        Get distance measurement in cm

        Returns:
            Distance in centimeters
        """
        # Send trigger pulse
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)

        # Measure echo time
        pulse_start = time.time()
        pulse_end = time.time()

        timeout = time.time() + 0.1  # 100ms timeout

        while GPIO.input(self.echo_pin) == 0 and time.time() < timeout:
            pulse_start = time.time()

        while GPIO.input(self.echo_pin) == 1 and time.time() < timeout:
            pulse_end = time.time()

        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2  # Speed of sound = 343 m/s

        if distance > self.max_distance:
            distance = self.max_distance

        return distance

    def is_object_nearby(self) -> bool:
        """Check if object is within threshold distance"""
        distance = self.get_distance()
        return distance < self.threshold

    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup([self.trigger_pin, self.echo_pin])
        logger.info("Proximity sensor cleanup complete")


class PIRSensor:
    """Handles PIR motion sensor"""

    def __init__(self, config: dict):
        """Initialize PIR sensor"""
        self.config = config
        self.pir_config = config['sensors']['proximity']['pir']

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.pin = self.pir_config['pin']
        GPIO.setup(self.pin, GPIO.IN)

        logger.info(f"PIR sensor initialized on pin {self.pin}")

    def motion_detected(self) -> bool:
        """Check if motion is detected"""
        return GPIO.input(self.pin) == 1

    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup([self.pin])
        logger.info("PIR sensor cleanup complete")
