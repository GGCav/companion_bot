"""
Display Renderer for Emotion Expression Pipeline
Handles pygame initialization, image loading, and frame rendering for piTFT
"""

try:
    import pygame  # type: ignore  # noqa: E0401
except ImportError:
    pygame = None
import os
import glob
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

from .procedural_face import ProceduralFaceRenderer



logger = logging.getLogger(__name__)
EmotionFrames = Tuple[pygame.Surface, pygame.Surface]


class DisplayRenderer:
    """
    Pygame rendering engine for emotion display
    Manages piTFT framebuffer, image loading, and alpha blending
    """

    def __init__(
        self,
        screen_size: Tuple[int, int] = (320, 240),
        framebuffer: str = "/dev/fb0",
        image_dir: str = "src/display",
        procedural_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize display renderer

        Args:
            screen_size: Display resolution (width, height)
            framebuffer: Path to framebuffer device (piTFT)
            image_dir: Directory containing emotion sprite images
        """
        self.screen_size = screen_size
        self.framebuffer = framebuffer
        self.image_dir = Path(image_dir)
        self.screen: Optional[pygame.Surface] = None

        self.emotion_images: Dict[str, EmotionFrames] = {}
        self.listening_image: Optional[pygame.Surface] = None


        procedural_config = procedural_config or {}
        self.use_procedural = procedural_config.get('enabled', False)
        self.procedural_renderer: Optional[ProceduralFaceRenderer] = None


        self._init_pygame()

        if self.use_procedural:
            self.procedural_renderer = ProceduralFaceRenderer(
                self.screen_size, procedural_config
            )
            logger.info("Procedural face renderer enabled")
        else:

            self._load_emotion_images()

    def _init_pygame(self):
        """Initialize pygame with piTFT framebuffer or fallback to window"""
        try:

            os.putenv('SDL_VIDEODRIVER', 'fbcon')
            os.putenv('SDL_FBDEV', self.framebuffer)
            os.putenv('SDL_NOMOUSE', '1')

            pygame.init()
            pygame.mouse.set_visible(False)
            self.screen = pygame.display.set_mode(self.screen_size)
            logger.info("Initialized piTFT display at %s", self.framebuffer)

        except pygame.error as e:
            logger.warning("piTFT initialization failed: %s", e)
            logger.warning("Falling back to window mode for testing")


            if 'SDL_VIDEODRIVER' in os.environ:
                del os.environ['SDL_VIDEODRIVER']
            if 'SDL_FBDEV' in os.environ:
                del os.environ['SDL_FBDEV']

            pygame.init()
            self.screen = pygame.display.set_mode(self.screen_size)
            pygame.display.set_caption("Emotion Display")
            logger.info("Initialized window mode")

    def _load_emotion_images(self):
        """
        Load all emotion sprite images from directory
        Automatically pairs base and speaking frames

        Pattern from test_emotion_display.py lines 10-41
        """
        if not self.image_dir.exists():
            logger.error("Image directory not found: %s", self.image_dir)
            return


        base_files = glob.glob(str(self.image_dir / "*.png"))

        loaded_count = 0
        for base_path in base_files:
            filename = os.path.basename(base_path)


            if "_speaking" in filename or "_active" in filename:
                continue

            emotion_name = os.path.splitext(filename)[0]


            if emotion_name == "listening":
                self._load_listening_image(base_path)
                continue


            try:
                base_surface = self._load_and_scale_image(base_path)


                speaking_path = self.image_dir / f"{emotion_name}_speaking.png"
                if speaking_path.exists():
                    speaking_surface = self._load_and_scale_image(
                        str(speaking_path)
                    )
                else:

                    speaking_surface = base_surface
                    logger.warning(
                        "No speaking frame for %s; using base", emotion_name
                    )

                self.emotion_images[emotion_name] = (
                    base_surface,
                    speaking_surface,
                )
                loaded_count += 1
                logger.debug("Loaded emotion: %s", emotion_name)

            except pygame.error as e:
                logger.error("Failed to load %s: %s", emotion_name, e)

        logger.info("Loaded %s emotion pairs", loaded_count)


        if loaded_count == 0:
            logger.error("No emotion images loaded; display disabled.")

    def _load_listening_image(self, base_path: str):
        """Load the special listening state image"""
        try:
            self.listening_image = self._load_and_scale_image(base_path)
            logger.debug("Loaded listening state image")
        except pygame.error as e:
            logger.error("Failed to load listening image: %s", e)

    def _load_and_scale_image(self, image_path: str) -> pygame.Surface:
        """
        Load PNG image and scale to screen size if needed

        Args:
            image_path: Path to PNG file

        Returns:
            Scaled pygame surface with alpha channel
        """
        surface = pygame.image.load(image_path).convert_alpha()


        if surface.get_size() != self.screen_size:
            surface = pygame.transform.smoothscale(surface, self.screen_size)

        return surface

    def get_emotion_frame(
        self, emotion: str, speaking: bool = False
    ) -> Optional[pygame.Surface]:
        """
        Get emotion surface for rendering

        Args:
            emotion: Emotion name (e.g., 'happy', 'sad')
            speaking: If True, return speaking frame; else base frame

        Returns:
            Pygame surface or None if emotion not found
        """
        if emotion not in self.emotion_images:
            logger.warning(
                "Emotion '%s' not found, using 'happy' fallback", emotion
            )
            emotion = 'happy'

            if emotion not in self.emotion_images:
                logger.error("Fallback emotion 'happy' also missing!")
                return None

        base_frame, speaking_frame = self.emotion_images[emotion]
        return speaking_frame if speaking else base_frame

    def get_listening_frame(self) -> Optional[pygame.Surface]:
        """Get listening state surface"""
        if self.listening_image is None:
            logger.warning("Listening image not loaded")
        return self.listening_image

    def render_frame(self, surface: pygame.Surface):
        """
        Render surface to screen

        Args:
            surface: Pygame surface to display
        """
        if surface is None:
            logger.warning("Attempted to render None surface")
            return

        self.screen.blit(surface, (0, 0))
        pygame.display.flip()

    def render_procedural(
        self,
        current_params: Dict,
        target_params: Optional[Dict],
        blend_alpha: float,
        speaking_level: float,
        listening: bool,
        delta_time: float,
    ):
        if not self.use_procedural or not self.procedural_renderer:
            logger.warning("Procedural renderer not available")
            return

        self.procedural_renderer.update_state(
            delta_time, speaking_level, listening
        )
        frame = self.procedural_renderer.render(
            current_params=current_params,
            target_params=target_params,
            blend_alpha=blend_alpha,
            listening=listening,
        )
        self.render_frame(frame)

    def create_blended_frame(
        self,
        img1: pygame.Surface,
        img2: pygame.Surface,
        alpha: float,
    ) -> pygame.Surface:
        """
        Create alpha-blended composite of two images for smooth transitions

        Args:
            img1: Current emotion surface
            img2: Target emotion surface
            alpha: Blend factor (0.0 = all img1, 1.0 = all img2)

        Returns:
            Blended surface
        """
        if img1 is None or img2 is None:
            logger.error("Cannot blend None surfaces")
            return img1 if img1 is not None else img2


        alpha = max(0.0, min(1.0, alpha))


        result = pygame.Surface(self.screen_size, pygame.SRCALPHA)


        img1_copy = img1.copy()
        img1_copy.set_alpha(int(255 * (1 - alpha)))
        result.blit(img1_copy, (0, 0))


        img2_copy = img2.copy()
        img2_copy.set_alpha(int(255 * alpha))
        result.blit(img2_copy, (0, 0))

        return result

    def clear_screen(self, color: Tuple[int, int, int] = (0, 0, 0)):
        """
        Clear screen with solid color

        Args:
            color: RGB color tuple (default: black)
        """
        self.screen.fill(color)

    def cleanup(self):
        """Clean up pygame resources"""
        pygame.quit()
        logger.info("Display renderer cleanup complete")
