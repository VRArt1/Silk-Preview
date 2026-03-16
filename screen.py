from PIL import Image, ImageSequence
from typing import Optional, Tuple, List


class Screen:
    FRAME_WIDTH = 878
    FRAME_HEIGHT = 1043

    # Default positions as percentages (x, y, w, h) - relative to frame dimensions
    TOP_SCREEN_PCT = (0.05, 0.025, 0.9, 0.425)  # ~ (44, 26, 790, 444) at 878x1043
    BOTTOM_SCREEN_PCT = (0.249, 0.566, 0.502, 0.361)  # ~ (219, 590, 441, 377) at 878x1043
    SINGLE_SCREEN_PCT = (0.394, 0.059, 0.935, 0.557)  # ~ (346, 62, 1032, 581) at 878x1043
    
    # Dual screen mode positions (Thor/Aynthor) - computed from percentages
    TOP_SCREEN = (44, 26, 790, 444)  # +1 pixel to left to fill gap
    BOTTOM_SCREEN = (219, 590, 441, 377)  # +1 height to fill gap
    
    # Single screen mode positions (Odin)
    SINGLE_SCREEN = (346, 62, 1032, 581)  # External screen position (+1 to fill gap)
    SINGLE_SCREEN_MAIN_OFFSET: int = -300  # Start above external screen  # Vertical offset for main screen (negative = moves up)
    BOTTOM_SCREEN_UI_OFFSET = 40
    BOTTOM_SCREEN_TOP_PADDING = 20
    BOTTOM_SCREEN_BOTTOM_PADDING = 50
    
    # Percentage-based offsets (for scaling across different screen sizes)
    # Calculated from reference: external.h = 581 (Odin)
    BOTTOM_SCREEN_TOP_PADDING_PCT = 0.034  # 20/581
    BOTTOM_SCREEN_BOTTOM_PADDING_PCT = 0.086  # 50/581
    
    @classmethod
    def set_frame_dimensions(cls, width: int, height: int):
        """Set frame dimensions and compute pixel positions from percentages."""
        cls.FRAME_WIDTH = width
        cls.FRAME_HEIGHT = height
        cls.TOP_SCREEN = cls.percentages_to_pixels(cls.TOP_SCREEN_PCT)
        cls.BOTTOM_SCREEN = cls.percentages_to_pixels(cls.BOTTOM_SCREEN_PCT)
        cls.SINGLE_SCREEN = cls.percentages_to_pixels(cls.SINGLE_SCREEN_PCT)
    
    @classmethod
    def percentages_to_pixels(cls, pct: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
        """Convert percentage values (0.0-1.0) to pixel coordinates."""
        px, py, pw, ph = pct
        return (
            round(px * cls.FRAME_WIDTH),
            round(py * cls.FRAME_HEIGHT),
            round(pw * cls.FRAME_WIDTH),
            round(ph * cls.FRAME_HEIGHT)
        )
    
    @classmethod
    def pixels_to_percentages(cls, rect: Tuple[int, int, int, int]) -> Tuple[float, float, float, float]:
        """Convert pixel coordinates to percentage values (0.0-1.0)."""
        x, y, w, h = rect
        if cls.FRAME_WIDTH == 0 or cls.FRAME_HEIGHT == 0:
            return (0, 0, 0, 0)
        return (
            x / cls.FRAME_WIDTH,
            y / cls.FRAME_HEIGHT,
            w / cls.FRAME_WIDTH,
            h / cls.FRAME_HEIGHT
        )
    
    @classmethod
    def get_default_screen_rect(cls, screen_type: str) -> Tuple[int, int, int, int]:
        if screen_type == "main" or screen_type == "top":
            return cls.TOP_SCREEN
        elif screen_type == "external" or screen_type == "bottom":
            return cls.BOTTOM_SCREEN
        return cls.TOP_SCREEN
    
    @classmethod
    def get_screen_as_percentages(cls, rect: Tuple[int, int, int, int]) -> Tuple[float, float, float, float]:
        x, y, w, h = rect
        return (
            x / cls.FRAME_WIDTH,
            y / cls.FRAME_HEIGHT,
            w / cls.FRAME_WIDTH,
            h / cls.FRAME_HEIGHT
        )
    
    @classmethod
    def get_rect_from_percentages(cls, px: float, py: float, pw: float, ph: float) -> Tuple[int, int, int, int]:
        return (
            round(px * cls.FRAME_WIDTH),
            round(py * cls.FRAME_HEIGHT),
            round(pw * cls.FRAME_WIDTH),
            round(ph * cls.FRAME_HEIGHT)
        )

    def __init__(self, name: str, rect: Tuple[int, int, int, int], resolution: Tuple[int, int]):
        self.name = name
        self.x, self.y, self.w, self.h = rect
        self.resolution = resolution
        self.wallpaper: Optional[Image.Image] = None
        self.wallpaper_frames: List[Image.Image] = []
        self.wallpaper_index = 0
        self.wallpaper_duration = 100
        self.wallpaper_video_path: Optional[str] = None  # Path to video file if video wallpaper
        
        self._percentages = self.get_screen_as_percentages((self.x, self.y, self.w, self.h))

    @property
    def rect(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    @rect.setter
    def rect(self, value: Tuple[int, int, int, int]):
        self.x, self.y, self.w, self.h = value
        self._percentages = self.get_screen_as_percentages(value)
    
    @property
    def percentages(self) -> Tuple[float, float, float, float]:
        return self._percentages

    def set_rect_from_percentages(self, frame_w: int, frame_h: int):
        px, py, pw, ph = self._percentages
        self.x = round(px * frame_w)
        self.y = round(py * frame_h)
        self.w = round(pw * frame_w)
        self.h = round(ph * frame_h)

    def set_wallpaper(self, img: Optional[Image.Image]):
        if img is None:
            self.wallpaper = None
            self.wallpaper_frames = []
            return
        
        if img.format == 'GIF' or hasattr(img, 'n_frames'):
            self.wallpaper_frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
            self.wallpaper_index = 0
            self.wallpaper_duration = img.info.get('duration', 100)
            if self.wallpaper_duration < 10:
                self.wallpaper_duration = 100
            self.wallpaper = self.wallpaper_frames[0] if self.wallpaper_frames else None
        else:
            self.wallpaper_frames = []
            self.wallpaper = img

    def get_current_wallpaper(self) -> Optional[Image.Image]:
        # Return None if video wallpaper is playing (rendered separately)
        if self.wallpaper_is_video:
            return None
        if self.wallpaper_frames:
            return self.wallpaper_frames[self.wallpaper_index]
        return self.wallpaper
    
    def set_current_video_frame(self, frame: Optional[Image.Image]):
        """Store current video frame from PIL video player."""
        self._current_video_frame = frame
    
    def clear_current_video_frame(self):
        """Clear current video frame."""
        self._current_video_frame = None
    
    @property
    def wallpaper_is_video(self) -> bool:
        """Check if wallpaper is a video file."""
        return self.wallpaper_video_path is not None
    
    def set_wallpaper_video(self, video_path: str, first_frame: Optional[Image.Image]):
        """Set wallpaper from video file (stores path, uses first frame as static preview)."""
        self.wallpaper_video_path = video_path
        # Use first frame as the static wallpaper preview
        self.wallpaper = first_frame.convert("RGBA") if first_frame else None
        self.wallpaper_frames = []  # No animation frames for video
        self._current_video_frame = None  # Reset current video frame
    
    def clear_wallpaper_video(self):
        """Clear video wallpaper data."""
        self.wallpaper_video_path = None
        self._current_video_frame = None
    
    def disable_video_wallpaper(self):
        """Temporarily disable video wallpaper, showing static first frame instead.
        Stores the video path so it can be restored later.
        """
        if self.wallpaper_video_path:
            self._saved_video_path = self.wallpaper_video_path
            self.wallpaper_video_path = None
            self._current_video_frame = None
    
    def reenable_video_wallpaper(self):
        """Re-enable video wallpaper if it was previously disabled."""
        if hasattr(self, '_saved_video_path') and self._saved_video_path:
            self.wallpaper_video_path = self._saved_video_path
            self._saved_video_path = None
    
    def clear_wallpaper(self):
        """Clear all wallpaper data."""
        self.wallpaper = None
        self.wallpaper_frames = []
        self.wallpaper_index = 0
        self.wallpaper_video_path = None
        self._current_video_frame = None

    def advance_animation(self, dt: float) -> bool:
        if len(self.wallpaper_frames) > 1:
            self.wallpaper_index = (self.wallpaper_index + 1) % len(self.wallpaper_frames)
            return True
        return False


class MainScreen(Screen):
    def __init__(self, rect: Tuple[int, int, int, int] = None):
        super().__init__(
            name="main",
            rect=rect or Screen.get_default_screen_rect("main"),
            resolution=(1920, 1080)
        )


class ExternalScreen(Screen):
    def __init__(self, rect: Tuple[int, int, int, int] = None):
        super().__init__(
            name="external",
            rect=rect or Screen.get_default_screen_rect("external"),
            resolution=(1240, 1080)
        )
        self.ui_height = Screen.BOTTOM_SCREEN_UI_OFFSET
    
    def set_ui_height(self, height: int):
        self.ui_height = height
    
    def get_grid_rect(self, scale: float = 1.0) -> Tuple[int, int, int, int]:
        # Use percentage of screen height for scalable padding
        padding_top = self.h * Screen.BOTTOM_SCREEN_TOP_PADDING_PCT
        padding_bottom = self.h * Screen.BOTTOM_SCREEN_BOTTOM_PADDING_PCT
        scaled_x = round(self.x * scale)
        scaled_y = round(self.y * scale) + round(padding_top * scale)
        scaled_w = round(self.w * scale)
        scaled_h = round(self.h * scale) - round(padding_top * scale) - round(padding_bottom * scale)
        return (scaled_x, scaled_y, scaled_w, scaled_h)


class ScreenManager:
    def __init__(self):
        self.main = MainScreen()
        self.external = ExternalScreen()
        self._frame_scale = 1.0
        self._frame_width = Screen.FRAME_WIDTH
        self._frame_height = Screen.FRAME_HEIGHT
        self._screen_mode = "dual"  # "dual" or "single"
    
    def set_frame_dimensions(self, width: int, height: int):
        self._frame_width = width
        self._frame_height = height
        if self._screen_mode == "single":
            self.set_single_screen_mode()
        else:
            self.main.set_rect_from_percentages(width, height)
            self.external.set_rect_from_percentages(width, height)
    
    def detect_from_frame(self, frame_img: Image.Image):
        width, height = frame_img.size
        self.set_frame_dimensions(width, height)
    
    def set_frame_scale(self, scale: float):
        self._frame_scale = scale
    
    def set_dual_screen_mode(self):
        """Set up dual screen mode (Thor/Aynthor)."""
        self._screen_mode = "dual"
        self.main.rect = Screen.TOP_SCREEN
        self.external.rect = Screen.BOTTOM_SCREEN
        # Re-apply percentages if frame dimensions are set
        if self._frame_width and self._frame_height:
            self.main.set_rect_from_percentages(self._frame_width, self._frame_height)
            self.external.set_rect_from_percentages(self._frame_width, self._frame_height)
    
    def set_single_screen_mode(self):
        """Set up single screen mode (Odin) - bottom screen fills display."""
        self._screen_mode = "single"
        # External screen position - use actual coordinates from SINGLE_SCREEN
        self.external.rect = Screen.SINGLE_SCREEN
        # Main screen stacked on top, matching width of external
        self._update_single_screen_main_position()
    
    def _update_single_screen_main_position(self):
        """Update main screen position in single screen mode (stacked on external)."""
        if self._screen_mode != "single":
            return
        # Main screen matches width of external, positioned above it with offset
        ext_x, ext_y, ext_w, ext_h = self.external.rect
        offset = Screen.SINGLE_SCREEN_MAIN_OFFSET
        # Main screen fills width, positioned above external (width -1 to match exactly)
        self.main.rect = (ext_x, ext_y + offset, ext_w - 1, ext_h)
    
    @property
    def screen_mode(self):
        return self._screen_mode
    
    def get_scaled_rect(self, screen: Screen, device_x: int = 0, device_y: int = 0) -> Tuple[int, int, int, int]:
        return (
            device_x + round(screen.x * self._frame_scale),
            device_y + round(screen.y * self._frame_scale),
            round(screen.w * self._frame_scale),
            round(screen.h * self._frame_scale)
        )
    
    def advance_animations(self, dt: float):
        self.main.advance_animation(dt)
        self.external.advance_animation(dt)
