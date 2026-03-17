from pathlib import Path
import json
import random
import math
import av
from typing import Tuple
from datetime import datetime
from PIL import Image, ImageSequence, ImageDraw, ImageOps, ImageChops
import time

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from screen import ScreenManager, MainScreen, ExternalScreen, Screen



BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
PLACEHOLDER_DIR = BASE_DIR / "Placeholder Assets"
GAMES_DIR = ASSETS_DIR / "games"

SOUND_FORMATS = (".ogg", ".mp3", ".wav")


class SoundManager:
    _initialized = False
    _mixer_initialized = False

    def __init__(self):
        self._sound_cache = {}
        self._theme_sounds_loaded = False
        self._current_theme_path = None

        self._master_volume = 1.0
        self._sfx_volume = 1.0
        self._music_volume = 1.0

        self._theme_sfx_volume = 1.0
        self._theme_music_volume = 1.0
        self._theme_sfx_volume_set = False
        self._theme_music_volume_set = False

        if not SoundManager._initialized and PYGAME_AVAILABLE:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                SoundManager._mixer_initialized = True
            except Exception as e:
                print(f"[SoundManager] Failed to initialize mixer: {e}")
                SoundManager._mixer_initialized = False
            SoundManager._initialized = True

    def load_theme_sounds(self, theme_path: Path):
        """Load sounds for the theme, with fallback to placeholder assets."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return

        self._sound_cache.clear()
        self._theme_sounds_loaded = True
        self._current_theme_path = theme_path

        sounds_dir = theme_path / "sounds"
        placeholder_sounds_dir = PLACEHOLDER_DIR / "sounds"

        # First, collect all unique sound names from both theme and fallback
        all_sound_names = set()

        # Get sounds from theme
        if sounds_dir.exists():
            for sound_file in sounds_dir.glob("*"):
                if sound_file.suffix.lower() in SOUND_FORMATS:
                    all_sound_names.add(sound_file.stem.lower())

        # Get sounds from fallback
        if placeholder_sounds_dir.exists():
            for sound_file in placeholder_sounds_dir.glob("*"):
                if sound_file.suffix.lower() in SOUND_FORMATS:
                    all_sound_names.add(sound_file.stem.lower())

        # Now load each sound: theme version first, then fallback if needed
        for sound_name in sorted(all_sound_names):
            self._load_sound_with_fallback(sound_name, sounds_dir, placeholder_sounds_dir)

    def _load_sound_with_fallback(self, sound_name: str, theme_sounds_dir: Path, fallback_dir: Path):
        """Load a sound - theme version takes priority over fallback."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return

        # Try theme sound first
        if theme_sounds_dir.exists():
            for ext in SOUND_FORMATS:
                theme_path = theme_sounds_dir / f"{sound_name}{ext}"
                if theme_path.exists():
                    try:
                        sound = pygame.mixer.Sound(str(theme_path))
                        self._sound_cache[sound_name] = sound
                        return
                    except Exception:
                        pass

        # Fall back to placeholder if theme sound wasn't found
        if fallback_dir.exists():
            for ext in SOUND_FORMATS:
                fallback_path = fallback_dir / f"{sound_name}{ext}"
                if fallback_path.exists():
                    try:
                        sound = pygame.mixer.Sound(str(fallback_path))
                        self._sound_cache[sound_name] = sound
                        return
                    except Exception:
                        pass

    def _load_sound_from_dir(self, sound_name: str, sounds_dir: Path):
        """Load a sound from a specific directory."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return

        for ext in SOUND_FORMATS:
            sound_path = sounds_dir / f"{sound_name}{ext}"
            if sound_path.exists():
                try:
                    sound = pygame.mixer.Sound(str(sound_path))
                    self._sound_cache[sound_name] = sound
                    return
                except Exception:
                    pass

    def play(self, sound_name: str):
        """Play a sound by name."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return

        sound = self._sound_cache.get(sound_name.lower())
        if sound:
            if self._theme_sfx_volume_set:
                effective_volume = self._master_volume * self._theme_sfx_volume
            else:
                effective_volume = self._master_volume * self._sfx_volume
            sound.set_volume(effective_volume)
            sound.play()

    def set_theme_sfx_volume(self, volume: float):
        """Set the theme-defined SFX volume (0.0 to 1.0)."""
        self._theme_sfx_volume = max(0.0, min(1.0, volume))
        self._theme_sfx_volume_set = True

    def set_theme_music_volume(self, volume: float):
        """Set the theme-defined music volume (0.0 to 1.0)."""
        self._theme_music_volume = max(0.0, min(1.0, volume))
        self._theme_music_volume_set = True
        if PYGAME_AVAILABLE and SoundManager._mixer_initialized:
            try:
                if self._theme_music_volume_set:
                    pygame.mixer.music.set_volume(self._master_volume * self._theme_music_volume)
                else:
                    pygame.mixer.music.set_volume(self._master_volume * self._music_volume)
            except:
                pass

    def set_master_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)."""
        self._master_volume = max(0.0, min(1.0, volume))

    def get_master_volume(self) -> float:
        return self._master_volume

    def set_sfx_volume(self, volume: float):
        """Set SFX volume (0.0 to 1.0)."""
        self._sfx_volume = max(0.0, min(1.0, volume))

    def get_sfx_volume(self) -> float:
        return self._sfx_volume

    def set_music_volume(self, volume: float):
        """Set music volume (0.0 to 1.0)."""
        self._music_volume = max(0.0, min(1.0, volume))
        if PYGAME_AVAILABLE and SoundManager._mixer_initialized:
            try:
                if self._theme_music_volume_set:
                    pygame.mixer.music.set_volume(self._master_volume * self._theme_music_volume)
                else:
                    pygame.mixer.music.set_volume(self._master_volume * self._music_volume)
            except:
                pass

    def get_music_volume(self) -> float:
        return self._music_volume

    def get_theme_music_volume(self) -> float:
        return self._theme_music_volume

    def play_music(self, filepath: str, loops: int = -1):
        """Play background music."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return

        try:
            pygame.mixer.music.load(filepath)
            if self._theme_music_volume_set:
                pygame.mixer.music.set_volume(self._master_volume * self._theme_music_volume)
            else:
                pygame.mixer.music.set_volume(self._master_volume * self._music_volume)
            pygame.mixer.music.play(loops=loops)
        except Exception as e:
            print(f"[SoundManager] Failed to play music: {e}")

    def stop_music(self):
        """Stop background music."""
        if PYGAME_AVAILABLE and SoundManager._mixer_initialized:
            try:
                pygame.mixer.music.stop()
            except:
                pass

    @property
    def is_available(self) -> bool:
        return PYGAME_AVAILABLE and SoundManager._mixer_initialized


class MusicManager:
    _initialized = False
    _check_timer_id = None

    def __init__(self, sound_manager: SoundManager):
        self._sound_manager = sound_manager
        self._theme_base_path = None
        self._placeholder_base_path = None
        self._theme_music_path = None
        self._placeholder_music_path = None
        
        self._mode = "DISABLED"  # TIME, PLAYLIST, DISABLED
        self._playback_mode = "IN ORDER"  # IN ORDER, SHUFFLE
        self._time_schedule = []  # List of (hour, minute, track_path)
        self._playlist = []  # List of track paths
        self._current_track_index = 0
        self._shuffled_playlist = []
        
        self._last_schedule_check_hour = -1
        self._theme_music_volume = 1.0
        self._theme_music_volume_set = False
        
        self._paused = False
        self._user_paused = False
        self._user_shuffle = False
        self._current_track_name = ""
        
        self._check_timer = None

    def load_from_theme(self, theme_path: Path, placeholder_path: Path):
        """Load music configuration from theme.json with fallback to placeholder."""
        self.stop()
        self._cancel_schedule_timer()
        
        self._theme_base_path = theme_path
        self._placeholder_base_path = placeholder_path
        self._theme_music_path = theme_path / "music"
        self._placeholder_music_path = placeholder_path / "music"
        
        # Load theme.json from both theme and placeholder
        theme_data = {}
        placeholder_data = {}
        
        theme_json = theme_path / "theme.json"
        if theme_json.exists():
            try:
                with open(theme_json, "r", encoding="utf-8") as f:
                    theme_data = json.load(f)
            except Exception:
                pass
        
        placeholder_json = placeholder_path / "theme.json"
        if placeholder_json.exists():
            try:
                with open(placeholder_json, "r", encoding="utf-8") as f:
                    placeholder_data = json.load(f)
            except Exception:
                pass
        
        # Determine mode: use theme if defined, else fallback to placeholder
        if "music_mode" in theme_data:
            self._mode = theme_data.get("music_mode", "DISABLED")
        elif "music_mode" in placeholder_data:
            self._mode = placeholder_data.get("music_mode", "DISABLED")
        else:
            self._mode = "DISABLED"
        
        # Determine playback mode
        if "music_playback_mode" in theme_data:
            self._playback_mode = theme_data.get("music_playback_mode", "IN ORDER")
        elif "music_playback_mode" in placeholder_data:
            self._playback_mode = placeholder_data.get("music_playback_mode", "IN ORDER")
        else:
            self._playback_mode = "IN ORDER"
        
        # Sync user shuffle with playback mode from theme
        self._user_shuffle = (self._playback_mode == "SHUFFLE")
        
        # Parse time schedule
        self._time_schedule = []
        time_schedule_str = theme_data.get("music_time_schedule", "") or placeholder_data.get("music_time_schedule", "")
        if time_schedule_str:
            self._parse_time_schedule(time_schedule_str)
        
        # Parse playlist
        self._playlist = []
        playlist_str = theme_data.get("music_playlist", "") or placeholder_data.get("music_playlist", "")
        if playlist_str:
            self._parse_playlist(playlist_str, theme_path, placeholder_path)
        
        # Determine volume: use theme if set, else fallback to placeholder, else use user default
        self._theme_music_volume_set = False
        if "music_volume" in theme_data:
            self._theme_music_volume = float(theme_data.get("music_volume", 1.0))
            self._theme_music_volume_set = True
        elif "music_volume" in placeholder_data:
            self._theme_music_volume = float(placeholder_data.get("music_volume", 1.0))
            self._theme_music_volume_set = True
        else:
            self._theme_music_volume = 1.0
        
        # Apply volume to sound manager
        self._sound_manager.set_theme_music_volume(self._theme_music_volume if self._theme_music_volume_set else 1.0)
        
        # Auto-start if not disabled
        if self._mode != "DISABLED":
            self.play()

    def _parse_time_schedule(self, schedule_str: str):
        """Parse time schedule string: hour:minute|path||hour:minute|path"""
        self._time_schedule = []
        entries = schedule_str.split("||")
        for entry in entries:
            if "|" in entry:
                time_part, path_part = entry.split("|", 1)
                if ":" in time_part:
                    hour_str, minute_str = time_part.split(":")
                    try:
                        hour = int(hour_str)
                        minute = int(minute_str)
                        # Resolve path relative to theme
                        track_path = self._resolve_track_path(path_part)
                        if track_path:
                            self._time_schedule.append((hour, minute, track_path))
                    except ValueError:
                        pass
        
        # Sort by time
        self._time_schedule.sort(key=lambda x: x[0] * 60 + x[1])

    def _parse_playlist(self, playlist_str: str, theme_path: Path, placeholder_path: Path):
        """Parse playlist string: path||path||path"""
        self._playlist = []
        tracks = playlist_str.split("||")
        for track in tracks:
            track = track.strip()
            if track:
                track_path = self._resolve_track_path(track, theme_path, placeholder_path)
                if track_path:
                    self._playlist.append(track_path)
        
        # Create shuffled playlist
        self._shuffled_playlist = self._playlist.copy()
        random.shuffle(self._shuffled_playlist)
        self._current_track_index = 0

    def _resolve_track_path(self, track: str, theme_path: Path = None, placeholder_path: Path = None) -> str:
        """Resolve track path, checking theme first then placeholder."""
        if theme_path is None:
            theme_path = self._theme_music_path.parent
        if placeholder_path is None:
            placeholder_path = self._placeholder_music_path.parent
        
        # Try theme path first
        theme_track = theme_path / track
        if theme_track.exists():
            return str(theme_track)
        
        # Try placeholder path
        placeholder_track = placeholder_path / track
        if placeholder_track.exists():
            return str(placeholder_track)
        
        # Track not found - return None
        return None

    def _get_effective_volume(self) -> float:
        """Calculate effective volume: master × user_music × theme_music (if set)"""
        master = self._sound_manager.get_master_volume()
        user_music = self._sound_manager.get_music_volume()
        if self._theme_music_volume_set:
            return master * user_music * self._theme_music_volume
        else:
            return master * user_music

    def play(self):
        """Start playing music based on mode."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return
        
        if self._mode == "DISABLED":
            return
        
        if self._paused:
            self._paused = False
            try:
                pygame.mixer.music.unpause()
                # If unpause doesn't work (music fully stopped), restart
                if pygame.mixer.music.get_pos() == -1:
                    if self._mode == "TIME":
                        track_path = self._get_schedule_track()
                    elif self._mode == "PLAYLIST":
                        track_path = self._get_playlist_track()
                    else:
                        track_path = None
                    if track_path:
                        self._play_track(track_path)
            except:
                pass
            return
        
        # Determine which track to play
        track_path = None
        
        if self._mode == "TIME":
            track_path = self._get_schedule_track()
        elif self._mode == "PLAYLIST":
            track_path = self._get_playlist_track()
        
        if track_path:
            self._play_track(track_path)
            self._start_schedule_timer()

    def _get_schedule_track(self) -> str:
        """Get track based on current time schedule."""
        if not self._time_schedule:
            return None
        
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        
        # Find the most recent schedule entry that has passed
        best_track = None
        for hour, minute, track in self._time_schedule:
            schedule_minutes = hour * 60 + minute
            if schedule_minutes <= current_minutes:
                best_track = track
            else:
                break
        
        # If no track found (all schedules are in future), wrap around to first
        if best_track is None and self._time_schedule:
            best_track = self._time_schedule[0][2]
        
        return best_track

    def _get_playlist_track(self) -> str:
        """Get next track from playlist."""
        if not self._playlist:
            return None
        
        if self._playback_mode == "SHUFFLE" or self._user_shuffle:
            if self._current_track_index >= len(self._shuffled_playlist):
                # Reset and reshuffle
                self._shuffled_playlist = self._playlist.copy()
                random.shuffle(self._shuffled_playlist)
                self._current_track_index = 0
            return self._shuffled_playlist[self._current_track_index]
        else:
            if self._current_track_index >= len(self._playlist):
                self._current_track_index = 0
            return self._playlist[self._current_track_index]

    def _play_track(self, track_path: str):
        """Play a specific track."""
        if not track_path:
            return
        
        # Calculate relative path for display
        path_obj = Path(track_path)
        
        # Try to make it relative to theme or placeholder base path
        rel_path = ""
        if self._theme_base_path:
            try:
                rel_path = str(path_obj.relative_to(self._theme_base_path))
            except ValueError:
                pass
        
        if not rel_path and self._placeholder_base_path:
            try:
                rel_path = str(path_obj.relative_to(self._placeholder_base_path))
            except ValueError:
                pass
        
        if not rel_path:
            rel_path = str(path_obj)
        
        self._current_track_name = rel_path
        
        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.set_volume(self._get_effective_volume())
            pygame.mixer.music.play()
        except Exception as e:
            print(f"[MusicManager] Failed to play {track_path}: {e}")

    def stop(self):
        """Stop music playback."""
        if PYGAME_AVAILABLE and SoundManager._mixer_initialized:
            try:
                pygame.mixer.music.stop()
            except:
                pass
        self._cancel_schedule_timer()

    def pause(self):
        """Pause music."""
        if PYGAME_AVAILABLE and SoundManager._mixer_initialized:
            try:
                pygame.mixer.music.pause()
            except:
                pass
        self._paused = True

    def toggle_pause(self):
        """Toggle between play and pause."""
        if self._paused:
            self.play()
        else:
            self.pause()

    def next_track(self):
        """Skip to next track in playlist."""
        if self._mode == "PLAYLIST":
            self._current_track_index += 1
            track_path = self._get_playlist_track()
            if track_path:
                was_paused = self._paused
                self._play_track(track_path)
                if was_paused:
                    self._paused = True
                    try:
                        pygame.mixer.music.pause()
                    except:
                        pass

    def previous_track(self):
        """Go to previous track in playlist."""
        if self._mode == "PLAYLIST":
            self._current_track_index = max(0, self._current_track_index - 1)
            track_path = self._get_playlist_track()
            if track_path:
                was_paused = self._paused
                self._play_track(track_path)
                if was_paused:
                    self._paused = True
                    try:
                        pygame.mixer.music.pause()
                    except:
                        pass

    def set_shuffle(self, shuffle: bool):
        """Toggle shuffle mode."""
        self._user_shuffle = shuffle
        if shuffle and self._playlist:
            # Reshuffle from current position
            remaining = self._playlist[self._current_track_index:]
            random.shuffle(remaining)
            self._shuffled_playlist = self._playlist[:self._current_track_index] + remaining

    def toggle_shuffle(self):
        """Toggle shuffle."""
        self.set_shuffle(not self._user_shuffle)

    def _start_schedule_timer(self):
        """Start timer to check schedule every 60 seconds."""
        self._cancel_schedule_timer()
        # Check immediately
        self._check_schedule()
        # Then check every 60 seconds
        if self._mode == "TIME":
            MusicManager._check_timer_id = "music_schedule_check"
    
    def update(self):
        """Check if music ended and auto-advance playlist."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return
        
        if self._mode == "DISABLED":
            return
        
        # Check if music has ended and auto-advance
        try:
            if not pygame.mixer.music.get_busy() and not self._paused:
                if self._mode == "PLAYLIST" and self._playlist:
                    self.next_track()
                elif self._mode == "TIME":
                    self._handle_time_mode_track_end()
        except:
            pass
    
    def _handle_time_mode_track_end(self):
        """Handle track end in TIME mode - loop or switch based on schedule."""
        if not self._time_schedule:
            return
        
        # Get the current scheduled track
        current_track = self._get_schedule_track()
        if not current_track:
            return
        
        # Check if the track has changed (time slot switched)
        if current_track != self._current_track_name:
            # Time slot changed - play new track
            self._play_track(current_track)
        else:
            # Same time slot - replay the track (loop)
            self._play_track(current_track)
    
    def _do_update(self):
        """Internal method that performs update and handles timer cleanup."""
        self._check_timer = None
        self.update()

    def _cancel_schedule_timer(self):
        """Cancel the schedule timer."""
        MusicManager._check_timer_id = None

    def _check_schedule(self):
        """Check if schedule needs to update."""
        if self._mode != "TIME":
            return
        
        now = datetime.now()
        
        # Check if hour changed
        if now.hour != self._last_schedule_check_hour:
            self._last_schedule_check_hour = now.hour
            track = self._get_schedule_track()
            if track:
                # Check if we need to switch tracks
                try:
                    current = pygame.mixer.music.get_busy()
                    if not current:
                        self._play_track(track)
                except:
                    pass

    def update_volume(self):
        """Update music volume (call when user or theme volume changes)."""
        if PYGAME_AVAILABLE and SoundManager._mixer_initialized:
            try:
                pygame.mixer.music.set_volume(self._get_effective_volume())
            except:
                pass

    @property
    def is_playing(self) -> bool:
        """Check if music is currently playing."""
        if not PYGAME_AVAILABLE or not SoundManager._mixer_initialized:
            return False
        try:
            return pygame.mixer.music.get_busy() and not self._paused
        except:
            return False

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_shuffle(self) -> bool:
        return self._user_shuffle

    @property
    def current_track_name(self) -> str:
        return self._current_track_name


class Renderer:
    # Device / Frame
    FRAME_WIDTH = 800
    FRAME_HEIGHT = 950
    DEVICE_PADDING = 20
    
    # Devices configuration
    DEVICES = {}

    # Grid
    GRID_OUTER_PADDING = 6
    GRID_PADDING = 0
    DEFAULT_GRID_ROWS = 3
    DEFAULT_GRID_COLS = 4

    # Selection highlight animation
    BASE_SEL_ANIM_DURATION = 0.1   # one-cell move recommended 0.10 - 0.14
    MAX_SEL_ANIM_DURATION = 0.35   # full-grid jump recommended 0.30 - 0.40

    # Smart folder / platform limits
    MAX_ROOT_SMART = 3
    MAX_PLATFORM_SMART = 2

    # Grid Object Scaling
    DEFAULT_FOLDER_SCALE = 0.8124
    SMART_FOLDER_SCALE = 0.8124
    ICON_OVERLAY_SCALE = 0.8124
    
    # Grid horizontal column shift (Cocoon behavior)
    ENABLE_COLUMN_SHIFT = False
    COLUMN_SHIFT_STRENGTH = 1.3   # 1.0 = full shift, 0.5 = subtle
    
    # Background scaling
    BG_SCALE = 0.25

    # Bezel options - populated dynamically from assets/bezels folder
    BEZEL_OPTIONS = {}
    
    # Track bezel file info: name -> (filename, screen_mode)
    BEZEL_INFO = {}
    BEZEL_SCREEN_MODE = {}  # name -> "dual" or "single"
    
    @classmethod
    def discover_bezels(cls):
        """Scan all folders in assets/bezels for available bezel images."""
        cls.BEZEL_OPTIONS.clear()
        cls.BEZEL_INFO.clear()
        cls.BEZEL_SCREEN_MODE.clear()
        cls.DEVICES.clear()
        
        bezel_dir = ASSETS_DIR / "bezels"
        
        if not bezel_dir.exists():
            return cls.BEZEL_OPTIONS
        
        # Scan all subdirectories in bezels folder
        for folder in sorted(bezel_dir.iterdir()):
            if not folder.is_dir():
                continue
            
            folder_name = folder.name
            
            # Load device.json from this folder if it exists
            device_file = folder / "device.json"
            device_config = None
            if device_file.exists():
                try:
                    with open(device_file, 'r') as f:
                        device_config = json.load(f)
                        cls.DEVICES[folder_name] = device_config
                except Exception as e:
                    print(f"Failed to load device.json for {folder_name}: {e}")
            
            # Get display name from device config or fall back to folder name
            if device_config and "display_name" in device_config:
                device_display_name = device_config["display_name"]
            else:
                device_display_name = folder_name.title()
            
            # Scan for PNG files in this folder (only images, not json)
            for f in sorted(folder.glob("*.png")):
                # Create display name: "Device Display Name - Image Name"
                image_name = f.stem.replace("_", " ").title()
                display_name = f"{device_display_name} - {image_name}"
                
                # Store bezel info
                relative_path = str(f.relative_to(ASSETS_DIR))
                cls.BEZEL_OPTIONS[display_name] = relative_path
                cls.BEZEL_INFO[display_name] = (relative_path, folder_name)
                
                # Determine screen mode from loaded device config
                if folder_name in cls.DEVICES:
                    screen_amount = cls.DEVICES[folder_name].get("screen_amount", 2)
                    mode = "single" if screen_amount == 1 else "dual"
                else:
                    mode = "dual"  # Default to dual screen
                
                cls.BEZEL_SCREEN_MODE[display_name] = mode
        
        return cls.BEZEL_OPTIONS
    
    def apply_device_settings(self, device_name: str):
        """Apply device settings from device.json in the bezel folder"""
        
        # Get frame dimensions from loaded bezel image FIRST (needed for centering)
        if self.bezel_img:
            Screen.FRAME_WIDTH = self.bezel_img.width
            Screen.FRAME_HEIGHT = self.bezel_img.height
            self.FRAME_WIDTH = Screen.FRAME_WIDTH
            self.FRAME_HEIGHT = Screen.FRAME_HEIGHT
        
        # Load device.json from the bezel folder (to pick up external edits)
        device_file = ASSETS_DIR / "bezels" / device_name / "device.json"
        
        device = None
        
        if device_file.exists():
            try:
                with open(device_file, 'r') as f:
                    device = json.load(f)
                    # Update in-memory DEVICES dict
                    self.DEVICES[device_name] = device
            except Exception as e:
                print(f"Failed to load device.json for {device_name}: {e}")
                device = None
        else:
            device = None
        
        if not device:
            print(f"No device config found for '{device_name}', using defaults")
            # Center screens on device canvas as fallback
            self._center_screens_on_device()
            return
        
        # Update screen mode based on screen_amount
        screen_amount = device.get("screen_amount", 2)
        self._device_screen_amount = screen_amount  # Store original device screen amount
        
        # Check if there's a saved display mode for this bezel, otherwise use device default
        saved_mode = self.BEZEL_SCREEN_MODE.get(self.current_bezel_name)
        if saved_mode:
            mode = saved_mode
        else:
            mode = "single" if screen_amount == 1 else "dual"
        self._display_mode = mode
        self.BEZEL_SCREEN_MODE[self.current_bezel_name] = mode
        
        # Update screen positions - convert pixels to percentages if needed
        if "screens" in device:
            screens = device["screens"]
            if "main" in screens:
                main = screens["main"]
                # Check if values are pixels (>1.0) or percentages (<=1.0)
                if main.get("w", 0) > 1.0 or main.get("h", 0) > 1.0:
                    # Pixel values - convert to percentages
                    pct = Screen.pixels_to_percentages((main["x"], main["y"], main["w"], main["h"]))
                    main["x_pct"] = round(pct[0], 4)
                    main["y_pct"] = round(pct[1], 4)
                    main["w_pct"] = round(pct[2], 4)
                    main["h_pct"] = round(pct[3], 4)
                else:
                    # Already percentages or has _pct versions
                    pass
            
            if "external" in screens:
                ext = screens["external"]
                if ext.get("w", 0) > 1.0 or ext.get("h", 0) > 1.0:
                    pct = Screen.pixels_to_percentages((ext["x"], ext["y"], ext["w"], ext["h"]))
                    ext["x_pct"] = round(pct[0], 4)
                    ext["y_pct"] = round(pct[1], 4)
                    ext["w_pct"] = round(pct[2], 4)
                    ext["h_pct"] = round(pct[3], 4)
        
        # Apply screen positions using percentages
        if "screens" in device:
            screens = device["screens"]
            if "main" in screens:
                main = screens["main"]
                # Use percentage values if available, otherwise use pixel values
                if "x_pct" in main:
                    px = main.get("x_pct", Screen.TOP_SCREEN_PCT[0])
                    py = main.get("y_pct", Screen.TOP_SCREEN_PCT[1])
                    pw = main.get("w_pct", Screen.TOP_SCREEN_PCT[2])
                    ph = main.get("h_pct", Screen.TOP_SCREEN_PCT[3])
                    Screen.TOP_SCREEN = Screen.percentages_to_pixels((px, py, pw, ph))
                else:
                    Screen.TOP_SCREEN = (main["x"], main["y"], main["w"], main["h"])
            
            if "external" in screens:
                ext = screens["external"]
                if "x_pct" in ext:
                    px = ext.get("x_pct", Screen.BOTTOM_SCREEN_PCT[0])
                    py = ext.get("y_pct", Screen.BOTTOM_SCREEN_PCT[1])
                    pw = ext.get("w_pct", Screen.BOTTOM_SCREEN_PCT[2])
                    ph = ext.get("h_pct", Screen.BOTTOM_SCREEN_PCT[3])
                    Screen.BOTTOM_SCREEN = Screen.percentages_to_pixels((px, py, pw, ph))
                    Screen.SINGLE_SCREEN = Screen.percentages_to_pixels((px, py, pw, ph))
                else:
                    Screen.BOTTOM_SCREEN = (ext["x"], ext["y"], ext["w"], ext["h"])
                    Screen.SINGLE_SCREEN = (ext["x"], ext["y"], ext["w"], ext["h"])
            
            # If device originally had 1 screen, stack main screen on external
            if self._device_screen_amount == 1:
                # Set screen_manager mode to single first (required for stacking to work)
                self.screen_manager._screen_mode = "single"
                self.screen_manager.external.rect = Screen.SINGLE_SCREEN
                self.screen_manager._update_single_screen_main_position()
                Screen.TOP_SCREEN = self.screen_manager.main.rect
        
        # Update app grid settings - convert pixels to percentages if needed
        if "app_grid" in device:
            grid = device["app_grid"]
            frame_w = Screen.FRAME_WIDTH
            frame_h = Screen.FRAME_HEIGHT
            
            # Convert pixel values to percentages if needed
            if grid.get("width", 0) > 1.0 or grid.get("height", 0) > 1.0:
                grid["x_offset_pct"] = round(grid.get("x_offset", 0) / frame_w, 4) if frame_w else 0
                grid["y_offset_pct"] = round(grid.get("y_offset", -40) / frame_h, 4) if frame_h else 0
                grid["width_pct"] = round(grid.get("width", 400) / frame_w, 4) if frame_w else 0
                grid["height_pct"] = round(grid.get("height", 50) / frame_h, 4) if frame_h else 0
            
            # Apply settings - use percentages if available
            if "width_pct" in grid:
                self.app_grid_x_offset = round(grid.get("x_offset_pct", 0) * frame_w)
                self.app_grid_y_offset = round(grid.get("y_offset_pct", -0.04) * frame_h)
                self.app_grid_width = round(grid.get("width_pct", 0.455) * frame_w)
                self.app_grid_icon_size = round(grid.get("height_pct", 0.048) * frame_h)
            else:
                self.app_grid_x_offset = grid.get("x_offset", 0)
                self.app_grid_y_offset = grid.get("y_offset", -40)
                self.app_grid_width = grid.get("width", 400)
                self.app_grid_icon_size = grid.get("height", 50)
            
            self.app_grid_icon_scale = grid.get("icon_scale", 1.0)
        
        # Update screen manager with new dimensions
        self.screen_manager._frame_width = Screen.FRAME_WIDTH
        self.screen_manager._frame_height = Screen.FRAME_HEIGHT
    
    def _center_screens_on_device(self):
        """Center screens on device canvas when no device config exists"""
        # For dual screen devices, center both screens
        # For single screen devices, center the external screen
        frame_w = self.FRAME_WIDTH
        frame_h = self.FRAME_HEIGHT
        
        # Default to centered single screen
        screen_w = frame_w // 2
        screen_h = frame_h // 2
        Screen.SINGLE_SCREEN = (
            (frame_w - screen_w) // 2,
            (frame_h - screen_h) // 2,
            screen_w,
            screen_h
        )
        Screen.BOTTOM_SCREEN = Screen.SINGLE_SCREEN
        
        # Check if in bezel edit mode with 1 screen selected, or if device originally had 1 screen
        use_single_mode = (
            (self.bezel_edit_mode and self._temp_screen_amount == 1) or 
            self._device_screen_amount == 1
        )
        
        if use_single_mode:
            # Single screen mode - stack main screen on top of external
            self.screen_manager._screen_mode = "single"
            Screen.TOP_SCREEN = Screen.SINGLE_SCREEN
            self.screen_manager.external.rect = Screen.SINGLE_SCREEN
            self.screen_manager._update_single_screen_main_position()
            Screen.TOP_SCREEN = self.screen_manager.main.rect
        else:
            # Default to centered main screen (upper half)
            Screen.TOP_SCREEN = (
                (frame_w - screen_w) // 2,
                (frame_h - screen_h * 2 - 50) // 2,
                screen_w,
                screen_h
            )
    
    def save_device_app_grid_settings(self):
        """Save current app_grid settings to devices.json for the current device"""
        # Get current device name from bezel path
        filename = self.BEZEL_INFO.get(self.current_bezel_name, "")[0]
        if not filename:
            return
        
        # Extract folder name (e.g., "bezels/ayn thor/..." -> "ayn thor")
        parts = filename.split("/")
        if len(parts) < 2:
            return
        device_name = parts[1]
        
        # Load current devices.json
        devices_file = BASE_DIR / "devices.json"
        if not devices_file.exists():
            return
        
        try:
            with open(devices_file, 'r') as f:
                devices = json.load(f)
            
            # Update the app_grid settings for this device
            if device_name in devices:
                if "app_grid" not in devices[device_name]:
                    devices[device_name]["app_grid"] = {}
                
                devices[device_name]["app_grid"]["x_offset"] = self.app_grid_x_offset
                devices[device_name]["app_grid"]["y_offset"] = self.app_grid_y_offset
                devices[device_name]["app_grid"]["width"] = self.app_grid_width
                devices[device_name]["app_grid"]["icon_size"] = self.app_grid_icon_size
                
                # Write back to file
                with open(devices_file, 'w') as f:
                    json.dump(devices, f, indent=2)
        except Exception as e:
            print(f"Failed to save device settings: {e}")
    
    def enter_bezel_edit_mode(self):
        """Enter bezel editing mode, saving current state for potential revert"""
        self.bezel_edit_mode = True
        
        # Reload device.json to ensure we have the latest values
        if self.current_bezel_name:
            # Get folder name from BEZEL_INFO using display name
            bezel_info = self.BEZEL_INFO.get(self.current_bezel_name, ("", ""))
            folder_name = bezel_info[1] if len(bezel_info) > 1 else ""
            if folder_name:
                self.apply_device_settings(folder_name)
            else:
                # Fallback: try to extract folder name from bezel path
                filename = self.BEZEL_INFO.get(self.current_bezel_name, ("", ""))[0]
                if filename:
                    parts = filename.split("/")
                    if len(parts) >= 2:
                        folder_name = parts[1]
                        self.apply_device_settings(folder_name)
        
        # Save current state for revert
        self._saved_screen_amount = self._get_current_screen_amount()
        self._saved_screens = self._get_current_screens()
        self._saved_app_grid = {
            "x_offset": self.app_grid_x_offset,
            "y_offset": self.app_grid_y_offset,
            "width": self.app_grid_width,
            "icon_size": self.app_grid_icon_size,
            "icon_scale": self.app_grid_icon_scale
        }
        
        # Initialize temp state with current values (deep copy to prevent aliasing)
        self._temp_screen_amount = self._saved_screen_amount
        self._temp_screens = {
            "main": dict(self._saved_screens.get("main", {})),
            "external": dict(self._saved_screens.get("external", {}))
        }
        self._temp_app_grid = dict(self._saved_app_grid)
        
        # Store original frame_hidden state and make bezel semi-transparent
        self._original_frame_hidden = self.frame_hidden
        self._bezel_transparent_mode = True
        self._invalidate_static_cache()
    
    def exit_bezel_edit_mode(self):
        """Exit bezel editing mode without applying changes"""
        self.bezel_edit_mode = False
        self._temp_screen_amount = None
        self._temp_screens = {}
        self._temp_app_grid = {}
        
        # Restore original frame visibility
        if hasattr(self, '_original_frame_hidden'):
            self.frame_hidden = self._original_frame_hidden
        self._bezel_transparent_mode = False
        self._invalidate_static_cache()
    
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes in bezel edit mode"""
        if not self.bezel_edit_mode:
            return False
        
        # Check screen amount
        if self._temp_screen_amount != self._saved_screen_amount:
            return True
        
        # Check screen positions
        for screen_name in ["main", "external"]:
            temp_screen = self._temp_screens.get(screen_name, {})
            saved_screen = self._saved_screens.get(screen_name, {})
            for key in ["x", "y", "w", "h"]:
                if temp_screen.get(key) != saved_screen.get(key):
                    return True
        
        # Check app grid settings
        temp_grid = self._temp_app_grid or {}
        saved_grid = self._saved_app_grid or {}
        for key in ["x_offset", "y_offset", "width", "icon_size"]:
            if temp_grid.get(key) != saved_grid.get(key):
                return True
        
        return False
    
    def apply_bezel_changes(self):
        """Apply temporary changes to actual settings and save to JSON"""
        if not self.bezel_edit_mode:
            return
        
        # Apply screen amount
        if self._temp_screen_amount is not None:
            self._apply_screen_amount(self._temp_screen_amount)
        
        # Apply screen positions
        self._apply_screen_positions(self._temp_screens)
        
        # Apply app grid settings
        if self._temp_app_grid:
            # Handle both percentage and pixel keys
            frame_w = Screen.FRAME_WIDTH
            frame_h = Screen.FRAME_HEIGHT
            
            # Check for percentage keys first
            if "x_offset_pct" in self._temp_app_grid:
                self.app_grid_x_offset = self._temp_app_grid.get("x_offset_pct", 0)
                if isinstance(self.app_grid_x_offset, float):
                    self.app_grid_x_offset = round(self.app_grid_x_offset * frame_w) if frame_w else 0
                self.app_grid_y_offset = self._temp_app_grid.get("y_offset_pct", -0.04)
                if isinstance(self.app_grid_y_offset, float):
                    self.app_grid_y_offset = round(self.app_grid_y_offset * frame_h) if frame_h else 0
                self.app_grid_width = self._temp_app_grid.get("width_pct", 0.455)
                if isinstance(self.app_grid_width, float):
                    self.app_grid_width = round(self.app_grid_width * frame_w) if frame_w else 0
                self.app_grid_icon_size = self._temp_app_grid.get("height_pct", 0.048)
                if isinstance(self.app_grid_icon_size, float):
                    self.app_grid_icon_size = round(self.app_grid_icon_size * frame_h) if frame_h else 0
            else:
                # Fall back to pixel keys
                self.app_grid_x_offset = self._temp_app_grid.get("x_offset", 0)
                self.app_grid_y_offset = self._temp_app_grid.get("y_offset", -40)
                self.app_grid_width = self._temp_app_grid.get("width", 400)
                self.app_grid_icon_size = self._temp_app_grid.get("icon_size", 50)
            
            self.app_grid_icon_scale = self._temp_app_grid.get("icon_scale", 1.0)
        
        # Save to JSON
        self._save_all_device_settings()
        
        # Exit edit mode
        self.exit_bezel_edit_mode()
    
    def revert_bezel_changes(self):
        """Revert to saved/JSON state"""
        if not self.bezel_edit_mode:
            return
        
        # Revert to saved state (from JSON or when entering edit mode)
        if self._saved_screen_amount is not None:
            self._apply_screen_amount(self._saved_screen_amount)
        
        self._apply_screen_positions(self._saved_screens)
        
        if self._saved_app_grid:
            frame_w = Screen.FRAME_WIDTH
            frame_h = Screen.FRAME_HEIGHT
            
            # Check for pixel keys first (what we save), then percentage keys (fallback)
            if "x_offset" in self._saved_app_grid:
                # Pixel values
                self.app_grid_x_offset = self._saved_app_grid.get("x_offset", 0)
                self.app_grid_y_offset = self._saved_app_grid.get("y_offset", -0.04 * frame_h if frame_h else 0)
                self.app_grid_width = self._saved_app_grid.get("width", 0.455 * frame_w if frame_w else 0)
                self.app_grid_icon_size = self._saved_app_grid.get("icon_size", 0.048 * frame_h if frame_h else 0)
            else:
                # Percentage values
                self.app_grid_x_offset = self._saved_app_grid.get("x_offset_pct", 0)
                if isinstance(self.app_grid_x_offset, float):
                    self.app_grid_x_offset = round(self.app_grid_x_offset * frame_w) if frame_w else 0
                self.app_grid_y_offset = self._saved_app_grid.get("y_offset_pct", -0.04)
                if isinstance(self.app_grid_y_offset, float):
                    self.app_grid_y_offset = round(self.app_grid_y_offset * frame_h) if frame_h else 0
                self.app_grid_width = self._saved_app_grid.get("width_pct", 0.455)
                if isinstance(self.app_grid_width, float):
                    self.app_grid_width = round(self.app_grid_width * frame_w) if frame_w else 0
                self.app_grid_icon_size = self._saved_app_grid.get("height_pct", 0.048)
                if isinstance(self.app_grid_icon_size, float):
                    self.app_grid_icon_size = round(self.app_grid_icon_size * frame_h) if frame_h else 0
            
            self.app_grid_icon_scale = self._saved_app_grid.get("icon_scale", 1.0)
        
        # Exit edit mode
        self.exit_bezel_edit_mode()
    
    def _get_current_screen_amount(self) -> int:
        """Get current screen amount (1 or 2)"""
        # Use _display_mode for current user selection
        mode = getattr(self, '_display_mode', self.BEZEL_SCREEN_MODE.get(self.current_bezel_name, "dual"))
        return 1 if mode == "single" else 2
    
    def _get_current_screens(self) -> dict:
        """Get current screen positions as percentages"""
        # Use _display_mode for current user selection
        mode = getattr(self, '_display_mode', self.BEZEL_SCREEN_MODE.get(self.current_bezel_name, "dual"))
        
        # Convert pixel positions to percentages
        main_pct = Screen.pixels_to_percentages(Screen.TOP_SCREEN)
        
        if mode == "single":
            ext_pct = Screen.pixels_to_percentages(Screen.SINGLE_SCREEN)
            return {
                "main": {
                    "x_pct": round(main_pct[0], 4),
                    "y_pct": round(main_pct[1], 4),
                    "w_pct": round(main_pct[2], 4),
                    "h_pct": round(main_pct[3], 4)
                },
                "external": {
                    "x_pct": round(ext_pct[0], 4),
                    "y_pct": round(ext_pct[1], 4),
                    "w_pct": round(ext_pct[2], 4),
                    "h_pct": round(ext_pct[3], 4)
                }
            }
        else:
            ext_pct = Screen.pixels_to_percentages(Screen.BOTTOM_SCREEN)
            return {
                "main": {
                    "x_pct": round(main_pct[0], 4),
                    "y_pct": round(main_pct[1], 4),
                    "w_pct": round(main_pct[2], 4),
                    "h_pct": round(main_pct[3], 4)
                },
                "external": {
                    "x_pct": round(ext_pct[0], 4),
                    "y_pct": round(ext_pct[1], 4),
                    "w_pct": round(ext_pct[2], 4),
                    "h_pct": round(ext_pct[3], 4)
                }
            }
    
    def _apply_screen_amount(self, amount: int):
        """Apply screen amount change"""
        
        if amount == 1:
            self._display_mode = "single"
            self.BEZEL_SCREEN_MODE[self.current_bezel_name] = "single"
            self.screen_manager.set_single_screen_mode()
        else:
            self._display_mode = "dual"
            self.BEZEL_SCREEN_MODE[self.current_bezel_name] = "dual"
            
            # If device originally had 1 screen, keep main screen stacked on external (hidden)
            if self._device_screen_amount == 1:
                # Ensure external.rect is set first before stacking
                self.screen_manager.external.rect = Screen.SINGLE_SCREEN
                self.screen_manager._screen_mode = "single"
                self.screen_manager._update_single_screen_main_position()
                Screen.TOP_SCREEN = self.screen_manager.main.rect
            else:
                self.screen_manager.set_dual_screen_mode()
    
    def _apply_screen_positions(self, screens: dict):
        """Apply saved screen positions from device.json"""
        if not screens:
            return
            
        # Check if device has main screen defined - if not, don't try to position it
        has_main = "main" in screens
        
        # Set bottom screen (always defined)
        if "external" in screens:
            ext = screens["external"]
            # Handle both percentage and pixel keys
            if "x_pct" in ext:
                pct = (ext.get("x_pct", 0), ext.get("y_pct", 0), ext.get("w_pct", 1), ext.get("h_pct", 1))
                pixel_pos = Screen.percentages_to_pixels(pct)
                Screen.BOTTOM_SCREEN = pixel_pos
                Screen.SINGLE_SCREEN = pixel_pos
            else:
                Screen.BOTTOM_SCREEN = (ext["x"], ext["y"], ext["w"], ext["h"])
                Screen.SINGLE_SCREEN = (ext["x"], ext["y"], ext["w"], ext["h"])
            self.screen_manager.external.rect = Screen.BOTTOM_SCREEN
            
            # If device originally had 1 screen, stack main screen on external
            if self._device_screen_amount == 1:
                # Set screen_manager mode to single first (required for stacking to work)
                self.screen_manager._screen_mode = "single"
                self.screen_manager.external.rect = Screen.SINGLE_SCREEN
                self.screen_manager._update_single_screen_main_position()
                Screen.TOP_SCREEN = self.screen_manager.main.rect
    
    def _save_all_device_settings(self):
        """Save all device settings (screens + app_grid) to device.json in the bezel folder"""
        filename = self.BEZEL_INFO.get(self.current_bezel_name, "")
        if not filename:
            print(f"Warning: No BEZEL_INFO for '{self.current_bezel_name}'")
            return
        
        # filename is a tuple of (relative_path, folder_name)
        # Use folder_name directly as the device name
        device_name = filename[1] if len(filename) > 1 else None
        if not device_name:
            print(f"Warning: No device name found in BEZEL_INFO for '{self.current_bezel_name}'")
            return
        
        # Save to device.json in the bezel folder
        device_file = ASSETS_DIR / "bezels" / device_name / "device.json"
        
        try:
            # Load existing device.json or create new one
            if device_file.exists():
                with open(device_file, 'r') as f:
                    existing_config = json.load(f)
            else:
                existing_config = {}
            
            # Build new config with display_name at the top (save as pixels for user readability)
            # Internally the software converts to percentages for relative positioning
            frame_w = Screen.FRAME_WIDTH
            frame_h = Screen.FRAME_HEIGHT
            
            # Get current screen positions as pixels
            screens = self._get_current_screens()
            # Convert percentage values back to pixels for saving
            main_pct = (screens.get("main", {}).get("x_pct", 0), screens.get("main", {}).get("y_pct", 0), 
                       screens.get("main", {}).get("w_pct", 1), screens.get("main", {}).get("h_pct", 1))
            main_pixel = Screen.percentages_to_pixels(main_pct)
            ext_pct = (screens.get("external", {}).get("x_pct", 0), screens.get("external", {}).get("y_pct", 0),
                       screens.get("external", {}).get("w_pct", 1), screens.get("external", {}).get("h_pct", 1))
            ext_pixel = Screen.percentages_to_pixels(ext_pct)
            
            display_name = existing_config.get("display_name", device_name.title())
            
            device_config = {
                "display_name": display_name,
                "screen_amount": self._get_current_screen_amount(),
                "screens": {
                    "main": {
                        "x": main_pixel[0], "y": main_pixel[1], "w": main_pixel[2], "h": main_pixel[3]
                    },
                    "external": {
                        "x": ext_pixel[0], "y": ext_pixel[1], "w": ext_pixel[2], "h": ext_pixel[3]
                    }
                },
                "app_grid": {
                    "x_offset": self.app_grid_x_offset,
                    "y_offset": self.app_grid_y_offset,
                    "width": self.app_grid_width,
                    "height": self.app_grid_icon_size,
                    "icon_scale": self.app_grid_icon_scale
                }
            }
            
            with open(device_file, 'w') as f:
                json.dump(device_config, f, indent=2)
            
            # Also update the in-memory DEVICES dict
            self.DEVICES[device_name] = device_config
            
        except Exception as e:
            print(f"Failed to save device settings: {e}")
    
    def set_temp_screen_amount(self, amount: int):
        """Set temporary screen amount during editing"""
        self._temp_screen_amount = amount
        self._apply_screen_amount(amount)
        self._invalidate_static_cache()
    
    def set_temp_screen_pos(self, screen_name: str, x: int, y: int, w: int, h: int):
        """Set temporary screen position during editing"""
        self._temp_screens[screen_name] = {"x": x, "y": y, "w": w, "h": h}
        self._apply_screen_positions(self._temp_screens)
        self._invalidate_static_cache()
    
    def set_temp_app_grid(self, key: str, value):
        """Set temporary app grid setting during editing"""
        self._temp_app_grid[key] = value
        if key == "x_offset":
            self.app_grid_x_offset = value
        elif key == "y_offset":
            self.app_grid_y_offset = value
        elif key == "width":
            self.app_grid_width = value
        elif key == "icon_size":
            self.app_grid_icon_size = value
        elif key == "icon_scale":
            self.app_grid_icon_scale = value
        self._invalidate_static_cache()

    def __init__(self, max_grid_slots: int, max_rows_dual: int, max_rows_single_dual: int, max_rows_single_stacked: int, total_cols: int):
        
        # Default folder color (matches available variants in assets/default folder)
        self.default_folder_color = "blue"  # or "red", "green", etc.
        
        # Top screen icon scale (0.0 to 1.0, default 0.6 = 60%)
        self.top_screen_icon_scale = 0.6
        
        # Bezel edit mode
        self.bezel_edit_mode = False  # Off by default
        self._temp_screen_amount = None  # Temporary screen amount during editing
        self._temp_screens = {}  # Temporary screen positions during editing
        self._temp_app_grid = {}  # Temporary app grid settings during editing
        self._saved_screen_amount = None  # Saved state for revert
        self._saved_screens = {}
        self._saved_app_grid = {}
        self._device_screen_amount = 2  # Original device screen amount (from device.json)
        self._display_mode = "dual"  # User's display mode selection: "single" or "dual" (separate from device)
        self._stacked_lookup = {}  # Lookup table for single stacked mode: {rows: {"offset_pct": x, "scale_factor": y}}
        self._screen_handles = {'main': [], 'external': []}  # Handle positions for drag
        self._grid_handles = []  # Handle positions for grid in bezel edit mode
        self._manual_grid_override = False  # Use manually adjusted grid size from handles
        
        # App grid settings (region for 5 evenly spaced app icons)
        self.app_grid_x_offset = 0  # Horizontal offset from center
        self.app_grid_y_offset = 0  # Vertical offset from bottom
        self.app_grid_width = 400  # Total width of the app grid region
        self.app_grid_icon_size = 50  # Size of each circular icon
        self.app_grid_icon_scale = 1.0  # Scale factor for icons (1.0 = 100%)
        self._app_images = []  # List of randomly selected app images
        self._app_images_loaded = False
        self._app_grid_debug = None  # Debug info for app grid positioning
        
        # Mouse position for magnify window
        self.mouse_x = 0
        self.mouse_y = 0
        self.magnify_size = 200  # Size of magnify window
        self.magnify_zoom = 2.667  # Zoom level (2.0 * 200/150)
        self.magnify_window = True  # Toggle for magnify window
        
        self._last_canvas_size = None
        
        self._sel_anim_start = None
        self._sel_anim_from = None
        self._sel_anim_to = None
        self._sel_anim_duration = 0.35  # seconds (tweakable)
        
        # Zoom animation state
        self._zoom_anim_start = None
        self._zoom_anim_from = None  # (rows, cols)
        self._zoom_anim_to = None    # (rows, cols)
        self._zoom_anim_duration = 0.25  # seconds (faster for responsiveness)
        self._current_grid_rows = 3  # default
        self._current_grid_cols = 4  # default
        self._zoom_from_cell_w = 0  # Cached cell width at zoom start
        self._zoom_from_cell_h = 0  # Cached cell height at zoom start
        self._zoom_to_cell_w = 0    # Target cell width
        self._zoom_to_cell_h = 0    # Target cell height
        self._zoom_item_positions = {}  # Cached positions at zoom start for visible items
        self._zoom_ended_needs_snap = False  # Flag to continue lerp after zoom ends
        
        # Timestamps for real-time animation
        self._last_wallpaper_top_update = time.perf_counter()
        self._last_wallpaper_bottom_update = time.perf_counter()
        self._last_hero_update = {} # keyed by selected_index
        self._last_logo_update = {}
        self._last_game_update = {}
    
        # Caches
        self._resize_cache = {}
        self._static_cache_image = None
        self._static_cache_size = None
        self._static_cache_dirty = True
        self._cached_clean_content = None  # Cached clean content without borders/handles
        self._cached_clean_content_size = None
    
        # Game image cache (must exist before _load_frame is called)
        self._game_image_cache = {}      # path → loaded PIL image
        
        self.video_frame_cache = {}
        
        self.animations = {}
        
        # Discover available bezels (also loads device.json from each bezel folder)
        Renderer.discover_bezels()

        # Device images
        self.current_bezel_name = "Rainbow"  # default frame
        self.bezel_img = self._load_frame(self.current_bezel_name)
        self.frame_hidden = False  # Debug flag to hide frame image
        self.draw_debug_borders = False  # Debug flag to draw screen borders
        self.debug_drag_mode = False  # Debug flag for drag mode
        self._invalidate_static_cache()
        
        # Set frame scale
        frame_w, frame_h = self.bezel_img.size
        self._frame_scale = min(frame_w / self.FRAME_WIDTH, frame_h / self.FRAME_HEIGHT)
        
        # Screen manager
        self.screen_manager = ScreenManager()
        self._detect_screen_positions()
        
        # Load UI elements
        self.ui_d_bottom_dock = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_d_bottom_dock.png")
        self.ui_d_bottom_left_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_d_bottom_left_cornerhints.png")
        self.ui_d_bottom_right_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_d_bottom_right_cornerhints.png")
        self.ui_d_top_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_d_top_cornerhints.png")
        self.ui_d_top_time = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_d_top_time.png")
        self.ui_d_top_user = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_d_top_user.png")
        self.ui_s_ds_left_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_s_ds_left_cornerhints.png")
        self.ui_s_ds_right_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_s_dss_right_cornerhints.png")
        self.ui_s_dock = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_s_dock.png")
        self.ui_s_ss_left_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_s_ss_left_cornerhints.png")
        self.ui_s_ss_right_cornerhints = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_s_dss_right_cornerhints.png")
        self.ui_s_ss_time = self._load_cached_rgba(ASSETS_DIR / "ui_placeholder/ui_s_ss_time.png")
        
        # UI element anchors (screen_type, horizontal_anchor, vertical_anchor)
        # screen_type: "main" = top/primary screen, "ext" = bottom/external screen
        self.ui_d_bottom_dock_anchor = ("ext", "center", "bottom")
        self.ui_d_bottom_left_cornerhints_anchor = ("ext", "left", "bottom")
        self.ui_d_bottom_right_cornerhints_anchor = ("ext", "right", "bottom")
        self.ui_d_top_cornerhints_anchor = ("main", "left", "bottom")
        self.ui_d_top_time_anchor = ("main", "right", "top")
        self.ui_d_top_user_anchor = ("main", "left", "top")
        self.ui_s_ds_left_cornerhints_anchor = ("ext", "left", "bottom")
        self.ui_s_ds_right_cornerhints_anchor = ("ext", "right", "bottom")
        self.ui_s_dock_anchor = ("ext", "center", "bottom")
        self.ui_s_ss_left_cornerhints_anchor = ("ext", "left", "bottom")
        self.ui_s_ss_right_cornerhints_anchor = ("ext", "right", "bottom")
        self.ui_s_ss_time_anchor = ("ext", "right", "top")
        
        # Visibility toggles
        self.corner_hints_visible = True
        self.dock_visible = True
        self.app_grid_visible = True
        self.populated_apps_visible = True
        
        # Background
        self.bg_img = self._load_cached_rgba(ASSETS_DIR / "bg.png", PLACEHOLDER_DIR / "bg.png")
        if self.bg_img and self.BG_SCALE != 1.0:
            w, h = self.bg_img.size
            self.bg_img = self.bg_img.resize((int(w * self.BG_SCALE), int(h * self.BG_SCALE)), Image.Resampling.LANCZOS)

        # Selection highlight
        self.selected_img = self._load_cached_rgba(ASSETS_DIR / "selected.png", PLACEHOLDER_DIR / "selected.png")

        # Single screen stacked mode mask
        self.ss_mask = self._load_cached_rgba(ASSETS_DIR / "ss_mask.png")

        # Theme state
        self.theme_path = None
        self.theme_data = {}
        self.preview_image = None

        # Clear top wallpaper
        self.wallpaper_top = None
        self.wallpaper_top_frames = []
        self.wallpaper_top_index = 0
        self.wallpaper_top_duration = 100

        # Clear bottom wallpaper
        self.wallpaper_bottom = None
        self.wallpaper_bottom_frames = []
        self.wallpaper_bottom_index = 0
        self.wallpaper_bottom_duration = 100

        # Clear any cached references to old images
        if hasattr(self, "_resize_cache"):
            self._resize_cache.clear()
        if hasattr(self, "_game_image_cache"):
            self._game_image_cache.clear()

        # Grid data
        self.smart_folders = {}
        self.icon_overlays = {}
        self.selected_index = 0  # Target selection index
        self.grid_items = []      # List of dicts for each cell
        self.grid_positions = []  # List of (x, y, w, h) for each cell
        self._grid_items_dirty = True  # Flag to rebuild grid items
        
        # Extended grid - virtual columns beyond visible area
        self.TOTAL_COLS = total_cols  # Total columns available (can extend beyond visible GRID_COLS)
        self.grid_scroll_x = 0  # Horizontal scroll offset (current animated value)
        self._grid_scroll_target = 0  # Target scroll position
        self._grid_scroll_from = 0  # Starting scroll position for animation
        self._grid_scroll_start = None  # Animation start time
        self._grid_scroll_duration = 0.2  # Scroll animation duration (seconds)
        
        # Maximum grid sizes (passed from app.py based on zoom_levels)
        self.MAX_GRID_ROWS_DUAL = max_rows_dual
        self.MAX_GRID_ROWS_SINGLE_DUAL = max_rows_single_dual
        self.MAX_GRID_ROWS_SINGLE_STACKED = max_rows_single_stacked
        self.MAX_TOTAL_SLOTS = max_grid_slots
        
        # Single screen stacked mode state
        self._single_screen_stacked = False
        self.MAX_TOTAL_SLOTS = max_grid_slots
        
        self._full_cell_width = 0  # Full cell width before shrinking to square
        self._last_grid_w = 400  # Last known grid width (for zoom calculations)
        self._last_grid_h = 300  # Last known grid height
        self._last_grid_x = 0  # Last known grid x position
        self._last_grid_y = 0  # Last known grid y position

        # Animation state for selection highlight
        self._selected_anim_x = None
        self._selected_anim_y = None
        self._selected_anim_w = None
        self._selected_anim_h = None
        self._selected_last_index = None
        
        # Column shift animation
        self._grid_shift_from = 0.0
        self._grid_shift_to = 0.0
        self._grid_shift_current = 0.0
        self._grid_shift_start = None
        
        self.GRID_SHIFT_DURATION = .4   # default speed (seconds)
        
     
        # Grid size (zoomable)
        self.GRID_ROWS = self.DEFAULT_GRID_ROWS
        self.GRID_COLS = self.DEFAULT_GRID_COLS
        
        self.max_grid_slots = max_grid_slots
        self.show_empty_slots = True  # Can be overridden from app.py
        
        # Discover ALL game image paths (no image loading yet)
        self._game_path_lookup = {}      # name → list of Paths (variants)
        self._game_image_cache = {}      # path → loaded PIL image
        self._used_game_images = set()   # track used images per theme

        game_files = [f for f in GAMES_DIR.iterdir() if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif')]
        for f in game_files:
            stem = f.stem.lower()
            # Determine base name before underscore or suffix (e.g., gba_blue → gba)
            base_name = stem.split("_")[0]
            self._game_path_lookup.setdefault(base_name, []).append(f)

        # For fallback random feeding
        self._shuffled_game_names = list(self._game_path_lookup.keys())
        random.shuffle(self._shuffled_game_names)
        self._next_game_img_index = 0

        # Sound manager
        self.sound_manager = SoundManager()
        
        # Music manager
        self.music_manager = MusicManager(self.sound_manager)

    # -----------------------------
    # Helpers
    # -----------------------------
    
    def get_max_grid_rows(self):
        """Get the maximum grid rows based on current screen mode."""
        if self.screen_manager.screen_mode == "single":
            if self._single_screen_stacked:
                return self.MAX_GRID_ROWS_SINGLE_STACKED
            else:
                return self.MAX_GRID_ROWS_SINGLE_DUAL
        return self.MAX_GRID_ROWS_DUAL
    
    def _preload_default_folder(self):
        default_folder_path = ASSETS_DIR / "default folder"
        if not default_folder_path.exists():
            return

        icon = hero = logo = None
        hero_frames = None
        hero_duration = 100

        color_candidates = [self.default_folder_color, "blue", None]

        for asset_type in ["icon", "hero", "logo"]:
            for color in color_candidates:
                for ext in ("png", "jpg", "jpeg", "webp", "gif"):
                    candidate_file = (
                        default_folder_path / f"{asset_type}_{color}.{ext}" if color else
                        default_folder_path / f"{asset_type}.{ext}"
                    )
                    if candidate_file.exists():
                        try:
                            if asset_type == "icon" and icon is None:
                                icon = self._load_cached_rgba(candidate_file)
                            elif asset_type == "logo" and logo is None:
                                logo = self._load_cached_rgba(candidate_file)
                            elif asset_type == "hero" and hero is None:
                                img = Image.open(candidate_file)
                                if getattr(img, "is_animated", False):
                                    hero_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                                    hero_duration = img.info.get("duration", 100)
                                    hero = hero_frames[0]
                                else:
                                    hero = img.convert("RGBA")
                        except Exception:
                            pass
                        break
                if (asset_type == "icon" and icon) or (asset_type == "hero" and hero) or (asset_type == "logo" and logo):
                    break

        if icon:
            self.smart_folders["internal:default"] = {
                "icon": icon,
                "hero": hero,
                "hero_frames": hero_frames,
                "hero_index": 0,
                "hero_duration": hero_duration,
                "logo": logo,
                "source": "root",
                "platform": None,
                "is_default_folder": True,
            }
    
    def set_grid_size(self, rows: int, cols: int):
        """Change grid size with animation (used by zoom in/out)."""
        if rows <= 0 or cols <= 0:
            return
        
        current_rows = int(round(self._current_grid_rows))
        current_cols = int(round(self._current_grid_cols))
        
        if current_rows == rows and current_cols == cols:
            return
        
        # Reset zoom ended flag at start of new zoom
        self._zoom_ended_needs_snap = False
        
        # Capture current positions for visible items (for smooth transition)
        self._zoom_item_positions = {}
        for idx, pos in enumerate(self.grid_positions):
            if idx < 30:  # Cache first 30 items
                self._zoom_item_positions[idx] = pos
        
        # Clear resize cache at start of new zoom
        self._resize_cache.clear()
        
        # Calculate current cell sizes for smooth animation
        if hasattr(self, '_last_grid_w') and hasattr(self, '_last_grid_h'):
            grid_w = self._last_grid_w
            grid_h = self._last_grid_h
        else:
            grid_w = 400
            grid_h = 300
        
        avail_w = grid_w - 2 * self.GRID_OUTER_PADDING - (current_cols - 1) * self.GRID_PADDING
        avail_h = grid_h - 2 * self.GRID_OUTER_PADDING - (current_rows - 1) * self.GRID_PADDING
        self._zoom_from_cell_w = avail_w / current_cols if current_cols > 0 else 50
        self._zoom_from_cell_h = avail_h / current_rows if current_rows > 0 else 50
        
        # Calculate target cell sizes (based on target rows/cols)
        avail_w_to = grid_w - 2 * self.GRID_OUTER_PADDING - (cols - 1) * self.GRID_PADDING
        avail_h_to = grid_h - 2 * self.GRID_OUTER_PADDING - (rows - 1) * self.GRID_PADDING
        self._zoom_to_cell_w = avail_w_to / cols if cols > 0 else 50
        self._zoom_to_cell_h = avail_h_to / rows if rows > 0 else 50
        
        # Start zoom animation
        self._zoom_anim_from = (current_rows, current_cols)
        self._zoom_anim_to = (rows, cols)
        self._zoom_anim_start = time.perf_counter()
        
        # Update target grid size (but don't rebuild items yet)
        self.GRID_ROWS = rows
        self.GRID_COLS = cols
        
        # Clamp selection to visible grid when zooming
        max_visible_index = rows * self.GRID_COLS - 1
        if self.selected_index > max_visible_index:
            self.selected_index = max_visible_index
        self.grid_scroll_x = 0  # Reset scroll on zoom
        self._grid_scroll_target = 0  # Reset scroll target
        self._grid_scroll_from = 0  # Reset scroll from
        self._grid_scroll_start = None  # Stop any scroll animation
    
    def set_default_folder_color(self, color_name: str):
        """Change the default folder color at runtime and refresh grid display."""
        # Skip if already this color
        if self.default_folder_color == color_name:
            return

        self.default_folder_color = color_name

        default_folder_path = ASSETS_DIR / "default folder"
        if not default_folder_path.exists():
            print("[DEBUG] Default folder path missing")
            return

        icon = hero = logo = None
        hero_frames = None
        hero_duration = 100

        # Try new color first, then fallback to blue or plain
        color_candidates = [self.default_folder_color, "blue", None]
        self._preload_default_folder()

        for asset_type in ["icon", "hero", "logo"]:
            for color in color_candidates:
                for ext in ("png", "jpg", "jpeg", "webp", "gif"):
                    candidate_file = (
                        default_folder_path / f"{asset_type}_{color}.{ext}" if color else
                        default_folder_path / f"{asset_type}.{ext}"
                    )
                    if candidate_file.exists():
                        try:
                            if asset_type == "icon" and icon is None:
                                icon = self._load_cached_rgba(candidate_file)
                            elif asset_type == "logo" and logo is None:
                                logo = self._load_cached_rgba(candidate_file)
                            elif asset_type == "hero" and hero is None:
                                img = Image.open(candidate_file)
                                if getattr(img, "is_animated", False):
                                    hero_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                                    hero_duration = img.info.get("duration", 100)
                                    hero = hero_frames[0]
                                else:
                                    hero = img.convert("RGBA")
                        except Exception as e:
                            print(f"[DEBUG] Failed to load {candidate_file}: {e}")
                        break
                if (asset_type == "icon" and icon) or (asset_type == "hero" and hero) or (asset_type == "logo" and logo):
                    break  # stop trying other colors for this asset_type

        # Update smart_folders entry if icon exists
        if icon:
            self.smart_folders["internal:default"].update({
                "icon": icon,
                "hero": hero,
                "hero_frames": hero_frames,
                "hero_index": 0,
                "hero_duration": hero_duration,
                "logo": logo,
            })
        else:
            print("[DEBUG] Default folder icon not found for new color")

        # Force redraw on next composite
        self._grid_items_dirty = True
        self._invalidate_static_cache()
    def _load_rgba(self, path: Path, fallback: Path | None = None):
        if path and path.exists():
            try:
                img = Image.open(path)
                if getattr(img, "is_animated", False):
                    return img
                return img.convert("RGBA")
            except Exception as e:
                print(f"[DEBUG] Failed to open image: {path} -> {e}")
        if fallback and fallback.exists():
            try:
                img = Image.open(fallback)
                if getattr(img, "is_animated", False):
                    return img
                return img.convert("RGBA")
            except Exception as e:
                print(f"[DEBUG] Failed to open fallback: {fallback} -> {e}")
        return None

    def _load_cached_rgba(self, path: Path, fallback: Path | None = None):
        """Load image from cache or disk."""
        if path in self._game_image_cache:
            return self._game_image_cache[path]
        img = self._load_rgba(path, fallback)
        if img:
            self._game_image_cache[path] = img
        return img
    
    def _load_frame(self, name: str):
        """Load a device frame by name"""
        filename = self.BEZEL_INFO.get(name, ("bezels/ayn thor/rainbow.png", "dual"))[0]
        return self._load_cached_rgba(ASSETS_DIR / filename)

    def set_bezel(self, name: str):
        """Swap to a different device frame"""
        if name in self.BEZEL_OPTIONS:
            self.current_bezel_name = name
            self.bezel_img = self._load_frame(name)
            
            # Apply device settings (reloads device.json from bezel folder)
            
            # Get folder name from BEZEL_INFO
            bezel_info = self.BEZEL_INFO.get(name, ("", "unknown"))
            folder_name = bezel_info[1] if len(bezel_info) > 1 else "unknown"
            
            # Apply device settings
            self.apply_device_settings(folder_name)
            
            if self.bezel_img:
                new_w, new_h = self.bezel_img.size
                self._frame_scale = min(new_w / self.FRAME_WIDTH, new_h / self.FRAME_HEIGHT)
                self._detect_screen_positions()
                self._update_screen_mode()
                # Reset selection animation to snap to new position
                self._reset_selection_animation()
            self._invalidate_static_cache()
            # Clear resize cache to ensure ss_mask and other bezel-specific images are re-rendered
            self._resize_cache.clear()
    
    def _reset_selection_animation(self):
        """Reset selection animation state so it snaps to new position."""
        self._selected_anim_x = None
        self._selected_anim_y = None
        self._selected_anim_w = None
        self._selected_anim_h = None
        self._sel_anim_from = None
        self._sel_anim_to = None
        self._sel_anim_start = None
    
    def _update_screen_mode(self):
        """Update screen positions based on current display mode and device configuration."""
        # Use _display_mode for user selection, not BEZEL_SCREEN_MODE
        # (BEZEL_SCREEN_MODE is for persisting per-bezel settings)
        mode = getattr(self, '_display_mode', self.BEZEL_SCREEN_MODE.get(self.current_bezel_name, "dual"))
        
        if mode == "single":
            # Single screen mode: bottom screen fills the display
            self.screen_manager.set_single_screen_mode()
        else:
            # Dual screen mode: use standard positions
            # But for 1-screen devices, we need to keep screens stacked
            if self._device_screen_amount == 1:
                # 1-screen device in dual mode: keep main screen stacked on external (hidden)
                self.screen_manager.external.rect = Screen.SINGLE_SCREEN
                self.screen_manager._screen_mode = "single"
                self.screen_manager._update_single_screen_main_position()
                Screen.TOP_SCREEN = self.screen_manager.main.rect
            else:
                self.screen_manager.set_dual_screen_mode()
    
    def _render_ui_elements(self, base, canvas_w, canvas_h, device_x, device_y, scale, skip_borders=False):
        """Render UI elements based on screen mode and visibility settings."""
        mode = self.screen_manager.screen_mode
        stacked = self._single_screen_stacked
        
        main_screen = self.screen_manager.main
        external_screen = self.screen_manager.external
        
        # Calculate screen positions
        main_x = device_x + round(main_screen.x * scale)
        main_y = device_y + round(main_screen.y * scale)
        main_w = round(main_screen.w * scale)
        main_h = round(main_screen.h * scale)
        
        ext_x = device_x + round(external_screen.x * scale)
        ext_y = device_y + round(external_screen.y * scale)
        ext_w = round(external_screen.w * scale)
        ext_h = round(external_screen.h * scale)
        
        def paste_ui(img, screen_x, screen_y, screen_w, screen_h, anchor=None):
            if img is None:
                return
            if anchor:
                screen_type, h_anchor, v_anchor = anchor
                target_w = screen_w if screen_type == "main" else ext_w
                target_h = screen_h if screen_type == "main" else ext_h
                target_x = main_x if screen_type == "main" else ext_x
                target_y = main_y if screen_type == "main" else ext_y
                
                img_w, img_h = img.size
                new_h = target_h
                new_w = round(img_w * (new_h / img_h))
                
                if h_anchor == "left":
                    x_offset = 0
                elif h_anchor == "center":
                    x_offset = (target_w - new_w) // 2
                else:
                    x_offset = target_w - new_w
                
                if v_anchor == "top":
                    y_offset = 0
                elif v_anchor == "center":
                    y_offset = (target_h - new_h) // 2
                else:
                    y_offset = target_h - new_h
                
                key = (id(img), new_w, new_h)
                resized = self._resize_cache.get(key)
                if resized is None:
                    resized = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                    self._resize_cache[key] = resized
                base.alpha_composite(resized, (target_x + x_offset, target_y + y_offset))
            else:
                key = (id(img), screen_w, screen_h)
                resized = self._resize_cache.get(key)
                if resized is None:
                    resized = img.resize((screen_w, screen_h), Image.Resampling.BILINEAR)
                    self._resize_cache[key] = resized
                base.alpha_composite(resized, (screen_x, screen_y))
        
        if mode == "dual":
            # DUAL SCREEN MODE
            # Bottom screen elements
            if self.dock_visible and self.ui_d_bottom_dock:
                paste_ui(self.ui_d_bottom_dock, ext_x, ext_y, ext_w, ext_h, self.ui_d_bottom_dock_anchor)
            if self.corner_hints_visible and self.ui_d_bottom_left_cornerhints:
                paste_ui(self.ui_d_bottom_left_cornerhints, ext_x, ext_y, ext_w, ext_h, self.ui_d_bottom_left_cornerhints_anchor)
            if self.corner_hints_visible and self.ui_d_bottom_right_cornerhints:
                paste_ui(self.ui_d_bottom_right_cornerhints, ext_x, ext_y, ext_w, ext_h, self.ui_d_bottom_right_cornerhints_anchor)
            
            # Top screen elements (time and user are always visible)
            if self.corner_hints_visible and self.ui_d_top_cornerhints:
                paste_ui(self.ui_d_top_cornerhints, main_x, main_y, main_w, main_h, self.ui_d_top_cornerhints_anchor)
            if self.ui_d_top_time:
                paste_ui(self.ui_d_top_time, main_x, main_y, main_w, main_h, self.ui_d_top_time_anchor)
            if self.ui_d_top_user:
                paste_ui(self.ui_d_top_user, main_x, main_y, main_w, main_h, self.ui_d_top_user_anchor)
        
        elif mode == "single" and stacked:
            # SINGLE SCREEN - STACKED mode (true single screen)
            # Dock uses same image for both single screen modes
            if self.dock_visible and self.ui_s_dock:
                paste_ui(self.ui_s_dock, ext_x, ext_y, ext_w, ext_h, self.ui_s_dock_anchor)
            
            # Corner hints
            if self.corner_hints_visible and self.ui_s_ss_left_cornerhints:
                paste_ui(self.ui_s_ss_left_cornerhints, ext_x, ext_y, ext_w, ext_h, self.ui_s_ss_left_cornerhints_anchor)
            if self.corner_hints_visible and self.ui_s_ss_right_cornerhints:
                paste_ui(self.ui_s_ss_right_cornerhints, ext_x, ext_y, ext_w, ext_h, self.ui_s_ss_right_cornerhints_anchor)
            
            # Time (always visible)
            if self.ui_s_ss_time:
                paste_ui(self.ui_s_ss_time, ext_x, ext_y, ext_w, ext_h, self.ui_s_ss_time_anchor)
        
        else:
            # SINGLE SCREEN - dual mode (top screen off, external only)
            # Dock
            if self.dock_visible and self.ui_s_dock:
                paste_ui(self.ui_s_dock, ext_x, ext_y, ext_w, ext_h, self.ui_s_dock_anchor)
            
            # Corner hints
            if self.corner_hints_visible and self.ui_s_ds_left_cornerhints:
                paste_ui(self.ui_s_ds_left_cornerhints, ext_x, ext_y, ext_w, ext_h, self.ui_s_ds_left_cornerhints_anchor)
            if self.corner_hints_visible and self.ui_s_ds_right_cornerhints:
                paste_ui(self.ui_s_ds_right_cornerhints, ext_x, ext_y, ext_w, ext_h, self.ui_s_ds_right_cornerhints_anchor)
        
        # Render app grid at bottom of external/bottom screen
        self._render_app_grid(base, canvas_w, canvas_h, ext_x, ext_y, ext_w, ext_h, mode, scale, skip_borders)
    
    def _render_app_grid(self, base, canvas_w, canvas_h, ext_x, ext_y, ext_w, ext_h, mode, scale, skip_borders=False):
        """Render 5 circular app icons evenly distributed in a defined region."""
        from PIL import ImageDraw
        
        if not self._app_images_loaded:
            return
        
        # Get sizes from settings
        # base_icon_size is the slot size for grid layout (vertical space)
        # icon_size is the actual rendered size (affected by icon_scale)
        base_icon_size = round(self.app_grid_icon_size * scale)
        icon_size = round(base_icon_size * self.app_grid_icon_scale)
        grid_width = round(self.app_grid_width * scale)
        y_offset = round(self.app_grid_y_offset * scale)
        
        # Calculate the region position (always centered horizontally)
        # Grid area uses base_icon_size for layout
        x_offset = round(self.app_grid_x_offset * scale)
        center_x = ext_x + ext_w // 2
        grid_left = center_x - grid_width // 2 + x_offset
        grid_right = grid_left + grid_width
        
        # Position from bottom with y_offset
        grid_bottom = ext_y + ext_h - y_offset
        grid_top = grid_bottom - base_icon_size  # Grid area height uses base_icon_size
        
        # Store for debug output
        self._app_grid_debug = {
            "mode": mode,
            "screen_w": ext_w,
            "screen_h": ext_h,
            "grid_width": grid_width,
            "base_icon_size": base_icon_size,
            "icon_size": icon_size,
            "icon_scale": self.app_grid_icon_scale,
            "grid_left": grid_left,
            "grid_right": grid_right,
            "grid_top": grid_top,
            "grid_bottom": grid_bottom,
        }
        
        # Draw temporary border around app grid area only in bezel edit mode
        if self.bezel_edit_mode and not skip_borders:
            border_draw = ImageDraw.Draw(base)
            border_draw.rectangle(
                [grid_left, grid_top - 5, grid_right, grid_bottom + 5],
                outline=(255, 0, 0, 255), width=3
            )
        
        # Calculate spacing for 5 evenly spaced icons centered within the grid width
        # Use base_icon_size for layout calculations
        available_width = grid_right - grid_left
        total_icon_width = 5 * base_icon_size
        total_gap_space = available_width - total_icon_width
        gap = total_gap_space // 6 if total_gap_space > 0 else 0
        
        # Render each app (up to 5), evenly spaced
        for i in range(5):
            # Position: start with gap, then for each icon add gap + base_icon_size
            # This gives us the top-left corner of each slot
            slot_x = grid_left + gap + i * (gap + base_icon_size)
            slot_y = grid_top
            
            # Center the scaled icon within the slot
            icon_x = slot_x + (base_icon_size - icon_size) // 2
            icon_y = slot_y + (base_icon_size - icon_size) // 2
            
            # Get the app image (or None if not enough)
            app_img = self._app_images[i] if i < len(self._app_images) else None
            
            if app_img is not None and self.populated_apps_visible:
                # Resize app image to fit within the circle
                resized = app_img.resize((icon_size, icon_size), Image.Resampling.BILINEAR)
                
                # Create circular mask
                circle_mask = Image.new("L", (icon_size, icon_size), 0)
                draw = ImageDraw.Draw(circle_mask)
                draw.ellipse((0, 0, icon_size - 1, icon_size - 1), fill=255)
                
                # Apply circular mask
                circular_app = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
                circular_app.paste(resized, (0, 0))
                circular_app.putalpha(circle_mask)
                
                # Composite onto base
                base.alpha_composite(circular_app, (icon_x, icon_y))
            elif app_img is None and self.app_grid_visible:
                # Empty slot: draw white circle (only if app_grid_visible is True)
                circular_app = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(circular_app)
                draw.ellipse((0, 0, icon_size - 1, icon_size - 1), fill=(255, 255, 255, 255))
                
                # Composite onto base
                base.alpha_composite(circular_app, (icon_x, icon_y))
        
        # Draw magnify window in bezel edit mode (hide handles in zoom view)
        # Only draw if not skipped (controlled by skip_magnify parameter in composite)
        if getattr(self, '_skip_magnify_render', False):
            pass  # Skip magnify when rendering content separately
        elif self.bezel_edit_mode and getattr(self, 'magnify_window', True):
            # Draw magnify window (lightweight - just crops and scales, no complex calculations)
            self._render_magnify_window(base, canvas_w, canvas_h, grid_left, grid_top, grid_right, grid_bottom, icon_size)
    
    def _is_in_magnify_area(self, canvas_w, canvas_h):
        """Check if magnify window is active and return its bounds."""
        if not self.bezel_edit_mode or not getattr(self, 'magnify_window', True):
            return None
        mag_size = self.magnify_size
        mag_margin = 20
        mag_x = canvas_w - mag_size - mag_margin
        mag_y = canvas_h - mag_size - mag_margin
        return (mag_x, mag_y, mag_x + mag_size, mag_y + mag_size)
    
    def get_magnify_window(self, canvas_size: tuple[int, int], base_image: Image.Image = None) -> Image.Image:
        """Get just the magnify window overlay (not scaled with canvas zoom)."""
        if not self.bezel_edit_mode or not getattr(self, 'magnify_window', True):
            return None
        
        canvas_w, canvas_h = canvas_size
        
        # Get grid positions - use cached values if available
        grid_left = getattr(self, '_app_grid_debug', {}).get('grid_left', canvas_w // 2 - 100)
        grid_right = getattr(self, '_app_grid_debug', {}).get('grid_right', canvas_w // 2 + 100)
        grid_top = getattr(self, '_app_grid_debug', {}).get('grid_top', canvas_h // 2 - 50)
        grid_bottom = getattr(self, '_app_grid_debug', {}).get('grid_bottom', canvas_h // 2 + 50)
        icon_size = 40
        
        # Use provided base image or create a placeholder
        if base_image is None:
            base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        else:
            base = base_image
        
        # Render magnify to a separate image
        mag_size = self.magnify_size
        mag_margin = 20
        mag_x = canvas_w - mag_size - mag_margin
        mag_y = canvas_h - mag_size - mag_margin
        zoom = getattr(self, 'magnify_zoom', 2.0)
        mouse_x = getattr(self, 'mouse_x', (grid_left + grid_right) // 2)
        mouse_y = getattr(self, 'mouse_y', (grid_top + grid_bottom) // 2)
        
        src_half = int(mag_size / zoom / 2)
        src_left = max(0, mouse_x - src_half)
        src_top = max(0, mouse_y - src_half)
        src_right = min(canvas_w, mouse_x + src_half)
        src_bottom = min(canvas_h, mouse_y + src_half)
        
        if src_right > src_left and src_bottom > src_top:
            try:
                region = base.crop((src_left, src_top, src_right, src_bottom))
                magnified = region.resize((mag_size, mag_size), Image.Resampling.NEAREST)
                
                # Create magnify overlay image
                mag_overlay = Image.new("RGBA", (mag_size + 4, mag_size + 4), (0, 0, 0, 0))
                from PIL import ImageDraw
                draw = ImageDraw.Draw(mag_overlay)
                draw.rectangle([0, 0, mag_size + 3, mag_size + 3], fill=(40, 40, 40, 200), outline=(100, 100, 100, 255), width=2)
                mag_overlay.alpha_composite(magnified, (2, 2))
                draw.rectangle([2, 2, mag_size + 2, mag_size + 2], outline=(255, 255, 255, 255), width=1)
                
                return mag_overlay
            except Exception:
                pass
        
        return None
    
    def _render_magnify_window(self, base, canvas_w, canvas_h, grid_left, grid_top, grid_right, grid_bottom, icon_size):
        """Render a magnified view centered on mouse position, clamped to canvas bounds."""
        from PIL import ImageDraw
        
        # Magnify window size and position (use instance attribute)
        mag_size = self.magnify_size
        mag_margin = 20
        mag_x = canvas_w - mag_size - mag_margin
        mag_y = canvas_h - mag_size - mag_margin
        
        # Zoom level - scales with window size
        zoom = getattr(self, 'magnify_zoom', 2.0)
        
        # Get mouse position (default to center of app grid if not set)
        mouse_x = getattr(self, 'mouse_x', (grid_left + grid_right) // 2)
        mouse_y = getattr(self, 'mouse_y', (grid_top + grid_bottom) // 2)
        
        # Calculate the source region to zoom (centered on mouse)
        src_half = int(mag_size / zoom / 2)
        
        # Clamp the source region to stay within canvas bounds
        src_left = mouse_x - src_half
        src_top = mouse_y - src_half
        src_right = mouse_x + src_half
        src_bottom = mouse_y + src_half
        
        # Adjust if region goes outside canvas
        if src_left < 0:
            src_right -= src_left
            src_left = 0
        if src_top < 0:
            src_bottom -= src_top
            src_top = 0
        if src_right > canvas_w:
            src_left -= (src_right - canvas_w)
            src_right = canvas_w
        if src_bottom > canvas_h:
            src_top -= (src_bottom - canvas_h)
            src_bottom = canvas_h
        
        # Final clamp to ensure we don't go negative
        src_left = max(0, src_left)
        src_top = max(0, src_top)
        src_right = min(canvas_w, src_right)
        src_bottom = min(canvas_h, src_bottom)
        
        # Crop and resize the region
        if src_right > src_left and src_bottom > src_top:
            try:
                region = base.crop((src_left, src_top, src_right, src_bottom))
                magnified = region.resize((mag_size, mag_size), Image.Resampling.NEAREST)
                
                # Draw background for magnify window
                draw = ImageDraw.Draw(base)
                draw.rectangle(
                    [mag_x - 2, mag_y - 2, mag_x + mag_size + 2, mag_y + mag_size + 2],
                    fill=(40, 40, 40, 200), outline=(100, 100, 100, 255), width=2
                )
                
                # Paste magnified region
                base.alpha_composite(magnified, (mag_x, mag_y))
                
                # Draw border around magnify window
                draw.rectangle(
                    [mag_x, mag_y, mag_x + mag_size, mag_y + mag_size],
                    outline=(255, 255, 255, 255), width=1
                )
            except Exception:
                pass  # Skip if cropping fails
    
    def _render_app_grid_controls(self, base, canvas_w, canvas_h):
        """Render app grid controls (directional arrows and size controls) on top of everything."""
        self._render_directional_arrows(base, canvas_w, canvas_h)
    
    def _render_directional_arrows(self, base, canvas_w, canvas_h):
        """Render directional arrows in the bottom left corner for moving the app grid, plus width/height controls to the right."""
        from PIL import ImageDraw
        
        # Arrow area position (left side - position controls)
        arrow_margin = 20
        arrow_size = 25
        pos_center_x = arrow_margin + arrow_size + 5
        pos_center_y = canvas_h - arrow_margin - arrow_size - 30
        
        draw = ImageDraw.Draw(base)
        
        # Draw background circle for position controls
        draw.ellipse(
            [pos_center_x - arrow_size - 5, pos_center_y - arrow_size - 5, 
             pos_center_x + arrow_size + 5, pos_center_y + arrow_size + 5],
            fill=(40, 40, 40, 180), outline=(100, 100, 100, 255), width=2
        )
        
        arrow_color = (255, 255, 255, 255)
        
        # Up arrow
        draw.polygon([
            (pos_center_x, pos_center_y - arrow_size),
            (pos_center_x - 8, pos_center_y - arrow_size + 15),
            (pos_center_x + 8, pos_center_y - arrow_size + 15)
        ], fill=arrow_color)
        
        # Down arrow
        draw.polygon([
            (pos_center_x, pos_center_y + arrow_size),
            (pos_center_x - 8, pos_center_y + arrow_size - 15),
            (pos_center_x + 8, pos_center_y + arrow_size - 15)
        ], fill=arrow_color)
        
        # Left arrow
        draw.polygon([
            (pos_center_x - arrow_size, pos_center_y),
            (pos_center_x - arrow_size + 15, pos_center_y - 8),
            (pos_center_x - arrow_size + 15, pos_center_y + 8)
        ], fill=arrow_color)
        
        # Right arrow
        draw.polygon([
            (pos_center_x + arrow_size, pos_center_y),
            (pos_center_x + arrow_size - 15, pos_center_y - 8),
            (pos_center_x + arrow_size - 15, pos_center_y + 8)
        ], fill=arrow_color)
        
        # Size controls (to the RIGHT of arrows)
        size_center_x = pos_center_x + arrow_size + 60  # To the right of arrows
        size_center_y = pos_center_y
        
        # Draw background rectangle for size controls (wider for W/H controls)
        draw.rounded_rectangle(
            [size_center_x - 50, size_center_y - 20, size_center_x + 75, size_center_y + 20],
            radius=8, fill=(40, 40, 40, 180), outline=(100, 100, 100, 255), width=2
        )
        
        size_color = (100, 200, 255, 255)  # Cyan for sizing
        
        # Width controls (left side of size panel)
        # Minus button
        draw.rectangle(
            [size_center_x - 45, size_center_y - 3, size_center_x - 30, size_center_y + 3],
            fill=size_color
        )
        
        # Label "W"
        draw.text((size_center_x - 20, size_center_y - 8), "W", fill=size_color)
        
        # Plus button (horizontal bar)
        draw.rectangle(
            [size_center_x - 5, size_center_y - 3, size_center_x + 10, size_center_y + 3],
            fill=size_color
        )
        # Plus button (vertical bar)
        draw.rectangle(
            [size_center_x, size_center_y - 7, size_center_x + 5, size_center_y + 7],
            fill=size_color
        )
        
        # Icon size controls (right side of size panel)
        # Minus button
        draw.rectangle(
            [size_center_x + 20, size_center_y - 3, size_center_x + 35, size_center_y + 3],
            fill=size_color
        )
        
        # Label "H" (for icon Height)
        draw.text((size_center_x + 40, size_center_y - 8), "H", fill=size_color)
        
        # Plus button (horizontal bar)
        draw.rectangle(
            [size_center_x + 55, size_center_y - 3, size_center_x + 70, size_center_y + 3],
            fill=size_color
        )
        # Plus button (vertical bar)
        draw.rectangle(
            [size_center_x + 60, size_center_y - 7, size_center_x + 65, size_center_y + 7],
            fill=size_color
        )
        
        # Store control positions for click detection
        self._app_grid_controls = {
            "arrow_center_x": pos_center_x,
            "arrow_center_y": pos_center_y,
            "arrow_size": arrow_size,
            "size_center_x": size_center_x,
            "size_center_y": size_center_y,
        }
    
    def _render_drag_handles(self, base, grid_left, grid_right, grid_top, grid_bottom):
        """Render draggable handles on the middle of each edge (red to match border)."""
        from PIL import ImageDraw
        
        draw = ImageDraw.Draw(base)
        handle_color = (255, 0, 0, 255)  # Red to match app grid border
        handle_size = 8
        
        # Top edge handle (center)
        draw.ellipse([
            (grid_left + grid_right) // 2 - handle_size, grid_top - handle_size,
            (grid_left + grid_right) // 2 + handle_size, grid_top + handle_size
        ], fill=handle_color, outline=(200, 0, 0, 255))
        
        # Bottom edge handle (center)
        draw.ellipse([
            (grid_left + grid_right) // 2 - handle_size, grid_bottom - handle_size,
            (grid_left + grid_right) // 2 + handle_size, grid_bottom + handle_size
        ], fill=handle_color, outline=(200, 0, 0, 255))
        
        # Left edge handle (center)
        draw.ellipse([
            grid_left - handle_size, (grid_top + grid_bottom) // 2 - handle_size,
            grid_left + handle_size, (grid_top + grid_bottom) // 2 + handle_size
        ], fill=handle_color, outline=(200, 0, 0, 255))
        
        # Right edge handle (center)
        draw.ellipse([
            grid_right - handle_size, (grid_top + grid_bottom) // 2 - handle_size,
            grid_right + handle_size, (grid_top + grid_bottom) // 2 + handle_size
        ], fill=handle_color, outline=(200, 0, 0, 255))
    
    def _detect_screen_positions(self):
        """Detect screen positions from the frame image"""
        if self.bezel_img:
            frame_w, frame_h = self.bezel_img.size
            self.screen_manager.set_frame_dimensions(frame_w, frame_h)
            self.screen_manager.set_frame_scale(self._frame_scale)

    @property
    def wallpaper_top(self):
        return self.screen_manager.main.wallpaper
    
    @wallpaper_top.setter
    def wallpaper_top(self, value):
        self.screen_manager.main.set_wallpaper(value)
    
    @property
    def wallpaper_top_frames(self):
        return self.screen_manager.main.wallpaper_frames
    
    @wallpaper_top_frames.setter
    def wallpaper_top_frames(self, value):
        self.screen_manager.main.wallpaper_frames = value
    
    @property
    def wallpaper_top_index(self):
        return self.screen_manager.main.wallpaper_index
    
    @wallpaper_top_index.setter
    def wallpaper_top_index(self, value):
        self.screen_manager.main.wallpaper_index = value
    
    @property
    def wallpaper_top_duration(self):
        return self.screen_manager.main.wallpaper_duration
    
    @wallpaper_top_duration.setter
    def wallpaper_top_duration(self, value):
        self.screen_manager.main.wallpaper_duration = value

    @property
    def wallpaper_bottom(self):
        return self.screen_manager.external.wallpaper
    
    @wallpaper_bottom.setter
    def wallpaper_bottom(self, value):
        self.screen_manager.external.set_wallpaper(value)
    
    @property
    def wallpaper_bottom_frames(self):
        return self.screen_manager.external.wallpaper_frames
    
    @wallpaper_bottom_frames.setter
    def wallpaper_bottom_frames(self, value):
        self.screen_manager.external.wallpaper_frames = value
    
    @property
    def wallpaper_bottom_index(self):
        return self.screen_manager.external.wallpaper_index
    
    @wallpaper_bottom_index.setter
    def wallpaper_bottom_index(self, value):
        self.screen_manager.external.wallpaper_index = value
    
    @property
    def wallpaper_bottom_duration(self):
        return self.screen_manager.external.wallpaper_duration
    
    @wallpaper_bottom_duration.setter
    def wallpaper_bottom_duration(self, value):
        self.screen_manager.external.wallpaper_duration = value

    def _apply_mask(self, img: Image.Image, mask: Image.Image):
        """Apply mask using alpha channel: opaque = visible, transparent = hidden"""
        if not img or not mask:
            return None
        img_resized = img.resize(mask.size, Image.Resampling.BILINEAR)
        
        # Extract alpha channel from mask for transparency-based masking
        if mask.mode == "RGBA":
            mask_alpha = mask.split()[3]  # Get alpha channel
        elif mask.mode == "LA":
            mask_alpha = mask.split()[1]  # Get alpha channel from LA
        elif mask.mode == "L":
            mask_alpha = mask  # Already grayscale, use as-is
        else:
            mask_alpha = mask.convert("L")  # Convert to grayscale
        
        return Image.composite(img_resized, Image.new("RGBA", mask.size, (0, 0, 0, 0)), mask_alpha)

    def _get_random_game_image(self, name: str):
        """Return a random variant of the game image for this platform name.
        Fallback to any platform if no images exist for this name.
        Avoid duplicates if possible.
        Returns dict with 'img', 'frames', 'index', 'duration' for animated images.
        """
        paths = self._game_path_lookup.get(name)

        # --- FALLBACK TO ANY PLATFORM ---
        if not paths:
            # flatten all game lists into one
            paths = [p for lst in self._game_path_lookup.values() for p in lst]

        if not paths:
            return None  # no images at all

        # pick unused if possible
        unused = [p for p in paths if p not in self._used_game_images]
        if not unused:
            unused = paths  # all used, fallback

        selected_path = random.choice(unused)
        self._used_game_images.add(selected_path)

        if selected_path not in self._game_image_cache:
            img = self._load_rgba(selected_path)
            if img:
                # Check if animated
                if getattr(img, "is_animated", False):
                    frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                    duration = img.info.get("duration", 100)
                    self._game_image_cache[selected_path] = {
                        "img": frames[0],
                        "frames": frames,
                        "index": 0,
                        "duration": duration
                    }
                else:
                    self._game_image_cache[selected_path] = {
                        "img": img.convert("RGBA") if img.mode != "RGBA" else img,
                        "frames": None,
                        "index": 0,
                        "duration": 100
                    }

        return self._game_image_cache.get(selected_path)
    
    def _get_next_game_image(self):
        """Return next shuffled game image, lazy loading + caching."""
        if not self._shuffled_game_names:
            return None

        name = self._shuffled_game_names[self._next_game_img_index]
        self._next_game_img_index += 1

        if self._next_game_img_index >= len(self._shuffled_game_names):
            self._next_game_img_index = 0

        # Load only if not cached
        if name not in self._game_image_cache:
            path = self._game_path_lookup.get(name)
            if path:
                img = self._load_rgba(path)
                if img:
                    self._game_image_cache[name] = img

        return self._game_image_cache.get(name)

    # -----------------------------
    # Background fitting
    # -----------------------------
    def _fit_background(self, base: Image.Image, bg: Image.Image, canvas_size: tuple[int,int], device_rect: tuple[int,int,int,int]):
        """
        Stretch bg to fill entire canvas for seamless scrolling.
        canvas_size = (canvas_w, canvas_h)
        device_rect = (device_x, device_y, device_w, device_h)
        """
        if not bg:
            return
        canvas_w, canvas_h = canvas_size
        
        # Stretch to fill entire canvas for seamless scrolling
        bg_resized = bg.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)
        self._bg_fitted_width = canvas_w  # Store for scroll calculations
        base.alpha_composite(bg_resized, (0, 0))

    # Video First Frame
    
    def first_frame_from_video(self, path):
        path = Path(path)
        cache_key = (str(path), path.stat().st_mtime)

        if cache_key in self.video_frame_cache:
            return self.video_frame_cache[cache_key]

        try:
            import av
            
            container = av.open(str(path))
            stream = container.streams.video[0]

            # Get rotation from various possible sources
            rotation = 0
            
            # Try stream metadata
            if stream.metadata:
                rot = stream.metadata.get('rotate', None)
                if rot:
                    rotation = int(rot)
            
            # Try side data on first frame
            if rotation == 0:
                container.seek(0)
                frame = next(container.decode(stream))
                # Check frame side data for rotation
                if hasattr(frame, 'side_data'):
                    for sd in frame.side_data:
                        pass
            
            # Try alternative - check rotation attribute on frame
            if rotation == 0:
                container.seek(0)
                frame = next(container.decode(stream))
                # Check if frame has rotation attribute
                frame_rot = getattr(frame, 'rotation', 0)
                if frame_rot:
                    rotation = frame_rot
            
            # Normalize rotation to positive values (90, 180, 270)
            rotation = rotation % 360
            
            container.seek(0)

            frame = next(container.decode(stream))
            img = frame.to_image()
            
            # Apply rotation if needed
            if rotation in (90, 180, 270):
                if rotation == 90:
                    img = img.transpose(Image.ROTATE_270)
                elif rotation == 180:
                    img = img.transpose(Image.ROTATE_180)
                elif rotation == 270:
                    img = img.transpose(Image.ROTATE_90)

            self.video_frame_cache[cache_key] = img
            return img

        except Exception as e:
            print(f"Video decode failed for {path}: {e}")

            return None

    def is_video_available(self) -> bool:
        """Check if video playback is available (opencv-python installed)."""
        try:
            import cv2
            return True
        except ImportError:
            return False
    
    def _load_image_with_exif(self, path: Path) -> Image.Image | None:
        """Load an image and apply EXIF orientation correction if needed."""
        try:
            img = Image.open(path)
            # Only apply EXIF transpose for non-animated images
            # (exif_transpose destroys animation frames)
            if not getattr(img, "is_animated", False):
                img = ImageOps.exif_transpose(img)
            return img
        except Exception as e:
            print(f"Failed to load image {path}: {e}")
            return None
    
    # -----------------------------
    # Theme Loading
    # -----------------------------
    def load_theme(self, theme_path: Path | None, max_grid_items: int | None = None):
        # Force full rebuild of static cache when theme changes
        self._static_cache_image = None
        self._static_cache_size = None
        self._static_cache_dirty = True
        self._grid_items_dirty = True

        # Also clear resize cache so old wallpaper sizes aren't reused
        self._resize_cache.clear()
        
        self.video_frame_cache.clear()

        # Reset shuffled game name order for this theme
        self._shuffled_game_names = list(self._game_path_lookup.keys())
        random.shuffle(self._shuffled_game_names)
        self._next_game_img_index = 0
        self.theme_path = theme_path if theme_path else PLACEHOLDER_DIR
        
        # Reset theme volume flags so new theme starts fresh
        self.sound_manager._theme_sfx_volume_set = False
        self.sound_manager._theme_music_volume_set = False
        
        # Clear wallpaper data from previous theme (critical for switching away from video themes!)
        self.screen_manager.main.clear_wallpaper()
        self.screen_manager.external.clear_wallpaper()

        if not (ASSETS_DIR / "empty.png").exists():
            raise FileNotFoundError("assets/empty.png is required for filling empty grid slots")
        empty_grid_image = self._load_cached_rgba(ASSETS_DIR / "empty.png")

        # Load theme.json
        self.theme_data = {}
        json_path = self.theme_path / "theme.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.theme_data = json.load(f)
            except Exception:
                self.theme_data = {}

        # Load sounds and set volume from theme (only if explicitly defined in theme.json)
        if "sfx_volume" in self.theme_data:
            self.sound_manager.set_theme_sfx_volume(float(self.theme_data.get("sfx_volume", 1.0)))
        if "music_volume" in self.theme_data:
            self.sound_manager.set_theme_music_volume(float(self.theme_data.get("music_volume", 1.0)))
        self.sound_manager.load_theme_sounds(self.theme_path)
        
        # Load music configuration and start playback
        self.music_manager.load_from_theme(self.theme_path, PLACEHOLDER_DIR)

        # Preview image
        self.preview_image = self._load_cached_rgba(self.theme_path / "preview.png", PLACEHOLDER_DIR / "preview.png")

        # Wallpapers with aliases
        top_candidates = [
            "main.png","top.png",
            "main.gif","top.gif",
            "main.jpg","top.jpg",
            "main.webp","top.webp",
            "main.mp4","top.mp4",
            "main.webm","top.webm"
        ]

        bottom_candidates = [
            "external.png","bottom.png",
            "external.jpg","external.jpeg","bottom.jpg","bottom.jpeg",
            "external.gif","bottom.gif",
            "external.webp","bottom.webp",
            "external.mp4","bottom.mp4",
            "external.webm","bottom.webm"
        ]

        # Top wallpaper (supports GIF), honoring theme.json override
        self.wallpaper_top = None
        self.wallpaper_top_frames = []
        self.wallpaper_top_index = 0
        self.wallpaper_top_duration = 100

        # Check if theme.json specifies exact file
        wallpaper_main_name = self.theme_data.get("wallpaper_main")

        top_files_to_try = []
        if wallpaper_main_name:
            # Only accept supported image types
            ext = Path(wallpaper_main_name).suffix.lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"):
                top_files_to_try.append(wallpaper_main_name)

        # Append default candidates as fallback
        top_files_to_try.extend(top_candidates)

        for fname in top_files_to_try:
            path_file = self.theme_path / "wallpapers" / fname
            if not path_file.exists():
                continue

            try:
                ext_lower = path_file.suffix.lower().strip(".")
                if ext_lower in ("mp4", "webm"):
                    # Only use video if opencv is available; otherwise use first frame as static
                    if self.is_video_available():
                        img = self.first_frame_from_video(path_file)
                        if not img:
                            continue
                        self.screen_manager.main.set_wallpaper_video(str(path_file), img)
                    else:
                        # Fallback: use first frame as static wallpaper
                        img = self.first_frame_from_video(path_file)
                        if not img:
                            continue
                        self.screen_manager.main.wallpaper = img.convert("RGBA")
                        self.screen_manager.main.wallpaper_frames = []
                else:
                    img = self._load_image_with_exif(path_file)
                    if img is None:
                        continue

                    if getattr(img, "is_animated", False):
                        frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                        duration = img.info.get("duration", 100)
                        # Set directly on screen manager to avoid setter clearing frames
                        self.screen_manager.main.wallpaper_frames = frames
                        self.screen_manager.main.wallpaper_index = 0
                        self.screen_manager.main.wallpaper_duration = duration
                        self.screen_manager.main.wallpaper = frames[0]
                    else:
                        self.screen_manager.main.wallpaper = img.convert("RGBA")
                        self.screen_manager.main.wallpaper_frames = []

            except Exception as e:
                print(f"Failed to load wallpaper {fname}: {e}")
                continue

            break

        if not self.screen_manager.main.wallpaper:
            for fname in top_candidates:
                placeholder_file = PLACEHOLDER_DIR / "wallpapers" / fname
                if placeholder_file.exists():
                    try:
                        img = self._load_image_with_exif(placeholder_file)
                        if img is None:
                            continue
                        if getattr(img, "is_animated", False):
                            frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                            duration = img.info.get("duration", 100)
                            self.screen_manager.main.wallpaper_frames = frames
                            self.screen_manager.main.wallpaper_index = 0
                            self.screen_manager.main.wallpaper_duration = duration
                            self.screen_manager.main.wallpaper = frames[0]
                        else:
                            self.screen_manager.main.wallpaper = img.convert("RGBA")
                            self.screen_manager.main.wallpaper_frames = []
                    except Exception:
                        continue
                    break
        
        # Bottom wallpaper (supports GIF/WebP)
        self.wallpaper_bottom = None
        self.wallpaper_bottom_frames = []
        self.wallpaper_bottom_index = 0
        self.wallpaper_bottom_duration = 100

        wallpaper_external_name = self.theme_data.get("wallpaper_external")
        bottom_files_to_try = []
        if wallpaper_external_name:
            ext = Path(wallpaper_external_name).suffix.lower()
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"):
                bottom_files_to_try.append(wallpaper_external_name)
        bottom_files_to_try.extend(bottom_candidates)

        for fname in bottom_files_to_try:
            path_file = self.theme_path / "wallpapers" / fname
            if not path_file.exists():
                continue

            try:
                ext_lower = path_file.suffix.lower().strip(".")
                if ext_lower in ("mp4", "webm"):
                    # Only use video if opencv is available; otherwise use first frame as static
                    if self.is_video_available():
                        img = self.first_frame_from_video(path_file)
                        if not img:
                            continue
                        self.screen_manager.external.set_wallpaper_video(str(path_file), img)
                    else:
                        # Fallback: use first frame as static wallpaper
                        img = self.first_frame_from_video(path_file)
                        if not img:
                            continue
                        self.screen_manager.external.wallpaper = img.convert("RGBA")
                        self.screen_manager.external.wallpaper_frames = []
                else:
                    img = self._load_image_with_exif(path_file)
                    if img is None:
                        continue

                    if getattr(img, "is_animated", False):
                        frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                        duration = img.info.get("duration", 100)
                        # Set directly on screen manager to avoid setter clearing frames
                        self.screen_manager.external.wallpaper_frames = frames
                        self.screen_manager.external.wallpaper_index = 0
                        self.screen_manager.external.wallpaper_duration = duration
                        self.screen_manager.external.wallpaper = frames[0]
                    else:
                        self.screen_manager.external.wallpaper = img.convert("RGBA")
                        self.screen_manager.external.wallpaper_frames = []

            except Exception as e:
                print(f"Failed to load wallpaper {fname}: {e}")
                continue

            break
        
        # Fallback to placeholder for external wallpaper if none found
        if not self.screen_manager.external.wallpaper:
            for fname in bottom_candidates:
                placeholder_file = PLACEHOLDER_DIR / "wallpapers" / fname
                if placeholder_file.exists():
                    try:
                        img = self._load_image_with_exif(placeholder_file)
                        if img is None:
                            continue
                        if getattr(img, "is_animated", False):
                            frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                            duration = img.info.get("duration", 100)
                            self.screen_manager.external.wallpaper_frames = frames
                            self.screen_manager.external.wallpaper_index = 0
                            self.screen_manager.external.wallpaper_duration = duration
                            self.screen_manager.external.wallpaper = frames[0]
                        else:
                            self.screen_manager.external.wallpaper = img.convert("RGBA")
                            self.screen_manager.external.wallpaper_frames = []
                    except Exception:
                        continue
                    break
        
        # -----------------------------
        # Smart folders & Icon overlays with strict max per type
        # -----------------------------
        self.smart_folders.clear()
        self.icon_overlays.clear()
        
        # Inject Default Folder (internal smart folder)
        default_folder_path = ASSETS_DIR / "default folder"
        if default_folder_path.exists():
            color_candidates = [self.default_folder_color, "blue", None]  # None = plain

            icon = hero = logo = None
            hero_frames = None
            hero_duration = 100

            for asset_type in ["icon", "hero", "logo"]:
                found_file = None
                for color in color_candidates:
                    for ext in ("png", "jpg", "jpeg", "webp", "gif"):
                        candidate_file = (
                            default_folder_path / f"{asset_type}_{color}.{ext}" if color else
                            default_folder_path / f"{asset_type}.{ext}"
                        )
                        if candidate_file.exists():
                            found_file = candidate_file
                            try:
                                if asset_type == "icon" and icon is None:
                                    icon = self._load_cached_rgba(candidate_file)
                                elif asset_type == "logo" and logo is None:
                                    logo = self._load_cached_rgba(candidate_file)
                                elif asset_type == "hero" and hero is None:
                                    img = Image.open(candidate_file)
                                    if getattr(img, "is_animated", False):
                                        hero_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                                        hero_duration = img.info.get("duration", 100)
                                        hero = hero_frames[0]
                                    else:
                                        hero = img.convert("RGBA")
                            except Exception as e:
                                print(f"[DEBUG] Failed to load {candidate_file}: {e}")
                            break
                    if found_file:
                        break  # stop checking other colors for this asset_type

            # Only register if we have an icon or hero
            if icon:
                self.smart_folders["internal:default"] = {
                    "icon": icon,
                    "hero": hero,
                    "hero_frames": hero_frames,
                    "hero_index": 0,
                    "hero_duration": hero_duration,
                    "logo": logo,
                    "source": "root",
                    "platform": None,
                    "is_default_folder": True,
                }
            else:
                print("[DEBUG] Default folder not added: no icon found")
        
        remaining_slots = max_grid_items if max_grid_items is not None else self.max_grid_slots

        root_added = 0
        platform_added = 0

        # --- Helper to load a single smart folder ---
        def load_smart_folder_simple(folder_path: Path, source: str, platform: str | None = None):
            nonlocal remaining_slots, root_added, platform_added

            if remaining_slots <= 0:
                return False

            folder_name = folder_path.name

            # ---------------------------------
            # ICON (REQUIRED)
            # ---------------------------------
            icon = None
            for ext in ("png", "jpg", "jpeg", "webp"):
                candidate = folder_path / f"icon.{ext}"
                if candidate.exists():
                    icon = self._load_cached_rgba(candidate, fallback=None)
                    break

            # Skip smart folder entirely if no icon
            if not icon:
                print(f"[WARN] Smart folder skipped (no icon): {folder_path}")
                return False

            # ---------------------------------
            # HERO / LOGO
            # ---------------------------------
            hero = None
            logo = None
            hero_frames = None
            hero_duration = 100
            logo_frames = None
            logo_duration = 100

            for f in folder_path.iterdir():
                fname = f.name.lower()
                suffix = f.suffix.lower()

                # ---- HERO (may be animated) ----
                if fname.startswith("hero") and suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                    try:
                        img = Image.open(f)
                        logo_frames = None # prevents previous loop iterations from leaking animation data if multiple files exist
                        if getattr(img, "is_animated", False):
                            hero_frames = [
                                frame.convert("RGBA")
                                for frame in ImageSequence.Iterator(img)
                            ]
                            hero_duration = img.info.get("duration", 100)
                            hero = hero_frames[0]
                        else:
                            hero = img.convert("RGBA")
                    except Exception:
                        pass

                # ---- LOGO (static only) ----
                elif fname.startswith("logo") and suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                    try:
                        img = Image.open(f)
                        logo_frames = None # prevents previous loop iterations from leaking animation data if multiple files exist
                        if getattr(img, "is_animated", False):
                            logo_frames = [
                                frame.convert("RGBA")
                                for frame in ImageSequence.Iterator(img)
                            ]
                            logo_duration = img.info.get("duration", 100)
                            logo = logo_frames[0]
                        else:
                            logo = self._load_cached_rgba(f, fallback=None)
                    except Exception as e:
                        print(f"[DEBUG] Failed to load logo {f}: {e}")
                        logo = None

            # ---------------------------------
            # REGISTER SMART FOLDER
            # ---------------------------------
            self.smart_folders[f"{source}:{folder_name}"] = {
                "icon": icon,
                "hero": hero,
                "hero_frames": hero_frames,
                "hero_index": 0,
                "hero_duration": hero_duration,
                "logo": logo,
                "logo_frames": logo_frames,
                "logo_index": 0,
                "logo_duration": logo_duration,
                "source": source,
                "platform": platform,
            }

            remaining_slots -= 1

            if source == "root":
                root_added += 1
            elif source == "by_platform":
                platform_added += 1

            return True

        def smart_folder_sort_key(path: Path):
            """
            Favorites always come first, then alphabetical.
            """
            name = path.name.lower()
            is_favorites = (name == "favorites")
            return (0 if is_favorites else 1, name)
        
        # --- Load root smart folders ---
        smart_root = self.theme_path / "smart_folders"
        if smart_root.exists():
            root_folders = [
                item for item in smart_root.iterdir()
                if item.is_dir() and item.name != "by_platform"
            ]

            # Favorites first, others shuffled
            favorites = [f for f in root_folders if f.name.lower() == "favorites"]
            others = [f for f in root_folders if f.name.lower() != "favorites"]
            random.shuffle(others)
            root_folders_shuffled = favorites + others

            for item in root_folders_shuffled:
                if remaining_slots <= 0 or root_added >= self.MAX_ROOT_SMART:
                    break
                load_smart_folder_simple(item, "root")

            # Load by-platform smart folders
            by_platform = smart_root / "by_platform"
            if by_platform.exists():
                platform_dirs = [p for p in by_platform.iterdir() if p.is_dir()]
                random.shuffle(platform_dirs)
                for platform_dir in platform_dirs:
                    if remaining_slots <= 0 or platform_added >= self.MAX_PLATFORM_SMART:
                        break
                    load_smart_folder_simple(platform_dir, "by_platform", platform_dir.name)

        # --- Load icon overlays into memory (1 variant per platform) ---
        icon_dir = self.theme_path / "icon_overlays"

        if icon_dir.exists():
            platform_dirs = [p for p in icon_dir.iterdir() if p.is_dir()]
            random.shuffle(platform_dirs)

            # Group by base platform name (before first underscore)
            platform_groups = {}
            for folder in platform_dirs:
                base_name = folder.name.split("_")[0].lower()
                platform_groups.setdefault(base_name, []).append(folder)

            # Pick one variant per platform
            for base_name, variants in platform_groups.items():
                if remaining_slots <= 0:
                    break

                # Pick a random variant
                chosen_folder = random.choice(variants)

                # Must have both overlay.png AND mask.png
                overlay_path = chosen_folder / "overlay.png"
                mask_path = chosen_folder / "mask.png"
                if not overlay_path.exists() or not mask_path.exists():
                    print(f"[WARN] Icon overlay skipped (missing overlay.png or mask.png): {chosen_folder}")
                    continue  # skip this variant entirely

                # Load images
                overlay = self._load_cached_rgba(overlay_path)
                mask = self._load_cached_rgba(mask_path)
                if not overlay or not mask:
                    print(f"[WARN] Icon overlay skipped (failed to load images): {chosen_folder}")
                    continue  # just in case loading failed

                # Pick random game image variant for this base platform
                game_data = self._get_random_game_image(base_name)
                if game_data and mask:
                    # Create a COPY of the game data to avoid modifying cached images
                    import copy
                    game_data_copy = {
                        "img": game_data["img"].copy() if game_data["img"] else None,
                        "frames": [f.copy() for f in game_data["frames"]] if game_data["frames"] else None,
                        "index": game_data["index"],
                        "duration": game_data["duration"]
                    }
                    # Apply mask to the copy
                    masked_img = self._apply_mask(game_data_copy["img"], mask)
                    game_data_copy["img"] = masked_img
                    # Also apply mask to all frames if animated
                    if game_data_copy["frames"]:
                        game_data_copy["frames"] = [self._apply_mask(f, mask) for f in game_data_copy["frames"]]
                    game_data = game_data_copy

                # Register overlay using base platform name
                self.icon_overlays[base_name] = {
                    "mask": mask,
                    "overlay": overlay,
                    "game_data": game_data,
                }

                remaining_slots -= 1

        # Clamp selection to available items
        if self.grid_items:
            self.selected_index = max(0, min(self.selected_index, len(self.grid_items) - 1))
        
        # Load random app images for bottom screen
        self._load_app_images()
    
    def _load_app_images(self):
        """Load 5 app images from assets/apps folder. First slot is 'app drawer.png' if it exists."""
        apps_dir = ASSETS_DIR / "apps"
        if not apps_dir.exists():
            self._app_images = []
            self._app_images_loaded = True
            return
        
        # Check for app drawer icon first
        app_drawer_path = apps_dir / "app drawer.png"
        app_drawer_img = None
        if app_drawer_path.exists():
            app_drawer_img = self._load_cached_rgba(app_drawer_path)
        
        # Get all image files from apps folder (excluding app drawer)
        app_files = []
        supported_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        for f in apps_dir.iterdir():
            if f.is_file() and f.suffix.lower() in supported_extensions and f.name.lower() != "app drawer.png":
                app_files.append(f)
        
        # Select remaining 4 random images (or fewer if not enough)
        num_to_select = min(4, len(app_files))
        if num_to_select > 0:
            selected = random.sample(app_files, num_to_select)
            self._app_images = []
            # Always put app drawer first if it exists
            if app_drawer_img:
                self._app_images.append(app_drawer_img)
            for f in selected:
                img = self._load_cached_rgba(f)
                if img:
                    self._app_images.append(img)
        else:
            # No other images, just use app drawer if it exists
            self._app_images = [app_drawer_img] if app_drawer_img else []
        
        self._app_images_loaded = True
        self._static_cache_dirty = True
    
    def _invalidate_static_cache(self):
        """Mark static cache as dirty so it rebuilds next render."""
        self._static_cache_dirty = True
        self._cached_clean_content = None
        self._cached_clean_content_size = None
    
    def _draw_border(self, img: Image.Image, rect: Tuple[int, int, int, int], color: Tuple[int, int, int, int], thickness: int = 3):
        """Draw a colored border rectangle on the image."""
        x, y, w, h = rect
        # Skip if rect is outside image bounds
        if x >= img.width or y >= img.height or x + w <= 0 or y + h <= 0:
            return
        for i in range(thickness):
            # Top
            for px in range(max(0, x), min(x + w, img.width)):
                py = y + i
                if 0 <= py < img.height:
                    img.putpixel((px, py), color)
            # Bottom
            for px in range(max(0, x), min(x + w, img.width)):
                py = y + h - 1 - i
                if 0 <= py < img.height:
                    img.putpixel((px, py), color)
            # Left
            for py in range(max(0, y), min(y + h, img.height)):
                px = x + i
                if 0 <= px < img.width:
                    img.putpixel((px, py), color)
            # Right
            for py in range(max(0, y), min(y + h, img.height)):
                px = x + w - 1 - i
                if 0 <= px < img.width:
                    img.putpixel((px, py), color)
    
    def _draw_handle(self, img: Image.Image, x: int, y: int, color: Tuple[int, int, int, int], size: int = 8):
        """Draw a draggable handle dot."""
        # Skip if outside bounds
        if x < -size or x > img.width + size or y < -size or y > img.height + size:
            return
        for dy in range(-size, size + 1):
            for dx in range(-size, size + 1):
                if dx*dx + dy*dy <= size*size:
                    px, py = x + dx, y + dy
                    if 0 <= px < img.width and 0 <= py < img.height:
                        img.putpixel((px, py), color)
        
    # New animation structure
    
    def register_animation(self, key, frames, duration):
        if not frames or len(frames) <= 1:
            return

        self.animations[key] = {
            "frames": frames,
            "duration": duration,
            "index": 0,
            "last_update": time.perf_counter()
        }
    
    def advance_animations(self):
        now = time.perf_counter()

        for anim in self.animations.values():
            if (now - anim["last_update"]) * 1000 >= anim["duration"]:
                anim["index"] = (anim["index"] + 1) % len(anim["frames"])
                anim["last_update"] = now
    
    
    def advance_wallpaper_frame(self):
        if not self.screen_manager.main.wallpaper_frames:
            return
        now = time.perf_counter()
        elapsed = (now - self._last_wallpaper_top_update) * 1000  # ms
        duration = self.screen_manager.main.wallpaper_duration
        # Advance frames to catch up to actual elapsed time
        frames_to_advance = int(elapsed / duration)
        if frames_to_advance > 0:
            for _ in range(frames_to_advance):
                self.screen_manager.main.wallpaper_index = (self.screen_manager.main.wallpaper_index + 1) % len(self.screen_manager.main.wallpaper_frames)
            # Keep the overshoot time for accurate timing
            overshoot = elapsed - (frames_to_advance * duration)
            self._last_wallpaper_top_update = now - (overshoot / 1000)

    def advance_bottom_wallpaper_frame(self):
        if not self.screen_manager.external.wallpaper_frames:
            return
        now = time.perf_counter()
        elapsed = (now - self._last_wallpaper_bottom_update) * 1000
        duration = self.screen_manager.external.wallpaper_duration
        frames_to_advance = int(elapsed / duration)
        if frames_to_advance > 0:
            for _ in range(frames_to_advance):
                self.screen_manager.external.wallpaper_index = (self.screen_manager.external.wallpaper_index + 1) % len(self.screen_manager.external.wallpaper_frames)
            overshoot = elapsed - (frames_to_advance * duration)
            self._last_wallpaper_bottom_update = now - (overshoot / 1000)

    def advance_selected_hero(self):
        """Advance hero animation ONLY for the currently selected grid item."""
        if not self.grid_items or self.selected_index >= len(self.grid_items):
            return
        item = self.grid_items[self.selected_index]
        if not item:
            return
        frames = item.get("hero_frames")
        if not frames:
            return
        now = time.perf_counter()
        
        # --- initialize last update if missing ---
        if self.selected_index not in self._last_hero_update:
            self._last_hero_update[self.selected_index] = now
            return  # skip advancing this tick so timing starts from now

        last_update = self._last_hero_update[self.selected_index]
        duration = item.get("hero_duration", 100)
        elapsed = (now - last_update) * 1000
        frames_to_advance = int(elapsed / duration)
        if frames_to_advance > 0:
            for _ in range(frames_to_advance):
                idx = item.get("hero_index", 0)
                idx = (idx + 1) % len(frames)
                item["hero_index"] = idx
                item["hero"] = frames[idx]
            overshoot = elapsed - (frames_to_advance * duration)
            self._last_hero_update[self.selected_index] = now - (overshoot / 1000)
    
    def advance_selected_logo(self):
        """Advance logo animation if the currently selected grid item has an animated logo."""
        if not self.grid_items or self.selected_index >= len(self.grid_items):
            return

        item = self.grid_items[self.selected_index]
        if not item:
            return

        frames = item.get("logo_frames")
        if not frames:
            return

        now = time.perf_counter()

        if self.selected_index not in self._last_logo_update:
            self._last_logo_update[self.selected_index] = now
            return

        last_update = self._last_logo_update[self.selected_index]
        duration = item.get("logo_duration", 100)
        elapsed = (now - last_update) * 1000
        frames_to_advance = int(elapsed / duration)
        
        if frames_to_advance > 0:
            for _ in range(frames_to_advance):
                idx = item.get("logo_index", 0)
                idx = (idx + 1) % len(frames)
                item["logo_index"] = idx
                item["logo"] = frames[idx]
            overshoot = elapsed - (frames_to_advance * duration)
            self._last_logo_update[self.selected_index] = now - (overshoot / 1000)
    
    def advance_game_images(self):
        """Advance game image animations for all visible grid items."""
        now = time.perf_counter()
        
        for idx, item in enumerate(self.grid_items):
            if not item:
                continue
            
            game_data = item.get("game_data")
            if not game_data or not game_data.get("frames"):
                continue
            
            # Initialize timing if needed
            if idx not in self._last_game_update:
                self._last_game_update[idx] = now
                continue
            
            last_update = self._last_game_update[idx]
            duration = game_data.get("duration", 100)
            elapsed = (now - last_update) * 1000
            frames_to_advance = int(elapsed / duration)
            
            if frames_to_advance > 0:
                for _ in range(frames_to_advance):
                    game_data["index"] = (game_data["index"] + 1) % len(game_data["frames"])
                    game_data["img"] = game_data["frames"][game_data["index"]]
                overshoot = elapsed - (frames_to_advance * duration)
                self._last_game_update[idx] = now - (overshoot / 1000)
    
    def get_background_image(self, canvas_size: tuple[int, int]) -> Image.Image:
        """Get just the background image fitted to canvas (not scaled with zoom)."""
        canvas_w, canvas_h = canvas_size
        
        if self.bezel_img is None:
            return Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        
        # Scale device to fit within canvas minus padding
        scale = min(
            (canvas_w - 2 * self.DEVICE_PADDING) / self.bezel_img.width,
            (canvas_h - 2 * self.DEVICE_PADDING) / self.bezel_img.height
        )
        device_w = round(self.bezel_img.width * scale)
        device_h = round(self.bezel_img.height * scale)
        device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
        device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2
        
        # Create base and fit background
        base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        self._fit_background(base, self.bg_img, (canvas_w, canvas_h), (device_x, device_y, device_w, device_h))
        return base
    
    def _update_handle_positions(self, canvas_size: tuple[int, int]):
        """Update handle positions for click detection without rendering.
        
        This is called when using cached content to ensure handle positions
        are available for click detection.
        """
        if not self.bezel_edit_mode or not self.bezel_img:
            self._screen_handles = {'main': [], 'external': []}
            return
            
        canvas_w, canvas_h = canvas_size
        
        # Calculate scale and positions
        scale = min(
            (canvas_w - 2 * self.DEVICE_PADDING) / self.bezel_img.width,
            (canvas_h - 2 * self.DEVICE_PADDING) / self.bezel_img.height
        )
        self._bezel_fit_scale = scale
        device_w = round(self.bezel_img.width * scale)
        device_h = round(self.bezel_img.height * scale)
        device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
        device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2
        
        main_screen = self.screen_manager.main
        external_screen = self.screen_manager.external
        
        # Main screen handles
        main_rect = (
            device_x + round(main_screen.x * scale),
            device_y + round(main_screen.y * scale),
            round(main_screen.w * scale),
            round(main_screen.h * scale)
        )
        mx, my, mw, mh = main_rect
        show_main_handles = self.screen_manager.screen_mode != "single"
        
        if mw > 0 and mh > 0 and show_main_handles:
            self._screen_handles = {
                'main': [
                    ('tl', mx, my),
                    ('tr', mx + mw, my),
                    ('bl', mx, my + mh),
                    ('br', mx + mw, my + mh),
                    ('top', mx + mw//2, my),
                    ('bottom', mx + mw//2, my + mh),
                    ('left', mx, my + mh//2),
                    ('right', mx + mw, my + mh//2),
                ],
                'external': []
            }
        else:
            self._screen_handles = {'main': [], 'external': []}
        
        # External screen handles
        ext_rect = (
            device_x + round(external_screen.x * scale),
            device_y + round(external_screen.y * scale),
            round(external_screen.w * scale),
            round(external_screen.h * scale)
        )
        ex, ey, ew, eh = ext_rect
        self._screen_handles['external'] = [
            ('tl', ex, ey),
            ('tr', ex + ew, ey),
            ('bl', ex, ey + eh),
            ('br', ex + ew, ey + eh),
            ('top', ex + ew//2, ey),
            ('bottom', ex + ew//2, ey + eh),
            ('left', ex, ey + eh//2),
            ('right', ex + ew, ey + eh//2),
        ]
    
    # Rendering
    def composite(self, canvas_size: tuple[int, int], skip_background: bool = False, skip_magnify: bool = False, skip_handles: bool = False, skip_borders: bool = False) -> Image.Image:
        canvas_w, canvas_h = canvas_size

        # Always compare with last static cache size
        canvas_resized = self._static_cache_size != canvas_size

        # Force rebuild if canvas size changed
        if canvas_resized:
            self._static_cache_dirty = True

        # Update last canvas size for animation tracking
        self._last_canvas_size = canvas_size
        
        # Set magnify skip flag for this render
        self._skip_magnify_render = skip_magnify

        # Check for cached clean content (used by magnify window)
        # Clean content = content without borders/handles, so it can be reused
        # Only use cache if skip_background is also True (we need background for magnify)
        wants_clean = skip_borders and skip_handles
        if wants_clean and skip_background and self._cached_clean_content is not None and self._cached_clean_content_size == canvas_size:
            # Still need to update handle positions for click detection even when using cached content
            self._update_handle_positions(canvas_size)
            return self._cached_clean_content.copy()
        
        # Always update handle positions when in bezel edit mode (needed for click detection)
        # even when skipping borders/handles for rendering
        if self.bezel_edit_mode and wants_clean:
            self._update_handle_positions(canvas_size)

        # Build static cache if needed
        if self._static_cache_image is None or self._static_cache_dirty or self._static_cache_size != canvas_size:
            static_base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

            # Handle hidden frame
            if self.bezel_img is None:
                return static_base

            # Scale device to fit within canvas minus padding
            scale = min(
                (canvas_w - 2 * self.DEVICE_PADDING) / self.bezel_img.width,
                (canvas_h - 2 * self.DEVICE_PADDING) / self.bezel_img.height
            )
            device_w = round(self.bezel_img.width * scale)
            device_h = round(self.bezel_img.height * scale)
            device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
            device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2

            # Background (fitted or stretched based on device position)
            if not skip_background:
                self._fit_background(static_base, self.bg_img, (canvas_w, canvas_h), (device_x, device_y, device_w, device_h))

            def paste(img, x, y, w, h):
                if not img:
                    return
                key = (id(img), w, h)
                resized = self._resize_cache.get(key)
                if resized is None:
                    resized = img.resize((w, h), Image.Resampling.BILINEAR)
                    self._resize_cache[key] = resized
                static_base.alpha_composite(resized, (x, y))

            # Frame (static) - skip if hidden
            if not self.frame_hidden:
                paste(self.bezel_img, device_x, device_y, device_w, device_h)

            # Store static cache
            self._static_cache_image = static_base
            self._static_cache_size = canvas_size
            self._static_cache_dirty = False

        # Start from cached static image
        base = self._static_cache_image.copy()

        if skip_background:
            # Clear the background area to fully transparent
            transparent_bg = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            # Only paste non-background content on top
            # We assume the frame/UI will still be composited later
            base = transparent_bg

        # Scale device to fit (for wallpaper/grid)
        scale = min(
            (canvas_w - 2 * self.DEVICE_PADDING) / self.bezel_img.width,
            (canvas_h - 2 * self.DEVICE_PADDING) / self.bezel_img.height
        )
        device_w = round(self.bezel_img.width * scale)
        device_h = round(self.bezel_img.height * scale)
        device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
        device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2

        self.screen_manager.set_frame_scale(scale)

        main_screen = self.screen_manager.main
        external_screen = self.screen_manager.external

        def paste(img, x, y, w, h):
            if not img:
                return
            key = (id(img), w, h)
            resized = self._resize_cache.get(key)
            if resized is None:
                # Use NEAREST during zoom for speed, BILINEAR otherwise
                resample = Image.Resampling.NEAREST if self._zoom_anim_start is not None else Image.Resampling.BILINEAR
                resized = img.resize((w, h), resample)
                self._resize_cache[key] = resized
            base.alpha_composite(resized, (x, y))

        # Bottom wallpaper
        ext_wallpaper = external_screen.get_current_wallpaper()
        if ext_wallpaper:
            paste(ext_wallpaper,
                  device_x + round(external_screen.x * scale),
                  device_y + round(external_screen.y * scale),
                  round(external_screen.w * scale),
                  round(external_screen.h * scale))

        # Animated top wallpaper (only in dual screen mode - single screen is handled at end)
        if self.screen_manager.screen_mode == "dual":
            main_wallpaper = main_screen.get_current_wallpaper()
            if main_screen.w > 0 and main_screen.h > 0 and main_wallpaper:
                paste(main_wallpaper,
                      device_x + round(main_screen.x * scale),
                      device_y + round(main_screen.y * scale),
                      round(main_screen.w * scale),
                      round(main_screen.h * scale))

        # Debug: draw colored borders around screens
        if self.draw_debug_borders or self.bezel_edit_mode:
            main_rect = (
                device_x + round(main_screen.x * scale),
                device_y + round(main_screen.y * scale),
                round(main_screen.w * scale),
                round(main_screen.h * scale)
            )
            ext_rect = (
                device_x + round(external_screen.x * scale),
                device_y + round(external_screen.y * scale),
                round(external_screen.w * scale),
                round(external_screen.h * scale)
            )
            
            # Debug mode (not bezel edit)
            if self.draw_debug_borders and not self.bezel_edit_mode:
                grid_rect_raw = external_screen.get_grid_rect(scale)
                grid_rect = (
                    device_x + grid_rect_raw[0],
                    device_y + grid_rect_raw[1],
                    grid_rect_raw[2],
                    grid_rect_raw[3]
                )
                
                # Draw cyan border around main screen (5px thick)
                if not skip_borders:
                    self._draw_border(base, main_rect, (0, 255, 255, 255), 5)
                    # Draw yellow border around external screen
                    self._draw_border(base, ext_rect, (255, 255, 0, 255), 5)
                
                # Draw drag handles - corners and edges
                if self.debug_drag_mode and not skip_handles:
                    # Main screen (cyan) - corners and edges
                    mx, my, mw, mh = main_rect
                    for hx in [mx, mx + mw]:
                        for hy in [my, my + mh]:
                            self._draw_handle(base, hx, hy, (0, 255, 255, 255), 8)
                    # Edges
                    self._draw_handle(base, mx + mw//2, my, (0, 255, 255, 255), 8)
                    self._draw_handle(base, mx + mw//2, my + mh, (0, 255, 255, 255), 8)
                    self._draw_handle(base, mx, my + mh//2, (0, 255, 255, 255), 8)
                    self._draw_handle(base, mx + mw, my + mh//2, (0, 255, 255, 255), 8)
                    # Center (move)
                    self._draw_handle(base, mx + mw//2, my + mh//2, (0, 255, 255, 255), 12)
                    
                    # External screen (yellow) - corners and edges
                    ex, ey, ew, eh = ext_rect
                    for hx in [ex, ex + ew]:
                        for hy in [ey, ey + eh]:
                            self._draw_handle(base, hx, hy, (255, 255, 0, 255), 8)
                    self._draw_handle(base, ex + ew//2, ey, (255, 255, 0, 255), 8)
                    self._draw_handle(base, ex + ew//2, ey + eh, (255, 255, 0, 255), 8)
                    self._draw_handle(base, ex, ey + eh//2, (255, 255, 0, 255), 8)
                    self._draw_handle(base, ex + ew, ey + eh//2, (255, 255, 0, 255), 8)
                    # Center (move)
                    self._draw_handle(base, ex + ew//2, ey + eh//2, (255, 255, 0, 255), 12)

        # Grid placement (squared & centered)
        # get_grid_rect returns position relative to frame, need to add device offset
        main_screen = self.screen_manager.main
        external_screen = self.screen_manager.external
        grid_rect_raw = external_screen.get_grid_rect(scale)
        
        # Check if we're in single screen stacked mode (top screen visible)
        # This is when user has 1 screen selected AND stacked mode is enabled
        is_single_stacked = (self._display_mode == "single" and self._single_screen_stacked)
        
        # Check for manual grid adjustment from handles
        has_manual_grid = (hasattr(self, '_manual_grid_override') and 
                          self._manual_grid_override and 
                          is_single_stacked)
        
        # Default grid position from get_grid_rect (includes padding)
        grid_x = device_x + grid_rect_raw[0]
        grid_y = device_y + grid_rect_raw[1]
        grid_w, grid_h = grid_rect_raw[2], grid_rect_raw[3]
        
        if has_manual_grid:
            # Use manually adjusted grid values from handles
            grid_x = self._last_grid_x
            grid_y = self._last_grid_y
            grid_w = self._last_grid_w
            grid_h = self._last_grid_h
        elif is_single_stacked:
            # Single screen stacked mode - use scalable lookup table
            # Scale factor determines what portion of full grid area to use
            rows = self.GRID_ROWS
            lookup = self._stacked_lookup.get(rows, {})
            scale_factor = lookup.get("scale_factor", 0.35)
            
            # Calculate target height as portion of available grid area
            original_h = grid_rect_raw[3]
            target_h = int(original_h * scale_factor)
            target_h = max(target_h, 50)
            
            # Anchor at bottom - move grid down by the difference
            shrink = original_h - target_h
            grid_y = grid_y + shrink
            grid_h = target_h

        # Store grid dimensions for zoom animation calculations
        self._last_grid_w = grid_w
        self._last_grid_h = grid_h
        self._last_grid_x = grid_x
        self._last_grid_y = grid_y
        
        # Clear grid handles when not in bezel edit mode
        if not self.bezel_edit_mode:
            self._grid_handles = []

        # Update zoom animation
        if self._zoom_anim_start is not None:
            now = time.perf_counter()
            elapsed = now - self._zoom_anim_start
            t = min(elapsed / self._zoom_anim_duration, 1.0)
            
            # Smoothstep easing
            t = t * t * (3 - 2 * t)
            
            if self._zoom_anim_from and self._zoom_anim_to:
                from_rows, from_cols = self._zoom_anim_from
                to_rows, to_cols = self._zoom_anim_to
                
                self._current_grid_rows = from_rows + (to_rows - from_rows) * t
                self._current_grid_cols = from_cols + (to_cols - from_cols) * t
                
                if t >= 1.0:
                    self._current_grid_rows = to_rows
                    self._current_grid_cols = to_cols
                    self._zoom_anim_start = None
                    self._zoom_item_positions = {}  # Clear cached positions
                    self._zoom_ended_needs_snap = True  # Continue selection animation after zoom

        # Animate scroll position
        if self._grid_scroll_start is not None:
            now = time.perf_counter()
            elapsed = now - self._grid_scroll_start
            t = min(elapsed / self._grid_scroll_duration, 1.0)
            
            # Smoothstep easing
            t = t * t * (3 - 2 * t)
            
            # Interpolate from start to target
            if hasattr(self, '_grid_scroll_from'):
                self.grid_scroll_x = self._grid_scroll_from + (self._grid_scroll_target - self._grid_scroll_from) * t
            
            if t >= 1.0:
                self.grid_scroll_x = self._grid_scroll_target
                self._grid_scroll_start = None

        # Use current grid size for rendering
        target_rows = self.GRID_ROWS
        target_cols = self.GRID_COLS
        
        # Animate cell sizes during zoom using cached values
        if self._zoom_anim_start is not None and self._zoom_from_cell_w > 0:
            # Interpolate using cached cell sizes
            from_rows, from_cols = self._zoom_anim_from
            progress = (self._current_grid_rows - from_rows) / (self.GRID_ROWS - from_rows) if self.GRID_ROWS != from_rows else 1.0
            # Round to nearest 2px to reduce resize operations during zoom
            cell_w = round((self._zoom_from_cell_w + (self._zoom_to_cell_w - self._zoom_from_cell_w) * progress) / 2) * 2
            cell_h = round((self._zoom_from_cell_h + (self._zoom_to_cell_h - self._zoom_from_cell_h) * progress) / 2) * 2
        else:
            # Calculate cell sizes based on current visible grid size (rows AND cols)
            avail_w = grid_w - 2 * self.GRID_OUTER_PADDING - (self.GRID_COLS - 1) * self.GRID_PADDING
            avail_h = grid_h - 2 * self.GRID_OUTER_PADDING - (self.GRID_ROWS - 1) * self.GRID_PADDING
            cell_w = round(avail_w / self.GRID_COLS)
            cell_h = round(avail_h / self.GRID_ROWS)
        
        # Store full cell width for scroll calculations
        self._full_cell_width = cell_w
        
        # Build grid items first (needed to know which items go where)
        # Only rebuild if dirty (grid size changed)
        if self._grid_items_dirty:
            self.grid_items = []
            remaining_slots = self.MAX_TOTAL_SLOTS  # Always build max items

            root_added = 0
            platform_added = 0

            # --- Add default folder first ---
            default_folder = self.smart_folders.get("internal:default")
            if default_folder:
                self.grid_items.append(default_folder)
                remaining_slots -= 1
                root_added += 1

            # --- Add favorites root folder ---
            for key, data in self.smart_folders.items():
                if key == "internal:default":
                    continue
                if remaining_slots <= 0 or root_added >= self.MAX_ROOT_SMART:
                    break
                if data.get("source") == "root" and key.lower().endswith("favorites"):
                    self.grid_items.append(data)
                    root_added += 1
                    remaining_slots -= 1

            # --- Add other root smart folders ---
            for key, data in self.smart_folders.items():
                if key == "internal:default":
                    continue
                if remaining_slots <= 0 or root_added >= self.MAX_ROOT_SMART:
                    break
                if data.get("source") == "root" and data not in self.grid_items:
                    self.grid_items.append(data)
                    root_added += 1
                    remaining_slots -= 1

            # --- Add platform smart folders ---
            for key, data in self.smart_folders.items():
                if remaining_slots <= 0 or platform_added >= self.MAX_PLATFORM_SMART:
                    break
                if data.get("source") == "by_platform":
                    self.grid_items.append(data)
                    platform_added += 1
                    remaining_slots -= 1

            # --- Fill remaining slots with icon overlays ---
            for overlay_data in self.icon_overlays.values():
                if remaining_slots <= 0:
                    break
                game_data = overlay_data.get("game_data")
                self.grid_items.append({
                    "icon": overlay_data["overlay"],
                    "game_data": game_data,
                    "hero": None,
                    "logo": None,
                })
                remaining_slots -= 1

            # --- Fill leftover slots with empty.png if user allows ---
            if getattr(self, "show_empty_slots", True) and remaining_slots > 0:
                empty_path = ASSETS_DIR / "empty.png"
                if empty_path.exists():
                    empty_grid_image = self._load_cached_rgba(empty_path)
                else:
                    # fallback: transparent placeholder so program doesn't crash
                    empty_grid_image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))

                # Fill remaining slots
                while remaining_slots > 0:
                    self.grid_items.append({
                        "icon": empty_grid_image,
                        "hero": None,
                        "hero_frames": None,
                        "hero_index": 0,
                        "hero_duration": 100,
                        "logo": None,
                        "logo_frames": None,
                        "logo_index": 0,
                        "logo_duration": 100,
                        "source": "empty",
                        "platform": None,
                    })
                    remaining_slots -= 1
            
            self._grid_items_dirty = False
            
            # Clamp selection to available items after rebuild
            if self.grid_items:
                self.selected_index = max(0, min(self.selected_index, len(self.grid_items) - 1))
        
        # Now calculate grid positions for ALL items (never use 0,0,0,0)
        self.grid_positions = []       # visual squares
        self.grid_click_regions = []   # full rectangles

        # Use current zoom level rows for layout (items expand right, not down)
        current_rows = self.GRID_ROWS
        scroll_offset = round(self.grid_scroll_x)

        for idx in range(len(self.grid_items)):
            # Column-major order: fill top-to-bottom, then move right
            col = idx // current_rows
            row = idx % current_rows

            # Apply scroll offset for extended grid (round to int for rendering)
            rect_x = grid_x + self.GRID_OUTER_PADDING + col * (cell_w + self.GRID_PADDING) - scroll_offset
            rect_y = grid_y + self.GRID_OUTER_PADDING + row * (cell_h + self.GRID_PADDING)

            # Store full rectangle for clicking
            self.grid_click_regions.append((rect_x, rect_y, cell_w, cell_h))

            # Now shrink to square (visual only)
            size = min(cell_w, cell_h)

            cx = rect_x + cell_w // 2
            cy = rect_y + cell_h // 2

            square_x = cx - size // 2
            square_y = cy - size // 2

            # Interpolate from cached position during zoom
            if self._zoom_anim_start is not None and idx in self._zoom_item_positions:
                from_x, from_y, from_w, from_h = self._zoom_item_positions[idx]
                # Calculate zoom progress
                if self._zoom_anim_from and self._zoom_anim_to:
                    from_rows, from_cols = self._zoom_anim_from
                    progress = (self._current_grid_rows - from_rows) / (self.GRID_ROWS - from_rows) if self.GRID_ROWS != from_rows else 1.0
                    # Interpolate position
                    interp_x = round(from_x + (square_x - from_x) * progress)
                    interp_y = round(from_y + (square_y - from_y) * progress)
                    interp_size = round(from_w + (size - from_w) * progress)
                    self.grid_positions.append((interp_x, interp_y, interp_size, interp_size))
                else:
                    self.grid_positions.append((square_x, square_y, size, size))
            else:
                # For new items (not in cache), start from off-screen right during zoom out
                if self._zoom_anim_start is not None and self._zoom_anim_from and self._zoom_anim_to:
                    from_rows, from_cols = self._zoom_anim_from
                    # If grid is getting larger (zooming out), new items come from right
                    if self.GRID_ROWS > from_rows or self.GRID_COLS > from_cols:
                        # Use animation time for progress (same as cell size animation)
                        now = time.perf_counter()
                        elapsed = now - self._zoom_anim_start
                        t = min(elapsed / self._zoom_anim_duration, 1.0)
                        # Smoothstep easing
                        progress = t * t * (3 - 2 * t)
                        # Start from off-screen right
                        start_x = grid_x + grid_w + 50
                        interp_x = round(start_x + (square_x - start_x) * progress)
                        self.grid_positions.append((interp_x, square_y, size, size))
                    else:
                        self.grid_positions.append((square_x, square_y, size, size))
                else:
                    self.grid_positions.append((square_x, square_y, size, size))
        
        # -------------------------------------------------
        # COLUMN-BASED GRID SHIFT (Animated, smooth)
        # Only apply when not scrolled beyond first visible columns
        # -------------------------------------------------
        if self.ENABLE_COLUMN_SHIFT and self.GRID_COLS > 1 and self.grid_scroll_x == 0:

            animated_index = self.selected_index
            # Column-major: col = idx // rows
            animated_col = animated_index // self.GRID_ROWS
            
            # Only shift based on visible columns
            visible_col = min(animated_col, self.GRID_COLS - 1)
            column_progress = visible_col / (self.GRID_COLS - 1) if self.GRID_COLS > 1 else 0

            # Convert to -1 → +1 range (reversed direction)
            normalized = -((column_progress - 0.5) * 2)

            # Determine full grid bounds
            min_x = min(p[0] for p in self.grid_positions)
            max_x = max(p[0] + p[2] for p in self.grid_positions)
            grid_width = max_x - min_x

            available_space = max(0, grid_w - grid_width)
            half_shift = available_space / 2

            target_shift = normalized * half_shift * self.COLUMN_SHIFT_STRENGTH

            now = time.perf_counter()

            # Start new animation if target changed
            if self._grid_shift_to != target_shift:
                self._grid_shift_from = self._grid_shift_current
                self._grid_shift_to = target_shift
                self._grid_shift_start = now

                # Match selection animation timing
                self._grid_shift_duration = self.GRID_SHIFT_DURATION # Change to self._sel_anim_duration to match that

            # Animate
            if self._grid_shift_start is not None:
                t = (now - self._grid_shift_start) / self._grid_shift_duration
                t = min(t, 1.0)

                # Smoothstep easing (same as selection)
                t = t * t * (3 - 2 * t)

                self._grid_shift_current = (
                    self._grid_shift_from +
                    (self._grid_shift_to - self._grid_shift_from) * t
                )

                if t >= 1.0:
                    self._grid_shift_current = self._grid_shift_to
                    self._grid_shift_start = None

            # Apply animated shift
            shift_amount = int(self._grid_shift_current)

            self.grid_positions = [
                (x + shift_amount, y, w, h)
                for (x, y, w, h) in self.grid_positions
            ]
        
        top_screen_overlay = None
        
        # Selection animation (distance-aware slide)
        if not self.grid_positions or self.selected_index >= len(self.grid_positions):
            return base
        
        target_x, target_y, target_w, target_h = self.grid_positions[self.selected_index]
        now = time.perf_counter()

        # Reset hero animation on selection change
        if self._selected_last_index != self.selected_index:
            if 0 <= self.selected_index < len(self.grid_items):
                item = self.grid_items[self.selected_index]
                if item and item.get("hero_frames"):
                    item["hero_index"] = 0
                    item["hero"] = item["hero_frames"][0]

            self._selected_last_index = self.selected_index

        # Snap instantly on resize
        if canvas_resized or self._selected_anim_x is None:
            self._selected_anim_x = target_x
            self._selected_anim_y = target_y
            self._selected_anim_w = target_w
            self._selected_anim_h = target_h
            self._sel_anim_from = None
            self._sel_anim_to = None
            self._sel_anim_start = None

        else:
            target = (target_x, target_y, target_w, target_h)

            # During zoom or after zoom ended, use lerp to smoothly follow the grid
            if self._zoom_anim_start is not None or self._zoom_ended_needs_snap:
                lerp_speed = 0.4  # Smooth following
                self._selected_anim_x = self._selected_anim_x + (target_x - self._selected_anim_x) * lerp_speed
                self._selected_anim_y = self._selected_anim_y + (target_y - self._selected_anim_y) * lerp_speed
                self._selected_anim_w = self._selected_anim_w + (target_w - self._selected_anim_w) * lerp_speed
                self._selected_anim_h = self._selected_anim_h + (target_h - self._selected_anim_h) * lerp_speed
                self._sel_anim_to = target
                # Snap to exact position if very close
                if (abs(self._selected_anim_x - target_x) < 0.5 and 
                    abs(self._selected_anim_y - target_y) < 0.5):
                    self._selected_anim_x = target_x
                    self._selected_anim_y = target_y
                    self._selected_anim_w = target_w
                    self._selected_anim_h = target_h
                    self._zoom_ended_needs_snap = False
            # Snap to target if close enough
            elif (abs(self._selected_anim_x - target_x) < 1 and 
                  abs(self._selected_anim_y - target_y) < 1 and
                  abs(self._selected_anim_w - target_w) < 1 and 
                  abs(self._selected_anim_h - target_h) < 1):
                self._selected_anim_x = target_x
                self._selected_anim_y = target_y
                self._selected_anim_w = target_w
                self._selected_anim_h = target_h
                self._sel_anim_to = target
            # Normal selection animation
            elif self._sel_anim_to != target:
                self._sel_anim_from = (
                    self._selected_anim_x,
                    self._selected_anim_y,
                    self._selected_anim_w,
                    self._selected_anim_h,
                )
                self._sel_anim_to = target
                self._sel_anim_start = now

                # Distance-aware duration
                dx = target_x - self._sel_anim_from[0]
                dy = target_y - self._sel_anim_from[1]
                distance = (dx * dx + dy * dy) ** 0.5
                cell_diag = (target_w * target_w + target_h * target_h) ** 0.5
                base_duration = self.BASE_SEL_ANIM_DURATION
                max_duration = self.MAX_SEL_ANIM_DURATION
                factor = max(1.0, distance / cell_diag) if cell_diag > 0 else 1.0
                self._sel_anim_duration = min(max_duration, base_duration * factor)

            # Animate
            if self._sel_anim_start is not None:
                t = (now - self._sel_anim_start) / self._sel_anim_duration
                t = min(t, 1.0)

                # Smoothstep easing (glide, no spring)
                t = t * t * (3 - 2 * t)

                fx, fy, fw, fh = self._sel_anim_from
                tx, ty, tw, th = self._sel_anim_to

                self._selected_anim_x = fx + (tx - fx) * t
                self._selected_anim_y = fy + (ty - fy) * t
                self._selected_anim_w = fw + (tw - fw) * t
                self._selected_anim_h = fh + (th - fh) * t

                if t >= 1.0:
                    self._selected_anim_x = tx
                    self._selected_anim_y = ty
                    self._selected_anim_w = tw
                    self._selected_anim_h = th
                    self._sel_anim_start = None
                    
        # Draw selected highlight FIRST (behind icons)
        if self.selected_img:
            paste(
                self.selected_img,
                round(self._selected_anim_x) if self._selected_anim_x is not None else 0,
                round(self._selected_anim_y) if self._selected_anim_y is not None else 0,
                round(self._selected_anim_w) if self._selected_anim_w is not None else 0,
                round(self._selected_anim_h) if self._selected_anim_h is not None else 0,
            )

        # Draw grid items ON TOP (lazy rendering - only visible items)
        grid_right = grid_x + grid_w

        for idx, item in enumerate(self.grid_items):
            if not item:
                continue
            
            if idx >= len(self.grid_positions):
                continue

            x, y, w, h = self.grid_positions[idx]
            
            # Skip if item is completely off-screen (lazy rendering)
            if x + w < grid_x or x > grid_right:
                continue

            # Determine what type of item this is
            is_default_folder = item.get("is_default_folder")
            is_smart_folder = item.get("source") in ("root", "by_platform")
            is_icon_overlay = item.get("game_data") is not None

            # Choose scale
            if is_default_folder:
                content_scale = self.DEFAULT_FOLDER_SCALE
            elif is_smart_folder:
                content_scale = self.SMART_FOLDER_SCALE
            elif is_icon_overlay:
                content_scale = self.ICON_OVERLAY_SCALE
            else:
                content_scale = 1.0

            # Apply scaling
            content_w = int(w * content_scale)
            content_h = int(h * content_scale)

            content_x = x + (w - content_w) // 2
            content_y = y + (h - content_h) // 2

            # Draw game image first (if exists)
            game_data = item.get("game_data")
            if game_data:
                paste(game_data["img"], content_x, content_y, content_w, content_h)

            # Draw icon on top
            if item.get("icon"):
                paste(item["icon"], content_x, content_y, content_w, content_h)

            if idx == self.selected_index:
                top_screen_overlay = item
                
        # Top screen hero/logo (only in dual screen mode - single screen is handled at end)
        if top_screen_overlay and main_screen.w > 0 and main_screen.h > 0 and self.screen_manager.screen_mode == "dual":
            top_x = device_x + round(main_screen.x * scale)
            top_y = device_y + round(main_screen.y * scale)
            top_w = round(main_screen.w * scale)
            top_h = round(main_screen.h * scale)

            # Hero - fit to width, center vertically (rendered first, behind logo)
            if top_screen_overlay.get("hero"):
                hero = top_screen_overlay["hero"]
                hero_w, hero_h = hero.size
                
                # Scale to fit width
                scale_hero = top_w / hero_w
                new_w = top_w
                new_h = int(hero_h * scale_hero)
                
                # Center vertically
                hero_x = top_x
                hero_y = top_y + (top_h - new_h) // 2
                
                # Resize hero
                key = (id(hero), new_w, new_h)
                hero_resized = self._resize_cache.get(key)
                if hero_resized is None:
                    hero_resized = hero.resize((new_w, new_h), Image.Resampling.BILINEAR)
                    self._resize_cache[key] = hero_resized
                
                # Clip hero to screen bounds
                mask = Image.new("L", (new_w, new_h), 0)
                draw = ImageDraw.Draw(mask)
                clip_x1 = max(0, top_x - hero_x)
                clip_y1 = max(0, top_y - hero_y)
                clip_x2 = min(new_w, top_x + top_w - hero_x)
                clip_y2 = min(new_h, top_y + top_h - hero_y)
                draw.rectangle([clip_x1, clip_y1, clip_x2, clip_y2], fill=255)
                masked_hero = Image.composite(hero_resized, Image.new("RGBA", (new_w, new_h), 0), mask)
                base.alpha_composite(masked_hero, (hero_x, hero_y))

            # Logo (rendered after hero, on top)
            if top_screen_overlay.get("logo"):
                logo = top_screen_overlay["logo"]

                # Preserve aspect ratio for default folder (fixed scale)
                if top_screen_overlay.get("is_default_folder"):
                    logo_w, logo_h = logo.size

                    scale_fit = min(top_w / logo_w, top_h / logo_h) * 0.56

                    new_w = int(logo_w * scale_fit)
                    new_h = int(logo_h * scale_fit)

                    key = (id(logo), new_w, new_h)
                    resized = self._resize_cache.get(key)
                    if resized is None:
                        resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        self._resize_cache[key] = resized

                    paste_x = top_x + (top_w - new_w) // 2
                    paste_y = top_y + (top_h - new_h) // 2 - int(top_h * 0.1025)

                    # Mask to top screen bounds
                    mask = Image.new("L", (new_w, new_h), 0)
                    draw = ImageDraw.Draw(mask)
                    clip_x1 = max(0, top_x - paste_x)
                    clip_y1 = max(0, top_y - paste_y)
                    clip_x2 = min(new_w, top_x + top_w - paste_x)
                    clip_y2 = min(new_h, top_y + top_h - paste_y)
                    if clip_x2 > clip_x1 and clip_y2 > clip_y1:
                        draw.rectangle([clip_x1, clip_y1, clip_x2, clip_y2], fill=255)
                        masked_logo = Image.composite(resized, Image.new("RGBA", (new_w, new_h), 0), mask)
                        base.alpha_composite(masked_logo, (paste_x, paste_y))
                    else:
                        base.alpha_composite(resized, (paste_x, paste_y))
                else:
                    # Other folders use configurable scale
                    logo_w, logo_h = logo.size

                    scale_fit = min(top_w / logo_w, top_h / logo_h) * self.top_screen_icon_scale

                    new_w = int(logo_w * scale_fit)
                    new_h = int(logo_h * scale_fit)

                    key = (id(logo), new_w, new_h)
                    resized = self._resize_cache.get(key)
                    if resized is None:
                        resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        self._resize_cache[key] = resized

                    paste_x = top_x + (top_w - new_w) // 2
                    paste_y = top_y + (top_h - new_h) // 2

                    # Mask to top screen bounds
                    mask = Image.new("L", (new_w, new_h), 0)
                    draw = ImageDraw.Draw(mask)
                    clip_x1 = max(0, top_x - paste_x)
                    clip_y1 = max(0, top_y - paste_y)
                    clip_x2 = min(new_w, top_x + top_w - paste_x)
                    clip_y2 = min(new_h, top_y + top_h - paste_y)
                    if clip_x2 > clip_x1 and clip_y2 > clip_y1:
                        draw.rectangle([clip_x1, clip_y1, clip_x2, clip_y2], fill=255)
                        masked_logo = Image.composite(resized, Image.new("RGBA", (new_w, new_h), 0), mask)
                        base.alpha_composite(masked_logo, (paste_x, paste_y))
                    else:
                        base.alpha_composite(resized, (paste_x, paste_y))

        # Render main screen on top in single screen STACKED mode only
        if (self.screen_manager.screen_mode == "single" and 
            self._single_screen_stacked and 
            main_screen.w > 0 and main_screen.h > 0):
            main_x = device_x + round(main_screen.x * scale)
            main_y = device_y + round(main_screen.y * scale)
            main_w = round(main_screen.w * scale)
            main_h = round(main_screen.h * scale)
            
            ext_x = device_x + round(external_screen.x * scale)
            ext_y = device_y + round(external_screen.y * scale)
            ext_w = round(external_screen.w * scale)
            ext_h = round(external_screen.h * scale)
            
            # Single screen mode wallpaper
            main_wallpaper = main_screen.get_current_wallpaper()
            if main_wallpaper and self.ss_mask:
                # Resize ss_mask to main screen size
                mask_key = (id(self.ss_mask), main_w, main_h)
                screen_mask = self._resize_cache.get(mask_key)
                if screen_mask is None:
                    screen_mask = self.ss_mask.resize((main_w, main_h), Image.Resampling.LANCZOS)
                    if screen_mask.mode == "RGBA":
                        screen_mask = screen_mask.split()[3]
                    elif screen_mask.mode != "L":
                        screen_mask = screen_mask.convert("L")
                    self._resize_cache[mask_key] = screen_mask
                
                # Create bottom screen mask for clipping
                bottom_mask = Image.new("L", (main_w, main_h), 0)
                draw = ImageDraw.Draw(bottom_mask)
                overlap_x1 = max(0, ext_x - main_x)
                overlap_y1 = max(0, ext_y - main_y)
                overlap_x2 = min(main_w, ext_x + ext_w - main_x)
                overlap_y2 = min(main_h, ext_y + ext_h - main_y)
                if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                    draw.rectangle([overlap_x1, overlap_y1, overlap_x2, overlap_y2], fill=255)
                
                # Combine masks
                combined_mask = ImageChops.multiply(screen_mask, bottom_mask)
                
                # Resize wallpaper to fit
                wallpaper_resized = main_wallpaper.resize((main_w, main_h), Image.Resampling.BILINEAR)
                masked_wallpaper = Image.composite(wallpaper_resized, Image.new("RGBA", (main_w, main_h), 0), combined_mask)
                base.alpha_composite(masked_wallpaper, (main_x, main_y))
            
            # Draw hero/logo on top of wallpaper in single screen mode
            if top_screen_overlay and self.ss_mask:
                # Get ss_mask resized to main screen size
                mask_key = (id(self.ss_mask), main_w, main_h)
                screen_mask = self._resize_cache.get(mask_key)
                if screen_mask is None:
                    screen_mask = self.ss_mask.resize((main_w, main_h), Image.Resampling.LANCZOS)
                    if screen_mask.mode == "RGBA":
                        screen_mask = screen_mask.split()[3]
                    elif screen_mask.mode != "L":
                        screen_mask = screen_mask.convert("L")
                    self._resize_cache[mask_key] = screen_mask
                
                # Create bottom screen mask for clipping
                bottom_mask = Image.new("L", (main_w, main_h), 0)
                draw = ImageDraw.Draw(bottom_mask)
                overlap_x1 = max(0, ext_x - main_x)
                overlap_y1 = max(0, ext_y - main_y)
                overlap_x2 = min(main_w, ext_x + ext_w - main_x)
                overlap_y2 = min(main_h, ext_y + ext_h - main_y)
                if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                    draw.rectangle([overlap_x1, overlap_y1, overlap_x2, overlap_y2], fill=255)
                
                # Combine masks
                combined_mask = ImageChops.multiply(screen_mask, bottom_mask)
                
                # Calculate visible overlap area
                visible_x1 = max(main_x, ext_x)
                visible_y1 = max(main_y, ext_y)
                visible_x2 = min(main_x + main_w, ext_x + ext_w)
                visible_y2 = min(main_y + main_h, ext_y + ext_h)
                
                visible_w = visible_x2 - visible_x1
                visible_h = visible_y2 - visible_y1
                
                if visible_w > 0 and visible_h > 0:
                    # Hero - fit to visible WIDTH at main screen position, then apply combined mask (rendered first, behind logo)
                    if top_screen_overlay.get("hero"):
                        hero = top_screen_overlay["hero"]
                        hero_w, hero_h = hero.size
                        
                        # Scale to fit visible width
                        scale_hero = visible_w / hero_w
                        new_w = visible_w
                        new_h = int(hero_h * scale_hero)
                        
                        if new_w > 0 and new_h > 0:
                            # Position at main screen origin (not visible origin), will be masked by combined_mask
                            hero_x = main_x
                            hero_y = main_y + (main_h - new_h) // 2
                            
                            key = (id(hero), new_w, new_h)
                            hero_resized = self._resize_cache.get(key)
                            if hero_resized is None:
                                hero_resized = hero.resize((new_w, new_h), Image.Resampling.BILINEAR)
                                self._resize_cache[key] = hero_resized
                            
                            # Create hero at main screen size to apply combined_mask properly
                            hero_full = Image.new("RGBA", (main_w, main_h), 0)
                            hero_full.paste(hero_resized, (hero_x - main_x, hero_y - main_y))
                            
                            # Apply combined mask
                            hero_masked = Image.composite(hero_full, Image.new("RGBA", (main_w, main_h), 0), combined_mask)
                            
                            # Crop to visible area and paste
                            crop_x = visible_x1 - main_x
                            crop_y = visible_y1 - main_y
                            hero_cropped = hero_masked.crop((crop_x, crop_y, crop_x + visible_w, crop_y + visible_h))
                            
                            base.alpha_composite(hero_cropped, (visible_x1, visible_y1))
                    
                    # Logo (rendered after hero, on top)
                    if top_screen_overlay.get("logo"):
                        logo = top_screen_overlay["logo"]
                        
                        if top_screen_overlay.get("is_default_folder"):
                            # Default folder - fixed scale relative to visible area
                            logo_w, logo_h = logo.size
                            scale_fit = min(visible_w / logo_w, visible_h / logo_h) * 0.56
                            new_w = int(logo_w * scale_fit)
                            new_h = int(logo_h * scale_fit)
                            
                            # Only resize if dimensions are valid
                            if new_w > 0 and new_h > 0:
                                key = (id(logo), new_w, new_h)
                                resized = self._resize_cache.get(key)
                                if resized is None:
                                    resized = logo.resize((new_w, new_h), Image.Resampling.BILINEAR)
                                    self._resize_cache[key] = resized
                                
                                # Center within visible area
                                paste_x = visible_x1 + (visible_w - new_w) // 2
                                paste_y = visible_y1 + (visible_h - new_h) // 2 - int(visible_h * 0.1025)
                                
                                base.alpha_composite(resized, (paste_x, paste_y))
                        else:
                            # Other folders - configurable scale relative to visible area
                            logo_w, logo_h = logo.size
                            scale_fit = min(visible_w / logo_w, visible_h / logo_h) * self.top_screen_icon_scale
                            new_w = int(logo_w * scale_fit)
                            new_h = int(logo_h * scale_fit)
                            
                            # Only resize if dimensions are valid
                            if new_w > 0 and new_h > 0:
                                key = (id(logo), new_w, new_h)
                                resized = self._resize_cache.get(key)
                                if resized is None:
                                    resized = logo.resize((new_w, new_h), Image.Resampling.BILINEAR)
                                    self._resize_cache[key] = resized
                                
                                # Center within visible area
                                paste_x = visible_x1 + (visible_w - new_w) // 2
                                paste_y = visible_y1 + (visible_h - new_h) // 2
                                
                                base.alpha_composite(resized, (paste_x, paste_y))
                                
        # UI Elements - render based on screen mode
        self._render_ui_elements(base, canvas_w, canvas_h, device_x, device_y, scale, skip_borders)

        # Frame - skip if hidden, or make semi-transparent if debug or bezel edit mode
        if not self.frame_hidden:
            if (self.debug_drag_mode or self.bezel_edit_mode) and self.bezel_img:
                # Create semi-transparent version
                frame_copy = self.bezel_img.copy()
                alpha = frame_copy.split()[3]
                alpha_adjusted = alpha.point(lambda p: int(p * 0.5))
                frame_copy.putalpha(alpha_adjusted)
                paste(frame_copy, device_x, device_y, device_w, device_h)
            else:
                paste(self.bezel_img, device_x, device_y, device_w, device_h)
        
        # App Grid Controls - now handled by tkinter widgets in app.py
        # Only show controls when in bezel edit mode
        # if self.bezel_edit_mode:
        #     self._render_app_grid_controls(base, canvas_w, canvas_h)
        
        # Draw handles on top of everything (in bezel edit mode)
        if self.bezel_edit_mode:
            # Recalculate screen positions for handles at the end
            main_screen = self.screen_manager.main
            external_screen = self.screen_manager.external
            
            main_rect = (
                device_x + round(main_screen.x * scale),
                device_y + round(main_screen.y * scale),
                round(main_screen.w * scale),
                round(main_screen.h * scale)
            )
            ext_rect = (
                device_x + round(external_screen.x * scale),
                device_y + round(external_screen.y * scale),
                round(external_screen.w * scale),
                round(external_screen.h * scale)
            )
            
            # Draw screen borders on top of everything
            if not skip_borders:
                if self.screen_manager.screen_mode == "dual":
                    self._draw_border(base, main_rect, (255, 165, 0, 255), 3)
                
                self._draw_border(base, ext_rect, (50, 205, 50, 255), 3)
            
            # Draw app grid handles (red) - but not in magnify window area
            # Note: Grid handles are added to _screen_handles AFTER screen handles are set below
            if not skip_handles and hasattr(self, '_app_grid_debug') and self._app_grid_debug:
                grid_left = self._app_grid_debug.get('grid_left')
                grid_right = self._app_grid_debug.get('grid_right')
                grid_top = self._app_grid_debug.get('grid_top')
                grid_bottom = self._app_grid_debug.get('grid_bottom')
                if grid_left is not None:
                    self._render_drag_handles(base, grid_left, grid_right, grid_top, grid_bottom)
        
        # Draw screen handles in bezel edit mode
        if self.bezel_edit_mode and not skip_handles:
            # Only show main screen handles if NOT in single screen mode
            show_main_handles = self.screen_manager.screen_mode != "single"
            
            mx, my, mw, mh = main_rect
            if mw > 0 and mh > 0 and show_main_handles:
                self._screen_handles = {
                    'main': [
                        ('tl', mx, my),
                        ('tr', mx + mw, my),
                        ('bl', mx, my + mh),
                        ('br', mx + mw, my + mh),
                        ('top', mx + mw//2, my),
                        ('bottom', mx + mw//2, my + mh),
                        ('left', mx, my + mh//2),
                        ('right', mx + mw, my + mh//2),
                    ],
                    'external': []
                }
                for hx in [mx, mx + mw]:
                    for hy in [my, my + mh]:
                        self._draw_handle(base, hx, hy, (255, 165, 0, 255), 6)
                self._draw_handle(base, mx + mw//2, my, (255, 165, 0, 255), 6)
                self._draw_handle(base, mx + mw//2, my + mh, (255, 165, 0, 255), 6)
                self._draw_handle(base, mx, my + mh//2, (255, 165, 0, 255), 6)
                self._draw_handle(base, mx + mw, my + mh//2, (255, 165, 0, 255), 6)
            else:
                self._screen_handles = {'main': [], 'external': []}
            
            # Draw external screen handles (lime green)
            ex, ey, ew, eh = ext_rect
            self._screen_handles['external'] = [
                ('tl', ex, ey),
                ('tr', ex + ew, ey),
                ('bl', ex, ey + eh),
                ('br', ex + ew, ey + eh),
                ('top', ex + ew//2, ey),
                ('bottom', ex + ew//2, ey + eh),
                ('left', ex, ey + eh//2),
                ('right', ex + ew, ey + eh//2),
            ]
            for hx in [ex, ex + ew]:
                for hy in [ey, ey + eh]:
                    self._draw_handle(base, hx, hy, (50, 205, 50, 255), 6)
            self._draw_handle(base, ex + ew//2, ey, (50, 205, 50, 255), 6)
            self._draw_handle(base, ex + ew//2, ey + eh, (50, 205, 50, 255), 6)
            self._draw_handle(base, ex, ey + eh//2, (50, 205, 50, 255), 6)
            self._draw_handle(base, ex + ew, ey + eh//2, (50, 205, 50, 255), 6)
            
            # Add app grid handles to _screen_handles for click detection (must be after screen handles are set)
            if hasattr(self, '_app_grid_debug') and self._app_grid_debug:
                grid_left = self._app_grid_debug.get('grid_left')
                grid_right = self._app_grid_debug.get('grid_right')
                grid_top = self._app_grid_debug.get('grid_top')
                grid_bottom = self._app_grid_debug.get('grid_bottom')
                if grid_left is not None:
                    self._screen_handles['grid'] = [
                        ('top', (grid_left + grid_right) // 2, grid_top),
                        ('bottom', (grid_left + grid_right) // 2, grid_bottom),
                        ('left', grid_left, (grid_top + grid_bottom) // 2),
                        ('right', grid_right, (grid_top + grid_bottom) // 2),
                    ]
        
        # Cache clean content (without borders/handles) for magnify window
        if wants_clean:
            self._cached_clean_content = base.copy()
            self._cached_clean_content_size = canvas_size
        
        return base
    
    def draw_overlays(self, base: Image.Image, canvas_size: tuple[int, int]) -> Image.Image:
        """Draw borders and handles on top of existing content image.
        
        This is used to add overlays to cached clean content for canvas display,
        avoiding the need to render the entire scene twice.
        
        Args:
            base: The base image (typically cached clean content) to draw overlays on
            canvas_size: The canvas dimensions (width, height)
            
        Returns:
            Image with overlays drawn on top
        """
        if not self.bezel_edit_mode:
            return base
            
        canvas_w, canvas_h = canvas_size
        
        # Recalculate scale and positions (needed for overlay positions)
        if not self.bezel_img:
            return base
            
        scale = min(
            (canvas_w - 2 * self.DEVICE_PADDING) / self.bezel_img.width,
            (canvas_h - 2 * self.DEVICE_PADDING) / self.bezel_img.height
        )
        device_w = round(self.bezel_img.width * scale)
        device_h = round(self.bezel_img.height * scale)
        device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
        device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2
        
        main_screen = self.screen_manager.main
        external_screen = self.screen_manager.external
        
        # Calculate screen rectangles
        main_rect = (
            device_x + round(main_screen.x * scale),
            device_y + round(main_screen.y * scale),
            round(main_screen.w * scale),
            round(main_screen.h * scale)
        )
        ext_rect = (
            device_x + round(external_screen.x * scale),
            device_y + round(external_screen.y * scale),
            round(external_screen.w * scale),
            round(external_screen.h * scale)
        )
        
        # Draw screen borders
        if self.screen_manager.screen_mode == "dual":
            self._draw_border(base, main_rect, (255, 165, 0, 255), 3)
        self._draw_border(base, ext_rect, (50, 205, 50, 255), 3)
        
        # Draw app grid handles
        if hasattr(self, '_app_grid_debug') and self._app_grid_debug:
            grid_left = self._app_grid_debug.get('grid_left')
            grid_right = self._app_grid_debug.get('grid_right')
            grid_top = self._app_grid_debug.get('grid_top')
            grid_bottom = self._app_grid_debug.get('grid_bottom')
            if grid_left is not None:
                # Draw red rectangle around app grid area (x, y, w, h format)
                rect_x = grid_left
                rect_y = grid_top - 5
                rect_w = grid_right - grid_left
                rect_h = (grid_bottom + 5) - (grid_top - 5)
                self._draw_border(base, (rect_x, rect_y, rect_w, rect_h), (255, 0, 0, 255), 3)
                
                # Set grid handles for click detection
                self._screen_handles['grid'] = [
                    ('top', (grid_left + grid_right) // 2, grid_top),
                    ('bottom', (grid_left + grid_right) // 2, grid_bottom),
                    ('left', grid_left, (grid_top + grid_bottom) // 2),
                    ('right', grid_right, (grid_top + grid_bottom) // 2),
                ]
                
                # Draw drag handles
                self._render_drag_handles(base, grid_left, grid_right, grid_top, grid_bottom)
        
        # Draw screen handles
        show_main_handles = self.screen_manager.screen_mode != "single"
        mx, my, mw, mh = main_rect
        if mw > 0 and mh > 0 and show_main_handles:
            for hx in [mx, mx + mw]:
                for hy in [my, my + mh]:
                    self._draw_handle(base, hx, hy, (255, 165, 0, 255), 6)
            self._draw_handle(base, mx + mw//2, my, (255, 165, 0, 255), 6)
            self._draw_handle(base, mx + mw//2, my + mh, (255, 165, 0, 255), 6)
            self._draw_handle(base, mx, my + mh//2, (255, 165, 0, 255), 6)
            self._draw_handle(base, mx + mw, my + mh//2, (255, 165, 0, 255), 6)
        
        # Draw external screen handles
        ex, ey, ew, eh = ext_rect
        for hx in [ex, ex + ew]:
            for hy in [ey, ey + eh]:
                self._draw_handle(base, hx, hy, (50, 205, 50, 255), 6)
        self._draw_handle(base, ex + ew//2, ey, (50, 205, 50, 255), 6)
        self._draw_handle(base, ex + ew//2, ey + eh, (50, 205, 50, 255), 6)
        self._draw_handle(base, ex, ey + eh//2, (50, 205, 50, 255), 6)
        self._draw_handle(base, ex + ew, ey + eh//2, (50, 205, 50, 255), 6)
        
        return base
    
    def get_video_mask_overlay(self, canvas_size: tuple[int, int]) -> tuple[Image.Image | None, tuple[int, int, int, int]]:
        """
        Generate a mask overlay for video in single-screen stacked mode.
        Returns (mask_image, position) or (None, None) if not applicable.
        
        The mask shows where the main screen video should be visible (soft-edged),
        with the overlap area clipped to only show over the external screen.
        """
        if not self.ss_mask or not self.bezel_img:
            return None, None
        
        # Check if we're in single screen stacked mode
        if self.screen_manager.screen_mode != "single":
            return None, None
        
        if not getattr(self, '_single_screen_stacked', False):
            return None, None
        
        canvas_w, canvas_h = canvas_size
        
        # Calculate scale (same as in composite)
        scale = min(
            (canvas_w - 2 * self.DEVICE_PADDING) / self.bezel_img.width,
            (canvas_h - 2 * self.DEVICE_PADDING) / self.bezel_img.height
        )
        
        device_w = round(self.bezel_img.width * scale)
        device_h = round(self.bezel_img.height * scale)
        device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
        device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2
        
        main_screen = self.screen_manager.main
        external_screen = self.screen_manager.external
        
        # Get main screen dimensions (before masking)
        main_x = device_x + round(main_screen.x * scale)
        main_y = device_y + round(main_screen.y * scale)
        main_w = round(main_screen.w * scale)
        main_h = round(main_screen.h * scale)
        
        # Get external screen dimensions
        ext_x = device_x + round(external_screen.x * scale)
        ext_y = device_y + round(external_screen.y * scale)
        ext_w = round(external_screen.w * scale)
        ext_h = round(external_screen.h * scale)
        
        # Resize ss_mask to main screen size
        mask_key = (id(self.ss_mask), main_w, main_h)
        screen_mask = self._resize_cache.get(mask_key)
        if screen_mask is None:
            screen_mask = self.ss_mask.resize((main_w, main_h), Image.Resampling.LANCZOS)
            if screen_mask.mode == "RGBA":
                screen_mask = screen_mask.split()[3]
            elif screen_mask.mode != "L":
                screen_mask = screen_mask.convert("L")
            self._resize_cache[mask_key] = screen_mask
        
        # Create bottom screen mask for clipping
        bottom_mask = Image.new("L", (main_w, main_h), 0)
        draw = ImageDraw.Draw(bottom_mask)
        overlap_x1 = max(0, ext_x - main_x)
        overlap_y1 = max(0, ext_y - main_y)
        overlap_x2 = min(main_w, ext_x + ext_w - main_x)
        overlap_y2 = min(main_h, ext_y + ext_h - main_y)
        if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
            draw.rectangle([overlap_x1, overlap_y1, overlap_x2, overlap_y2], fill=255)
        
        # Combine masks
        from PIL import ImageChops
        combined_mask = ImageChops.multiply(screen_mask, bottom_mask)
        
        # Create RGBA overlay with the mask as alpha
        overlay = Image.new("RGBA", (main_w, main_h), (0, 0, 0, 0))
        
        # Create white fill with the combined mask as alpha
        white_fill = Image.new("RGBA", (main_w, main_h), (255, 255, 255, 255))
        overlay = Image.composite(white_fill, Image.new("RGBA", (main_w, main_h), (0, 0, 0, 0)), combined_mask)
        
        return overlay, (main_x, main_y, main_w, main_h)