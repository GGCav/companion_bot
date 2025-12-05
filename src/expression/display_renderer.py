"""
Display Renderer for Emotion Expression Pipeline
Handles pygame initialization, image loading, and frame rendering for piTFT
"""

import pygame
import os
import glob
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class DisplayRenderer:
    """
    Pygame rendering engine for emotion display
    Manages piTFT framebuffer, image loading, and alpha blending
    """

    def __init__(self, screen_size: Tuple[int, int] = (320, 240),
                 framebuffer: str = "/dev/fb1",
                 image_dir: str = "src/Display"):
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

        # Image cache: {emotion: (base_surface, speaking_surface)}
        self.emotion_images: Dict[str, Tuple[pygame.Surface, pygame.Surface]] = {}
        self.listening_image: Optional[pygame.Surface] = None

        # Initialize pygame with piTFT
        self._init_pygame()

        # Load all emotion sprites
        self._load_emotion_images()

    def _init_pygame(self):
        """Initialize pygame with piTFT framebuffer or fallback to window"""
        try:
            # Try piTFT configuration
            os.putenv('SDL_VIDEODRIVER', 'fbcon')
            os.putenv('SDL_FBDEV', self.framebuffer)
            os.putenv('SDL_NOMOUSE', '1')  # Disable mouse cursor

            pygame.init()
            self.screen = pygame.display.set_mode(self.screen_size)
            logger.info(f"Initialized piTFT display at {self.framebuffer}")

        except pygame.error as e:
            logger.warning(f"piTFT initialization failed: {e}")
            logger.warning("Falling back to window mode for testing")

            # Clear environment variables and retry in window mode
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
            logger.error(f"Image directory not found: {self.image_dir}")
            return

        # Find all base emotion PNG files (exclude _speaking and _active variants)
        base_files = glob.glob(str(self.image_dir / "*.png"))

        loaded_count = 0
        for base_path in base_files:
            filename = os.path.basename(base_path)

            # Skip speaking/active frames - they'll be paired later
            if "_speaking" in filename or "_active" in filename:
                continue

            emotion_name = os.path.splitext(filename)[0]  # e.g., "happy"

            # Special handling for listening state (not an emotion)
            if emotion_name == "listening":
                self._load_listening_image(base_path)
                continue

            # Load emotion pair (base + speaking)
            try:
                base_surface = self._load_and_scale_image(base_path)

                # Try to find speaking variant
                speaking_path = self.image_dir / f"{emotion_name}_speaking.png"
                if speaking_path.exists():
                    speaking_surface = self._load_and_scale_image(str(speaking_path))
                else:
                    # Reuse base frame if no speaking frame exists
                    speaking_surface = base_surface
                    logger.warning(f"No speaking frame for {emotion_name}, using base frame")

                self.emotion_images[emotion_name] = (base_surface, speaking_surface)
                loaded_count += 1
                logger.debug(f"Loaded emotion: {emotion_name}")

            except Exception as e:
                logger.error(f"Failed to load {emotion_name}: {e}")

        logger.info(f"Loaded {loaded_count} emotion pairs")

        # Validate required emotions loaded
        if loaded_count == 0:
            logger.error("No emotion images loaded! Display will not function.")

    def _load_listening_image(self, base_path: str):
        """Load the special listening state image"""
        try:
            self.listening_image = self._load_and_scale_image(base_path)
            logger.debug("Loaded listening state image")
        except Exception as e:
            logger.error(f"Failed to load listening image: {e}")

    def _load_and_scale_image(self, image_path: str) -> pygame.Surface:
        """
        Load PNG image and scale to screen size if needed

        Args:
            image_path: Path to PNG file

        Returns:
            Scaled pygame surface with alpha channel
        """
        surface = pygame.image.load(image_path).convert_alpha()

        # Scale to screen size if dimensions don't match
        if surface.get_size() != self.screen_size:
            surface = pygame.transform.smoothscale(surface, self.screen_size)

        return surface

    def get_emotion_frame(self, emotion: str, speaking: bool = False) -> Optional[pygame.Surface]:
        """
        Get emotion surface for rendering

        Args:
            emotion: Emotion name (e.g., 'happy', 'sad')
            speaking: If True, return speaking frame; else base frame

        Returns:
            Pygame surface or None if emotion not found
        """
        if emotion not in self.emotion_images:
            logger.warning(f"Emotion '{emotion}' not found, using 'happy' fallback")
            emotion = 'happy'  # Fallback to happy

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

    def create_blended_frame(self, img1: pygame.Surface, img2: pygame.Surface,
                           alpha: float) -> pygame.Surface:
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

        # Clamp alpha to valid range
        alpha = max(0.0, min(1.0, alpha))

        # Create result surface with alpha channel
        result = pygame.Surface(self.screen_size, pygame.SRCALPHA)

        # Draw current frame with (1-alpha) opacity
        img1_copy = img1.copy()
        img1_copy.set_alpha(int(255 * (1 - alpha)))
        result.blit(img1_copy, (0, 0))

        # Draw next frame with alpha opacity
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
