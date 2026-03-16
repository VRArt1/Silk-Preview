import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple


class PILVideoPlayer:
    """PIL/OpenCV-based video player for wallpaper playback with background threading."""
    
    _cv2_available = None
    
    def __init__(self, video_path: str, parent_window, geometry: Tuple[int, int, int, int]):
        """
        Initialize PIL-based video player.
        
        Args:
            video_path: Path to video file (mp4, webm)
            parent_window: Parent Tkinter canvas for rendering
            geometry: (x, y, width, height) - position and size on canvas
        """
        self.video_path = video_path
        self.parent_window = parent_window
        self.geometry = geometry
        self.is_playing = False
        self._running = False
        self._thread = None
        self._cap = None
        self._current_frame = None
        self._frame_lock = None
        self._fps = 30.0
        self._video_width = 0
        self._video_height = 0
        self._target_width = geometry[2]
        self._target_height = geometry[3]
        
        # Check cv2 availability
        if not self._check_cv2_available():
            return
        
        self._init_player()
    
    @classmethod
    def _check_cv2_available(cls) -> bool:
        """Check if cv2 is available."""
        if cls._cv2_available is not None:
            return cls._cv2_available
        
        try:
            import cv2
            cls._cv2_available = True
            return True
        except ImportError as e:
            print(f"opencv-python not installed. PIL video wallpapers will not work: {e}")
            cls._cv2_available = False
            return False
    
    def _init_player(self):
        """Initialize the video capture."""
        try:
            import cv2
            
            self._cap = cv2.VideoCapture(self.video_path)
            if not self._cap.isOpened():
                print(f"Failed to open video: {self.video_path}")
                self._cap = None
                return
            
            # Get video properties
            self._video_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._video_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._fps = self._cap.get(cv2.CAP_PROP_FPS)
            if self._fps <= 0:
                self._fps = 30.0
            
            # Initialize thread-safe frame storage
            import threading
            self._frame_lock = threading.Lock()
            self._current_frame = None
            
        except Exception as e:
            print(f"Error initializing PIL video player: {e}")
            self._cap = None
    
    def play(self, on_playing_callback=None):
        """Start video playback in background thread."""
        if not self._cap:
            return False
        
        if self.is_playing:
            return True
        
        self._running = True
        self.is_playing = True
        
        # Start background decode thread
        import threading
        self._thread = threading.Thread(target=self._decode_loop, daemon=True)
        self._thread.start()
        
        if on_playing_callback:
            self.parent_window.after(0, on_playing_callback)
        
        return True
    
    def _decode_loop(self):
        """Background thread that decodes video frames at the video's native FPS."""
        import cv2
        from PIL import Image
        
        # Use the video's native FPS for decoding
        frame_delay = 1.0 / self._fps if self._fps > 0 else 0.033
        next_frame_time = time.time() + frame_delay
        
        while self._running and self._cap and self._cap.isOpened():
            current_time = time.time()
            
            # Wait until it's time for the next frame
            if current_time < next_frame_time:
                time.sleep(next_frame_time - current_time)
            
            # Read frame from video
            ret, frame = self._cap.read()
            
            if not ret:
                # Loop back to beginning
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if not ret:
                    break
                # Reset timing after loop
                next_frame_time = time.time() + frame_delay
                continue
            
            # Convert BGR to RGBA
            frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            
            # Resize to target dimensions
            try:
                target_w = int(self._target_width) if self._target_width else 0
                target_h = int(self._target_height) if self._target_height else 0
                if target_w > 0 and target_h > 0:
                    frame_rgba = cv2.resize(frame_rgba, (target_w, target_h), 
                                          interpolation=cv2.INTER_LINEAR)
            except (TypeError, ValueError):
                pass
            
            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgba, 'RGBA')
            
            # Store latest frame thread-safely
            with self._frame_lock:
                self._current_frame = pil_image
                self._frame_count = getattr(self, '_frame_count', 0) + 1
            
            # Schedule next frame time
            next_frame_time += frame_delay
    
    def get_current_frame(self):
        """Get the current frame for rendering. Thread-safe."""
        if not self._frame_lock:
            return None
        
        with self._frame_lock:
            return self._current_frame
    
    def has_new_frame(self):
        """Check if there's a new frame since last check."""
        if not self._frame_lock:
            return False
        current_count = getattr(self, '_frame_count', 0)
        with self._frame_lock:
            new_count = getattr(self, '_frame_count', 0)
        return new_count != current_count
    
    def pause(self):
        """Pause video playback."""
        self.is_playing = False
    
    def stop(self):
        """Stop video playback."""
        self._running = False
        self.is_playing = False
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
    
    def set_position(self, x: int, y: int, width: int, height: int):
        """Update video position and size."""
        self.geometry = (x, y, width, height)
        self._target_width = width
        self._target_height = height
    
    def is_loaded(self) -> bool:
        """Check if player was successfully initialized."""
        return self._cap is not None and self._cap.isOpened()
    
    def get_video_size(self) -> Tuple[int, int]:
        """Get original video dimensions."""
        return (self._video_width, self._video_height)
    
    def cleanup(self):
        """Stop and release video player resources."""
        self.stop()
        
        if self._cap:
            self._cap.release()
            self._cap = None
        
        self._current_frame = None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.cleanup()


class VideoPlayerManager:
    """Manages multiple video players for wallpaper playback."""
    
    def __init__(self, parent_window, renderer=None):
        self.parent_window = parent_window
        self.renderer = renderer  # Store renderer to access screen objects
        self.players = {}  # {screen_name: VideoPlayer}
    
    def create_player(self, screen_name: str, video_path: str, geometry: Tuple[int, int, int, int], use_pil: bool = True) -> bool:
        """
        Create a video player for a screen.
        
        Args:
            screen_name: 'main' or 'external'
            video_path: Path to video file
            geometry: (x, y, width, height)
            use_pil: Ignored - now always uses PIL-based player
        
        Returns:
            True if player created successfully
        """
        # Always use PIL-based player
        return self._create_pil_player(screen_name, video_path, geometry)
    
    def _create_pil_player(self, screen_name: str, video_path: str, geometry: Tuple[int, int, int, int]) -> bool:
        """Create a PIL-based video player for a screen."""
        # Cleanup existing player for this screen if any
        if screen_name in self.players:
            self.remove_player(screen_name)
        
        try:
            player = PILVideoPlayer(video_path, self.parent_window, geometry)
            if player.is_loaded():
                self.players[screen_name] = player
                return True
            else:
                player.cleanup()
                return False
        except Exception as e:
            print(f"Error creating PIL video player for {screen_name}: {e}")
            return False
    
    def is_pil_player(self, screen_name: str) -> bool:
        """Check if a player is a PIL-based player."""
        if screen_name not in self.players:
            return False
        return isinstance(self.players[screen_name], PILVideoPlayer)
    
    def get_current_frame(self, screen_name: str):
        """Get the current frame from a PIL player."""
        if screen_name not in self.players:
            return None
        player = self.players[screen_name]
        if isinstance(player, PILVideoPlayer):
            return player.get_current_frame()
        return None
    
    def play(self, screen_name: str, on_playing_callback=None) -> bool:
        """Play video on a specific screen.
        
        Args:
            screen_name: 'main' or 'external'
            on_playing_callback: Called when video actually starts playing
        """
        if screen_name not in self.players:
            return False
        
        try:
            return self.players[screen_name].play(on_playing_callback=on_playing_callback)
        except Exception as e:
            print(f"Error playing video on {screen_name}: {e}")
            return False
    
    def play_all(self):
        """Play all video players."""
        for name, player in self.players.items():
            try:
                player.play()
            except Exception as e:
                print(f"Error playing {name}: {e}")
    
    def pause(self, screen_name: str):
        """Pause video on a specific screen."""
        if screen_name in self.players:
            try:
                self.players[screen_name].pause()
            except:
                pass
    
    def pause_all(self):
        """Pause all video players."""
        for player in self.players.values():
            try:
                player.pause()
            except:
                pass
    
    def stop(self, screen_name: str):
        """Stop video on a specific screen."""
        if screen_name in self.players:
            try:
                self.players[screen_name].stop()
            except:
                pass
    
    def stop_all(self):
        """Stop all video players."""
        for player in self.players.values():
            try:
                player.stop()
            except:
                pass
    
    def update_geometry(self, screen_name: str, geometry: Tuple[int, int, int, int]):
        """Update position/size for a screen's video."""
        if screen_name in self.players:
            try:
                self.players[screen_name].set_position(*geometry)
            except:
                pass
    
    def update_all_geometries(self, geometries: dict):
        """Update geometries for all screens."""
        for screen_name, geometry in geometries.items():
            self.update_geometry(screen_name, geometry)
    
    def raise_all_videos(self, canvas):
        """Raise all video window items above other canvas items."""
        for player in self.players.values():
            if hasattr(player, 'video_window_id') and player.video_window_id:
                try:
                    canvas.tag_raise(player.video_window_id)
                except:
                    pass
    
    def lower_all_videos(self, canvas):
        """Lower all video items below content (but above bg)."""
        for player in self.players.values():
            # Handle VLC-based players
            if hasattr(player, 'video_window_id') and player.video_window_id:
                try:
                    canvas.tag_lower(player.video_window_id)
                except:
                    pass
            # Handle PIL-based players
            elif hasattr(player, '_canvas_image_id') and player._canvas_image_id:
                try:
                    canvas.tag_lower(player._canvas_image_id)
                except:
                    pass
    
    def remove_player(self, screen_name: str):
        """Remove and cleanup a video player."""
        # Clear video frame from screen before removing player
        if self.renderer and hasattr(self.renderer, 'screen_manager'):
            screen = getattr(self.renderer.screen_manager, screen_name, None)
            if screen:
                screen.clear_current_video_frame()
        
        if screen_name in self.players:
            try:
                self.players[screen_name].cleanup()
            except:
                pass
            del self.players[screen_name]
    
    def cleanup(self):
        """Cleanup all video players."""
        for screen_name in list(self.players.keys()):
            self.remove_player(screen_name)
    
    def has_player(self, screen_name: str) -> bool:
        """Check if a player exists for a screen."""
        return screen_name in self.players and self.players[screen_name].is_loaded()
    
    def get_player_window_id(self, screen_name: str):
        """Get the canvas window id for a player's video frame."""
        if screen_name in self.players:
            player = self.players[screen_name]
            if hasattr(player, 'video_window_id'):
                return player.video_window_id
        return None
    
    def is_available(self) -> bool:
        """Check if video playback is available (PIL/opencv installed)."""
        return PILVideoPlayer._check_cv2_available()
    
    def update_canvas_frames(self, canvas, is_single_stacked=False, ss_mask=None, main_screen_geometry=None, external_screen_geometry=None):
        """Update canvas with latest frames from PIL players. Only updates when new frames available.
        
        Args:
            canvas: Tkinter canvas to render to
            is_single_stacked: Whether in single-screen stacked mode
            ss_mask: The ss_mask image from renderer (for main screen masking)
            main_screen_geometry: (x, y, w, h) geometry of main screen
            external_screen_geometry: (x, y, w, h) geometry of external screen
        """
        for screen_name, player in self.players.items():
            if isinstance(player, PILVideoPlayer) and player.is_loaded() and player.is_playing:
                # Check if there's a new frame
                current_count = getattr(player, '_frame_count', 0)
                last_count = getattr(player, '_last_frame_update_count', -1)
                
                if current_count != last_count:
                    frame = player.get_current_frame()
                    if frame is not None and canvas:
                        try:
                            # Apply ss_mask if in single-screen stacked mode
                            if is_single_stacked and ss_mask:
                                frame = self.apply_ss_mask(frame, screen_name, is_single_stacked, ss_mask, main_screen_geometry, external_screen_geometry)
                            
                            from PIL import ImageTk
                            # Convert PIL frame to Tkinter PhotoImage
                            tk_frame = ImageTk.PhotoImage(frame)
                            
                            # Store single reference to prevent garbage collection
                            player._tk_frame = tk_frame
                            
                            # Create canvas item if doesn't exist
                            if not hasattr(player, '_canvas_image_id') or not player._canvas_image_id:
                                player._canvas_image_id = canvas.create_image(
                                    player.geometry[0],
                                    player.geometry[1],
                                    anchor='nw',
                                    image=tk_frame
                                )
                            else:
                                # Update canvas item
                                canvas.itemconfig(player._canvas_image_id, image=tk_frame)
                                canvas.coords(
                                    player._canvas_image_id,
                                    player.geometry[0],
                                    player.geometry[1]
                                )
                            
                            # Update last count
                            player._last_frame_update_count = current_count
                        except Exception as e:
                            print(f"[PIL VIDEO] Error updating frame for {screen_name}: {e}")
    
    def apply_ss_mask(self, frame, screen_name: str, is_single_stacked: bool, ss_mask, main_screen_geometry: tuple = None, external_screen_geometry: tuple = None):
        """Apply ss_mask to a video frame for single-screen stacked mode.
        
        Args:
            frame: PIL Image frame
            screen_name: 'main' or 'external'
            is_single_stacked: Whether in single-screen stacked mode
            ss_mask: The ss_mask image from renderer
            main_screen_geometry: (x, y, w, h) geometry of main screen (in canvas coords)
            external_screen_geometry: (x, y, w, h) geometry of external screen (in canvas coords)
            
        Returns:
            Masked frame if needed, or original frame
        """
        from PIL import Image, ImageDraw, ImageChops
        
        # Only apply mask to main screen in single-screen stacked mode
        if screen_name != 'main' or not is_single_stacked or not ss_mask:
            return frame
        
        # Get frame dimensions
        video_w, video_h = frame.size
        
        # Resize ss_mask to frame size
        screen_mask = ss_mask.resize((video_w, video_h), Image.Resampling.LANCZOS)
        # Extract alpha channel as mask
        if screen_mask.mode == "RGBA":
            screen_mask = screen_mask.split()[3]
        elif screen_mask.mode != "L":
            screen_mask = screen_mask.convert("L")
        
        # Create bottom screen mask for clipping (overlap with external screen)
        if main_screen_geometry and external_screen_geometry:
            main_x, main_y, main_w, main_h = main_screen_geometry
            ext_x, ext_y, ext_w, ext_h = external_screen_geometry
            
            # Calculate overlap area - where external screen overlaps with main screen
            # In single-screen stacked mode, external is below main (ext_y > main_y)
            overlap_x1 = max(0, ext_x - main_x)
            overlap_y1 = max(0, ext_y - main_y)
            overlap_x2 = min(main_w, ext_x + ext_w - main_x)
            overlap_y2 = min(main_h, ext_y + ext_h - main_y)
            
            if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                # Create mask with overlap region filled
                bottom_mask = Image.new("L", (video_w, video_h), 0)
                draw = ImageDraw.Draw(bottom_mask)
                draw.rectangle([overlap_x1, overlap_y1, overlap_x2, overlap_y2], fill=255)
                # Combine masks - ss_mask provides shape, bottom_mask clips to external screen overlap
                combined_mask = ImageChops.multiply(screen_mask, bottom_mask)
            else:
                combined_mask = screen_mask
        else:
            combined_mask = screen_mask
        
        # Apply mask to frame alpha channel directly
        if frame.mode != "RGBA":
            frame = frame.convert("RGBA")
        
        # Apply the combined mask to the frame's alpha channel
        r, g, b, a = frame.split()
        # Multiply existing alpha with combined mask
        a = ImageChops.multiply(a, combined_mask)
        masked_frame = Image.merge('RGBA', (r, g, b, a))
        return masked_frame
                            
    def create_canvas_items(self, canvas):
        """Create canvas image items for PIL-based video players."""
        pass  # Now handled in update_canvas_frames
