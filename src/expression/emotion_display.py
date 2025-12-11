"""
Emotion Display Controller for Companion Bot
Main controller for expression pipeline with threading and state management
"""

try:
    import pygame  # type: ignore  # noqa: E0401
except ImportError:
    pygame = None
import threading
import queue
import time
import logging
import math
from typing import Optional, Dict, Callable, Tuple



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

        self.is_listening: bool = False
        self.is_speaking: bool = False


        self.current_emotion: str = "happy"
        self.target_emotion: Optional[str] = None


        self.speaking_frame_toggle: bool = False
        self.last_toggle_time: float = 0.0
        self.toggle_interval: float = 0.15
        self.speaking_level: float = 0.0
        self.speaking_level_target: float = 0.0
        self.speaking_phase: float = 0.0
        self.last_gesture_time: float = 0.0
        self.pending_tap_time: float = 0.0
        self.gesture_busy_until: float = 0.0
        self.petting_active: bool = False


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
        self.speaking_rest_factor = self.procedural_config.get(
            'speaking_rest_factor', 0.35
        )
        self.speaking_wave_hz = self.procedural_config.get(
            'speaking_wave_hz', 6.0
        )
        self.touch_config = self.display_config.get('touch', {})
        self.touch_enabled = self.touch_config.get('enabled', True)
        self.touch_thresholds = self.touch_config.get('thresholds', {})
        self.gesture_effects = self.touch_config.get('gesture_effects', {})
        self.gesture_cooldown = float(
            self.touch_thresholds.get('cooldown', 0.8)
        )
        self.effect_queue_cooldown = float(
            self.touch_thresholds.get('effect_cooldown', 0.4)
        )
        self.effect_busy_window = float(
            self.touch_thresholds.get('effect_busy', 1.2)
        )
        self.effect_callback: Optional[Callable[[Dict], None]] = None
        self.exit_callback: Optional[Callable[[], None]] = None


        screen_size = tuple(self.display_config.get('resolution', [320, 240]))
        image_dir = self.display_config.get('image_dir', 'src/display')
        self.fps = self.display_config.get('fps', 60)
        gpio_cfg = self.display_config.get('gpio', {})
        self.gpio_enabled = gpio_cfg.get('enabled', True)
        self.gpio_exit_pin = gpio_cfg.get('exit_button_pin', 27)


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


        self.is_running = False
        self.display_thread: Optional[threading.Thread] = None
        self.command_queue = queue.Queue()
        self.state_lock = threading.Lock()


        self.clock = pygame.time.Clock()
        self._last_delta_time = 0.0


        self._touch_start_pos: Optional[Tuple[int, int]] = None
        self._touch_down_pos: Optional[Tuple[int, int]] = None
        self._touch_down_time: float = 0.0
        self._last_tap_time: float = 0.0
        self._drag_distance: float = 0.0
        self._last_effect_time: float = 0.0
        self.pending_tap_time: float = 0.0


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

            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time
            self._last_delta_time = delta_time


            self._process_commands()


            if self._check_gpio_exit():
                logger.info("GPIO exit button pressed")
                if self.exit_callback:
                    try:
                        self.exit_callback()
                    except Exception as exc:
                        logger.error("Exit callback failed: %s", exc)
                self.is_running = False
                break


            self._update_state(delta_time)


            self._render_frame()


            if self.touch_enabled and self.state.petting_active:
                self._discard_touch_events()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                elif self.touch_enabled:
                    self._handle_touch_event(event)


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
                    self.state.speaking_phase = 0.0
                else:

                    self.state.speaking_phase = 0.0
                logger.debug("Speaking: %s", active)

            elif cmd_type == 'APPLY_EFFECT':
                effect = cmd.get('effect', {})
                self._apply_effect(effect)

            elif cmd_type == 'SET_PETTING':
                active = cmd.get('active', False)
                self.state.petting_active = bool(active)

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
        pending_tap_fire = False

        with self.state_lock:

            if self.transition.is_transitioning():
                _from_em, to_em, _alpha = self.transition.update(delta_time)

                if not self.transition.is_transitioning():
                    self.state.current_emotion = to_em
                    self.state.target_emotion = None


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


            if self.procedural_enabled:
                smooth = max(
                    1e-3, self.procedural_config.get('speaking_smooth', 8.0)
                )
                blend = 1.0 - math.exp(-smooth * max(delta_time, 0.0))
                target_level = 0.0
                if self.state.is_speaking:

                    self.state.speaking_phase += (
                        2.0
                        * math.pi
                        * self.speaking_wave_hz
                        * max(delta_time, 0.0)
                    )
                    wave = 0.5 + 0.5 * math.sin(self.state.speaking_phase)
                    target_level = self.state.speaking_level_target * (
                        self.speaking_rest_factor
                        + (1 - self.speaking_rest_factor) * wave
                    )
                self.state.speaking_level = (
                    (1 - blend) * self.state.speaking_level
                    + blend * target_level
                )


        if self.touch_enabled and self.pending_tap_time > 0.0:
            double_tap_window = float(
                self.touch_thresholds.get('double_tap_window', 0.35)
            )
            now = time.time()
            if now - self.pending_tap_time > double_tap_window:
                pending_tap_fire = True
                self.pending_tap_time = 0.0

        if pending_tap_fire:
            self._trigger_gesture_effect("tap")

    def _render_frame(self):
        """
        Render current frame based on state priority
        Priority: LISTENING > SPEAKING > EMOTION + TRANSITION
        """
        with self.state_lock:

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


            if self.transition.is_transitioning():

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
                return

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

            return not GPIO.input(self.gpio_exit_pin)
        except (RuntimeError, ValueError, OSError) as e:
            logger.error("GPIO read error: %s", e)
            return False



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

    def set_effect_callback(self, callback: Callable[[Dict], None]):
        """
        Set an optional effect callback invoked on gesture effects.

        Args:
            callback: Callable receiving a dict with effect info.
        """
        self.effect_callback = callback

    def set_exit_callback(self, callback: Callable[[], None]):
        """
        Set a callback invoked when the GPIO exit button is pressed.
        """
        self.exit_callback = callback

    def cleanup(self):
        """Clean up display resources and GPIO"""
        logger.info("Cleaning up emotion display...")


        self.stop()


        self.renderer.cleanup()


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

        if "happy" in self.emotion_params:
            return self.emotion_params["happy"]
        return list(self.emotion_params.values())[0]



    def _handle_touch_event(self, event):
        """
        Handle raw pygame touch/mouse events and detect gestures.
        """
        if pygame is None:
            return

        if self.state.petting_active:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            self._touch_start_pos = event.pos
            self._touch_down_pos = event.pos
            self._touch_down_time = time.time()
            self._drag_distance = 0.0

        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            if self._touch_down_pos:
                dx = event.pos[0] - self._touch_down_pos[0]
                dy = event.pos[1] - self._touch_down_pos[1]
                self._drag_distance += abs(dx) + abs(dy)
                self._touch_down_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP:
            if self._touch_start_pos is None:
                return
            up_pos = event.pos
            start_pos = self._touch_start_pos
            duration = time.time() - self._touch_down_time
            dist = self._drag_distance
            dx = up_pos[0] - start_pos[0]
            dy = up_pos[1] - start_pos[1]

            self._touch_start_pos = None
            self._touch_down_pos = None
            self._drag_distance = 0.0

            gesture = self._classify_gesture(duration, dist, dx, dy)
            if gesture:
                self._trigger_gesture_effect(gesture)

    def _discard_touch_events(self):
        """
        Drop queued touch/mouse events so they don't fire after a petting lock.
        """
        if pygame is None:
            return
        touch_events = (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
        )
        pygame.event.clear(touch_events)

    def _classify_gesture(
        self, duration: float, dist: float, dx: float, dy: float
    ) -> Optional[str]:
        """
        Classify gesture based on simple thresholds.
        """
        tap_dist = float(self.touch_thresholds.get('tap_distance', 20))
        double_tap_window = float(
            self.touch_thresholds.get('double_tap_window', 0.35)
        )
        long_press_time = float(self.touch_thresholds.get('long_press', 0.6))
        drag_dist = float(self.touch_thresholds.get('drag_distance', 60))
        circle_dist = float(self.touch_thresholds.get('circle_distance', 140))
        circle_return = float(self.touch_thresholds.get('circle_return', 45))

        now = time.time()
        closure = abs(dx) + abs(dy)

        closure_ratio = closure / max(dist, 1e-6)


        if duration >= long_press_time and dist < drag_dist:
            return "long_press"


        if dist < tap_dist and duration < long_press_time:
            if (
                self.pending_tap_time > 0.0
                and now - self.pending_tap_time <= double_tap_window
            ):
                self.pending_tap_time = 0.0
                return "double_tap"
            self.pending_tap_time = now
            return None


        if (
            dist >= circle_dist
            and closure <= circle_return
            and closure_ratio <= 0.25
        ):
            return "scroll"


        if dist >= drag_dist:
            return "drag"

        return None

    def _trigger_gesture_effect(self, gesture: str):
        """
        Trigger configured effect for a gesture with rate limiting.
        """
        now = time.time()
        if now - self.state.last_gesture_time < self.gesture_cooldown:
            return
        if now < self.state.gesture_busy_until:
            return
        if self.state.petting_active:
            return
        self.state.last_gesture_time = now

        effect = self.gesture_effects.get(gesture)
        if not effect:
            logger.debug("Gesture %s has no configured effect", gesture)
            return


        self.state.petting_active = True
        self.state.gesture_busy_until = now + self.effect_busy_window
        self._discard_touch_events()


        if now - self._last_effect_time < self.effect_queue_cooldown:

            self.state.petting_active = False
            logger.debug("Effect suppressed by cooldown")
            return
        self._last_effect_time = now


        emotion = effect.get('emotion')
        if emotion:
            self.set_emotion(emotion, transition_duration=0.4)


        busy_seconds = self.effect_busy_window
        speak_text = effect.get('speak')
        if isinstance(speak_text, str) and speak_text.strip():
            estimated = (len(speak_text) / 10.0) + 1.5
            busy_seconds = max(busy_seconds, estimated)

        self.state.gesture_busy_until = now + busy_seconds


        if self.effect_callback:



            def _cb_wrapper():
                try:
                    self.effect_callback(effect)
                except (
                    RuntimeError,
                    ValueError,
                    OSError,
                    TypeError,
                ) as exc:
                    logger.error("Effect callback failed: %s", exc)

            threading.Thread(target=_cb_wrapper, daemon=True).start()
        else:

            self.command_queue.put({
                'type': 'APPLY_EFFECT',
                'effect': effect
            })

    def _apply_effect(self, effect: Dict):
        """
        Handle non-emotion effects internally (placeholder for future hooks).
        """
        sound = effect.get('sound')
        speak = effect.get('speak')
        hardware = effect.get('hardware')
        if sound:
            logger.info("Gesture sound requested: %s", sound)
        if speak:
            logger.info("Gesture speak requested: %s", speak)
        if hardware:
            logger.info("Gesture hardware action: %s", hardware)
