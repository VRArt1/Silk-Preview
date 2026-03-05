from pathlib import Path
import json
import random
import math
import av
from PIL import Image, ImageSequence
import time

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
PLACEHOLDER_DIR = BASE_DIR / "Placeholder Assets"
GAMES_DIR = ASSETS_DIR / "games"

class Renderer:
    # Device / Frame
    FRAME_WIDTH = 800
    FRAME_HEIGHT = 950
    DEVICE_PADDING = 20

    # Top Screen / Wallpaper
    TOP_SCREEN_X = 41
    TOP_SCREEN_Y = 24
    TOP_SCREEN_W = 718
    TOP_SCREEN_H = 405

    # Bottom Screen / Wallpaper
    BOTTOM_SCREEN_X = 205
    BOTTOM_SCREEN_Y = 540
    BOTTOM_SCREEN_W = 392
    BOTTOM_SCREEN_H = 340
    BOTTOM_SCREEN_HT_OFFSET = 15 # subtracted from top height of grid area
    BOTTOM_SCREEN_HB_OFFSET = 40  # subtracted from bottom height for grid area

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

    # Frame options
    FRAME_OPTIONS = {
        "Black": "device_frame_black.png",
        "Clear Purple": "device_frame_purple.png",
        "Rainbow": "device_frame_rainbow.png",
        "White": "device_frame_white.png",
        "Custom": "device_frame_custom.png",
    }

    def __init__(self, max_grid_slots):
    
        # Default folder color (matches available variants in assets/default folder)
        self.default_folder_color = "blue"  # or "red", "green", etc.
        
        self._last_canvas_size = None
        
        self._sel_anim_start = None
        self._sel_anim_from = None
        self._sel_anim_to = None
        self._sel_anim_duration = 0.35  # seconds (tweakable)
        
        # Timestamps for real-time animation
        self._last_wallpaper_top_update = time.perf_counter()
        self._last_wallpaper_bottom_update = time.perf_counter()
        self._last_hero_update = {} # keyed by selected_index
        self._last_logo_update = {}
    
        # Caches
        self._resize_cache = {}
        self._static_cache_image = None
        self._static_cache_size = None
        self._static_cache_dirty = True
    
        # Game image cache (must exist before _load_frame is called)
        self._game_image_cache = {}      # path → loaded PIL image
        
        self.video_frame_cache = {}
        
        self.animations = {}

        # Device images
        self.current_frame_name = "Rainbow"  # default frame
        self.frame_img = self._load_frame(self.current_frame_name)
        self._invalidate_static_cache()
        self.ui_img = self._load_cached_rgba(ASSETS_DIR / "device_ui.png", PLACEHOLDER_DIR / "device_ui.png")
        self.ui_visible = True
        
        # Background
        self.bg_img = self._load_cached_rgba(ASSETS_DIR / "bg.png", PLACEHOLDER_DIR / "bg.png")
        if self.bg_img and self.BG_SCALE != 1.0:
            w, h = self.bg_img.size
            self.bg_img = self.bg_img.resize((int(w * self.BG_SCALE), int(h * self.BG_SCALE)), Image.Resampling.LANCZOS)

        # Selection highlight
        self.selected_img = self._load_cached_rgba(ASSETS_DIR / "selected.png", PLACEHOLDER_DIR / "selected.png")

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
        
        # Discover ALL game image paths (no image loading yet)
        self._game_path_lookup = {}      # name → list of Paths (variants)
        self._game_image_cache = {}      # path → loaded PIL image
        self._used_game_images = set()   # track used images per theme

        game_files = [f for f in GAMES_DIR.iterdir() if f.is_file()]
        for f in game_files:
            stem = f.stem.lower()
            # Determine base name before underscore or suffix (e.g., gba_blue → gba)
            base_name = stem.split("_")[0]
            self._game_path_lookup.setdefault(base_name, []).append(f)

        # For fallback random feeding
        self._shuffled_game_names = list(self._game_path_lookup.keys())
        random.shuffle(self._shuffled_game_names)
        self._next_game_img_index = 0

    # -----------------------------
    # Helpers
    # -----------------------------
    
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
        """Change grid size (used by zoom in/out)."""
        if rows <= 0 or cols <= 0:
            return

        self.GRID_ROWS = rows
        self.GRID_COLS = cols

        # Clamp selection index
        max_index = rows * cols - 1
        self.selected_index = min(self.selected_index, max_index)

        # Grid affects layout → invalidate cache
        self._invalidate_static_cache()
    
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
        self._invalidate_static_cache()    
    def _load_rgba(self, path: Path, fallback: Path | None = None):
        if path and path.exists():
            try:
                return Image.open(path).convert("RGBA")
            except Exception as e:
                print(f"[DEBUG] Failed to open image: {path} -> {e}")
        if fallback and fallback.exists():
            try:
                return Image.open(fallback).convert("RGBA")
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
        filename = self.FRAME_OPTIONS.get(name, "device_frame_rainbow.png")
        return self._load_cached_rgba(ASSETS_DIR / filename, PLACEHOLDER_DIR / filename)

    def set_frame(self, name: str):
        """Swap to a different device frame"""
        if name in self.FRAME_OPTIONS:
            self.current_frame_name = name
            self.frame_img = self._load_frame(name)
            new_w, new_h = self.frame_img.size
            self._frame_scale = min(new_w / self.FRAME_WIDTH, new_h / self.FRAME_HEIGHT)

            self._invalidate_static_cache()

    def _apply_mask(self, img: Image.Image, mask: Image.Image):
        """Apply mask: white = visible, transparency = invisible"""
        if not img or not mask:
            return None
        img_resized = img.resize(mask.size, Image.Resampling.BILINEAR)
        if mask.mode != "L":
            alpha = mask.split()[3] if mask.mode == "RGBA" else None
            mask = mask.convert("L")
            if alpha:
                mask = Image.composite(mask, Image.new("L", mask.size, 0), alpha)
        return Image.composite(img_resized, Image.new("RGBA", mask.size, (0, 0, 0, 0)), mask)

    def _get_random_game_image(self, name: str):
        """Return a random variant of the game image for this platform name.
        Fallback to any platform if no images exist for this name.
        Avoid duplicates if possible.
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
                self._game_image_cache[selected_path] = img

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
    def _fit_background(self, base: Image.Image, bg: Image.Image, device_rect: tuple[int,int,int,int]):
        """
        Fit the bg image to the height of the device area and center horizontally.
        device_rect = (device_x, device_y, device_w, device_h)
        """
        if not bg:
            return
        device_x, device_y, device_w, device_h = device_rect
        bw, bh = bg.size
        scale = device_h / bh
        new_w = int(bw * scale)
        new_h = device_h
        bg_resized = bg.resize((new_w, new_h), Image.Resampling.BILINEAR)
        x = device_x + (device_w - new_w) // 2
        y = device_y
        base.alpha_composite(bg_resized, (x, y))

    # Video First Frame
    
    def first_frame_from_video(self, path):
        path = Path(path)
        cache_key = (str(path), path.stat().st_mtime)

        if cache_key in self.video_frame_cache:
            return self.video_frame_cache[cache_key]

        try:
            container = av.open(str(path))
            stream = container.streams.video[0]

            container.seek(0)

            frame = next(container.decode(stream))
            img = frame.to_image()

            self.video_frame_cache[cache_key] = img
            return img

        except Exception as e:
            print(f"Video decode failed for {path}: {e}")

        return None
    
    # -----------------------------
    # Theme Loading
    # -----------------------------
    def load_theme(self, theme_path: Path | None, max_grid_items: int | None = None):
        # Force full rebuild of static cache when theme changes
        self._static_cache_image = None
        self._static_cache_size = None
        self._static_cache_dirty = True

        # Also clear resize cache so old wallpaper sizes aren't reused
        self._resize_cache.clear()
        
        self.video_frame_cache.clear()

        # Reset shuffled game name order for this theme
        self._shuffled_game_names = list(self._game_path_lookup.keys())
        random.shuffle(self._shuffled_game_names)
        self._next_game_img_index = 0
        self.theme_path = theme_path if theme_path else PLACEHOLDER_DIR

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
                    # Use your helper to get the first frame as an image
                    img = self.first_frame_from_video(path_file)
                    if not img:
                        continue
                else:
                    img = Image.open(path_file)

                if getattr(img, "is_animated", False):
                    self.wallpaper_top_frames = [
                        frame.convert("RGBA") for frame in ImageSequence.Iterator(img)
                    ]
                    self.wallpaper_top_duration = img.info.get("duration", 100)
                    self.wallpaper_top = self.wallpaper_top_frames[0]
                else:
                    self.wallpaper_top = img.convert("RGBA")

            except Exception as e:
                print(f"Failed to load wallpaper {fname}: {e}")
                continue

            break

        if not self.wallpaper_top:
            for fname in top_candidates:
                placeholder_file = PLACEHOLDER_DIR / "wallpapers" / fname
                if placeholder_file.exists():
                    try:
                        img = Image.open(placeholder_file)
                        if getattr(img, "is_animated", False):
                            self.wallpaper_top_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                            self.wallpaper_top_duration = img.info.get("duration", 100)
                            self.wallpaper_top = self.wallpaper_top_frames[0]
                        else:
                            self.wallpaper_top = img.convert("RGBA")
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
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                bottom_files_to_try.append(wallpaper_external_name)
        bottom_files_to_try.extend(bottom_candidates)

        for fname in bottom_files_to_try:
            path_file = self.theme_path / "wallpapers" / fname
            if not path_file.exists():
                continue

            try:
                ext_lower = path_file.suffix.lower().strip(".")
                if ext_lower in ("mp4", "webm"):
                    img = self.first_frame_from_video(path_file)
                    if not img:
                        continue
                else:
                    img = Image.open(path_file)

                if getattr(img, "is_animated", False):
                    self.wallpaper_bottom_frames = [
                        frame.convert("RGBA") for frame in ImageSequence.Iterator(img)
                    ]
                    self.wallpaper_bottom_duration = img.info.get("duration", 100)
                    self.wallpaper_bottom = self.wallpaper_bottom_frames[0]
                else:
                    self.wallpaper_bottom = img.convert("RGBA")

            except Exception as e:
                print(f"Failed to load wallpaper {fname}: {e}")
                continue

            break

        if not self.wallpaper_bottom:
            for fname in bottom_candidates:
                placeholder_file = PLACEHOLDER_DIR / "wallpapers" / fname
                if placeholder_file.exists():
                    try:
                        img = Image.open(placeholder_file)
                        if getattr(img, "is_animated", False):
                            self.wallpaper_bottom_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(img)]
                            self.wallpaper_bottom_duration = img.info.get("duration", 100)
                            self.wallpaper_bottom = self.wallpaper_bottom_frames[0]
                        else:
                            self.wallpaper_bottom = img.convert("RGBA")
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
                    continue  # skip this variant entirely

                # Load images
                overlay = self._load_cached_rgba(overlay_path)
                mask = self._load_cached_rgba(mask_path)
                if not overlay or not mask:
                    continue  # just in case loading failed

                # Pick random game image variant for this base platform
                game_img = self._get_random_game_image(base_name)
                if mask and game_img:
                    game_img = self._apply_mask(game_img, mask)

                # Register overlay using base platform name
                self.icon_overlays[base_name] = {
                    "mask": mask,
                    "overlay": overlay,
                    "game_img": game_img,
                }

                remaining_slots -= 1

        total_slots = self.GRID_ROWS * self.GRID_COLS
        self.selected_index = max(0, min(self.selected_index, total_slots - 1))
        
    def _invalidate_static_cache(self):
        """Mark static cache as dirty so it rebuilds next render."""
        self._static_cache_dirty = True
        
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
        if not self.wallpaper_top_frames:
            return
        now = time.perf_counter()
        elapsed = (now - self._last_wallpaper_top_update) * 1000  # ms
        if elapsed >= self.wallpaper_top_duration:
            self.wallpaper_top_index = (self.wallpaper_top_index + 1) % len(self.wallpaper_top_frames)
            self.wallpaper_top = self.wallpaper_top_frames[self.wallpaper_top_index]
            self._last_wallpaper_top_update = now

    def advance_bottom_wallpaper_frame(self):
        if not self.wallpaper_bottom_frames:
            return
        now = time.perf_counter()
        elapsed = (now - self._last_wallpaper_bottom_update) * 1000
        if elapsed >= self.wallpaper_bottom_duration:
            self.wallpaper_bottom_index = (self.wallpaper_bottom_index + 1) % len(self.wallpaper_bottom_frames)
            self.wallpaper_bottom = self.wallpaper_bottom_frames[self.wallpaper_bottom_index]
            self._last_wallpaper_bottom_update = now

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
        if (now - last_update) * 1000 >= duration:
            idx = item.get("hero_index", 0)
            idx = (idx + 1) % len(frames)
            item["hero_index"] = idx
            item["hero"] = frames[idx]
            self._last_hero_update[self.selected_index] = now
    
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

        if (now - last_update) * 1000 >= duration:
            idx = item.get("logo_index", 0)
            idx = (idx + 1) % len(frames)

            item["logo_index"] = idx
            item["logo"] = frames[idx]

            self._last_logo_update[self.selected_index] = now
    
    # Rendering
    def composite(self, canvas_size: tuple[int, int], skip_background: bool = False) -> Image.Image:
        canvas_w, canvas_h = canvas_size

        # Always compare with last static cache size
        canvas_resized = self._static_cache_size != canvas_size

        # Force rebuild if canvas size changed
        if canvas_resized:
            self._static_cache_dirty = True
            # Clear any old resized images
            self._resize_cache.clear()

        # Update last canvas size for animation tracking
        self._last_canvas_size = canvas_size

        # Build static cache if needed
        if self._static_cache_image is None or self._static_cache_dirty or self._static_cache_size != canvas_size:
            static_base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))

            # Background (fitted)
            if not skip_background:
                self._fit_background(static_base, self.bg_img, (0, 0, canvas_w, canvas_h))

            # Scale device to fit within canvas minus padding
            scale = min(
                (canvas_w - 2 * self.DEVICE_PADDING) / self.frame_img.width,
                (canvas_h - 2 * self.DEVICE_PADDING) / self.frame_img.height
            )
            device_w = round(self.frame_img.width * scale)
            device_h = round(self.frame_img.height * scale)
            device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
            device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2

            def paste(img, x, y, w, h):
                if not img:
                    return
                key = (id(img), w, h)
                resized = self._resize_cache.get(key)
                if resized is None:
                    resized = img.resize((w, h), Image.Resampling.BILINEAR)
                    self._resize_cache[key] = resized
                static_base.alpha_composite(resized, (x, y))

            # UI (static)
            if self.ui_visible and self.ui_img:
                paste(self.ui_img, device_x, device_y, device_w, device_h)

            # Frame (static)
            paste(self.frame_img, device_x, device_y, device_w, device_h)

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
            (canvas_w - 2 * self.DEVICE_PADDING) / self.frame_img.width,
            (canvas_h - 2 * self.DEVICE_PADDING) / self.frame_img.height
        )
        device_w = round(self.frame_img.width * scale)
        device_h = round(self.frame_img.height * scale)
        device_x = self.DEVICE_PADDING + (canvas_w - 2 * self.DEVICE_PADDING - device_w) // 2
        device_y = self.DEVICE_PADDING + (canvas_h - 2 * self.DEVICE_PADDING - device_h) // 2

        def paste(img, x, y, w, h):
            if not img:
                return
            key = (id(img), w, h)
            resized = self._resize_cache.get(key)
            if resized is None:
                resized = img.resize((w, h), Image.Resampling.BILINEAR)
                self._resize_cache[key] = resized
            base.alpha_composite(resized, (x, y))

        # Animated top wallpaper
        paste(self.wallpaper_top,
              device_x + round(self.TOP_SCREEN_X * scale),
              device_y + round(self.TOP_SCREEN_Y * scale),
              round(self.TOP_SCREEN_W * scale),
              round(self.TOP_SCREEN_H * scale))

        # Bottom wallpaper
        paste(self.wallpaper_bottom,
              device_x + round(self.BOTTOM_SCREEN_X * scale),
              device_y + round(self.BOTTOM_SCREEN_Y * scale),
              round(self.BOTTOM_SCREEN_W * scale),
              round(self.BOTTOM_SCREEN_H * scale))

        # Grid placement (squared & centered)
        grid_x = device_x + round(self.BOTTOM_SCREEN_X * scale)
        grid_y = device_y + round(self.BOTTOM_SCREEN_Y * scale) + round(self.BOTTOM_SCREEN_HT_OFFSET * scale)
        grid_w = round(self.BOTTOM_SCREEN_W * scale)
        grid_h = (
            round(self.BOTTOM_SCREEN_H * scale)
            - round(self.BOTTOM_SCREEN_HT_OFFSET * scale)
            - round(self.BOTTOM_SCREEN_HB_OFFSET * scale)
        )


        total_slots = self.GRID_ROWS * self.GRID_COLS

        avail_w = grid_w - 2 * self.GRID_OUTER_PADDING - (self.GRID_COLS - 1) * self.GRID_PADDING
        avail_h = grid_h - 2 * self.GRID_OUTER_PADDING - (self.GRID_ROWS - 1) * self.GRID_PADDING
        cell_size = min(avail_w // self.GRID_COLS, avail_h // self.GRID_ROWS)
        cell_w = cell_h = cell_size

        extra_w = avail_w - cell_w * self.GRID_COLS
        extra_h = avail_h - cell_h * self.GRID_ROWS
        offset_x = self.GRID_OUTER_PADDING + extra_w // 2
        offset_y = self.GRID_OUTER_PADDING + extra_h // 2

        # Precompute grid positions

        avail_w = grid_w - 2 * self.GRID_OUTER_PADDING - (self.GRID_COLS - 1) * self.GRID_PADDING
        avail_h = grid_h - 2 * self.GRID_OUTER_PADDING - (self.GRID_ROWS - 1) * self.GRID_PADDING
        cell_w = avail_w // self.GRID_COLS
        cell_h = avail_h // self.GRID_ROWS

        self.grid_positions = []       # visual squares
        self.grid_click_regions = []   # full rectangles

        for idx in range(total_slots):
            row = idx // self.GRID_COLS
            col = idx % self.GRID_COLS

            rect_x = grid_x + self.GRID_OUTER_PADDING + col * (cell_w + self.GRID_PADDING)
            rect_y = grid_y + self.GRID_OUTER_PADDING + row * (cell_h + self.GRID_PADDING)

            # Store full rectangle for clicking
            self.grid_click_regions.append((rect_x, rect_y, cell_w, cell_h))

            # Now shrink to square (visual only)
            size = min(cell_w, cell_h)

            cx = rect_x + cell_w // 2
            cy = rect_y + cell_h // 2

            square_x = cx - size // 2
            square_y = cy - size // 2

            self.grid_positions.append((square_x, square_y, size, size))

        # Build grid items with strict order, no None filling
        total_slots = self.GRID_ROWS * self.GRID_COLS
        self.grid_items = []
        remaining_slots = total_slots

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
            self.grid_items.append({
                "icon": overlay_data["overlay"],
                "game_img": overlay_data["game_img"],
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
        
        # Precompute grid_positions
        avail_w = grid_w - 2 * self.GRID_OUTER_PADDING - (self.GRID_COLS - 1) * self.GRID_PADDING
        avail_h = grid_h - 2 * self.GRID_OUTER_PADDING - (self.GRID_ROWS - 1) * self.GRID_PADDING
        cell_w = avail_w // self.GRID_COLS
        cell_h = avail_h // self.GRID_ROWS

        self.grid_positions = []
        for idx in range(total_slots):
            row = idx // self.GRID_COLS
            col = idx % self.GRID_COLS
            x = grid_x + self.GRID_OUTER_PADDING + col * (cell_w + self.GRID_PADDING)
            y = grid_y + self.GRID_OUTER_PADDING + row * (cell_h + self.GRID_PADDING)
            self.grid_positions.append((x, y, cell_w, cell_h))
        
        # ---- FORCE 1:1 SQUARES AFTER RECT LAYOUT ----
        new_positions = []

        for (x, y, w, h) in self.grid_positions:
            size = min(w, h)

            cx = x + w // 2
            cy = y + h // 2

            new_x = cx - size // 2
            new_y = cy - size // 2

            new_positions.append((new_x, new_y, size, size))

        self.grid_positions = new_positions


        # -------------------------------------------------
        # COLUMN-BASED GRID SHIFT (Animated, smooth)
        # -------------------------------------------------
        if self.ENABLE_COLUMN_SHIFT and self.GRID_COLS > 1:

            animated_index = self.selected_index
            animated_col = animated_index % self.GRID_COLS
            column_progress = animated_col / (self.GRID_COLS - 1)

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

            # Start new animation when target changes
            if self._sel_anim_to != target:
                self._sel_anim_from = (
                    self._selected_anim_x,
                    self._selected_anim_y,
                    self._selected_anim_w,
                    self._selected_anim_h,
                )
                self._sel_anim_to = target
                self._sel_anim_start = now

                # -------------------------------
                # Distance-aware duration
                # -------------------------------
                dx = target_x - self._sel_anim_from[0]
                dy = target_y - self._sel_anim_from[1]
                distance = (dx * dx + dy * dy) ** 0.5

                cell_diag = (target_w * target_w + target_h * target_h) ** 0.5

                base_duration = self.BASE_SEL_ANIM_DURATION
                max_duration  = self.MAX_SEL_ANIM_DURATION

                factor = max(1.0, distance / cell_diag)
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
                round(self._selected_anim_x),
                round(self._selected_anim_y),
                round(self._selected_anim_w),
                round(self._selected_anim_h),
            )

        # Draw grid items ON TOP

        for idx, item in enumerate(self.grid_items):
            if not item:
                continue

            x, y, w, h = self.grid_positions[idx]

            # Determine what type of item this is
            is_default_folder = item.get("is_default_folder")
            is_smart_folder = item.get("source") in ("root", "by_platform")
            is_icon_overlay = item.get("game_img") is not None

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
            if item.get("game_img"):
                paste(item["game_img"], content_x, content_y, content_w, content_h)

            # Draw icon on top
            if item.get("icon"):
                paste(item["icon"], content_x, content_y, content_w, content_h)

            if idx == self.selected_index:
                top_screen_overlay = item
                
        # Top screen hero/logo
        if top_screen_overlay:
            top_x = device_x + round(self.TOP_SCREEN_X * scale)
            top_y = device_y + round(self.TOP_SCREEN_Y * scale)
            top_w = round(self.TOP_SCREEN_W * scale)
            top_h = round(self.TOP_SCREEN_H * scale)

            # Hero still stretches normally
            if top_screen_overlay.get("hero"):
                paste(top_screen_overlay["hero"], top_x, top_y, top_w, top_h)

            # Logo
            if top_screen_overlay.get("logo"):
                logo = top_screen_overlay["logo"]

                # Preserve aspect ratio for default folder
                if top_screen_overlay.get("is_default_folder"):
                    logo_w, logo_h = logo.size

                    scale_fit = min(top_w / logo_w, top_h / logo_h) * 0.56

                    new_w = int(logo_w * scale_fit)
                    new_h = int(logo_h * scale_fit)

                    key = (id(logo), new_w, new_h)
                    resized = self._resize_cache.get(key)
                    if resized is None:
                        resized = logo.resize((new_w, new_h), Image.Resampling.BILINEAR)
                        self._resize_cache[key] = resized

                    paste_x = top_x + (top_w - new_w) // 2
                    paste_y = top_y + (top_h - new_h) // 2 - int(top_h * 0.1025)

                    base.alpha_composite(resized, (paste_x, paste_y))
                    

                else:
                    # Normal behavior for other folders
                    # paste(logo, top_x, top_y, top_w, top_h)
                    
                    logo_w, logo_h = logo.size

                    scale_fit = min(top_w / logo_w, top_h / logo_h) * 0.56

                    new_w = int(logo_w * scale_fit)
                    new_h = int(logo_h * scale_fit)

                    key = (id(logo), new_w, new_h)
                    resized = self._resize_cache.get(key)
                    if resized is None:
                        resized = logo.resize((new_w, new_h), Image.Resampling.BILINEAR)
                        self._resize_cache[key] = resized

                    paste_x = top_x + (top_w - new_w) // 2
                    paste_y = top_y + (top_h - new_h) // 2

                    base.alpha_composite(resized, (paste_x, paste_y))
                
        # UI
        if self.ui_visible and self.ui_img:
            paste(self.ui_img, device_x, device_y, device_w, device_h)

        # Frame
        paste(self.frame_img, device_x, device_y, device_w, device_h)
            
        return base