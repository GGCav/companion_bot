"""
Pi Camera v2 Handler
Optimized camera capture for Raspberry Pi Camera Module v2
"""

import cv2
import numpy as np
import threading
import queue
import logging
import time
from typing import Optional, Tuple

try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logging.warning("picamera2 not available, falling back to OpenCV")

logger = logging.getLogger(__name__)


class Camera:
    """Handles Pi Camera v2 capture with threading"""

    def __init__(self, config: dict):
        """
        Initialize camera

        Args:
            config: Camera configuration dictionary from settings.yaml
        """
        self.config = config
        self.camera_config = config['vision']['camera']
        self.performance_config = config['vision']['performance']

        self.width, self.height = self.camera_config['resolution']
        self.fps = self.camera_config['framerate']
        self.rotation = self.camera_config.get('rotation', 0)

        self.camera: Optional[object] = None
        self.use_picamera2 = PICAMERA2_AVAILABLE

        # Frame buffer
        self.frame_queue = queue.Queue(maxsize=self.performance_config['buffer_size'])
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

        # Threading
        self.is_running = False
        self.capture_thread: Optional[threading.Thread] = None

        # FPS tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0

        self._initialize_camera()

    def _initialize_camera(self):
        """Initialize the camera hardware"""
        try:
            if self.use_picamera2:
                self._init_picamera2()
            else:
                self._init_opencv_camera()

            logger.info(f"Camera initialized: {self.width}x{self.height} @ {self.fps}fps")

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise

    def _init_picamera2(self):
        """Initialize using picamera2 (recommended for Pi Camera)"""
        self.camera = Picamera2()

        # Configure camera
        camera_config = self.camera.create_still_configuration(
            main={"size": (self.width, self.height)},
            controls={"FrameRate": self.fps}
        )
        self.camera.configure(camera_config)

        # Apply settings
        if self.camera_config.get('hflip', False):
            self.camera.options['hflip'] = True
        if self.camera_config.get('vflip', False):
            self.camera.options['vflip'] = True

        logger.info("Using picamera2 for camera capture")

    def _init_opencv_camera(self):
        """Initialize using OpenCV (fallback)"""
        self.camera = cv2.VideoCapture(0)

        if not self.camera.isOpened():
            raise RuntimeError("Failed to open camera with OpenCV")

        # Set camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)

        logger.info("Using OpenCV for camera capture")

    def start(self):
        """Start camera capture thread"""
        if self.is_running:
            logger.warning("Camera already running")
            return

        if self.use_picamera2:
            self.camera.start()

        # Warm up camera
        warmup_time = self.config['system']['startup']['camera_warmup_time']
        logger.info(f"Camera warming up for {warmup_time}s...")
        time.sleep(warmup_time)

        self.is_running = True

        if self.performance_config['use_threading']:
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            logger.info("Camera capture thread started")
        else:
            logger.info("Camera started in synchronous mode")

    def stop(self):
        """Stop camera capture"""
        if not self.is_running:
            return

        self.is_running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)

        if self.use_picamera2:
            self.camera.stop()
        else:
            self.camera.release()

        logger.info("Camera stopped")

    def _capture_loop(self):
        """Main capture loop running in thread"""
        while self.is_running:
            try:
                frame = self._grab_frame()

                if frame is not None:
                    # Update latest frame
                    with self.frame_lock:
                        self.latest_frame = frame

                    # Add to queue (non-blocking)
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        # Drop oldest frame if queue is full
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait(frame)
                        except queue.Empty:
                            pass

                    # Update FPS counter
                    self._update_fps()

            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)

    def _grab_frame(self) -> Optional[np.ndarray]:
        """
        Grab a single frame from camera

        Returns:
            Frame as numpy array (BGR format)
        """
        try:
            if self.use_picamera2:
                # Capture from picamera2
                frame = self.camera.capture_array()

                # Convert RGB to BGR for OpenCV compatibility
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            else:
                # Capture from OpenCV
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to read frame")
                    return None

            # Apply rotation if specified
            if self.rotation != 0:
                frame = self._rotate_frame(frame)

            return frame

        except Exception as e:
            logger.error(f"Failed to grab frame: {e}")
            return None

    def _rotate_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Rotate frame by specified angle

        Args:
            frame: Input frame

        Returns:
            Rotated frame
        """
        if self.rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    def read(self) -> Optional[np.ndarray]:
        """
        Read the latest frame

        Returns:
            Latest frame or None if not available
        """
        if not self.is_running:
            logger.warning("Camera not running")
            return None

        if self.performance_config['use_threading']:
            with self.frame_lock:
                return self.latest_frame.copy() if self.latest_frame is not None else None
        else:
            return self._grab_frame()

    def read_from_queue(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """
        Read frame from queue (blocking)

        Args:
            timeout: Maximum time to wait for frame

        Returns:
            Frame or None if timeout
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _update_fps(self):
        """Update FPS counter"""
        self.fps_counter += 1

        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.current_fps = self.fps_counter / elapsed
            self.fps_counter = 0
            self.fps_start_time = time.time()

    def get_fps(self) -> float:
        """
        Get current FPS

        Returns:
            Current frames per second
        """
        return self.current_fps

    def get_resolution(self) -> Tuple[int, int]:
        """
        Get camera resolution

        Returns:
            (width, height) tuple
        """
        return (self.width, self.height)

    def capture_image(self, filename: str):
        """
        Capture and save a single image

        Args:
            filename: Output filename
        """
        frame = self.read()
        if frame is not None:
            cv2.imwrite(filename, frame)
            logger.info(f"Image saved to {filename}")
        else:
            logger.warning("No frame available to save")

    def cleanup(self):
        """Clean up camera resources"""
        self.stop()
        logger.info("Camera cleanup complete")


if __name__ == "__main__":
    # Test camera
    logging.basicConfig(level=logging.INFO)

    # Mock config
    config = {
        'vision': {
            'camera': {
                'resolution': [640, 480],
                'framerate': 30,
                'rotation': 0,
                'hflip': False,
                'vflip': False
            },
            'performance': {
                'use_threading': True,
                'buffer_size': 2
            }
        },
        'system': {
            'startup': {
                'camera_warmup_time': 2.0
            }
        }
    }

    print("Initializing camera...")
    camera = Camera(config)

    try:
        camera.start()
        print("Camera started. Press Ctrl+C to stop")
        print("Displaying FPS for 10 seconds...")

        start_time = time.time()
        while time.time() - start_time < 10:
            frame = camera.read()
            if frame is not None:
                # Display frame (if running on Pi with display)
                print(f"\rFPS: {camera.get_fps():.1f}", end='')
            time.sleep(0.1)

        print("\n\nCapturing test image...")
        camera.capture_image("/tmp/test_capture.jpg")
        print("Image saved to /tmp/test_capture.jpg")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        camera.cleanup()
        print("Test complete!")
