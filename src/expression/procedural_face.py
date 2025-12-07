"""
Procedural face renderer for lightweight, animatable expressions.
"""

import math
import random
from typing import Dict, Tuple, Optional

import pygame


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


class ProceduralFaceRenderer:
    """
    Draws a simple face (eyes, brows, mouth) using Pygame primitives so we can
    animate without swapping PNGs. All colors and geometry are driven by the
    supplied emotion parameters and blended when transitioning.
    """

    def __init__(self, screen_size: Tuple[int, int], config: Dict):
        self.screen_size = screen_size
        self.surface = pygame.Surface(screen_size, pygame.SRCALPHA)

        blink_range = config.get("blink_interval", [3.0, 6.0])
        self.blink_interval_range = (
            float(blink_range[0]),
            float(blink_range[1]) if len(blink_range) > 1 else float(blink_range[0]),
        )
        self.blink_duration = float(config.get("blink_duration", 0.12))
        self.eye_jitter = float(config.get("eye_jitter", 1.5))
        self.mouth_smooth = float(config.get("mouth_smooth", 8.0))
        self.transition_smooth = float(config.get("transition_smooth", 6.0))
        self.listening_pulse_speed = float(config.get("listening_pulse_speed", 1.5))
        self.listening_pulse_strength = float(config.get("listening_pulse_strength", 0.08))
        self.listening_glow_color = tuple(config.get("listening_glow_color", [0, 200, 255]))
        self.listening_glow_alpha = float(config.get("listening_glow_alpha", 0.35))
        self.listening_glow_thickness = int(config.get("listening_glow_thickness", 6))
        self.background_color = tuple(config.get("background", [0, 0, 0]))

        self._blink_timer = 0.0
        self._time_since_blink = 0.0
        self._next_blink = self._random_blink_interval()
        self._is_blinking = False

        self._mouth_level = 0.0
        self._speaking_target = 0.0
        self._listening_phase = 0.0

    def _random_blink_interval(self) -> float:
        return random.uniform(*self.blink_interval_range)

    def update_state(self, delta_time: float, speaking_level: float, listening: bool):
        self._speaking_target = _clamp01(speaking_level)

        # Smooth mouth openness
        smooth = max(1e-3, self.mouth_smooth)
        blend = 1.0 - math.exp(-smooth * max(delta_time, 0.0))
        self._mouth_level = _lerp(self._mouth_level, self._speaking_target, blend)

        # Blink logic
        self._time_since_blink += delta_time
        if not self._is_blinking and self._time_since_blink >= self._next_blink:
            self._is_blinking = True
            self._blink_timer = 0.0

        if self._is_blinking:
            self._blink_timer += delta_time
            if self._blink_timer >= self.blink_duration:
                self._is_blinking = False
                self._time_since_blink = 0.0
                self._next_blink = self._random_blink_interval()

        # Listening pulse for subtle scale/brightness
        if listening:
            self._listening_phase += delta_time * self.listening_pulse_speed
        else:
            self._listening_phase = 0.0

    def render(
        self,
        current_params: Dict,
        target_params: Optional[Dict],
        blend_alpha: float,
        listening: bool,
    ) -> pygame.Surface:
        params = self._blend_params(current_params, target_params, blend_alpha)
        w, h = self.screen_size
        self.surface.fill(self.background_color)

        eye_spacing = params.get("eye_spacing", 90)
        eye_width = params.get("eye_width", 42)
        eye_height = params.get("eye_height", 42)
        eye_y = params.get("eye_y", int(h * 0.42))
        pupil_size = params.get("pupil_size", 12)
        brow_raise = params.get("brow_raise", 0.0)
        brow_slant = params.get("brow_slant", 0.0)
        mouth_width = params.get("mouth_width", 120)
        mouth_height = params.get("mouth_height", 24)
        mouth_curve = params.get("mouth_curve", 0.0)
        mouth_base = params.get("mouth_open", 0.05)

        eye_color = tuple(params.get("eye_color", [240, 240, 240]))
        pupil_color = tuple(params.get("pupil_color", [20, 20, 20]))
        brow_color = tuple(params.get("brow_color", [220, 220, 220]))
        mouth_color = tuple(params.get("mouth_color", [240, 120, 120]))

        listening_scale = 1.0 + (math.sin(self._listening_phase) * self.listening_pulse_strength if listening else 0.0)

        # Eyes
        for direction in (-1, 1):
            jitter_x = random.uniform(-self.eye_jitter, self.eye_jitter)
            jitter_y = random.uniform(-self.eye_jitter, self.eye_jitter)
            eye_center = (
                int(w / 2 + direction * eye_spacing * listening_scale + jitter_x),
                int(eye_y * listening_scale + jitter_y),
            )

            blink_scale = 0.2 if self._is_blinking else 1.0
            self._draw_eye(eye_center, int(eye_width * listening_scale), int(eye_height * listening_scale * blink_scale),
                           eye_color, pupil_color, pupil_size, params.get("pupil_offset", 0))

            # Brows
            self._draw_brow(eye_center, eye_width, eye_height, brow_raise, brow_slant * direction, brow_color)

        # Mouth
        mouth_open = mouth_base + self._mouth_level * params.get("mouth_sensitivity", 0.6)
        mouth_open = _clamp01(mouth_open)
        self._draw_mouth((w // 2, int(h * 0.7)), mouth_width, mouth_height, mouth_curve, mouth_open, mouth_color)

        if listening and self.listening_glow_alpha > 0.0:
            pulse = 0.5 + 0.5 * math.sin(self._listening_phase)
            alpha = int(255 * self.listening_glow_alpha * pulse)
            if alpha > 0:
                overlay = pygame.Surface(self.screen_size, pygame.SRCALPHA)
                color = (
                    self.listening_glow_color[0],
                    self.listening_glow_color[1],
                    self.listening_glow_color[2],
                    alpha,
                )
                thickness = max(2, self.listening_glow_thickness)
                rect = overlay.get_rect().inflate(-thickness, -thickness)
                pygame.draw.rect(overlay, color, rect, thickness)
                self.surface.blit(overlay, (0, 0))

        return self.surface

    def _blend_params(self, current: Dict, target: Optional[Dict], alpha: float) -> Dict:
        if not target:
            return current
        t = _clamp01(alpha)
        blended = {}
        keys = set(current.keys()) | set(target.keys())
        for key in keys:
            a = current.get(key, 0.0)
            b = target.get(key, a)
            if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
                blended[key] = [ _lerp(x, y, t) for x, y in zip(a, b) ]
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                blended[key] = _lerp(float(a), float(b), t)
            else:
                blended[key] = b
        return blended

    def _draw_eye(
        self,
        center: Tuple[int, int],
        width: int,
        height: int,
        eye_color: Tuple[int, int, int],
        pupil_color: Tuple[int, int, int],
        pupil_size: float,
        pupil_offset: float,
    ):
        rect = pygame.Rect(0, 0, width, height)
        rect.center = center
        pygame.draw.ellipse(self.surface, eye_color, rect)

        pupil_rect = pygame.Rect(0, 0, int(pupil_size), int(pupil_size))
        pupil_rect.center = (center[0] + pupil_offset, center[1])
        pygame.draw.circle(self.surface, pupil_color, pupil_rect.center, pupil_rect.width // 2)

    def _draw_brow(
        self,
        eye_center: Tuple[int, int],
        eye_width: int,
        eye_height: int,
        raise_amt: float,
        slant: float,
        color: Tuple[int, int, int],
    ):
        start = (
            int(eye_center[0] - eye_width * 0.6),
            int(eye_center[1] - eye_height * (0.8 + raise_amt) - slant * 10),
        )
        end = (
            int(eye_center[0] + eye_width * 0.6),
            int(eye_center[1] - eye_height * (0.8 + raise_amt) + slant * 10),
        )
        # Older pygame on Pi may not accept keyword args for width
        pygame.draw.line(self.surface, color, start, end, 4)

    def _draw_mouth(
        self,
        center: Tuple[int, int],
        width: int,
        height: int,
        curve: float,
        openness: float,
        color: Tuple[int, int, int],
    ):
        w2 = width // 2
        h2 = max(2, int(height * (0.3 + openness)))
        curve_offset = int(curve * height)

        start = (center[0] - w2, center[1])
        end = (center[0] + w2, center[1])
        control = (center[0], center[1] + curve_offset)

        # Approximate quadratic curve with lines
        points = []
        steps = 20
        for i in range(steps + 1):
            t = i / steps
            x = int((1 - t) * (1 - t) * start[0] + 2 * (1 - t) * t * control[0] + t * t * end[0])
            y = int((1 - t) * (1 - t) * start[1] + 2 * (1 - t) * t * control[1] + t * t * end[1])
            points.append((x, y))

        # Use positional width for compatibility
        pygame.draw.lines(self.surface, color, False, points, h2)

