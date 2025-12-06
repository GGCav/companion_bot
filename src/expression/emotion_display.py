"""
Emotion Display Controller for Companion Bot
Main controller for expression pipeline with threading and state management
"""

try:
    import pygame  # type: ignore  # noqa: E0401
except ImportError:  # pragma: no cover
    pygame = None  # type: ignore
import threading
import queue
import time
import logging
import math
from typing import Optional, Dict

# pylint: disable=import-error

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - GPIO features disabled")

from .display_renderer import DisplayRenderer
from .transition_controller import TransitionController

logger = logging.getLogger(__name__)

DEFAULT_EMOTION_PRESETS: Dict[str, Dict] = {
    "happy": {
        "eye_spacing": 90,
        "eye_width": 44,
        "eye_height": 38,
        "eye_y": 95,
        "pupil_size": 12,
        "pupil_offset": 2,
        "brow_raise": 0.1,
        "brow_slant": -0.05,
        "mouth_width": 130,
        "mouth_height": 26,
        "mouth_curve": 0.35,
        "mouth_open": 0.08,
        "mouth_sensitivity": 0.7,
        "eye_color": [245, 245, 245],
        "pupil_color": [20, 20, 20],
        "brow_color": [230, 230, 230],
        "mouth_color": [240, 140, 140],
    },
    "sad": {
        "eye_spacing": 85,
        "eye_width": 42,
        "eye_height": 36,
        "eye_y": 100,
        "pupil_size": 11,
        "pupil_offset": -1,
        "brow_raise": -0.1,
        "brow_slant": 0.15,
        "mouth_width": 120,
        "mouth_height": 22,
        "mouth_curve": -0.45,
        "mouth_open": 0.05,
        "mouth_sensitivity": 0.55,
        "eye_color": [235, 235, 240],
        "pupil_color": [15, 15, 25],
        "brow_color": [210, 210, 220],
        "mouth_color": [200, 120, 160],
    },
    "excited": {
        "eye_spacing": 95,
        "eye_width": 46,
        "eye_height": 40,
        "eye_y": 92,
        "pupil_size": 13,
        "pupil_offset": 3,
        "brow_raise": 0.25,
        "brow_slant": -0.08,
        "mouth_width": 140,
        "mouth_height": 28,
        "mouth_curve": 0.5,
        "mouth_open": 0.18,
        "mouth_sensitivity": 0.9,
        "eye_color": [250, 250, 250],
        "pupil_color": [10, 10, 10],
        "brow_color": [240, 240, 240],
        "mouth_color": [255, 150, 150],
    },
    "curious": {
        "eye_spacing": 88,
        "eye_width": 44,
        "eye_height": 38,
        "eye_y": 96,
        "pupil_size": 12,
        "pupil_offset": 4,
        "brow_raise": 0.05,
        "brow_slant": -0.15,
        "mouth_width": 115,
        "mouth_height": 22,
        "mouth_curve": 0.12,
        "mouth_open": 0.06,
        "mouth_sensitivity": 0.6,
        "eye_color": [245, 245, 245],
        "pupil_color": [25, 25, 25],
        "brow_color": [225, 225, 225],
        "mouth_color": [220, 150, 160],
    },
    "sleepy": {
        "eye_spacing": 85,
        "eye_width": 44,
        "eye_height": 24,
        "eye_y": 104,
        "pupil_size": 10,
        "pupil_offset": 0,
        "brow_raise": -0.05,
        "brow_slant": 0.05,
        "mouth_width": 110,
        "mouth_height": 18,
        "mouth_curve": -0.1,
        "mouth_open": 0.04,
        "mouth_sensitivity": 0.4,
        "eye_color": [235, 235, 235],
        "pupil_color": [20, 20, 20],
        "brow_color": [215, 215, 215],
        "mouth_color": [200, 140, 150],
    },
    "angry": {
        "eye_spacing": 90,
        "eye_width": 44,
        "eye_height": 34,
        "eye_y": 94,
        "pupil_size": 12,
        "pupil_offset": -2,
        "brow_raise": -0.15,
        "brow_slant": 0.25,
        "mouth_width": 125,
        "mouth_height": 24,
        "mouth_curve": -0.25,
        "mouth_open": 0.09,
        "mouth_sensitivity": 0.75,
        "eye_color": [240, 230, 230],
        "pupil_color": [30, 10, 10],
        "brow_color": [220, 200, 200],
        "mouth_color": [255, 120, 120],
    },
    "scared": {
        "eye_spacing": 90,
        "eye_width": 46,
        "eye_height": 42,
        "eye_y": 92,
        "pupil_size": 10,
        "pupil_offset": -3,
        "brow_raise": 0.2,
        "brow_slant": 0.1,
        "mouth_width": 125,
        "mouth_height": 22,
        "mouth_curve": -0.35,
        "mouth_open": 0.14,
        "mouth_sensitivity": 0.85,
        "eye_color": [240, 240, 245],
        "pupil_color": [15, 15, 20],
        "brow_color": [225, 225, 235],
        "mouth_color": [240, 150, 180],
    },
    "playful": {
        "eye_spacing": 94,
        "eye_width": 44,
        "eye_height": 38,
        "eye_y": 94,
        "pupil_size": 13,
        "pupil_offset": 5,
        "brow_raise": 0.1,
        "brow_slant": -0.12,
        "mouth_width": 135,
        "mouth_height": 26,
        "mouth_curve": 0.28,
        "mouth_open": 0.12,
        "mouth_sensitivity": 0.8,
        "eye_color": [250, 250, 250],
        "pupil_color": [15, 15, 15],
        "brow_color": [235, 235, 235],
        "mouth_color": [255, 170, 140],
    },
    "lonely": {
        "eye_spacing": 82,
        "eye_width": 42,
        "eye_height": 34,
        "eye_y": 100,
        "pupil_size": 11,
        "pupil_offset": -1,
        "brow_raise": -0.08,
        "brow_slant": 0.1,
        "mouth_width": 112,
        "mouth_height": 20,
        "mouth_curve": -0.2,
        "mouth_open": 0.05,
        "mouth_sensitivity": 0.6,
        "eye_color": [235, 235, 240],
        "pupil_color": [15, 15, 20],
        "brow_color": [215, 215, 225],
        "mouth_color": [205, 140, 170],
    },
    "bored": {
        "eye_spacing": 90,
        "eye_width": 42,
        "eye_height": 30,
        "eye_y": 102,
        "pupil_size": 11,
        "pupil_offset": 0,
        "brow_raise": -0.02,
        "brow_slant": 0.0,
        "mouth_width": 118,
        "mouth_height": 18,
        "mouth_curve": -0.05,
        "mouth_open": 0.04,
        "mouth_sensitivity": 0.45,
        "eye_color": [240, 240, 240],
        "pupil_color": [20, 20, 20],
        "brow_color": [220, 220, 220],
        "mouth_color": [200, 140, 150],
    },
    "surprised": {
        "eye_spacing": 92,
        "eye_width": 46,
        "eye_height": 44,
        "eye_y": 92,
        "pupil_size": 11,
        "pupil_offset": 0,
        "brow_raise": 0.18,
        "brow_slant": 0.02,
        "mouth_width": 118,
        "mouth_height": 26,
        "mouth_curve": 0.12,
        "mouth_open": 0.2,
        "mouth_sensitivity": 0.9,
        "eye_color": [250, 250, 250],
        "pupil_color": [15, 15, 15],
        "brow_color": [240, 240, 240],
        "mouth_color": [240, 160, 180],
    },
    "loving": {
        "eye_spacing": 90,
        "eye_width": 44,
        "eye_height": 38,
        "eye_y": 95,
        "pupil_size": 12,
        "pupil_offset": 3,
        "brow_raise": 0.15,
        "brow_slant": -0.05,
        "mouth_width": 130,
        "mouth_height": 26,
        "mouth_curve": 0.32,
        "mouth_open": 0.12,
        "mouth_sensitivity": 0.75,
        "eye_color": [245, 245, 245],
        "pupil_color": [20, 20, 20],
        "brow_color": [230, 230, 230],
        "mouth_color": [255, 150, 170],
    },
}


class DisplayState:
    """Container for display state"""
    def __init__(self):
        # Priority states
        self.is_listening: bool = False
        self.is_speaking: bool = False

        # Emotion state
        self.current_emotion: str = "happy"
        self.target_emotion: Optional[str] = None

        # Speaking animation state
        self.speaking_frame_toggle: bool = False
        self.last_toggle_time: float = 0.0
        self.toggle_interval: float = 0.15  # Speaking toggle interval
        self.speaking_level: float = 0.0
        self.speaking_level_target: float = 0.0


class EmotionDisplay:
    """
    Main emotion display controller
    Manages display lifecycle, state machine, threading, and GPIO
    """

    def __init__(self, config: dict, framebuffer: str = "/dev/fb0"):
        """
        Initialize emotion display

        Args:
            config: Configuration dictionary from settings.yaml
            framebuffer: Framebuffer device path (default: /dev/fb0 for piTFT)
        """
        self.config = config
        self.display_config = config.get('expression', {}).get('display', {})
        self.procedural_config = self.display_config.get('procedural_face', {})

        # Extract configuration
        screen_size = tuple(self.display_config.get('resolution', [320, 240]))
        image_dir = self.display_config.get('image_dir', 'src/display')
        self.fps = self.display_config.get('fps', 60)
        gpio_cfg = self.display_config.get('gpio', {})
        self.gpio_enabled = gpio_cfg.get('enabled', True)
        self.gpio_exit_pin = gpio_cfg.get('exit_button_pin', 27)

        # Initialize components
        self.renderer = DisplayRenderer(
            screen_size=screen_size,
            framebuffer=framebuffer,
            image_dir=image_dir,
            procedural_config=self.procedural_config
        )
        self.transition = TransitionController()
        self.state = DisplayState()
        speaking_cfg = self.display_config.get('speaking', {})
        self.state.toggle_interval = speaking_cfg.get('toggle_interval', 0.15)
        self.procedural_enabled = self.renderer.use_procedural
        self.emotion_params: Dict[str, Dict] = self._build_emotion_params()

        # Threading components
        self.is_running = False
        self.display_thread: Optional[threading.Thread] = None
        self.command_queue = queue.Queue()
        self.state_lock = threading.Lock()

        # Performance tracking
        self.clock = pygame.time.Clock()
        self._last_delta_time = 0.0

        # Initialize GPIO if available
        self._init_gpio()

        logger.info("EmotionDisplay initialized")

    def _init_gpio(self):
        """Initialize GPIO for exit button (if available)"""
        if not GPIO_AVAILABLE or not self.gpio_enabled:
            logger.info("GPIO disabled")
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_exit_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info(
                "GPIO initialized - exit button on pin %s",
                self.gpio_exit_pin
            )
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("GPIO initialization failed: %s", e)

    def start(self):
        """Start the display loop in a dedicated thread"""
        if self.is_running:
            logger.warning("Display already running")
            return

        self.is_running = True
        self.display_thread = threading.Thread(
            target=self._display_loop,
            daemon=True
        )
        self.display_thread.start()
        logger.info("Display thread started")

    def stop(self):
        """Stop the display loop gracefully"""
        if not self.is_running:
            return

        self.is_running = False
        if self.display_thread:
            self.display_thread.join(timeout=2.0)
        logger.info("Display thread stopped")

    def _display_loop(self):
        """
        Main display loop - runs at configured FPS (default 60)
        Pattern from camera.py and two_collide.py
        """
        logger.info("Display loop starting at %s FPS", self.fps)
        last_time = time.time()

        while self.is_running:
            # Calculate delta time
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time
            self._last_delta_time = delta_time

            # Process command queue
            self._process_commands()

            # Check GPIO exit button
            if self._check_gpio_exit():
                logger.info("GPIO exit button pressed")
                self.is_running = False
                break

            # Update state
            self._update_state(delta_time)

            # Render frame
            self._render_frame()

            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False

            # Maintain target FPS
            self.clock.tick(self.fps)

        logger.info("Display loop exited")

    def _process_commands(self):
        """Process commands from the command queue"""
        try:
            while True:
                cmd = self.command_queue.get_nowait()
                self._execute_command(cmd)
        except queue.Empty:
            pass

    def _execute_command(self, cmd: dict):
        """
        Execute a command

        Args:
            cmd: Command dictionary with 'type' and parameters
        """
        cmd_type = cmd.get('type')

        with self.state_lock:
            if cmd_type == 'SET_EMOTION':
                emotion = cmd.get('emotion', 'happy')
                duration = cmd.get('duration', 0.5)
                self._start_emotion_transition(emotion, duration)

            elif cmd_type == 'SET_LISTENING':
                active = cmd.get('active', False)
                self.state.is_listening = active
                logger.debug("Listening: %s", active)

            elif cmd_type == 'SET_SPEAKING':
                active = cmd.get('active', False)
                self.state.is_speaking = active
                level = cmd.get('level')
                if level is None:
                    level = 1.0 if active else 0.0
                self.state.speaking_level_target = max(
                    0.0, min(1.0, float(level))
                )
                if not active:
                    self.state.speaking_frame_toggle = False
                logger.debug("Speaking: %s", active)

    def _start_emotion_transition(self, emotion: str, duration: float):
        """Start transition to new emotion"""
        if (
            emotion == self.state.current_emotion
            and not self.transition.is_transitioning()
        ):
            logger.debug("Already showing %s, skipping transition", emotion)
            return

        self.transition.start_transition(
            from_emotion=self.state.current_emotion,
            to_emotion=emotion,
            duration=duration
        )
        self.state.target_emotion = emotion

    def _update_state(self, delta_time: float):
        """
        Update display state each frame

        Args:
            delta_time: Time since last update (seconds)
        """
        with self.state_lock:
            # Update transition progress
            if self.transition.is_transitioning():
                _from_em, to_em, _alpha = self.transition.update(delta_time)
                # Update current emotion when transition completes
                if not self.transition.is_transitioning():
                    self.state.current_emotion = to_em
                    self.state.target_emotion = None

            # Update speaking animation toggle
            if self.state.is_speaking or self.state.is_listening:
                current_time = time.time()
                if (
                    current_time - self.state.last_toggle_time
                    >= self.state.toggle_interval
                ):
                    self.state.speaking_frame_toggle = (
                        not self.state.speaking_frame_toggle
                    )
                    self.state.last_toggle_time = current_time

            # Speaking intensity smoothing for procedural renderer
            if self.procedural_enabled:
                smooth = max(
                    1e-3, self.procedural_config.get('speaking_smooth', 8.0)
                )
                blend = 1.0 - math.exp(-smooth * max(delta_time, 0.0))
                self.state.speaking_level = (
                    (1 - blend) * self.state.speaking_level
                    + blend * self.state.speaking_level_target
                )

    def _render_frame(self):
        """
        Render current frame based on state priority
        Priority: LISTENING > SPEAKING > EMOTION + TRANSITION
        """
        with self.state_lock:
            # Priority 1: Listening state
            if self.state.is_listening:
                if self.procedural_enabled:
                    params = self._get_emotion_params(
                        self.state.current_emotion
                    )
                    self.renderer.render_procedural(
                        current_params=params,
                        target_params=None,
                        blend_alpha=0.0,
                        speaking_level=0.0,
                        listening=True,
                        delta_time=self._last_delta_time
                    )
                    return
                frame = self.renderer.get_listening_frame()
                if frame:
                    self.renderer.render_frame(frame)
                    return

            # Priority 2: Speaking animation
            if self.state.is_speaking:
                emotion = self.state.current_emotion
                if self.procedural_enabled:
                    params = self._get_emotion_params(emotion)
                    self.renderer.render_procedural(
                        current_params=params,
                        target_params=None,
                        blend_alpha=0.0,
                        speaking_level=max(0.1, self.state.speaking_level),
                        listening=False,
                        delta_time=self._last_delta_time
                    )
                    return
                frame = self.renderer.get_emotion_frame(
                    emotion, speaking=self.state.speaking_frame_toggle
                )
                if frame:
                    self.renderer.render_frame(frame)
                    return

            # Priority 3: Emotion display with transitions
            if self.transition.is_transitioning():
                # Just get current values (no time advance)
                from_em, to_em, alpha = self.transition.update(0)
                if self.procedural_enabled:
                    from_params = self._get_emotion_params(from_em)
                    to_params = self._get_emotion_params(to_em)
                    self.renderer.render_procedural(
                        current_params=from_params,
                        target_params=to_params,
                        blend_alpha=alpha,
                        speaking_level=0.0,
                        listening=False,
                        delta_time=self._last_delta_time
                    )
                    return
                from_frame = self.renderer.get_emotion_frame(
                    from_em, speaking=False
                )
                to_frame = self.renderer.get_emotion_frame(
                    to_em, speaking=False
                )

                if from_frame and to_frame:
                    blended = self.renderer.create_blended_frame(
                        from_frame, to_frame, alpha
                    )
                    self.renderer.render_frame(blended)
                    return

            # Default: Show current emotion
            if self.procedural_enabled:
                params = self._get_emotion_params(
                    self.state.current_emotion
                )
                self.renderer.render_procedural(
                    current_params=params,
                    target_params=None,
                    blend_alpha=0.0,
                    speaking_level=0.0,
                    listening=False,
                    delta_time=self._last_delta_time
                )
            else:
                frame = self.renderer.get_emotion_frame(
                    self.state.current_emotion, speaking=False
                )
            if frame:
                self.renderer.render_frame(frame)

    def _check_gpio_exit(self) -> bool:
        """
        Check if GPIO exit button is pressed

        Returns:
            True if button pressed, False otherwise
        """
        if not GPIO_AVAILABLE or not self.gpio_enabled:
            return False

        try:
            # Active low (pressed = 0)
            return not GPIO.input(self.gpio_exit_pin)
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("GPIO read error: %s", e)
            return False

    # Public API methods (thread-safe)

    def set_emotion(self, emotion: str, transition_duration: float = 0.5):
        """
        Set display emotion with smooth transition

        Args:
            emotion: Emotion name (e.g., 'happy', 'sad', 'excited')
            transition_duration: Transition duration in seconds
        """
        self.command_queue.put({
            'type': 'SET_EMOTION',
            'emotion': emotion,
            'duration': transition_duration
        })

    def set_listening(self, active: bool):
        """
        Set listening state

        Args:
            active: True to show listening animation, False to return
        """
        self.command_queue.put({
            'type': 'SET_LISTENING',
            'active': active
        })

    def set_speaking(self, active: bool, level: Optional[float] = None):
        """
        Set speaking state

        Args:
            active: True to enable speaking animation, False to stop
            level: Optional mouth intensity (0-1) for procedural mode
        """
        self.command_queue.put({
            'type': 'SET_SPEAKING',
            'active': active,
            'level': level
        })

    def cleanup(self):
        """Clean up display resources and GPIO"""
        logger.info("Cleaning up emotion display...")

        # Stop display loop
        self.stop()

        # Clean up renderer
        self.renderer.cleanup()

        # Clean up GPIO
        if GPIO_AVAILABLE and self.gpio_enabled:
            try:
                GPIO.cleanup()
                logger.info("GPIO cleanup complete")
            except (RuntimeError, ValueError, OSError) as e:
                logger.error("GPIO cleanup error: %s", e)

        logger.info("EmotionDisplay cleanup complete")

    def _build_emotion_params(self) -> Dict[str, Dict]:
        """
        Build emotion parameter presets with optional config overrides.
        """
        presets = {
            key: val.copy() for key, val in DEFAULT_EMOTION_PRESETS.items()
        }
        overrides = self.procedural_config.get('presets', {})
        for key, override in overrides.items():
            if key in presets and isinstance(override, dict):
                merged = presets[key].copy()
                merged.update(override)
                presets[key] = merged
            elif isinstance(override, dict):
                presets[key] = override
        return presets

    def _get_emotion_params(self, emotion: str) -> Dict:
        if emotion in self.emotion_params:
            return self.emotion_params[emotion]
        # Fallbacks
        if "happy" in self.emotion_params:
            return self.emotion_params["happy"]
        return list(self.emotion_params.values())[0]
