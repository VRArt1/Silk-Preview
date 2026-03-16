import tkinter as tk
import configparser
from datetime import datetime
from tkinter import filedialog, StringVar
from tkinter import PhotoImage
from tkinter import ttk
from pathlib import Path
from PIL import ImageTk, Image, ImageEnhance, ImageChops, ImageDraw
import time

from tkinterdnd2 import DND_FILES, TkinterDnD

from renderer import Renderer
from widgets.preview_panel import PreviewPanel
from video_player import VideoPlayerManager


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.title("Silk Preview")
        self.minsize(900, 700)
        
        icon_path = Path(__file__).parent / "assets/favicon.png"
        if icon_path.exists():
            self.icon_img = PhotoImage(file=icon_path)
            self.iconphoto(False, self.icon_img)
        
        checkmark_path = Path(__file__).parent / "assets/ui/checkmark.png"
        if checkmark_path.exists():
            self.checkmark_img_orig = Image.open(checkmark_path).convert("RGBA")
        else:
            self.checkmark_img_orig = None
        

        # ----------------------------
        # Settings
        # ----------------------------
        self.config = configparser.ConfigParser()
        self.settings_path = Path(__file__).parent / "settings.ini"
        self.config.read(self.settings_path)

        # Ensure sections exist
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        if "Misc" not in self.config:
            self.config["Misc"] = {}

        # ----------------------------
        # Zoom levels (rows, cols) - per screen mode
        # ----------------------------
        # Dual screen device (Aynthor) - top + bottom screens
        self.zoom_levels_dual = [
            (4, 5),  # large
            (3, 4),  # default
            (2, 3),  # small
        ]
        # Single screen device with top screen OFF (dual mode on single device)
        self.zoom_levels_single_dual = [
            (5, 12),  # smallest
            (4, 9),
            (3, 7),
            (2, 5),
            (1, 3),  # largest
        ]
        # Single screen device with top screen ON (true single screen mode)
        self.zoom_levels_single_stacked = [
            (3, 14),  # smallest
            (2, 12),
            (1, 9),  # largest
        ]
        
        # Combined lookup table for single screen stacked mode
        # offset_pct: how much of top screen is visible (for positioning top screen)
        # scale_factor: portion of full grid area to use for item grid
        self.stacked_lookup = {
            3: {"offset_pct": 0.399, "scale_factor": 0.588},   # 3 rows
            2: {"offset_pct": 0.492, "scale_factor": 0.481},   # 2 rows
            1: {"offset_pct": 0.621, "scale_factor": 0.348},   # 1 row
        }
        
        # Backwards compatibility - offset percentages only (for top screen positioning)
        self.stacked_offset_percentages = {rows: v["offset_pct"] for rows, v in self.stacked_lookup.items()}
        
        # Load Settings in order (for correct defaults when saving)
        # default_folder_color
        if "default_folder_color" not in self.config["Settings"]:
            self.config["Settings"]["default_folder_color"] = "blue"
        self.default_folder_color = self.config.get("Settings", "default_folder_color", fallback="blue")
        self.default_folder_color_var = tk.StringVar(value=self.default_folder_color)
        
        # dock_background
        if "dock_background" not in self.config["Settings"]:
            self.config["Settings"]["dock_background"] = "True"
        
        # logo_size
        if "logo_size" not in self.config["Settings"]:
            self.config["Settings"]["logo_size"] = "60"
        self.logo_size = self.config.getint("Settings", "logo_size", fallback=60)
        
        # show_corner_hints
        if "show_corner_hints" not in self.config["Settings"]:
            self.config["Settings"]["show_corner_hints"] = "True"
        
        # single_screen_mode
        if "single_screen_mode" not in self.config["Settings"]:
            self.config["Settings"]["single_screen_mode"] = "True"
        self.single_screen_stacked_mode = self.config.getboolean("Settings", "single_screen_mode", fallback=True)
        
        # apps
        if "apps" not in self.config["Settings"]:
            self.config["Settings"]["apps"] = "True"
        self.apps_visible = self.config.getboolean("Settings", "apps", fallback=True)
        
        # empty_apps
        if "empty_apps" not in self.config["Settings"]:
            self.config["Settings"]["empty_apps"] = "True"
        self.empty_apps_visible = self.config.getboolean("Settings", "empty_apps", fallback=True)
        
        # empty_slots
        if "empty_slots" not in self.config["Settings"]:
            self.config["Settings"]["empty_slots"] = "True"
        self.empty_slots = self.config.getboolean("Settings", "empty_slots", fallback=True)
        
        # remember_last_theme
        if "remember_last_theme" not in self.config["Settings"]:
            self.config["Settings"]["remember_last_theme"] = "True"
        self.remember_last_theme = self.config.getboolean("Settings", "remember_last_theme", fallback=True)
        
        # last_theme_path
        if "last_theme_path" not in self.config["Settings"]:
            self.config["Settings"]["last_theme_path"] = ""
        self.last_theme_path = self.config.get("Settings", "last_theme_path", fallback=None)
        
        # video_playback
        if "video_playback" not in self.config["Settings"]:
            self.config["Settings"]["video_playback"] = "True"
        self.video_playback = self.config.getboolean("Settings", "video_playback", fallback=True)
        
        # bg_scroll_speed
        if "bg_scroll_speed" not in self.config["Settings"]:
            self.config["Settings"]["bg_scroll_speed"] = "1"
        self.bg_scroll_speed = self.config.getint("Settings", "bg_scroll_speed", fallback=1)
        
        # reverse_direction
        if "reverse_direction" not in self.config["Settings"]:
            self.config["Settings"]["reverse_direction"] = "False"
        self.reverse_direction = self.config.getboolean("Settings", "reverse_direction", fallback=False)
        
        # Calculate max values from zoom levels
        self.max_rows_dual = max(r for r, c in self.zoom_levels_dual)
        self.max_cols_dual = max(c for r, c in self.zoom_levels_dual)
        self.max_rows_single_dual = max(r for r, c in self.zoom_levels_single_dual)
        self.max_cols_single_dual = max(c for r, c in self.zoom_levels_single_dual)
        self.max_rows_single_stacked = max(r for r, c in self.zoom_levels_single_stacked)
        self.max_cols_single_stacked = max(c for r, c in self.zoom_levels_single_stacked)
        
        # Use appropriate zoom levels based on screen mode (default to dual)
        self.zoom_levels = self.zoom_levels_dual
        self.zoom_index = self.config.getint("Misc", "zoom_index", fallback=1)
        # Clamp zoom_index to valid range for default mode
        if self.zoom_index >= len(self.zoom_levels):
            self.zoom_index = len(self.zoom_levels) - 1
        
        # Canvas zoom level (for zooming the device on canvas)
        if "canvas_zoom" not in self.config["Misc"]:
            self.config["Misc"]["canvas_zoom"] = "1.0"
        self.canvas_zoom = self.config.getfloat("Misc", "canvas_zoom", fallback=1.0)

        # Maximum number of grid slots across all zoom levels
        self.max_grid_slots_dual = self.max_rows_dual * self.max_cols_dual
        self.max_grid_slots_single = max(
            self.max_rows_single_dual * self.max_cols_single_dual,
            self.max_rows_single_stacked * self.max_cols_single_stacked
        )
        self.max_grid_slots = max(self.max_grid_slots_dual, self.max_grid_slots_single)
        
        # Total columns for extended grid navigation (use max of all modes)
        self.total_cols = max(self.max_cols_dual, self.max_cols_single_dual, self.max_cols_single_stacked)

        # App grid settings are now loaded from device.json in each bezel folder
        # These are just initial defaults that will be overwritten by device settings
        self.app_grid_x_offset = 0
        self.app_grid_y_offset = -40
        self.app_grid_width = 400
        self.app_grid_icon_size = 50
        self.app_grid_icon_scale = 1.0
        
        # Magnify window size
        self.magnify_size = self.config.getint("Misc", "magnify_size", fallback=200)
        
        # Magnify window toggle
        if "magnify_window" not in self.config["Misc"]:
            self.config["Misc"]["magnify_window"] = "True"
        self.magnify_window = self.config.getboolean("Misc", "magnify_window", fallback=True)
        
        # ----------------------------
        # Renderer
        # ----------------------------
        self.renderer = Renderer(
            max_grid_slots=self.max_grid_slots,
            max_rows_dual=self.max_rows_dual,
            max_rows_single_dual=self.max_rows_single_dual,
            max_rows_single_stacked=self.max_rows_single_stacked,
            total_cols=self.total_cols
        )
        
        # Assign the value so Renderer knows
        self.renderer.show_empty_slots = self.empty_slots
        self.renderer._single_screen_stacked = self.single_screen_stacked_mode
        self.renderer._stacked_lookup = self.stacked_lookup
        self.renderer.app_grid_visible = self.empty_apps_visible
        self.renderer.populated_apps_visible = self.apps_visible
        self.renderer.app_grid_x_offset = self.app_grid_x_offset
        self.renderer.app_grid_y_offset = self.app_grid_y_offset
        self.renderer.app_grid_width = self.app_grid_width
        self.renderer.app_grid_icon_size = self.app_grid_icon_size
        self.renderer.app_grid_icon_scale = self.app_grid_icon_scale
        self.renderer.default_folder_color = self.default_folder_color
        self.renderer.magnify_size = self.magnify_size
        self.renderer.magnify_window = self.magnify_window
        self.renderer.top_screen_icon_scale = self.logo_size / 100.0
        
        # Set initial top screen offset based on stacked mode setting
        from screen import Screen
        if not self.single_screen_stacked_mode:
            Screen.SINGLE_SCREEN_MAIN_OFFSET = -580  # Hide top screen
        
        # ----------------------------
        # Folder menu state (must be before any redraw calls)
        # ----------------------------
        self.folder_menu_open = False
        self.folder_menu_anchor_index = None
        self.folder_colors = ["blue", "red", "gray", "orange", "yellow", "green", "purple", "pink"]
        self._folder_menu_items = []
        self._folder_color_previews_loaded = False
        
        # Determine initial theme folder
        # Default to Placeholder Assets, only use remembered path if enabled AND valid
        initial_theme_folder = Path(__file__).parent / "Placeholder Assets"
        if self.remember_last_theme and self.last_theme_path:
            remembered_path = Path(self.last_theme_path)
            if remembered_path.exists():
                initial_theme_folder = remembered_path
        
        # ----------------------------
        # Main layout
        # ----------------------------
        self.main_frame = tk.Frame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_propagate(True)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=0)
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=0)

        # Canvas
        self.canvas = tk.Canvas(self.main_frame, bg="#202020", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        # Video player manager for video wallpapers (after canvas is created)
        self.video_player_manager = VideoPlayerManager(self.canvas, self.renderer)
        
        # Canvas Zoom buttons frame (separate from canvas so they aren't affected by zoom)
        self.canvas_zoom_frame = tk.Frame(self.main_frame, bg="#2a2a2a")
        self.canvas_zoom_frame.grid(row=0, column=0, sticky="sw", padx=10, pady=10)
        
        self.canvas_zoom_in_btn = tk.Button(
            self.canvas_zoom_frame, text="+", width=3, height=1, font=("Arial", 10, "bold"),
            command=self.canvas_zoom_in, bg="#3a3a3a", fg="white", relief="flat"
        )
        self.canvas_zoom_in_btn.pack(side="top", pady=(0, 2))
        
        self.canvas_zoom_out_btn = tk.Button(
            self.canvas_zoom_frame, text="−", width=3, height=1, font=("Arial", 10, "bold"),
            command=self.canvas_zoom_out, bg="#3a3a3a", fg="white", relief="flat"
        )
        self.canvas_zoom_out_btn.pack(side="top")
        
        # Bezel Edit Overlay Frame (initially hidden)
        self.bezel_edit_overlay = tk.Frame(self.canvas, bg="#2a2a2a", bd=2, relief="raised")
        self._create_bezel_edit_controls()
        
        # Register the root window as drop target for drag-and-drop (delayed to ensure window is ready)
        self.after(100, self._setup_dnd)

        # Preview panel
        self.preview_panel = PreviewPanel(self.main_frame, renderer=self.renderer, width=300)
        self.preview_panel.grid(row=0, column=1, sticky="ns")
        
        # Load initial theme using unified path (skip cleanup and save since no videos exist yet and controls not ready)
        if initial_theme_folder.exists():
            self._load_theme_from_path(initial_theme_folder, skip_cleanup=True, skip_save=True)

        # Controls
        self.controls = tk.Frame(self.main_frame)
        self.controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=8)

        # ----------------------------
        # Frame/Bezel selector - auto-discover available bezels
        # ----------------------------
        self.bezel_options = sorted(self.renderer.BEZEL_OPTIONS.keys())
        
        # Get saved bezel from config (saved in Misc section)
        saved_bezel = self.config.get("Misc", "bezel", fallback="")
        
        # Determine default bezel:
        # 1. If saved_bezel is valid, use it
        # 2. Else if "AYN Thor - Rainbow" exists, use it (default for new users)
        # 3. Else use first in sorted list
        if saved_bezel and saved_bezel in self.bezel_options:
            default_bezel = saved_bezel
        elif "AYN Thor - Rainbow" in self.bezel_options:
            default_bezel = "AYN Thor - Rainbow"
        elif self.bezel_options:
            default_bezel = self.bezel_options[0]
        else:
            default_bezel = "AYN Thor - Rainbow"  # Fallback hardcoded default
        
        self.bezel_var = StringVar(value=default_bezel)
        
        # Load the default bezel
        self.renderer.set_bezel(default_bezel)
        
        # Sync app grid variables from renderer (in case bezel changed them)
        self.app_grid_x_offset = self.renderer.app_grid_x_offset
        self.app_grid_y_offset = self.renderer.app_grid_y_offset
        self.app_grid_width = self.renderer.app_grid_width
        self.app_grid_icon_size = self.renderer.app_grid_icon_size
        self.app_grid_icon_scale = self.renderer.app_grid_icon_scale
        
        # Update zoom levels based on the screen mode that was loaded
        self._update_zoom_levels_for_mode()
        
        # Apply the grid size based on current zoom level
        rows, cols = self.zoom_levels[self.zoom_index]
        if hasattr(self.renderer, "set_grid_size"):
            self.renderer.set_grid_size(rows, cols)
        
        # Calculate dropdown width based on longest option
        max_width = max((len(opt) for opt in self.bezel_options), default=20)
        
        self.bezel_dropdown = ttk.Combobox(
            self.controls,
            textvariable=self.bezel_var,
            values=self.bezel_options,
            state="readonly",
            width=max_width
        )
        self.bezel_dropdown.pack(side="left", padx=(0, 5))
        self.bezel_dropdown.bind("<<ComboboxSelected>>", lambda e: self.change_bezel(self.bezel_var.get()))

        # ----------------------------
        # Buttons
        # ----------------------------
        ttk.Button(self.controls, text="Load Theme", command=self.load_theme).pack(side="left", padx=4)
        ttk.Button(self.controls, text="Refresh Theme", command=self.refresh).pack(side="left", padx=4)
        
        # ----------------------------
        # Screenshot button
        # ----------------------------
        self.screenshot_button = ttk.Button(self.controls, text="Screenshot")
        self.screenshot_button.pack(side="left", padx=4)
        self.screenshot_button.bind("<Button-1>", self._handle_screenshot_click)
        
        # Zoom controls
        ttk.Button(self.controls, text="−", width=3, command=self.zoom_out).pack(side="left", padx=(4))
        ttk.Button(self.controls, text="+", width=3, command=self.zoom_in).pack(side="left", padx=0)
        
        # ----------------------------
        # UI Toggle Variables (for settings dialog)
        # ----------------------------
        self.corner_hints_var = tk.BooleanVar(value=self.renderer.corner_hints_visible)
        self.dock_var = tk.BooleanVar(value=self.renderer.dock_visible)
        self.app_grid_visible = self.empty_apps_visible
        self.populated_apps_visible = self.apps_visible
        self.single_stacked_var = tk.BooleanVar(value=self.single_screen_stacked_mode)
        self._icon_scale_var = tk.IntVar(value=self.logo_size)
        self.empty_slots_var = tk.BooleanVar(value=self.empty_slots)
        self.remember_var = tk.BooleanVar(value=self.remember_last_theme)
        self.bezel_edit_var = tk.BooleanVar(value=False)
        self.video_playback_var = tk.BooleanVar(value=self.video_playback)
        
        # Bezel edit drag state
        self._dragging_handle = None
        self._drag_start_pos = None
        self._drag_start_values = None
        
        # ----------------------------
        # Settings button (right-aligned)
        # ----------------------------
        self.settings_button = ttk.Button(
            self.controls,
            text="Settings",
            command=self.open_settings
        )
        self.settings_button.pack(side="right", padx=4)
        
        # ----------------------------
        # Bezel Edit Mode button (left of Settings)
        # ----------------------------
        self.bezel_edit_btn = ttk.Button(
            self.controls,
            text="Bezel Edit Mode",
            command=self.toggle_bezel_edit_mode
        )
        self.bezel_edit_btn.pack(side="right", padx=4)
        
        # ----------------------------
        # Canvas and keyboard binds
        # ----------------------------
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_resize_complete)
        
        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)  # Track mouse position for magnify window
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)  # Mouse drag
        self.canvas.bind("<Enter>", self._on_canvas_enter)  # Mouse enters canvas
        self.canvas.bind("<Leave>", self._on_canvas_leave)  # Mouse leaves canvas
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_left_release)
        
        self.bind("<Left>", lambda e: self.move_selection(-1, 0))
        self.bind("<Right>", lambda e: self.move_selection(1, 0))
        self.bind("<Up>", lambda e: self.move_selection(0, -1))
        self.bind("<Down>", lambda e: self.move_selection(0, 1))
        self.bind("<minus>", lambda e: self.zoom_out())
        self.bind("<equal>", lambda e: self.zoom_in())
        self.bind("<plus>", lambda e: self.zoom_in())
        
        # Additional keyboard shortcuts
        self.bind("<Tab>", self.cycle_bezel)
        self.bind("<Shift-Tab>", self.cycle_bezel_backward)
        self.bind("<Key-l>", lambda e: self.load_theme())
        self.bind("<Key-r>", lambda e: self.refresh())
        self.bind("<Key-s>", lambda e: self.take_screenshot())
        self.bind("<Control-s>", lambda e: self.take_screenshot(clean=True))
        self.bind("<Escape>", lambda e: self.open_settings())


        # ----------------------------
        # Apply zoom and start loop
        # ----------------------------
        self._apply_zoom()
        self._apply_canvas_zoom()
        self.update_idletasks()
        self.redraw()
        self._schedule_gif_redraw()
        
    # ----------------------------
    # Canvas resize
    # ----------------------------
    def _on_canvas_resize(self, event):
        """Canvas configure event - redraw on resize."""
        w, h = event.width, event.height
        if w > 1 and h > 1:
            self._do_resize_with_size(w, h)
    
    def _on_canvas_resize_complete(self, event):
        """Force final redraw when mouse is released after resize."""
        # User interaction ended - resume video updates
        self._user_interacting = False
        self._do_resize_with_size(self.canvas.winfo_width(), self.canvas.winfo_height())
    
    def _on_canvas_drag(self, event):
        """Handle mouse drag on canvas - pause video updates during drag."""
        self._user_interacting = True
    
    def _on_canvas_enter(self, event):
        """Handle mouse entering canvas - pause video updates."""
        self._user_interacting = True
    
    def _on_canvas_leave(self, event):
        """Handle mouse leaving canvas - resume video updates."""
        self._user_interacting = False
    
    def _do_resize_with_size(self, w, h):
        """Redraw with specific dimensions."""
        if w > 1 and h > 1:
            size = (w, h)
            if getattr(self, "_last_canvas_size", None) != size:
                self._last_canvas_size = size
                self.renderer._invalidate_static_cache()
                # Reset zoom animation on resize so grid snaps to correct size
                self.renderer._zoom_anim_start = None
                self.renderer._zoom_anim_from = None
                self.renderer._zoom_anim_to = None
                # Reset selection animation on resize so it snaps instantly
                self.renderer._selected_anim_x = None
                self.renderer._selected_anim_y = None
                self.renderer._selected_anim_w = None
                self.renderer._selected_anim_h = None
                self.renderer._sel_anim_from = None
                self.renderer._sel_anim_to = None
                self.renderer._sel_anim_start = None
                # Recalculate scroll position instantly (no animation) to account for changed cell sizes
                self._update_grid_scroll(instant=True)
                # Recalculate offset for new window size (if in stacked mode)
                if self.single_screen_stacked_mode:
                    rows = self.renderer.GRID_ROWS
                    self._apply_stacked_offset(rows)
                # Update video player positions if any
                self._update_video_positions()
                self.redraw()

    def cycle_bezel(self, event):
        # Get current index
        current_index = self.bezel_options.index(self.bezel_var.get())
        # Move to next index, wrap around
        next_index = (current_index + 1) % len(self.bezel_options)
        # Update dropdown and renderer
        self.bezel_var.set(self.bezel_options[next_index])
        self.change_bezel(self.bezel_options[next_index])
        return "break"  # Prevent default tab behavior (focus change)
    
    def cycle_bezel_backward(self, event):
        # Get current index
        current_index = self.bezel_options.index(self.bezel_var.get())
        # Move to previous index, wrap around
        prev_index = (current_index - 1) % len(self.bezel_options)
        # Update dropdown and renderer
        self.bezel_var.set(self.bezel_options[prev_index])
        self.change_bezel(self.bezel_options[prev_index])
        return "break"  # Prevent default focus change
    
    def toggle_remember_last_theme(self):
        self.remember_last_theme = self.remember_var.get()
        self.save_settings()
    
    def open_settings(self):
        if not hasattr(self, '_settings_dialog') or not self._settings_dialog.winfo_exists():
            from widgets.settings_dialog import SettingsDialog
            self._settings_dialog = SettingsDialog(self, app=self)
        else:
            self._settings_dialog.lift()
            self._settings_dialog.focus_force()
            self._settings_dialog.update_from_app()
    
    def toggle_empty_slots(self):
        # Update both App and Renderer
        self.empty_slots = self.empty_slots_var.get()
        self.renderer.show_empty_slots = self.empty_slots
        self.renderer._grid_items_dirty = True
        
        # Save to settings.ini immediately
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        self.config["Settings"]["empty_slots"] = str(self.empty_slots)
        with open(self.settings_path, "w") as f:
            self.config.write(f)

        # Redraw UI to reflect change immediately
        self.redraw()
        
        # After redraw, clamp selection and update scroll
        if self.renderer.grid_items:
            self.renderer.selected_index = max(0, min(self.renderer.selected_index, len(self.renderer.grid_items) - 1))
        
        # Update scroll to show current selection (after grid is rebuilt)
        self._update_grid_scroll()
    
    def _load_folder_color_previews(self):
        """
        Loads all default folder color images once for menu preview use.
        """
        if getattr(self, "_folder_color_previews_loaded", False):
            return

        from pathlib import Path
        from PIL import Image

        self.folder_color_previews = {}

        folder_dir = Path(__file__).parent / "assets" / "default folder"

        for img_path in folder_dir.glob("icon*.png"):
            stem = img_path.stem.lower()

            # Extract color from names like:
            # icon.png -> blue (default)
            # icon_blue.png -> blue
            # icon_gray.png -> gray

            if "_" in stem:
                color_name = stem.split("_")[-1]
            else:
                # If it's just "icon.png", assume it's blue (or whatever your default is)
                color_name = "blue"
            try:
                img = Image.open(img_path).convert("RGBA")
                self.folder_color_previews[color_name] = img
            except Exception:
                pass

        self._folder_color_previews_loaded = True
    
    # -------------------------------------------------
    # Automatic GIF/WebP redraw for top screen
    # -------------------------------------------------
    def _schedule_gif_redraw(self):
        """
        Automatically advance and redraw top/bottom wallpapers and selected hero.
        Uses accurate timing based on animation durations.
        """
        # Advance top wallpaper if animated
        if getattr(self.renderer, "wallpaper_top_frames", None):
            self.renderer.advance_wallpaper_frame()

        # Advance bottom wallpaper if animated
        if getattr(self.renderer, "wallpaper_bottom_frames", None):
            self.renderer.advance_bottom_wallpaper_frame()

        # Advance selected hero (if animated)
        self.renderer.advance_selected_hero()
        
        # Advance selected logo (if animated)
        self.renderer.advance_selected_logo()
        
        # Advance game images (if animated)
        self.renderer.advance_game_images()

        # Redraw canvas
        self.redraw()

        # Use 16ms timer for ~60 FPS animation
        self.after(16, self._schedule_gif_redraw)
    
    # -------------------------------------------------
    # PIL Video frame updates
    # -------------------------------------------------
    def _schedule_pil_video_update(self):
        """Schedule update for PIL video frames with hybrid idle/interval scheduling."""
        # Skip video updates entirely if video playback is disabled
        if not getattr(self, 'video_playback', True):
            return
        
        import time
        
        # Check elapsed time since last update
        current_time = time.time()
        last_update = getattr(self, '_last_video_update', 0)
        elapsed = current_time - last_update
        
        # Minimum interval to keep UI responsive (150ms = ~6 FPS)
        min_interval = 0.150
        
        # If not enough time has passed, schedule normally and exit
        if elapsed < min_interval:
            wait_time = int((min_interval - elapsed) * 1000)
            self._pil_video_timer_id = self.after(wait_time, self._schedule_pil_video_update)
            return
        
        # Skip video updates during user interaction for better UI responsiveness
        if getattr(self, '_user_interacting', False):
            self._pil_video_timer_id = self.after(50, self._schedule_pil_video_update)
            return
        
        # Update frames for PIL-based video players directly to canvas
        if hasattr(self, 'video_player_manager'):
            has_players = len(self.video_player_manager.players) > 0 if hasattr(self.video_player_manager, 'players') else False
            if has_players:
                # Check if in single-screen stacked mode for ss_mask
                is_single_stacked = (
                    self.renderer.screen_manager.screen_mode == "single" and 
                    getattr(self.renderer, '_single_screen_stacked', False)
                )
                ss_mask = getattr(self.renderer, 'ss_mask', None)
                
                # Get canvas dimensions for geometry calculation
                canvas_w = self.canvas.winfo_width()
                canvas_h = self.canvas.winfo_height()
                bezel_scale = min(
                    (canvas_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.width,
                    (canvas_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.height
                )
                device_x = self.renderer.DEVICE_PADDING + (canvas_w - 2 * self.renderer.DEVICE_PADDING - round(self.renderer.bezel_img.width * bezel_scale)) // 2
                device_y = self.renderer.DEVICE_PADDING + (canvas_h - 2 * self.renderer.DEVICE_PADDING - round(self.renderer.bezel_img.height * bezel_scale)) // 2
            
                # Get main screen geometry
                main_screen_geometry = None
                main_screen = getattr(self.renderer.screen_manager, 'main', None)
                if main_screen:
                    main_screen_geometry = (
                        device_x + round(main_screen.x * bezel_scale),
                        device_y + round(main_screen.y * bezel_scale),
                        round(main_screen.w * bezel_scale),
                        round(main_screen.h * bezel_scale)
                    )
                    # Apply canvas zoom if needed (to match _get_screen_geometry)
                    canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                    if canvas_zoom != 1.0:
                        zoomed_w = int(canvas_w * canvas_zoom)
                        zoomed_h = int(canvas_h * canvas_zoom)
                        offset_x = (zoomed_w - canvas_w) // 2
                        offset_y = (zoomed_h - canvas_h) // 2
                        main_screen_geometry = (
                            int(main_screen_geometry[0] * canvas_zoom - offset_x),
                            int(main_screen_geometry[1] * canvas_zoom - offset_y),
                            int(main_screen_geometry[2] * canvas_zoom),
                            int(main_screen_geometry[3] * canvas_zoom)
                        )
                
                # Get external screen geometry for overlap calculation
                external_screen_geometry = None
                ext_screen = getattr(self.renderer.screen_manager, 'external', None)
                if ext_screen:
                    external_screen_geometry = (
                        device_x + round(ext_screen.x * bezel_scale),
                        device_y + round(ext_screen.y * bezel_scale),
                        round(ext_screen.w * bezel_scale),
                        round(ext_screen.h * bezel_scale)
                    )
                    # Apply canvas zoom if needed (to match _get_screen_geometry)
                    canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                    if canvas_zoom != 1.0:
                        zoomed_w = int(canvas_w * canvas_zoom)
                        zoomed_h = int(canvas_h * canvas_zoom)
                        offset_x = (zoomed_w - canvas_w) // 2
                        offset_y = (zoomed_h - canvas_h) // 2
                        external_screen_geometry = (
                            int(external_screen_geometry[0] * canvas_zoom - offset_x),
                            int(external_screen_geometry[1] * canvas_zoom - offset_y),
                            int(external_screen_geometry[2] * canvas_zoom),
                            int(external_screen_geometry[3] * canvas_zoom)
                        )
                
                # Measure ONLY the rendering time (not setup)
                render_start = time.time()
                self.video_player_manager.update_canvas_frames(
                    self.canvas,
                    is_single_stacked=is_single_stacked,
                    ss_mask=ss_mask,
                    main_screen_geometry=main_screen_geometry,
                    external_screen_geometry=external_screen_geometry
                )
                render_time = time.time() - render_start
            else:
                render_time = 0
        else:
            render_time = 0
        
        # Record update time
        self._last_video_update = time.time()
        
        # Schedule next update with fixed interval for predictable performance
        # Using 150ms interval (~6 FPS) which gives more time for UI responsiveness
        self._pil_video_timer_id = self.after(150, self._schedule_pil_video_update)
    
    def _stop_pil_video_updates(self):
        """Stop the PIL video update timer."""
        if hasattr(self, '_pil_video_timer_id') and self._pil_video_timer_id:
            self.after_cancel(self._pil_video_timer_id)
            self._pil_video_timer_id = None
    
    # -------------------------------------------------
    # Frame color callback
    # -------------------------------------------------
    def change_bezel(self, selection):
        # Exit bezel edit mode if active
        if self.renderer.bezel_edit_mode:
            if self.renderer.has_unsaved_changes():
                result = self._ask_apply_or_revert()
                if result == "apply":
                    self.renderer.apply_bezel_changes()
                elif result == "revert":
                    self.renderer.revert_bezel_changes()
                else:
                    # Cancelled - revert to previous bezel selection
                    self.bezel_var.set(self.renderer.current_bezel_name)
                    return
            else:
                self.renderer.exit_bezel_edit_mode()
            
            self.bezel_edit_var.set(False)
            self._update_bezel_edit_overlay()
        
        # Check if device has JSON data
        filename = self.renderer.BEZEL_INFO.get(selection, ("", "dual"))[0]
        if filename:
            parts = filename.split("/")
            if len(parts) >= 2:
                device_name = parts[1]
                if device_name not in self.renderer.DEVICES:
                    # Ask user if they want to set up the bezel
                    if not self._ask_setup_new_bezel(device_name):
                        # User declined - revert to previous bezel
                        self.bezel_var.set(self.renderer.current_bezel_name)
                        return
                    # User wants to set up - will enter bezel edit mode after setting bezel
                    self._pending_bezel_setup = True
        
        self.renderer.set_bezel(selection)
        
        # This is a band aid solution to fixing the background scroll from freezing on bezel switching.
        # If you can fix it please do <3
        self._do_resize_with_size(self.canvas.winfo_width(), self.canvas.winfo_height())
        
        # Update video positions after bezel change
        self._update_video_positions()
        
        # Save the bezel selection to settings
        self.save_settings()
        
        # Sync app grid variables from renderer (in case bezel changed them)
        self.app_grid_x_offset = self.renderer.app_grid_x_offset
        self.app_grid_y_offset = self.renderer.app_grid_y_offset
        self.app_grid_width = self.renderer.app_grid_width
        self.app_grid_icon_size = self.renderer.app_grid_icon_size
        self.app_grid_icon_scale = self.renderer.app_grid_icon_scale
        
        # Update zoom levels and smart-preserve zoom level
        old_rows = self.renderer.GRID_ROWS
        self._update_zoom_levels_for_mode()
        
        # Find closest matching zoom in new set (match by row count)
        best_idx = 0
        best_diff = float('inf')
        for i, (rows, cols) in enumerate(self.zoom_levels):
            diff = abs(rows - old_rows)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        self.zoom_index = best_idx
        
        # Get new zoom dimensions
        new_rows, new_cols = self.zoom_levels[self.zoom_index]
        
        # DIRECTLY set grid dimensions (no animation for bezel switches)
        self.renderer.GRID_ROWS = new_rows
        self.renderer.GRID_COLS = new_cols
        self.renderer._current_grid_rows = float(new_rows)
        self.renderer._current_grid_cols = float(new_cols)
        
        # Recalculate offset for new device's screen size (if in stacked mode)
        # This ensures SINGLE_SCREEN_MAIN_OFFSET is correct for the new device
        if self.single_screen_stacked_mode:
            self._apply_stacked_offset(new_rows)
        
        # Mark caches for rebuild (CRITICAL for visual update)
        self.renderer._grid_items_dirty = True
        self.renderer._static_cache_dirty = True
        self.renderer._resize_cache.clear()
        
        # Snap grid position instantly (no animation)
        self.renderer.grid_scroll_x = 0
        self.renderer._grid_scroll_target = 0
        self.renderer._grid_scroll_from = 0
        self.renderer._grid_scroll_start = None
        
        # Reset zoom animation so it snaps to new size
        self.renderer._zoom_anim_start = None
        self.renderer._zoom_anim_from = None
        self.renderer._zoom_anim_to = None
        self.renderer._zoom_ended_needs_snap = False
        
        # Reset selection animation so it snaps to new position
        self.renderer._reset_selection_animation()
        
        # Redraw to apply the changes
        self.redraw()
        
        self._update_single_screen_controls_visibility()
        
        self.canvas.focus_set()

    def _handle_screenshot_click(self, event):
        # 0x0004 = Control key mask in Tkinter
        ctrl_pressed = (event.state & 0x0004) != 0
        self.take_screenshot(clean=ctrl_pressed)
    
    def take_screenshot(self, clean=False):
        """Take a screenshot of the device including surrounding padding and save as PNG."""
        
        # Invalidate cache to ensure fresh render
        self.renderer._invalidate_static_cache()
        
        # Update video positions to match current canvas state
        self._update_video_positions()
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return

        # -----------------------------
        # High-res factor
        # -----------------------------
        RES_FACTOR = 2
        render_w = canvas_w * RES_FACTOR
        render_h = canvas_h * RES_FACTOR

        # -----------------------------
        # Compute device rectangle first (needed for video and content positioning)
        # -----------------------------
        pad = self.renderer.DEVICE_PADDING * RES_FACTOR

        scale = min(
            (canvas_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.width,
            (canvas_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.height
        )

        device_w = round(self.renderer.bezel_img.width * scale * RES_FACTOR)
        device_h = round(self.renderer.bezel_img.height * scale * RES_FACTOR)
        device_x = pad + (render_w - 2 * pad - device_w) // 2
        device_y = pad + (render_h - 2 * pad - device_h) // 2

        # -----------------------------
        # Add video wallpapers FIRST (behind content)
        # -----------------------------
        # Get video frames for screenshot
        # -----------------------------
        video_layer = Image.new('RGBA', (render_w, render_h), (0, 0, 0, 0))
        
        video_found = False
        if hasattr(self, 'video_player_manager'):
            # Check if in single-screen stacked mode (need to apply ss_mask to main screen video)
            is_single_stacked = (
                self.renderer.screen_manager.screen_mode == "single" and 
                getattr(self.renderer, '_single_screen_stacked', False)
            )
            
            # Get external screen geometry for overlap calculation
            ext_screen = self.renderer.screen_manager.external
            
            for screen_name, player in self.video_player_manager.players.items():
                frame = player.get_current_frame() if hasattr(player, 'get_current_frame') else None
                if frame:
                    video_found = True
                    
                    # Calculate video position matching high-res composite rendering
                    # (same way renderer calculates wallpaper positions at high-res)
                    # Use render dimensions - but DON'T multiply DEVICE_PADDING by RES_FACTOR
                    # (renderer uses canvas_size directly without scaling padding)
                    bezel_scale_hires = min(
                        (render_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.width,
                        (render_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.height
                    )
                    
                    device_x = self.renderer.DEVICE_PADDING + (render_w - 2 * self.renderer.DEVICE_PADDING - round(self.renderer.bezel_img.width * bezel_scale_hires)) // 2
                    device_y = self.renderer.DEVICE_PADDING + (render_h - 2 * self.renderer.DEVICE_PADDING - round(self.renderer.bezel_img.height * bezel_scale_hires)) // 2
                    
                    screen = getattr(self.renderer.screen_manager, screen_name, None)
                    if screen:
                        screen_x = device_x + round(screen.x * bezel_scale_hires)
                        screen_y = device_y + round(screen.y * bezel_scale_hires)
                        screen_w = round(screen.w * bezel_scale_hires)
                        screen_h = round(screen.h * bezel_scale_hires)
                        
                        video_x = int(screen_x)
                        video_y = int(screen_y)
                        video_w = int(screen_w)
                        video_h = int(screen_h)
                        
                        video_img = frame.resize((video_w, video_h), Image.Resampling.BILINEAR)
                        
                        # Apply ss_mask for main screen in single-screen stacked mode
                        if screen_name == 'main' and is_single_stacked and self.renderer.ss_mask:
                            # Resize ss_mask to main screen size
                            screen_mask = self.renderer.ss_mask.resize((video_w, video_h), Image.Resampling.LANCZOS)
                            # Extract alpha channel as mask
                            if screen_mask.mode == "RGBA":
                                screen_mask = screen_mask.split()[3]
                            elif screen_mask.mode != "L":
                                screen_mask = screen_mask.convert("L")
                            
                            # Create bottom screen mask for clipping (overlap with external screen)
                            if ext_screen:
                                ext_x = device_x + round(ext_screen.x * bezel_scale_hires)
                                ext_y = device_y + round(ext_screen.y * bezel_scale_hires)
                                ext_w = round(ext_screen.w * bezel_scale_hires)
                                ext_h = round(ext_screen.h * bezel_scale_hires)
                                
                                # Calculate overlap area
                                overlap_x1 = max(0, ext_x - video_x)
                                overlap_y1 = max(0, ext_y - video_y)
                                overlap_x2 = min(video_w, ext_x + ext_w - video_x)
                                overlap_y2 = min(video_h, ext_y + ext_h - video_y)
                                
                                if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                                    bottom_mask = Image.new("L", (video_w, video_h), 0)
                                    draw = ImageDraw.Draw(bottom_mask)
                                    draw.rectangle([overlap_x1, overlap_y1, overlap_x2, overlap_y2], fill=255)
                                    # Combine masks
                                    combined_mask = ImageChops.multiply(screen_mask, bottom_mask)
                                else:
                                    combined_mask = screen_mask
                            else:
                                combined_mask = screen_mask
                            
                            # Apply mask to video - apply directly to alpha channel
                            if video_img.mode != "RGBA":
                                video_img = video_img.convert("RGBA")
                            r, g, b, a = video_img.split()
                            a = ImageChops.multiply(a, combined_mask)
                            video_img = Image.merge('RGBA', (r, g, b, a))
                        
                        video_layer.paste(video_img, (video_x, video_y), video_img)

        # -----------------------------
        # Render layers matching live display:
        # 1. BG (full)
        # 2. Video (on top of bg)
        # 3. Content with skip_background=True (on top of video)
        # -----------------------------
        
        # Layer 1: Background (fitted to full render area)
        if clean:
            # For clean screenshot, use transparent background
            base_layer = Image.new('RGBA', (render_w, render_h), (0, 0, 0, 0))
        else:
            # Get background fitted to canvas
            bg_image = self.renderer.get_background_image((render_w, render_h))
            if bg_image:
                bg_image = bg_image.convert('RGBA')
                # Scale bg to fit render size
                bg_image = bg_image.resize((render_w, render_h), Image.Resampling.BILINEAR)
            base_layer = bg_image if bg_image else Image.new('RGBA', (render_w, render_h), (0, 0, 0, 0))
        
        # Render content WITHOUT bg at high-res (matches video positioning)
        content_no_bg = self.renderer.composite((render_w, render_h), skip_background=True)
        
        # Layer 2: Add video on top of bg
        if video_found:
            # Create mask from content alpha - where content is transparent (0), show video
            # where content is opaque (>0), hide video (apps/UI should be on top)
            content_rgba = content_no_bg
            if content_rgba.mode != 'RGBA':
                content_rgba = content_rgba.convert('RGBA')
            
            # Invert content alpha: transparent areas become 255 (show video)
            _, _, _, content_alpha = content_rgba.split()
            video_mask = ImageChops.invert(content_alpha)
            
            # Apply mask to video layer
            video_r, video_g, video_b, video_alpha = video_layer.split()
            video_alpha_masked = ImageChops.multiply(video_alpha, video_mask)
            video_layer_masked = Image.merge('RGBA', (video_r, video_g, video_b, video_alpha_masked))
            
            base_layer = Image.alpha_composite(base_layer, video_layer_masked)
        
        # Layer 3: Content WITHOUT bg (so it shows video/bg through transparent areas)
        full_image = Image.alpha_composite(base_layer, content_no_bg)

        # -----------------------------
        # Compute device rectangle exactly like preview
        # -----------------------------
        pad = self.renderer.DEVICE_PADDING * RES_FACTOR

        scale = min(
            (canvas_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.width,
            (canvas_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.height
        )

        device_w = round(self.renderer.bezel_img.width * scale * RES_FACTOR)
        device_h = round(self.renderer.bezel_img.height * scale * RES_FACTOR)
        device_x = pad + (render_w - 2 * pad - device_w) // 2
        device_y = pad + (render_h - 2 * pad - device_h) // 2

        # Crop rectangle
        if clean:
            # Crop exactly around device (same as preview)
            SCREENSHOT_PADDING = 10 * RES_FACTOR  # 10px padding in high-res space
            left = max(device_x - SCREENSHOT_PADDING, 0)
            top = max(device_y - SCREENSHOT_PADDING, 0)
            right = min(device_x + device_w + SCREENSHOT_PADDING, render_w)
            bottom = min(device_y + device_h + SCREENSHOT_PADDING, render_h)
        else:
            # Regular screenshot: add extra padding (like preview padding)
            SCREENSHOT_PADDING = 20 * RES_FACTOR  # 10px padding in high-res space
            left = max(device_x - SCREENSHOT_PADDING, 0)
            top = max(device_y - SCREENSHOT_PADDING, 0)
            right = min(device_x + device_w + SCREENSHOT_PADDING, render_w)
            bottom = min(device_y + device_h + SCREENSHOT_PADDING, render_h)

        # Crop high-res composite
        screenshot = full_image.crop((left, top, right, bottom))

        # Save screenshot
        screenshots_dir = Path(__file__).parent / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        filename = datetime.now().strftime("%Y%m%d%H%M%S") + ".png"
        path = screenshots_dir / filename

        screenshot.save(path, format="PNG")
        mode = "Clean device" if clean else "Full device"
        print(f"{mode} screenshot saved: {path}") 
        
        
    def load_theme(self):
        folder = filedialog.askdirectory()
        if folder:
            self._load_theme_from_path(Path(folder))

    def _load_theme_from_path(self, theme_path: Path, skip_cleanup: bool = False, skip_save: bool = False):
        """Load a theme from a given path (used by both button and drag-drop).
        
        Args:
            theme_path: Path to the theme folder
            skip_cleanup: If True, skip video cleanup (used for initial boot)
            skip_save: If True, skip saving settings (used for initial boot)
        """
        if theme_path.is_dir():
            # Cleanup old video players - detach VLC first to prevent errors
            # Skip cleanup on initial boot (no videos to clean up yet)
            if not skip_cleanup and hasattr(self, 'video_player_manager'):
                for player in list(self.video_player_manager.players.values()):
                    # Detach VLC from window (only for VLC-based players, not PIL)
                    if hasattr(player, 'player') and player.player:
                        try:
                            player.player.set_hwnd(0)
                        except:
                            pass
                    # Delete canvas window
                    if hasattr(player, 'video_window_id') and player.video_window_id:
                        try:
                            self.canvas.delete(player.video_window_id)
                        except:
                            pass
                        player.video_window_id = None
                    # Delete PIL video canvas image
                    if hasattr(player, '_canvas_image_id') and player._canvas_image_id:
                        try:
                            self.canvas.delete(player._canvas_image_id)
                        except:
                            pass
                        player._canvas_image_id = None
                    # Destroy video frame
                    if hasattr(player, 'video_frame') and player.video_frame:
                        try:
                            player.video_frame.destroy()
                        except:
                            pass
                        player.video_frame = None
                    # Release VLC (only for VLC-based players, not PIL)
                    if hasattr(player, 'player') and player.player:
                        try:
                            player.player.release()
                        except:
                            pass
                        player.player = None
                self.video_player_manager.players.clear()
                
                # Stop the old video timer to prevent lag
                if hasattr(self, '_pil_video_timer_id') and self._pil_video_timer_id:
                    self.after_cancel(self._pil_video_timer_id)
                    self._pil_video_timer_id = None
            
            # Load new theme
            self.renderer.load_theme(theme_path, max_grid_items=self.max_grid_slots)
            
            # Refresh preview panel
            self.preview_panel.refresh()
            
            # Check if there are video wallpapers
            main_screen = self.renderer.screen_manager.main
            external_screen = self.renderer.screen_manager.external
            has_video = (main_screen.wallpaper_is_video and main_screen.wallpaper_video_path) or \
                       (external_screen.wallpaper_is_video and external_screen.wallpaper_video_path)
            
            if has_video:
                # Skip video setup if video playback is disabled
                if not getattr(self, 'video_playback', True):
                    # Disable video wallpaper mode to show static first frame
                    self.renderer.screen_manager.main.disable_video_wallpaper()
                    self.renderer.screen_manager.external.disable_video_wallpaper()
                    # Clean up any existing video players
                    if hasattr(self, 'video_player_manager'):
                        self.video_player_manager.cleanup()
                    self._stop_pil_video_updates()
                    # Invalidate cache to force re-render with static wallpaper
                    self.renderer._invalidate_static_cache()
                    # Show static first frame via regular wallpaper rendering
                    self.redraw()
                else:
                    # Re-enable video wallpaper mode before setting up videos
                    self.renderer.screen_manager.main.reenable_video_wallpaper()
                    self.renderer.screen_manager.external.reenable_video_wallpaper()
                    # Setup videos with retry - redraw will happen when video starts playing
                    self._try_setup_videos_with_retry(on_video_ready_callback=self._on_video_playing)
            else:
                # No videos, redraw immediately
                self._setup_video_wallpapers()
                self.redraw()
            
            self.last_theme_path = str(theme_path)
            if not skip_save:
                self.save_settings()
    
    def _on_video_playing(self):
        """Callback when video starts playing - now safe to draw content."""
        self.redraw()
        # Lower videos to be just above BG (not below everything)
        # This ensures: BG < video < content
        if hasattr(self, 'video_player_manager') and hasattr(self.video_player_manager, 'lower_all_videos'):
            # Get BG canvas items
            bg_id = getattr(self, '_canvas_bg_id', None)
            bg_id_2 = getattr(self, '_canvas_bg_id_2', None)
            
            # Lower videos to just above BG
            for player in self.video_player_manager.players.values():
                canvas_id = getattr(player, '_canvas_image_id', None)
                if canvas_id:
                    if bg_id:
                        self.canvas.tag_lower(canvas_id, bg_id)
                    if bg_id_2:
                        self.canvas.tag_lower(canvas_id, bg_id_2)
        
        # Force redraw like canvas zoom does to fix layering
        self.renderer._invalidate_static_cache()
        self.redraw()
        self._update_video_positions()
    
    def _try_setup_videos_with_retry(self, on_video_ready_callback=None, retry_count=0, max_retries=5):
        """Try to setup videos, retrying if canvas isn't ready yet."""
        # Check if videos were created
        self.update_idletasks()
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # If canvas not ready, retry after delay
        if canvas_w <= 1 or canvas_h <= 1:
            if retry_count < max_retries:
                self.after(50, lambda: self._try_setup_videos_with_retry(
                    on_video_ready_callback=on_video_ready_callback,
                    retry_count=retry_count + 1,
                    max_retries=max_retries
                ))
            return
        
        # Canvas is ready, setup videos
        self._setup_video_wallpapers(on_video_ready_callback=on_video_ready_callback)
        
        # Check if videos were actually created (may have failed due to other reasons)
        # Skip retry if video playback is disabled (we intentionally didn't create players)
        if (getattr(self, 'video_playback', True) and 
            retry_count < max_retries and 
            hasattr(self, 'video_player_manager') and
            len(self.video_player_manager.players) == 0):
            # Videos weren't created, try again
            self.after(50, lambda: self._try_setup_videos_with_retry(
                on_video_ready_callback=on_video_ready_callback,
                retry_count=retry_count + 1,
                max_retries=max_retries
            ))
    
    def _setup_video_wallpapers(self, on_video_ready_callback=None):
        """Setup video players for video wallpapers.
        
        Args:
            on_video_ready_callback: Called when video starts playing
        """
        # Disable video setup entirely if video playback is disabled
        # Clean up any existing players and use static first frame instead
        if not getattr(self, 'video_playback', True):
            # Clean up any existing video players from previous theme
            if hasattr(self, 'video_player_manager'):
                self.video_player_manager.cleanup()
            # Stop any scheduled video updates
            self._stop_pil_video_updates()
            return
        
        main_has_video = False
        external_has_video = False
        
        # Check external screen first (rendered behind in single-screen stacked mode)
        external_screen = self.renderer.screen_manager.external
        if external_screen.wallpaper_is_video and external_screen.wallpaper_video_path:
            geometry = self._get_screen_geometry('external')
            if geometry:
                # Use PIL-based player to fix Z-order issues
                self.video_player_manager.create_player('external', external_screen.wallpaper_video_path, geometry, use_pil=True)
                self.video_player_manager.play('external', on_playing_callback=on_video_ready_callback)
                external_has_video = True
        
        # Check main screen second (rendered in front in single-screen stacked mode)
        main_screen = self.renderer.screen_manager.main
        if main_screen.wallpaper_is_video and main_screen.wallpaper_video_path:
            geometry = self._get_screen_geometry('main')
            if geometry:
                # Use PIL-based player to fix Z-order issues
                self.video_player_manager.create_player('main', main_screen.wallpaper_video_path, geometry, use_pil=True)
                # Always call callback for main screen to ensure redraw happens
                self.video_player_manager.play('main', on_playing_callback=on_video_ready_callback)
                main_has_video = True
        
        # If no videos at all but callback provided, call it immediately
        if not main_has_video and not external_has_video and on_video_ready_callback:
            on_video_ready_callback()
        
        # Ensure video update timer is started if videos were created (only if video playback is enabled)
        if (main_has_video or external_has_video) and getattr(self, 'video_playback', True):
            self._schedule_pil_video_update()
            # Lower videos to be behind content
            if hasattr(self.video_player_manager, 'lower_all_videos'):
                self.video_player_manager.lower_all_videos(self.canvas)
    
    def _get_screen_geometry(self, screen_name: str):
        """Get screen geometry in canvas coordinates for video positioning.
        
        This should match how the renderer draws wallpapers in composite().
        """
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w <= 1 or canvas_h <= 1:
            return None
        
        # Get canvas zoom
        canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
        
        # Calculate bezel scale the same way the renderer does - scale to fit canvas
        bezel_scale = min(
            (canvas_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.width,
            (canvas_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.height
        )
        
        # Calculate bezel position within canvas (centered with padding) - matches renderer
        device_w = round(self.renderer.bezel_img.width * bezel_scale)
        device_h = round(self.renderer.bezel_img.height * bezel_scale)
        device_x = self.renderer.DEVICE_PADDING + (canvas_w - 2 * self.renderer.DEVICE_PADDING - device_w) // 2
        device_y = self.renderer.DEVICE_PADDING + (canvas_h - 2 * self.renderer.DEVICE_PADDING - device_h) // 2
        
        # Get the screen
        if screen_name == 'main':
            screen = self.renderer.screen_manager.main
        else:
            screen = self.renderer.screen_manager.external
        
        # Calculate screen position within bezel (matches renderer's wallpaper drawing)
        screen_x = device_x + round(screen.x * bezel_scale)
        screen_y = device_y + round(screen.y * bezel_scale)
        screen_w = round(screen.w * bezel_scale)
        screen_h = round(screen.h * bezel_scale)
        
        # Apply canvas zoom if needed
        if canvas_zoom != 1.0:
            zoomed_w = int(canvas_w * canvas_zoom)
            zoomed_h = int(canvas_h * canvas_zoom)
            offset_x = (zoomed_w - canvas_w) // 2
            offset_y = (zoomed_h - canvas_h) // 2
            
            screen_x = screen_x * canvas_zoom - offset_x
            screen_y = screen_y * canvas_zoom - offset_y
            screen_w = screen_w * canvas_zoom
            screen_h = screen_h * canvas_zoom
        
        return (screen_x, screen_y, screen_w, screen_h)
    
    def _update_video_positions(self):
        """Update video player positions (e.g., after resize or screen drag)."""
        if not hasattr(self, 'video_player_manager'):
            return
        
        # Update main screen video position
        if self.video_player_manager.has_player('main'):
            geometry = self._get_screen_geometry('main')
            if geometry:
                self.video_player_manager.update_geometry('main', geometry)
        
        # Update external screen video position
        if self.video_player_manager.has_player('external'):
            geometry = self._get_screen_geometry('external')
            if geometry:
                self.video_player_manager.update_geometry('external', geometry)
    
    def _update_video_mask_overlay(self):
        """Create or update mask overlay for single-screen stacked mode video."""
        if not hasattr(self, 'video_player_manager'):
            return
        
        # Check renderer is ready
        if not hasattr(self, 'renderer') or not self.renderer.bezel_img:
            return
        
        # Skip mask overlay when using PIL-based video - masking is already applied in apply_ss_mask()
        # Only use overlay for non-PIL video (like VLC)
        if hasattr(self.video_player_manager, 'players'):
            from video_player import PILVideoPlayer
            for screen_name, player in self.video_player_manager.players.items():
                if isinstance(player, PILVideoPlayer):
                    # PIL video - mask is applied in apply_ss_mask(), skip overlay
                    # Remove existing mask if present
                    mask_id = getattr(self, '_canvas_mask_id', None)
                    if mask_id is not None and mask_id != 0:
                        self.canvas.delete(mask_id)
                        self._canvas_mask_id = None
                    return
        
        # Check renderer is ready
        if not hasattr(self, 'renderer') or not self.renderer.bezel_img:
            return
        
        # Skip mask overlay when using PIL-based video - masking is already applied in apply_ss_mask()
        # Only use overlay for non-PIL video (like VLC)
        if hasattr(self.video_player_manager, 'players'):
            for screen_name, player in self.video_player_manager.players.items():
                if hasattr(player, '_use_pil') and player._use_pil:
                    # PIL video - mask is applied in apply_ss_mask(), skip overlay
                    # Remove existing mask if present
                    mask_id = getattr(self, '_canvas_mask_id', None)
                    if mask_id is not None and mask_id != 0:
                        self.canvas.delete(mask_id)
                        self._canvas_mask_id = None
                    return
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Get mask overlay from renderer
        mask_overlay, pos = self.renderer.get_video_mask_overlay((canvas_w, canvas_h))
        
        # If we have a mask and main video, create/update overlay
        if mask_overlay is not None and pos and self.video_player_manager.has_player('main'):
            x, y, w, h = pos
            
            # Convert PIL image to Tkinter
            self.tk_mask_img = ImageTk.PhotoImage(mask_overlay)
            
            mask_id = getattr(self, '_canvas_mask_id', None)
            if mask_id is None or mask_id == 0:
                self._canvas_mask_id = self.canvas.create_image(x + w//2, y + h//2, anchor="center", image=self.tk_mask_img)
            else:
                self.canvas.coords(mask_id, x + w//2, y + h//2)
                self.canvas.itemconfig(mask_id, image=self.tk_mask_img)
            
            # Raise mask above main video window (main is already below content, so mask will be too)
            mask_id = getattr(self, '_canvas_mask_id', None)
            if mask_id is not None and self.video_player_manager.has_player('main'):
                main_window_id = self.video_player_manager.get_player_window_id('main')
                if main_window_id is not None:
                    self.canvas.tag_raise(mask_id, main_window_id)
        else:
            # No mask needed - remove existing mask
            mask_id = getattr(self, '_canvas_mask_id', None)
            if mask_id is not None and mask_id != 0:
                self.canvas.delete(mask_id)
                self._canvas_mask_id = None
    
    def _on_theme_drop(self, event):
        """Handle folder drop from file explorer."""
        # Parse dropped path(s) - format can be: {C:/path/to/folder} or multiple paths
        data = event.data
        paths = []
        
        # Handle Windows format with curly braces
        if data.startswith('{'):
            # Split by } { pattern
            parts = data.split('} {')
            for part in parts:
                part = part.strip('{}')
                if part:
                    paths.append(part)
        else:
            paths = data.split()
        
        # Load first valid directory
        for path_str in paths:
            path = Path(path_str)
            if path.is_dir():
                self._load_theme_from_path(path)
                break
    
    def _setup_dnd(self):
        """Set up drag-and-drop after window is ready."""
        # Register root window as drop target
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_theme_drop)
        
        # Also register main_frame and canvas
        self.main_frame.drop_target_register(DND_FILES)
        self.main_frame.dnd_bind('<<Drop>>', self._on_theme_drop)
        
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind('<<Drop>>', self._on_theme_drop)


    def refresh(self):
        # Refresh bezel list in case new ones were added/removed
        self.renderer.discover_bezels()
        self.bezel_options = sorted(self.renderer.BEZEL_OPTIONS.keys())
        
        # Update the dropdown with new options
        if hasattr(self, 'bezel_dropdown'):
            self.bezel_dropdown['values'] = self.bezel_options
        
        # Reload current theme using full method that handles video setup properly
        self._load_theme_from_path(self.renderer.theme_path, skip_cleanup=False, skip_save=True)
        self.preview_panel.refresh()
        
        # Trigger resize handling to properly update video positions and caches
        self._do_resize_with_size(self.canvas.winfo_width(), self.canvas.winfo_height())
        
    def toggle_corner_hints(self):
        self.renderer.corner_hints_visible = self.corner_hints_var.get()
        self.renderer._invalidate_static_cache()
        self.save_settings()
        self.redraw()
    
    def toggle_dock(self):
        self.renderer.dock_visible = self.dock_var.get()
        self.renderer._invalidate_static_cache()
        self.save_settings()
        self.redraw()
    
    def toggle_app_grid(self):
        self.renderer.app_grid_visible = self.app_grid_visible
        self.empty_apps_visible = self.app_grid_visible
        
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        self.config["Settings"]["empty_apps"] = str(self.empty_apps_visible)
        with open(self.settings_path, "w") as f:
            self.config.write(f)
        
        self.redraw()
    
    def toggle_populated_apps(self):
        self.renderer.populated_apps_visible = self.populated_apps_visible
        self.apps_visible = self.populated_apps_visible
        
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        self.config["Settings"]["apps"] = str(self.apps_visible)
        with open(self.settings_path, "w") as f:
            self.config.write(f)
        
        self.redraw()
    
    # -------------------------------------------------
    # Debug controls
    # -------------------------------------------------
    def _get_scaled_screen_rects(self):
        """Get scaled screen rectangles for current canvas size."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        pad = self.renderer.DEVICE_PADDING
        
        if self.renderer.bezel_img is None:
            return None, None, None
        
        scale = min(
            (canvas_w - 2 * pad) / self.renderer.bezel_img.width,
            (canvas_h - 2 * pad) / self.renderer.bezel_img.height
        )
        
        device_w = round(self.renderer.bezel_img.width * scale)
        device_h = round(self.renderer.bezel_img.height * scale)
        device_x = pad + (canvas_w - 2 * pad - device_w) // 2
        device_y = pad + (canvas_h - 2 * pad - device_h) // 2
        
        main = self.renderer.screen_manager.main
        ext = self.renderer.screen_manager.external
        
        main_rect = (
            device_x + round(main.x * scale),
            device_y + round(main.y * scale),
            round(main.w * scale),
            round(main.h * scale)
        )
        
        ext_rect = (
            device_x + round(ext.x * scale),
            device_y + round(ext.y * scale),
            round(ext.w * scale),
            round(ext.h * scale)
        )
        
        grid_rect = ext.get_grid_rect(scale)
        
        return main_rect, ext_rect, grid_rect

    # -------------------------------------------------
    # Toggle single screen stacked mode
    # -------------------------------------------------
    def toggle_single_screen_stacked(self):
        from screen import Screen
        
        self.single_screen_stacked_mode = self.single_stacked_var.get()
        self.renderer._single_screen_stacked = self.single_screen_stacked_mode
        
        # If turning off stacked mode, reset top screen to off-screen position
        if not self.single_screen_stacked_mode:
            Screen.SINGLE_SCREEN_MAIN_OFFSET = -580
            self.renderer.screen_manager._update_single_screen_main_position()
        
        # Smart preserve zoom - find closest matching grid size
        old_rows = self.renderer.GRID_ROWS
        
        # Update zoom levels to new set
        self._update_zoom_levels_for_mode()
        
        # Find best match in new zoom levels (match by row count)
        best_idx = 0
        best_diff = float('inf')
        
        for i, (rows, cols) in enumerate(self.zoom_levels):
            diff = abs(rows - old_rows)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        
        self.zoom_index = best_idx
        
        # Apply new zoom level - DIRECTLY set grid dimensions (no animation for mode switches)
        rows, cols = self.zoom_levels[self.zoom_index]
        self.renderer.GRID_ROWS = rows
        self.renderer.GRID_COLS = cols
        self.renderer._current_grid_rows = float(rows)
        self.renderer._current_grid_cols = float(cols)
        
        # Rebuild grid items with new layout
        self.renderer._grid_items_dirty = True
        
        # Mark caches for rebuild (CRITICAL for visual update)
        self.renderer._static_cache_dirty = True
        self.renderer._resize_cache.clear()
        # Also invalidate clean content cache for magnify window
        self.renderer._cached_clean_content = None
        
        # Save and redraw
        self.save_settings()
        self.redraw()
        
        # Recalculate scroll position to keep selection visible (instant snap)
        self._update_grid_scroll(instant=True)
        
        # Reset zoom animation so it snaps to new size
        self.renderer._zoom_anim_start = None
        self.renderer._zoom_anim_from = None
        self.renderer._zoom_anim_to = None
        self.renderer._zoom_ended_needs_snap = False
        
        # Reset selection animation so it snaps to new position
        self.renderer._reset_selection_animation()
        
        # Redraw again to apply the snap
        self.redraw()
    
    def toggle_bezel_edit_mode(self):
        """Toggle bezel editing mode on/off"""
        # Toggle the state
        new_mode = not self.renderer.bezel_edit_mode
        
        if new_mode:
            # Entering bezel edit mode
            self.renderer.enter_bezel_edit_mode()
            self.bezel_edit_var.set(True)
        else:
            # Exiting bezel edit mode - only ask if there are unsaved changes
            if self.renderer.has_unsaved_changes():
                result = self._ask_apply_or_revert()
                if result == "apply":
                    self.renderer.apply_bezel_changes()
                elif result == "revert":
                    self.renderer.revert_bezel_changes()
                else:
                    # Cancelled, keep edit mode on
                    return
            else:
                # No changes, just exit
                self.renderer.exit_bezel_edit_mode()
            
            self.bezel_edit_var.set(False)
        
        # Show/hide the overlay controls
        self._update_bezel_edit_overlay()
        
        self.redraw()
    
    def _ask_apply_or_revert(self):
        """Ask user whether to apply or revert bezel changes"""
        # Create a custom dialog
        dialog = tk.Toplevel(self)
        dialog.title("Bezel Edit Mode")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("300x120")
        
        result = {"action": "cancel"}
        
        label = tk.Label(dialog, text="Would you like to apply or revert your changes?", pady=10)
        label.pack()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def on_apply():
            result["action"] = "apply"
            dialog.destroy()
        
        def on_revert():
            result["action"] = "revert"
            dialog.destroy()
        
        def on_cancel():
            result["action"] = "cancel"
            dialog.destroy()
        
        apply_btn = tk.Button(button_frame, text="Apply", command=on_apply, width=8)
        apply_btn.pack(side="left", padx=5)
        
        revert_btn = tk.Button(button_frame, text="Revert", command=on_revert, width=8)
        revert_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=on_cancel, width=8)
        cancel_btn.pack(side="left", padx=5)
        
        dialog.wait_window()
        return result["action"]
    
    def _ask_setup_new_bezel(self, device_name: str) -> bool:
        """Ask user if they want to set up a new bezel configuration"""
        dialog = tk.Toplevel(self)
        dialog.title("New Bezel Setup")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.geometry("350x150")
        
        result = {"setup": False}
        
        label = tk.Label(dialog, text=f"No configuration found for {device_name}.\nWould you like to set it up this bezel?", pady=15)
        label.pack()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=15)
        
        def on_yes():
            result["setup"] = True
            dialog.destroy()
        
        def on_no():
            result["setup"] = False
            dialog.destroy()
        
        yes_btn = tk.Button(button_frame, text="Yes", command=on_yes, width=10)
        yes_btn.pack(side="left", padx=10)
        
        no_btn = tk.Button(button_frame, text="No", command=on_no, width=10)
        no_btn.pack(side="left", padx=10)
        
        dialog.wait_window()
        return result["setup"]
    
    def _create_bezel_edit_controls(self):
        """Create tkinter control widgets for bezel edit mode"""
        # Main control frame
        main_frame = tk.Frame(self.bezel_edit_overlay, bg="#2a2a2a")
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Top row: Apply and Revert buttons (right side)
        top_frame = tk.Frame(main_frame, bg="#2a2a2a")
        top_frame.pack(fill="x", pady=(0, 5))
        
        self.apply_button = tk.Button(top_frame, text="Apply", command=self._on_bezel_apply, bg="#4CAF50", fg="white", width=8)
        self.apply_button.pack(side="right", padx=2)
        
        self.revert_button = tk.Button(top_frame, text="Revert", command=self._on_bezel_revert, bg="#f44336", fg="white", width=8)
        self.revert_button.pack(side="right", padx=2)
        
        # Screen amount toggle (left side)
        self.screen_amount_button = tk.Button(top_frame, text="2 Screens", command=self._toggle_screen_amount, width=10)
        self.screen_amount_button.pack(side="left", padx=2)
        
        # Advanced Mode toggle (left side)
        self.advanced_mode_var = tk.BooleanVar(value=False)
        self.advanced_mode_button = tk.Checkbutton(
            top_frame, text="Advanced", variable=self.advanced_mode_var,
            command=self._toggle_advanced_mode, bg="#2a2a2a", fg="white",
            selectcolor="#3a3a3a", activebackground="#2a2a2a"
        )
        self.advanced_mode_button.pack(side="left", padx=(10, 2))
        
        # Store advanced entry widgets and their insert positions for show/hide
        self.advanced_entries = []
        self._entry_insert_after = {}  # entry -> widget to insert after
        
        # App Grid label (centered like Screens label)
        tk.Label(main_frame, text="App Grid", bg="#2a2a2a", fg="white").pack(pady=5)
        
        # App Grid controls
        grid_frame = tk.Frame(main_frame, bg="#3a3a3a", bd=1, relief="sunken")
        grid_frame.pack(fill="x", pady=5)
        
        # Icon Height controls with entry between buttons (entry hidden by default)
        tk.Label(grid_frame, text="Height:", bg="#3a3a3a", fg="red").pack(side="left", padx=5)
        height_minus_btn = tk.Button(grid_frame, text="-", width=2, command=lambda: self._adjust_app_grid("icon_size", -5))
        height_minus_btn.pack(side="left", padx=1)
        self.icon_size_var = tk.StringVar(value=str(self.app_grid_icon_size))
        self.icon_size_entry = tk.Entry(grid_frame, textvariable=self.icon_size_var, width=4)
        self.icon_size_entry.bind("<Return>", lambda e: self._on_entry_change("icon_size"))
        self.advanced_entries.append(self.icon_size_entry)
        self._entry_insert_after[self.icon_size_entry] = height_minus_btn
        tk.Button(grid_frame, text="+", width=2, command=lambda: self._adjust_app_grid("icon_size", 5)).pack(side="left", padx=1)
        
        # Width controls with entry between buttons (entry hidden by default)
        tk.Label(grid_frame, text="Width:", bg="#3a3a3a", fg="red").pack(side="left", padx=(10, 0))
        width_minus_btn = tk.Button(grid_frame, text="-", width=2, command=lambda: self._adjust_app_grid("width", -20))
        width_minus_btn.pack(side="left", padx=1)
        self.grid_width_var = tk.StringVar(value=str(self.app_grid_width))
        self.grid_width_entry = tk.Entry(grid_frame, textvariable=self.grid_width_var, width=4)
        self.grid_width_entry.bind("<Return>", lambda e: self._on_entry_change("width"))
        self.advanced_entries.append(self.grid_width_entry)
        self._entry_insert_after[self.grid_width_entry] = width_minus_btn
        tk.Button(grid_frame, text="+", width=2, command=lambda: self._adjust_app_grid("width", 20)).pack(side="left", padx=1)
        
        # Position and Icon Scale controls on same row
        pos_frame = tk.Frame(main_frame, bg="#3a3a3a", bd=1, relief="sunken")
        pos_frame.pack(fill="x", pady=5)
        
        tk.Label(pos_frame, text="Position:", bg="#3a3a3a", fg="red").pack(side="left", padx=5)
        pos_up_btn = tk.Button(pos_frame, text="↑", width=2, command=lambda: self._adjust_app_grid("y_offset", 10))
        pos_up_btn.pack(side="left", padx=1)
        self.y_offset_var = tk.StringVar(value=str(self.app_grid_y_offset))
        self.y_offset_entry = tk.Entry(pos_frame, textvariable=self.y_offset_var, width=4)
        self.y_offset_entry.bind("<Return>", lambda e: self._on_entry_change("y_offset"))
        self.advanced_entries.append(self.y_offset_entry)
        self._entry_insert_after[self.y_offset_entry] = pos_up_btn
        tk.Button(pos_frame, text="↓", width=2, command=lambda: self._adjust_app_grid("y_offset", -10)).pack(side="left", padx=1)
        
        # Icon Scale on same row as Position (entry hidden by default)
        tk.Label(pos_frame, text="Icon Scale:", bg="#3a3a3a", fg="red").pack(side="left", padx=(10, 0))
        scale_minus_btn = tk.Button(pos_frame, text="-", width=2, command=lambda: self._adjust_app_grid("icon_scale", -0.1))
        scale_minus_btn.pack(side="left", padx=1)
        self.icon_scale_var = tk.StringVar(value=str(self.app_grid_icon_scale))
        self.icon_scale_entry = tk.Entry(pos_frame, textvariable=self.icon_scale_var, width=4)
        self.icon_scale_entry.bind("<Return>", lambda e: self._on_entry_change("icon_scale"))
        self.advanced_entries.append(self.icon_scale_entry)
        self._entry_insert_after[self.icon_scale_entry] = scale_minus_btn
        tk.Button(pos_frame, text="+", width=2, command=lambda: self._adjust_app_grid("icon_scale", 0.1)).pack(side="left", padx=1)
        
        # Screen label (changes based on screen amount)
        self.screens_label = tk.Label(main_frame, text="Screens", bg="#2a2a2a", fg="white")
        self.screens_label.pack(pady=5)
        
        # Screen Position Controls
        self.screens_frame = tk.Frame(main_frame, bg="#3a3a3a", bd=1, relief="sunken")
        self.screens_frame.pack(fill="x", pady=5)
        
        # Top Screen controls
        top_screen_frame = tk.Frame(self.screens_frame, bg="#3a3a3a")
        top_screen_frame.pack(fill="x", padx=5, pady=3)
        
        tk.Label(top_screen_frame, text="Top:", bg="#3a3a3a", fg="orange", width=8, anchor="w").pack(side="left")
        tk.Button(top_screen_frame, text="↑", width=2, command=lambda: self._adjust_screen_pos("main", "y", -10)).pack(side="left", padx=1)
        tk.Button(top_screen_frame, text="↓", width=2, command=lambda: self._adjust_screen_pos("main", "y", 10)).pack(side="left", padx=1)
        tk.Button(top_screen_frame, text="←", width=2, command=lambda: self._adjust_screen_pos("main", "x", -10)).pack(side="left", padx=1)
        tk.Button(top_screen_frame, text="→", width=2, command=lambda: self._adjust_screen_pos("main", "x", 10)).pack(side="left", padx=1)
        tk.Label(top_screen_frame, text="W:", bg="#3a3a3a", fg="orange").pack(side="left", padx=(10, 0))
        tk.Button(top_screen_frame, text="-", width=2, command=lambda: self._adjust_screen_pos("main", "w", -10)).pack(side="left", padx=1)
        tk.Button(top_screen_frame, text="+", width=2, command=lambda: self._adjust_screen_pos("main", "w", 10)).pack(side="left", padx=1)
        tk.Label(top_screen_frame, text="H:", bg="#3a3a3a", fg="orange").pack(side="left", padx=(5, 0))
        tk.Button(top_screen_frame, text="-", width=2, command=lambda: self._adjust_screen_pos("main", "h", -10)).pack(side="left", padx=1)
        tk.Button(top_screen_frame, text="+", width=2, command=lambda: self._adjust_screen_pos("main", "h", 10)).pack(side="left", padx=1)
        
        # Top Screen advanced row (hidden by default)
        top_screen_advanced = tk.Frame(self.screens_frame, bg="#3a3a3a")
        top_screen_advanced.pack(fill="x", padx=5, pady=1)
        
        tk.Label(top_screen_advanced, text="", bg="#3a3a3a", width=8).pack(side="left")
        tk.Label(top_screen_advanced, text="Y:", bg="#3a3a3a", fg="orange").pack(side="left")
        self.main_y_var = tk.StringVar()
        self.main_y_entry = tk.Entry(top_screen_advanced, textvariable=self.main_y_var, width=5)
        self.main_y_entry.pack(side="left", padx=1)
        self.main_y_entry.bind("<Return>", lambda e: self._on_screen_entry_change("main", "y"))
        self.advanced_entries.append(self.main_y_entry)
        tk.Label(top_screen_advanced, text="X:", bg="#3a3a3a", fg="orange").pack(side="left", padx=(10, 0))
        self.main_x_var = tk.StringVar()
        self.main_x_entry = tk.Entry(top_screen_advanced, textvariable=self.main_x_var, width=5)
        self.main_x_entry.pack(side="left", padx=1)
        self.main_x_entry.bind("<Return>", lambda e: self._on_screen_entry_change("main", "x"))
        self.advanced_entries.append(self.main_x_entry)
        tk.Label(top_screen_advanced, text="W:", bg="#3a3a3a", fg="orange").pack(side="left", padx=(10, 0))
        self.main_w_var = tk.StringVar()
        self.main_w_entry = tk.Entry(top_screen_advanced, textvariable=self.main_w_var, width=5)
        self.main_w_entry.pack(side="left", padx=1)
        self.main_w_entry.bind("<Return>", lambda e: self._on_screen_entry_change("main", "w"))
        self.advanced_entries.append(self.main_w_entry)
        tk.Label(top_screen_advanced, text="H:", bg="#3a3a3a", fg="orange").pack(side="left", padx=(10, 0))
        self.main_h_var = tk.StringVar()
        self.main_h_entry = tk.Entry(top_screen_advanced, textvariable=self.main_h_var, width=5)
        self.main_h_entry.pack(side="left", padx=1)
        self.main_h_entry.bind("<Return>", lambda e: self._on_screen_entry_change("main", "h"))
        self.advanced_entries.append(self.main_h_entry)
        
        # Bottom Screen controls
        bottom_screen_frame = tk.Frame(self.screens_frame, bg="#3a3a3a")
        bottom_screen_frame.pack(fill="x", padx=5, pady=3)
        
        tk.Label(bottom_screen_frame, text="Bottom:", bg="#3a3a3a", fg="lime", width=8, anchor="w").pack(side="left")
        tk.Button(bottom_screen_frame, text="↑", width=2, command=lambda: self._adjust_screen_pos("external", "y", -10)).pack(side="left", padx=1)
        tk.Button(bottom_screen_frame, text="↓", width=2, command=lambda: self._adjust_screen_pos("external", "y", 10)).pack(side="left", padx=1)
        tk.Button(bottom_screen_frame, text="←", width=2, command=lambda: self._adjust_screen_pos("external", "x", -10)).pack(side="left", padx=1)
        tk.Button(bottom_screen_frame, text="→", width=2, command=lambda: self._adjust_screen_pos("external", "x", 10)).pack(side="left", padx=1)
        tk.Label(bottom_screen_frame, text="W:", bg="#3a3a3a", fg="lime").pack(side="left", padx=(10, 0))
        tk.Button(bottom_screen_frame, text="-", width=2, command=lambda: self._adjust_screen_pos("external", "w", -10)).pack(side="left", padx=1)
        tk.Button(bottom_screen_frame, text="+", width=2, command=lambda: self._adjust_screen_pos("external", "w", 10)).pack(side="left", padx=1)
        tk.Label(bottom_screen_frame, text="H:", bg="#3a3a3a", fg="lime").pack(side="left", padx=(5, 0))
        tk.Button(bottom_screen_frame, text="-", width=2, command=lambda: self._adjust_screen_pos("external", "h", -10)).pack(side="left", padx=1)
        tk.Button(bottom_screen_frame, text="+", width=2, command=lambda: self._adjust_screen_pos("external", "h", 10)).pack(side="left", padx=1)
        
        # Bottom Screen advanced row (hidden by default)
        bottom_screen_advanced = tk.Frame(self.screens_frame, bg="#3a3a3a")
        bottom_screen_advanced.pack(fill="x", padx=5, pady=1)
        
        tk.Label(bottom_screen_advanced, text="", bg="#3a3a3a", width=8).pack(side="left")
        tk.Label(bottom_screen_advanced, text="Y:", bg="#3a3a3a", fg="lime").pack(side="left")
        self.ext_y_var = tk.StringVar()
        self.ext_y_entry = tk.Entry(bottom_screen_advanced, textvariable=self.ext_y_var, width=5)
        self.ext_y_entry.pack(side="left", padx=1)
        self.ext_y_entry.bind("<Return>", lambda e: self._on_screen_entry_change("external", "y"))
        self.advanced_entries.append(self.ext_y_entry)
        tk.Label(bottom_screen_advanced, text="X:", bg="#3a3a3a", fg="lime").pack(side="left", padx=(10, 0))
        self.ext_x_var = tk.StringVar()
        self.ext_x_entry = tk.Entry(bottom_screen_advanced, textvariable=self.ext_x_var, width=5)
        self.ext_x_entry.pack(side="left", padx=1)
        self.ext_x_entry.bind("<Return>", lambda e: self._on_screen_entry_change("external", "x"))
        self.advanced_entries.append(self.ext_x_entry)
        tk.Label(bottom_screen_advanced, text="W:", bg="#3a3a3a", fg="lime").pack(side="left", padx=(10, 0))
        self.ext_w_var = tk.StringVar()
        self.ext_w_entry = tk.Entry(bottom_screen_advanced, textvariable=self.ext_w_var, width=5)
        self.ext_w_entry.pack(side="left", padx=1)
        self.ext_w_entry.bind("<Return>", lambda e: self._on_screen_entry_change("external", "w"))
        self.advanced_entries.append(self.ext_w_entry)
        tk.Label(bottom_screen_advanced, text="H:", bg="#3a3a3a", fg="lime").pack(side="left", padx=(10, 0))
        self.ext_h_var = tk.StringVar()
        self.ext_h_entry = tk.Entry(bottom_screen_advanced, textvariable=self.ext_h_var, width=5)
        self.ext_h_entry.pack(side="left", padx=1)
        self.ext_h_entry.bind("<Return>", lambda e: self._on_screen_entry_change("external", "h"))
        self.advanced_entries.append(self.ext_h_entry)
        
        # Center screens buttons - two rows
        self.center_buttons_frame = tk.Frame(main_frame, bg="#3a3a3a")
        self.center_buttons_frame.pack(pady=5)
        
        # Top screen center buttons row
        self.top_center_frame = tk.Frame(self.center_buttons_frame, bg="#3a3a3a")
        self.top_center_frame.pack(fill="x", pady=2)
        
        tk.Label(self.top_center_frame, text="Top:", bg="#3a3a3a", fg="orange", width=8, anchor="w").pack(side="left")
        tk.Button(self.top_center_frame, text="Center ↔", width=10, command=lambda: self._center_screen_horizontal("main")).pack(side="left", padx=2)
        tk.Button(self.top_center_frame, text="Center ↕", width=10, command=lambda: self._center_screen_vertical("main")).pack(side="left", padx=2)
        
        # Bottom screen center buttons row
        self.bottom_center_frame = tk.Frame(self.center_buttons_frame, bg="#3a3a3a")
        self.bottom_center_frame.pack(fill="x", pady=2)
        
        tk.Label(self.bottom_center_frame, text="Bottom:", bg="#3a3a3a", fg="lime", width=8, anchor="w").pack(side="left")
        tk.Button(self.bottom_center_frame, text="Center ↔", width=10, command=lambda: self._center_screen_horizontal("external")).pack(side="left", padx=2)
        tk.Button(self.bottom_center_frame, text="Center ↕", width=10, command=lambda: self._center_screen_vertical("external")).pack(side="left", padx=2)
        
        # Magnify controls at bottom
        magnify_frame = tk.Frame(main_frame, bg="#3a3a3a", bd=1, relief="sunken")
        magnify_frame.pack(fill="x", pady=5)
        
        self.magnify_window_var = tk.BooleanVar(value=getattr(self.renderer, 'magnify_window', True))
        magnify_window_check = tk.Checkbutton(
            magnify_frame,
            text="Magnify Window",
            variable=self.magnify_window_var,
            command=self._on_magnify_window_change,
            bg="#3a3a3a",
            fg="white",
            selectcolor="#3a3a3a",
            activebackground="#3a3a3a"
        )
        magnify_window_check.pack(side="left", padx=5)
        
        tk.Label(magnify_frame, text="Size:", bg="#3a3a3a", fg="white").pack(side="left", padx=(10, 0))
        self.magnify_size_var = tk.IntVar(value=getattr(self.renderer, 'magnify_size', 200))
        magnify_size_slider = tk.Scale(
            magnify_frame,
            from_=100,
            to=300,
            orient="horizontal",
            variable=self.magnify_size_var,
            command=self._on_magnify_size_change,
            bg="#3a3a3a",
            fg="white",
            highlightthickness=0,
            length=150
        )
        magnify_size_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        self.magnify_size_label = tk.Label(magnify_frame, text=f"{self.magnify_size_var.get()}", bg="#3a3a3a", fg="white")
        self.magnify_size_label.pack(side="left", padx=5)
        
        # Store references for visibility toggling
        self.screen_frame = top_screen_frame
        self.ext_frame = bottom_screen_frame
        self.top_screen_advanced = top_screen_advanced
        self.bottom_screen_advanced = bottom_screen_advanced
        
        # Initially hide the overlay and advanced mode entries
        self.bezel_edit_overlay.place_forget()
        self._toggle_advanced_mode()  # Hide advanced entries initially
    
    def _toggle_advanced_mode(self):
        """Toggle advanced mode to show/hide text entry fields"""
        advanced = self.advanced_mode_var.get()
        amount = self.renderer._temp_screen_amount or 2
        
        # Handle app grid advanced entries
        if advanced:
            for entry in self.advanced_entries:
                if entry in self._entry_insert_after:
                    after_widget = self._entry_insert_after[entry]
                    entry.pack(side="left", padx=1, after=after_widget)
        else:
            for entry in self.advanced_entries:
                if entry in self._entry_insert_after:
                    entry.pack_forget()
        
        # Handle screen advanced rows
        if advanced:
            if amount == 2 and hasattr(self, 'top_screen_advanced'):
                self.top_screen_advanced.pack(fill="x", padx=5, pady=1, before=self.ext_frame)
            if hasattr(self, 'bottom_screen_advanced'):
                self.bottom_screen_advanced.pack(fill="x", padx=5, pady=1)
        else:
            if hasattr(self, 'top_screen_advanced'):
                self.top_screen_advanced.pack_forget()
            if hasattr(self, 'bottom_screen_advanced'):
                self.bottom_screen_advanced.pack_forget()
    
    def _on_magnify_window_change(self):
        self.magnify_window = self.magnify_window_var.get()
        self.renderer.magnify_window = self.magnify_window
        self.redraw()
        
        if "Misc" not in self.config:
            self.config["Misc"] = {}
        self.config["Misc"]["magnify_window"] = str(self.magnify_window)
    
    def _on_magnify_size_change(self, value):
        size = int(float(value))
        size = round(size / 10) * 10
        size = max(100, min(300, size))
        self.magnify_size_var.set(size)
        self.renderer.magnify_size = size
        self.renderer.magnify_zoom = 2.0 * (size / 150)
        self.magnify_size_label.config(text=f"{size}")
        
        if "Misc" not in self.config:
            self.config["Misc"] = {}
        self.config["Misc"]["magnify_size"] = str(size)
        with open(self.settings_path, "w") as f:
            self.config.write(f)
        
        self.redraw()
    
    def _center_screens_to_device(self):
        """Center both screens to the device image"""
        from screen import Screen
        
        frame_w = Screen.FRAME_WIDTH
        frame_h = Screen.FRAME_HEIGHT
        
        amount = self.renderer._temp_screen_amount or 2
        
        if amount == 2:
            # Dual screen mode - center top and bottom screens
            # Top screen: center horizontally, position in upper half
            top_w = Screen.TOP_SCREEN[2]
            top_h = Screen.TOP_SCREEN[3]
            top_x = (frame_w - top_w) // 2
            top_y = (frame_h // 2 - top_h) // 2
            
            # Bottom screen: center horizontally, position in lower half
            bot_w = Screen.BOTTOM_SCREEN[2]
            bot_h = Screen.BOTTOM_SCREEN[3]
            bot_x = (frame_w - bot_w) // 2
            bot_y = frame_h // 2 + (frame_h // 2 - bot_h) // 2
            
            self.renderer.set_temp_screen_pos("main", top_x, top_y, top_w, top_h)
            self.renderer.set_temp_screen_pos("external", bot_x, bot_y, bot_w, bot_h)
        else:
            # Single screen mode - center bottom screen
            bot_w = Screen.BOTTOM_SCREEN[2]
            bot_h = Screen.BOTTOM_SCREEN[3]
            bot_x = (frame_w - bot_w) // 2
            bot_y = (frame_h - bot_h) // 2
            
            self.renderer.set_temp_screen_pos("external", bot_x, bot_y, bot_w, bot_h)
        
        self._update_entry_fields()
        self.redraw()
    
    def _center_screen_horizontal(self, screen_name: str):
        """Center a screen horizontally within the device"""
        from screen import Screen
        
        frame_w = Screen.FRAME_WIDTH
        frame_h = Screen.FRAME_HEIGHT
        
        if screen_name == "main":
            # Top screen
            cur_x = self.renderer.screen_manager.main.x
            cur_y = self.renderer.screen_manager.main.y
            cur_w = self.renderer.screen_manager.main.w
            cur_h = self.renderer.screen_manager.main.h
            new_x = (frame_w - cur_w) // 2
            self.renderer.set_temp_screen_pos(screen_name, new_x, cur_y, cur_w, cur_h)
        else:
            # Bottom/external screen
            cur_x = self.renderer.screen_manager.external.x
            cur_y = self.renderer.screen_manager.external.y
            cur_w = self.renderer.screen_manager.external.w
            cur_h = self.renderer.screen_manager.external.h
            new_x = (frame_w - cur_w) // 2
            self.renderer.set_temp_screen_pos(screen_name, new_x, cur_y, cur_w, cur_h)
        
        self._update_entry_fields()
        self.redraw()
    
    def _center_screen_vertical(self, screen_name: str):
        """Center a screen vertically within the device"""
        from screen import Screen
        
        frame_w = Screen.FRAME_WIDTH
        frame_h = Screen.FRAME_HEIGHT
        
        if screen_name == "main":
            # Top screen - center in upper half
            cur_x = self.renderer.screen_manager.main.x
            cur_y = self.renderer.screen_manager.main.y
            cur_w = self.renderer.screen_manager.main.w
            cur_h = self.renderer.screen_manager.main.h
            new_y = (frame_h // 2 - cur_h) // 2
            self.renderer.set_temp_screen_pos(screen_name, cur_x, new_y, cur_w, cur_h)
        else:
            # Bottom/external screen - center in lower half for dual, full height for single
            amount = self.renderer._temp_screen_amount or 2
            cur_x = self.renderer.screen_manager.external.x
            cur_y = self.renderer.screen_manager.external.y
            cur_w = self.renderer.screen_manager.external.w
            cur_h = self.renderer.screen_manager.external.h
            if amount == 2:
                new_y = frame_h // 2 + (frame_h // 2 - cur_h) // 2
            else:
                new_y = (frame_h - cur_h) // 2
            self.renderer.set_temp_screen_pos(screen_name, cur_x, new_y, cur_w, cur_h)
        
        self._update_entry_fields()
        self.redraw()
    
    def _on_entry_change(self, setting: str):
        """Handle manual entry in text fields"""
        from screen import Screen
        
        # Get the screen dimensions for constraints
        if self.renderer.screen_manager.screen_mode == "single":
            screen = Screen.SINGLE_SCREEN
        else:
            screen = Screen.BOTTOM_SCREEN
        screen_w = screen[2]
        screen_h = screen[3]
        
        try:
            if setting == "icon_size":
                value = int(self.icon_size_var.get())
                value = max(20, min(screen_h - 10, value))
                self.app_grid_icon_size = value
                self.icon_size_var.set(str(value))
                self.renderer.set_temp_app_grid("icon_size", value)
            elif setting == "width":
                value = int(self.grid_width_var.get())
                value = max(50, min(screen_w, value))
                self.app_grid_width = value
                self.grid_width_var.set(str(value))
                self.renderer.set_temp_app_grid("width", value)
            elif setting == "y_offset":
                value = int(self.y_offset_var.get())
                min_offset = -screen_h + self.app_grid_icon_size + 10
                max_offset = 10
                value = max(min_offset, min(max_offset, value))
                self.app_grid_y_offset = value
                self.y_offset_var.set(str(value))
                self.renderer.set_temp_app_grid("y_offset", value)
            elif setting == "icon_scale":
                value = float(self.icon_scale_var.get())
                value = max(0.1, min(3.0, value))
                self.app_grid_icon_scale = value
                self.icon_scale_var.set(str(round(value, 2)))
                self.renderer.set_temp_app_grid("icon_scale", value)
            self.redraw()
        except ValueError:
            # Reset to current value if invalid
            if setting == "icon_size":
                self.icon_size_var.set(str(self.app_grid_icon_size))
            elif setting == "width":
                self.grid_width_var.set(str(self.app_grid_width))
            elif setting == "y_offset":
                self.y_offset_var.set(str(self.app_grid_y_offset))
            elif setting == "icon_scale":
                self.icon_scale_var.set(str(self.app_grid_icon_scale))
    
    def _on_screen_entry_change(self, screen_name: str, prop: str):
        """Handle manual entry in screen position text fields"""
        from screen import Screen
        
        try:
            if screen_name == "main":
                var_map = {"x": self.main_x_var, "y": self.main_y_var, "w": self.main_w_var, "h": self.main_h_var}
                current = list(Screen.TOP_SCREEN)
            else:
                var_map = {"x": self.ext_x_var, "y": self.ext_y_var, "w": self.ext_w_var, "h": self.ext_h_var}
                current = list(Screen.BOTTOM_SCREEN)
            
            value = int(var_map[prop].get())
            idx = {"x": 0, "y": 1, "w": 2, "h": 3}[prop]
            current[idx] = max(0 if idx < 2 else 50, value)
            var_map[prop].set(str(current[idx]))
            
            self.renderer.set_temp_screen_pos(screen_name, *current)
            self.redraw()
        except ValueError:
            pass
    
    def _update_entry_fields(self):
        """Update text entry fields with current values"""
        from screen import Screen
        self.icon_size_var.set(str(self.app_grid_icon_size))
        self.grid_width_var.set(str(self.app_grid_width))
        self.y_offset_var.set(str(self.app_grid_y_offset))
        self.icon_scale_var.set(str(self.app_grid_icon_scale))
        # Update screen entries
        main = Screen.TOP_SCREEN
        self.main_x_var.set(str(main[0]))
        self.main_y_var.set(str(main[1]))
        self.main_w_var.set(str(main[2]))
        self.main_h_var.set(str(main[3]))
        ext = Screen.BOTTOM_SCREEN
        self.ext_x_var.set(str(ext[0]))
        self.ext_y_var.set(str(ext[1]))
        self.ext_w_var.set(str(ext[2]))
        self.ext_h_var.set(str(ext[3]))
    
    def _adjust_screen_pos(self, screen_name: str, prop: str, delta: int):
        """Adjust a screen position/size setting"""
        from screen import Screen
        
        if screen_name == "main":
            current = list(Screen.TOP_SCREEN)
        else:
            current = list(Screen.BOTTOM_SCREEN)
        
        if prop == "x":
            current[0] += delta
        elif prop == "y":
            current[1] += delta
        elif prop == "w":
            current[2] = max(50, current[2] + delta)
        elif prop == "h":
            current[3] = max(50, current[3] + delta)
        
        new_pos = tuple(current)
        self.renderer.set_temp_screen_pos(screen_name, *new_pos)
        self._update_entry_fields()
        self.redraw()
    
    def _toggle_screen_amount(self):
        """Toggle between 1 and 2 screen modes"""
        current = self.renderer._temp_screen_amount or 2
        new_amount = 1 if current == 2 else 2
        self.renderer.set_temp_screen_amount(new_amount)
        # Invalidate cache to ensure fresh render
        self.renderer._invalidate_static_cache()
        self._update_bezel_edit_overlay()
        self.redraw()
    
    def _adjust_app_grid(self, setting: str, delta):
        """Adjust an app grid setting by delta (int or float)"""
        from screen import Screen
        
        # Get the screen dimensions for constraints
        if self.renderer.screen_manager.screen_mode == "single":
            screen = Screen.SINGLE_SCREEN
        else:
            screen = Screen.BOTTOM_SCREEN
        screen_w = screen[2]
        screen_h = screen[3]
        
        if setting == "width":
            # Grid width cannot exceed screen width
            new_width = self.app_grid_width + int(delta)
            self.app_grid_width = max(50, min(screen_w, new_width))
            self.renderer.set_temp_app_grid("width", self.app_grid_width)
            self.grid_width_var.set(str(self.app_grid_width))
        elif setting == "icon_size":
            # Icon height cannot exceed screen height (minus some padding)
            new_size = self.app_grid_icon_size + int(delta)
            self.app_grid_icon_size = max(20, min(screen_h - 10, new_size))
            self.renderer.set_temp_app_grid("icon_size", self.app_grid_icon_size)
            self.icon_size_var.set(str(self.app_grid_icon_size))
        elif setting == "y_offset":
            # Y offset should keep grid within screen bounds
            # y_offset is from bottom, so positive moves up
            # Grid bottom = screen_h - y_offset
            # Grid top = grid_bottom - icon_size
            # Constraints: grid_top >= 0, grid_bottom <= screen_h
            new_offset = self.app_grid_y_offset + int(delta)
            # Grid must stay within screen (0 to screen_h - icon_size)
            min_offset = -screen_h + self.app_grid_icon_size + 10  # Allow going up to near top
            max_offset = 10  # Small padding from bottom
            self.app_grid_y_offset = max(min_offset, min(max_offset, new_offset))
            self.renderer.set_temp_app_grid("y_offset", self.app_grid_y_offset)
            self.y_offset_var.set(str(self.app_grid_y_offset))
        elif setting == "icon_scale":
            self.app_grid_icon_scale = max(0.1, min(3.0, round(self.app_grid_icon_scale + float(delta), 2)))
            self.renderer.set_temp_app_grid("icon_scale", self.app_grid_icon_scale)
            self.icon_scale_var.set(str(self.app_grid_icon_scale))
        self.redraw()
        self.redraw()
    
    def _on_bezel_apply(self):
        """Apply bezel changes and exit edit mode"""
        self.renderer.apply_bezel_changes()
        self.bezel_edit_var.set(False)
        self.bezel_edit_overlay.place_forget()
        self.redraw()
    
    def _on_bezel_revert(self):
        """Revert bezel changes and exit edit mode"""
        self.renderer.revert_bezel_changes()
        self.bezel_edit_var.set(False)
        self.bezel_edit_overlay.place_forget()
        self.redraw()
    
    def _update_bezel_edit_overlay(self):
        """Show/hide bezel edit overlay based on edit mode"""
        if self.renderer.bezel_edit_mode:
            # Position overlay at bottom-left of canvas
            self.bezel_edit_overlay.place(x=10, y=10, anchor="nw")
            # Update screen amount button text
            amount = self.renderer._temp_screen_amount or 2
            self.screen_amount_button.config(text=f"{amount} Screen{'s' if amount > 1 else ''}")
            # Update screens label
            if hasattr(self, 'screens_label'):
                self.screens_label.config(text="Screens" if amount == 2 else "Screen")
            # Show/hide top screen controls based on screen amount
            if hasattr(self, 'screen_frame'):
                if amount == 2:
                    # Pack top screen frame before bottom screen frame
                    self.screen_frame.pack(fill="x", padx=5, pady=3, before=self.ext_frame)
                    if self.advanced_mode_var.get() and hasattr(self, 'top_screen_advanced'):
                        self.top_screen_advanced.pack(fill="x", padx=5, pady=1, before=self.ext_frame)
                else:
                    self.screen_frame.pack_forget()
                    if hasattr(self, 'top_screen_advanced'):
                        self.top_screen_advanced.pack_forget()
            # Show/hide top center buttons based on screen amount
            if hasattr(self, 'top_center_frame'):
                if amount == 2:
                    self.top_center_frame.pack(fill="x", pady=2, before=self.bottom_center_frame)
                else:
                    self.top_center_frame.pack_forget()
            # Update entry fields with current values
            self._update_entry_fields()
        else:
            self.bezel_edit_overlay.place_forget()
    
    def _update_single_screen_controls_visibility(self):
        pass
    
    def _update_zoom_levels_for_mode(self):
        """Switch zoom levels based on current screen mode and stacked mode setting."""
        if self.renderer.screen_manager.screen_mode == "single":
            if self.single_screen_stacked_mode:
                self.zoom_levels = self.zoom_levels_single_stacked
            else:
                self.zoom_levels = self.zoom_levels_single_dual
        else:
            self.zoom_levels = self.zoom_levels_dual
        
        # Clamp zoom index to new range
        if self.zoom_index >= len(self.zoom_levels):
            self.zoom_index = len(self.zoom_levels) - 1
    
    # -------------------------------------------------
    # Zoom controls
    # -------------------------------------------------
    def zoom_in(self):
        if self.zoom_index < len(self.zoom_levels) - 1:
            self.zoom_index += 1
            self._apply_zoom()
    
    def zoom_out(self):
        if self.zoom_index > 0:
            self.zoom_index -= 1
            self._apply_zoom()
    
    def canvas_zoom_in(self):
        """Zoom in the device on the canvas (does not affect screenshots)."""
        if self.canvas_zoom < 3.0:
            self.canvas_zoom = min(3.0, self.canvas_zoom + 0.25)
            self._apply_canvas_zoom()
            self._save_canvas_zoom()
    
    def canvas_zoom_out(self):
        """Zoom out the device on the canvas (does not affect screenshots)."""
        if self.canvas_zoom > 0.25:
            self.canvas_zoom = max(0.25, self.canvas_zoom - 0.25)
            self._apply_canvas_zoom()
            self._save_canvas_zoom()
    
    def _print_debug_info(self):
        """Print debug info about grid and screen positions."""
        print("You found me! :D")
    
    def _apply_canvas_zoom(self):
        """Apply canvas zoom by triggering a redraw with scaled image."""
        # Invalidate renderer cache to avoid stale background
        self.renderer._invalidate_static_cache()
        self.redraw()
        # Update video positions for new zoom level
        self._update_video_positions()
    
    def _save_canvas_zoom(self):
        """Save canvas zoom to settings."""
        if "Misc" not in self.config:
            self.config["Misc"] = {}
        self.config["Misc"]["canvas_zoom"] = str(self.canvas_zoom)
        with open(self.settings_path, "w") as f:
            self.config.write(f)
    
    def _update_bg_scroll(self):
        """Update background scroll animation."""
        speed = getattr(self, 'bg_scroll_speed', 1)
        reverse = getattr(self, 'reverse_direction', False)
        direction = 1 if reverse else -1
        
        # Cancel existing timer if any
        if hasattr(self, '_bg_scroll_timer') and self._bg_scroll_timer:
            self.after_cancel(self._bg_scroll_timer)
            self._bg_scroll_timer = None
        
        if speed <= 0:
            return
        
        # Get canvas and background dimensions
        try:
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            if canvas_w <= 1 or canvas_h <= 1:
                self._bg_scroll_timer = self.after(16, self._update_bg_scroll)
                return
        except:
            return
        
        # Get the background image width - use fitted width for proper looping
        bg_width = getattr(self, '_bg_fitted_width', canvas_w)
        if bg_width <= 0:
            bg_width = canvas_w
        
        # Update scroll offset (use direction to flip sign)
        effective_speed = float(speed * direction)
        self._bg_scroll_offset = (self._bg_scroll_offset + effective_speed) % bg_width
        
        if self._bg_scroll_offset < 0:
            self._bg_scroll_offset += float(bg_width)
        
        # Update canvas item positions
        img_x = canvas_w // 2
        img_y = canvas_h // 2
        
        # Check if canvas items exist, recreate if needed
        try:
            self.canvas.coords(self._canvas_bg_id, 0, 0)
        except:
            # Canvas item doesn't exist, recreate
            self._canvas_bg_id = self.canvas.create_image(img_x, img_y, anchor="center", image=self.tk_bg_img)
            self._canvas_bg_id_2 = self.canvas.create_image(img_x + bg_width, img_y, anchor="center", image=self.tk_bg_img)
            self.canvas.lower(self._canvas_bg_id)
            self.canvas.lower(self._canvas_bg_id_2)
        
        try:
            self.canvas.coords(self._canvas_bg_id, img_x - self._bg_scroll_offset, img_y)
            self.canvas.coords(self._canvas_bg_id_2, img_x - self._bg_scroll_offset + bg_width, img_y)
            # Always update image reference in case it changed
            self.canvas.itemconfig(self._canvas_bg_id, image=self.tk_bg_img)
            self.canvas.itemconfig(self._canvas_bg_id_2, image=self.tk_bg_img)
        except:
            pass
        
        # Schedule next frame
        self._bg_scroll_timer = self.after(16, self._update_bg_scroll)
    
    def _apply_zoom(self):
        rows, cols = self.zoom_levels[self.zoom_index]

        if hasattr(self.renderer, "set_grid_size"):
            self.renderer.set_grid_size(rows, cols)
        
        # In single screen stacked mode, automatically set the offset
        if (self.single_screen_stacked_mode and 
            self.renderer.screen_manager.screen_mode == "single"):
            self._apply_stacked_offset(rows)
        
        self.save_settings()
        self.redraw()
    
    def _apply_stacked_offset(self, rows: int):
        """Calculate and apply top screen offset for stacked mode."""
        from screen import Screen
        
        # Get percentage for this row count
        percentage = self.stacked_offset_percentages.get(rows, 0.5)
        
        # Get actual external screen height from current device
        ext_h = Screen.SINGLE_SCREEN[3]
        visible_pixels = int(ext_h * percentage)
        offset = -(ext_h - visible_pixels)
        
        # Clamp to valid range
        offset = max(-(ext_h - 10), min(0, offset))
        
        Screen.SINGLE_SCREEN_MAIN_OFFSET = offset
        self.renderer.screen_manager._update_single_screen_main_position()

    def _on_icon_scale_change(self, value):
        """Update logo size from slider."""
        scale = int(value)
        self.logo_size = scale
        self._icon_scale_var.set(scale)
        self.renderer.top_screen_icon_scale = scale / 100.0
        self.save_settings()
        self.redraw()
    
    # -------------------------------------------------
    # Save settings
    # -------------------------------------------------
    
    def save_settings(self):
        # Ensure sections exist
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        # Settings (all menu items)
        self.config["Settings"]["default_folder_color"] = self.default_folder_color_var.get()
        self.config["Settings"]["dock_background"] = str(self.renderer.dock_visible)
        self.config["Settings"]["logo_size"] = str(getattr(self, "logo_size", 60))
        self.config["Settings"]["show_corner_hints"] = str(self.renderer.corner_hints_visible)
        self.config["Settings"]["single_screen_mode"] = str(getattr(self, "single_screen_stacked_mode", False))
        self.config["Settings"]["apps"] = str(getattr(self, "apps_visible", True))
        self.config["Settings"]["empty_apps"] = str(getattr(self, "empty_apps_visible", True))
        self.config["Settings"]["empty_slots"] = str(getattr(self, "empty_slots", True))
        self.config["Settings"]["remember_last_theme"] = str(self.remember_last_theme)
        self.config["Settings"]["last_theme_path"] = self.last_theme_path or ""
        self.config["Settings"]["video_playback"] = str(getattr(self, "video_playback", True))
        self.config["Settings"]["bg_scroll_speed"] = str(getattr(self, "bg_scroll_speed", 1))
        self.config["Settings"]["reverse_direction"] = str(getattr(self, "reverse_direction", False))
        
        # Misc (settings not in the menu)
        self.config["Misc"]["canvas_zoom"] = str(getattr(self, "canvas_zoom", 1.0))
        self.config["Misc"]["magnify_window"] = str(getattr(self, "magnify_window", True))
        self.config["Misc"]["magnify_size"] = str(getattr(self, "magnify_size", 200))
        self.config["Misc"]["bezel"] = self.bezel_var.get()
        self.config["Misc"]["zoom_index"] = str(self.zoom_index)

        with open(self.settings_path, "w") as f:
            self.config.write(f)
    
    # -------------------------------------------------
    # Grid selection
    # -------------------------------------------------

    def move_selection(self, dx, dy):
        """Keyboard movement with extended grid scrolling."""
        current_rows = self.renderer.GRID_ROWS
        total_items = len(self.renderer.grid_items) if self.renderer.grid_items else 0
        
        idx = self.renderer.selected_index
        # Column-major: col = idx // current_rows, row = idx % current_rows
        col = idx // current_rows
        row = idx % current_rows

        # Calculate new position (allow going beyond visible columns)
        new_col = col + dx
        new_row = max(0, min(current_rows - 1, row + dy))
        new_idx = new_col * current_rows + new_row

        # Don't move if target position is out of bounds
        if new_idx < 0 or new_idx >= total_items:
            return
        
        if new_idx != self.renderer.selected_index:
            self.renderer.selected_index = new_idx
            # Reset logo animation for new selection
            if new_idx in self.renderer._last_logo_update:
                del self.renderer._last_logo_update[new_idx]
            # Reset logo index to 0
            if self.renderer.grid_items and new_idx < len(self.renderer.grid_items):
                item = self.renderer.grid_items[new_idx]
                if item and item.get("logo_frames"):
                    item["logo_index"] = 0
                    item["logo"] = item["logo_frames"][0]
            
            # Update scroll offset to keep selection visible
            self._update_grid_scroll()
        
        self.redraw()
    
    def _update_grid_scroll(self, instant=False):
        """Update grid scroll offset to keep selection visible (with optional animation)."""
        current_rows = self.renderer.GRID_ROWS
        idx = self.renderer.selected_index
        col = idx // current_rows  # Column-major
        
        # Use full cell width (before shrinking to square) for consistent scrolling
        cell_w = self.renderer._full_cell_width
        if cell_w <= 0:
            return
        
        cell_with_padding = cell_w + self.renderer.GRID_PADDING
        
        # Calculate visible column range (GRID_COLS is the visible width)
        visible_cols = self.renderer.GRID_COLS
        
        # Calculate max scroll position (can't scroll past the last column)
        total_cols = (len(self.renderer.grid_items) + current_rows - 1) // current_rows if self.renderer.grid_items else 0
        max_scroll = max(0, (total_cols - visible_cols) * cell_with_padding)
        
        first_visible_col = int(self.renderer.grid_scroll_x / cell_with_padding) if cell_with_padding > 0 else 0
        last_visible_col = first_visible_col + visible_cols - 1
        
        # Calculate target scroll position
        target_scroll = self.renderer.grid_scroll_x
        
        if col < first_visible_col:
            # Need to scroll left
            target_scroll = max(0, col * cell_with_padding)
        elif col > last_visible_col:
            # Need to scroll right
            target_scroll = max(0, min(max_scroll, (col - visible_cols + 1) * cell_with_padding))
        
        # Clamp target scroll to max
        target_scroll = min(target_scroll, max_scroll)
        
        if instant:
            # Snap instantly (no animation)
            self.renderer.grid_scroll_x = target_scroll
            self.renderer._grid_scroll_target = target_scroll
            self.renderer._grid_scroll_from = target_scroll
            self.renderer._grid_scroll_start = None
        elif target_scroll != self.renderer.grid_scroll_x:
            # Start animation if target changed
            self.renderer._grid_scroll_from = self.renderer.grid_scroll_x
            self.renderer._grid_scroll_target = target_scroll
            self.renderer._grid_scroll_start = time.perf_counter()

    
    # --- App Grid Controls ---
    
    def _check_app_grid_arrows_click(self, click_x, click_y):
        """Check if click is on the app grid directional arrows or handle movement and size adjustments."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Get control positions from renderer if available
        controls = getattr(self.renderer, '_app_grid_controls', None)
        if controls:
            pos_center_x = controls['arrow_center_x']
            pos_center_y = controls['arrow_center_y']
            arrow_size = controls['arrow_size']
            size_center_x = controls['size_center_x']
            size_center_y = controls['size_center_y']
        else:
            # Fallback to calculated positions
            arrow_margin = 20
            arrow_size = 25
            pos_center_x = arrow_margin + arrow_size + 5
            pos_center_y = canvas_h - arrow_margin - arrow_size - 30
            size_center_x = pos_center_x + arrow_size + 60
            size_center_y = pos_center_y
        
        # Check if click is in size control area (rectangle on the right)
        if (size_center_y - 20 <= click_y <= size_center_y + 20 and
            size_center_x - 50 <= click_x <= size_center_x + 50):
            
            # Width controls (left side of size panel)
            # Minus button
            if size_center_x - 45 <= click_x <= size_center_x - 30:
                self.app_grid_width = max(50, self.app_grid_width - 20)
                self.renderer.app_grid_width = self.app_grid_width
                self.renderer.save_device_app_grid_settings()
                self.redraw()
                return True
            # Plus button
            elif size_center_x - 5 <= click_x <= size_center_x + 10:
                self.app_grid_width = min(800, self.app_grid_width + 20)
                self.renderer.app_grid_width = self.app_grid_width
                self.renderer.save_device_app_grid_settings()
                self.redraw()
                return True
            # Height controls (right side of size panel)
            # Minus button
            elif size_center_x + 20 <= click_x <= size_center_x + 35:
                self.app_grid_icon_size = max(20, self.app_grid_icon_size - 5)
                self.renderer.app_grid_icon_size = self.app_grid_icon_size
                self.renderer.save_device_app_grid_settings()
                self.redraw()
                return True
            # Plus button would be to the right of the "H" label
            elif size_center_x + 55 <= click_x <= size_center_x + 70:
                self.app_grid_icon_size = min(100, self.app_grid_icon_size + 5)
                self.renderer.app_grid_icon_size = self.app_grid_icon_size
                self.renderer.save_device_app_grid_settings()
                self.redraw()
                return True
        
        # Check if click is within the arrow control area (circle on the left)
        dist = ((click_x - pos_center_x) ** 2 + (click_y - pos_center_y) ** 2) ** 0.5
        if dist > arrow_size + 10:
            return False
        
        # Determine which direction was clicked
        move_step = 10
        
        # Check vertical movement (up/Down)
        if abs(click_y - pos_center_y) > abs(click_x - pos_center_x):
            if click_y < pos_center_y:  # Up
                self.app_grid_y_offset += move_step
            else:  # Down
                self.app_grid_y_offset -= move_step
        else:
            # Check horizontal movement (Left/Right)
            if click_x < pos_center_x:  # Left
                self.app_grid_x_offset -= move_step
            else:  # Right
                self.app_grid_x_offset += move_step
        
        # Update renderer and redraw
        self.renderer.app_grid_x_offset = self.app_grid_x_offset
        self.renderer.app_grid_y_offset = self.app_grid_y_offset
        self.renderer.save_device_app_grid_settings()
        self.redraw()
        return True
    
    # --- Mouse motion tracking ---
    
    def _on_canvas_motion(self, event):
        """Track mouse position for magnify window and handle dragging."""
        # Mark that user is interacting - pause video updates during interaction
        self._user_interacting = True
        
        self.renderer.mouse_x = event.x
        self.renderer.mouse_y = event.y
        
        canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        center_x = canvas_w // 2
        center_y = canvas_h // 2
        
        if canvas_zoom != 1.0:
            self.renderer.mouse_x = (event.x - center_x) / canvas_zoom + center_x
            self.renderer.mouse_y = (event.y - center_y) / canvas_zoom + center_y
        
        # Handle dragging in bezel edit mode
        if self._dragging_handle and self._drag_start_pos and self._drag_start_values:
            dx = event.x - self._drag_start_pos[0]
            dy = event.y - self._drag_start_pos[1]
            
            renderer = self.renderer
            
            handle_type = self._dragging_handle
            
            # Handle app grid dragging - scale delta by canvas_zoom
            if handle_type.startswith('grid_'):
                start = self._drag_start_values
                canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                scaled_dx = dx / canvas_zoom if canvas_zoom > 0 else dx
                scaled_dy = dy / canvas_zoom if canvas_zoom > 0 else dy
                if handle_type == 'grid_top':
                    renderer.app_grid_y_offset = start['y_offset'] + scaled_dy
                elif handle_type == 'grid_bottom':
                    renderer.app_grid_y_offset = start['y_offset'] + scaled_dy
                elif handle_type == 'grid_left':
                    renderer.app_grid_x_offset = start['x_offset'] + scaled_dx
                elif handle_type == 'grid_right':
                    renderer.app_grid_x_offset = start['x_offset'] + scaled_dx
                renderer._invalidate_static_cache()
                self.redraw()
            
            # Handle item grid dragging/resizing (magenta handles)
            elif handle_type.startswith('item_grid_'):
                # Enable manual grid override
                renderer._manual_grid_override = True
                
                start = self._drag_start_values
                edge = handle_type.replace('item_grid_', '')
                
                # Get the external screen to access the grid positioning
                external = renderer.screen_manager.external
                
                # Scale delta by canvas_zoom to convert from canvas coords to frame coords
                canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                scaled_dx = dx / canvas_zoom if canvas_zoom > 0 else dx
                scaled_dy = dy / canvas_zoom if canvas_zoom > 0 else dy
                
                # Adjust grid height based on edge being dragged
                # Note: This is a simple implementation - grid is positioned relative to external screen
                if edge == 'top':
                    # Moving top edge changes grid position and height
                    new_y = max(external.y, start['grid_y'] + scaled_dy)
                    renderer._last_grid_y = new_y
                    renderer._last_grid_h = start['grid_h'] - scaled_dy
                elif edge == 'bottom':
                    # Moving bottom edge changes height only
                    renderer._last_grid_h = max(50, start['grid_h'] + scaled_dy)
                elif edge == 'left':
                    # Moving left edge changes position and width
                    new_x = max(external.x, start['grid_x'] + scaled_dx)
                    renderer._last_grid_x = new_x
                    renderer._last_grid_w = start['grid_w'] - scaled_dx
                elif edge == 'right':
                    # Moving right edge changes width only
                    renderer._last_grid_w = max(50, start['grid_w'] + scaled_dx)
                
                renderer._invalidate_static_cache()
                self.redraw()
            
            # Handle screen dragging/resizing - scale delta by canvas_zoom
            elif '_' in handle_type:
                parts = handle_type.split('_', 1)
                if len(parts) == 2:
                    screen_name, edge = parts
                    if screen_name in ('main', 'external'):
                        screen = renderer.screen_manager.main if screen_name == 'main' else renderer.screen_manager.external
                        start = self._drag_start_values
                        
                        # Scale delta by canvas_zoom AND bezel_fit_scale
                        canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                        bezel_scale = getattr(renderer, '_bezel_fit_scale', 1.0)
                        scale_factor = canvas_zoom * bezel_scale
                        scaled_dx = dx / scale_factor if scale_factor > 0 else dx
                        scaled_dy = dy / scale_factor if scale_factor > 0 else dy
                        
                        # Corner handles - resize both dimensions
                        if edge in ('tl', 'tr', 'bl', 'br'):
                            if 't' in edge:  # top
                                screen.y = max(0, start['y'] + scaled_dy)
                                screen.h = start['h'] - scaled_dy
                            if 'b' in edge:  # bottom
                                screen.h = start['h'] + scaled_dy
                            if 'l' in edge:  # left
                                screen.x = max(0, start['x'] + scaled_dx)
                                screen.w = start['w'] - scaled_dx
                            if 'r' in edge:  # right
                                screen.w = start['w'] + scaled_dx
                        # Edge handles - resize single dimension
                        elif edge == 'top':
                            screen.y = max(0, start['y'] + scaled_dy)
                            screen.h = start['h'] - scaled_dy
                        elif edge == 'bottom':
                            screen.h = start['h'] + scaled_dy
                        elif edge == 'left':
                            screen.x = max(0, start['x'] + scaled_dx)
                            screen.w = start['w'] - scaled_dx
                        elif edge == 'right':
                            screen.w = start['w'] + scaled_dx
                        
                        # Ensure minimum size
                        screen.w = max(50, screen.w)
                        screen.h = max(50, screen.h)
                        
                        # Update temp screens in renderer
                        temp_screens = getattr(renderer, '_temp_screens', {})
                        if screen_name in temp_screens:
                            temp_screens[screen_name]['x'] = screen.x
                            temp_screens[screen_name]['y'] = screen.y
                            temp_screens[screen_name]['w'] = screen.w
                            temp_screens[screen_name]['h'] = screen.h
                        
                        renderer._invalidate_static_cache()
                        self.redraw()
    
    # --- Canvis clicking ---

    def on_canvas_left_click(self, event):
        """Handle left-click for both grid selection and folder menu."""
        
        # Handle bezel edit mode - check for handle drag start
        if self.renderer.bezel_edit_mode:
            handle_info = self._check_handle_click(event.x, event.y)
            if handle_info:
                self._dragging_handle = handle_info[0]
                self._drag_start_pos = (event.x, event.y)
                self._drag_start_values = handle_info[1]
                return
            return
        
        # Check if click is on app grid directional arrows (bottom left)
        if self._check_app_grid_arrows_click(event.x, event.y):
            return

        clicked_on_menu = False
        if self.folder_menu_open and self.folder_menu_anchor_index is not None:
            # Check if click is on a color circle
            try:
                x, y, w, h = self.renderer.grid_positions[self.folder_menu_anchor_index]
            except AttributeError:
                x, y, w, h = 100, 100, 50, 50

            cell_size = min(w, h)
            circle_size = max(16, cell_size // 3)
            menu_padding = max(4, circle_size // 3)
            spacing = max(6, circle_size // 2)
            menu_width = menu_padding*2 + len(self.folder_colors) * (circle_size + spacing) - spacing
            menu_height = circle_size + menu_padding*2 + max(12, circle_size // 2)
            menu_x = x + w//2 - menu_width//2
            menu_y = y - menu_height - 10

            # Compute dynamic spacing (same as drawing code)
            num_gaps = len(self.folder_colors) - 1
            total_space = menu_width - 2 * menu_padding - len(self.folder_colors) * circle_size
            spacing_dynamic = total_space / num_gaps if num_gaps > 0 else 0

            for i, color_name in enumerate(self.folder_colors):
                circle_x = menu_x + menu_padding + (circle_size // 2) + i * (circle_size + spacing_dynamic)
                circle_y = menu_y + menu_padding + max(12, circle_size // 2)
                if (event.x - circle_x)**2 + (event.y - circle_y)**2 <= (circle_size//2)**2:
                    # clicked a color
                    self.default_folder_color_var.set(color_name)
                    self.renderer.set_default_folder_color(color_name)
                    self.save_settings()
                    if hasattr(self, '_settings_dialog') and self._settings_dialog.winfo_exists():
                        self._settings_dialog._rebuild_accent_color_picker()
                    clicked_on_menu = True
                    break

        # Close menu if it was open (whether clicked on menu or not)
        if self.folder_menu_open:
            self.folder_menu_open = False
            self.folder_menu_anchor_index = None
            self.redraw()

        # If click was not on menu, select grid item
        if not clicked_on_menu:
            idx = self.get_grid_index_at(event.x, event.y)
            if idx is not None and idx != self.renderer.selected_index:
                self.renderer.selected_index = idx
                # Reset logo animation for new selection
                if idx in self.renderer._last_logo_update:
                    del self.renderer._last_logo_update[idx]
                # Reset logo index to 0
                if self.renderer.grid_items and idx < len(self.renderer.grid_items):
                    item = self.renderer.grid_items[idx]
                    if item and item.get("logo_frames"):
                        item["logo_index"] = 0
                        item["logo"] = item["logo_frames"][0]
                self.redraw()
    
    def on_canvas_right_click(self, event):
        """Toggle folder menu on right-click if clicked on the default folder (index 0)."""
        idx = self.get_grid_index_at(event.x, event.y)
        
        if idx == 0:  # only default folder opens menu
            if self.folder_menu_open and self.folder_menu_anchor_index == idx:
                # Close if already open on this folder
                self.folder_menu_open = False
                self.folder_menu_anchor_index = None
            else:
                self.folder_menu_open = True
                self.folder_menu_anchor_index = idx
            self.redraw()
    
    def _check_handle_click(self, x, y):
        """Check if click is on a drag handle. Returns (handle_type, start_values) or None."""
        renderer = self.renderer
        canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        center_x = canvas_w // 2
        center_y = canvas_h // 2
        
        handle_size = 12
        
        # Handle positions from renderer are in canvas coords (at zoom=1)
        # When zoomed, content is scaled and centered, so need to transform click coords
        screen_info = getattr(renderer, '_screen_handles', {})
        for screen_name, handles in screen_info.items():
            for handle_type, hx, hy in handles:
                # Transform click from canvas coords back to content coords
                content_x = (x - center_x) / canvas_zoom + center_x if canvas_zoom > 0 else x
                content_y = (y - center_y) / canvas_zoom + center_y if canvas_zoom > 0 else y
                
                if abs(content_x - hx) <= handle_size and abs(content_y - hy) <= handle_size:
                    return (f'{screen_name}_{handle_type}', {
                        'x': renderer.screen_manager.main.x if screen_name == 'main' else renderer.screen_manager.external.x,
                        'y': renderer.screen_manager.main.y if screen_name == 'main' else renderer.screen_manager.external.y,
                        'w': renderer.screen_manager.main.w if screen_name == 'main' else renderer.screen_manager.external.w,
                        'h': renderer.screen_manager.main.h if screen_name == 'main' else renderer.screen_manager.external.h,
                    })
        
        return None
    
    def on_canvas_left_release(self, event):
        """Handle mouse release to apply drag changes."""
        if self._dragging_handle:
            self._dragging_handle = None
            self._drag_start_pos = None
            self._drag_start_values = None
    
    # --- Grid index ---
    def get_grid_index_at(self, click_x, click_y):
        """Click detection - only works on visible items within grid bounds."""
        # Account for canvas zoom - transform click from canvas coords to content coords
        canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
        if canvas_zoom != 1.0:
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            center_x = canvas_w // 2
            center_y = canvas_h // 2
            click_x = (click_x - center_x) / canvas_zoom + center_x
            click_y = (click_y - center_y) / canvas_zoom + center_y
        
        if hasattr(self.renderer, 'grid_positions') and hasattr(self.renderer, 'grid_click_regions'):
            current_rows = self.renderer.GRID_ROWS
            visible_cols = self.renderer.GRID_COLS
            grid_x = getattr(self.renderer, '_last_grid_x', 0)
            grid_y = getattr(self.renderer, '_last_grid_y', 0)
            grid_w = getattr(self.renderer, '_last_grid_w', 0)
            grid_h = getattr(self.renderer, '_last_grid_h', 0)
            
            for idx in range(len(self.renderer.grid_click_regions)):
                if idx >= len(self.renderer.grid_positions):
                    continue
                    
                pos = self.renderer.grid_positions[idx]
                click_region = self.renderer.grid_click_regions[idx]
                
                # Check if item is visible (size > 0 and within grid bounds)
                if pos[2] <= 0 or pos[3] <= 0:
                    continue
                
                # Calculate item's column position
                col = idx // current_rows
                
                # Account for scroll position when determining visible columns
                cell_w = getattr(self.renderer, '_full_cell_width', 0)
                cell_padding = getattr(self.renderer, 'GRID_PADDING', 0)
                cell_with_padding = cell_w + cell_padding if cell_w > 0 else 0
                scroll_columns = int(self.renderer.grid_scroll_x / cell_with_padding) if cell_with_padding > 0 else 0
                first_visible_col = scroll_columns
                last_visible_col = scroll_columns + visible_cols - 1
                
                # Only allow clicks on items within visible columns (accounting for scroll)
                if col < first_visible_col or col > last_visible_col:
                    continue
                
                x, y, w, h = click_region
                
                # Check if within grid bounds on screen
                if not (x >= grid_x and x + w <= grid_x + grid_w and 
                        y >= grid_y and y + h <= grid_y + grid_h):
                    continue
        
        # Check if click is within this item
                if x <= click_x <= x + w and y <= click_y <= y + h:
                    return idx
        
        return None
        
    def _build_folder_color_circle(self, color_name, size, darken=False):
        """
        Build circular folder color preview using:
        - Center-cropped zoom (2x by default)
        - Custom mask
        - Overlay image
        - Optional darkening for selected color
        """

        # Check we have previews
        if not hasattr(self, "folder_color_previews"):
            return None

        base_img = self.folder_color_previews.get(color_name)
        if base_img is None:
            return None

        img = base_img.convert("RGBA")

        # --- TRUE 2x zoom by cropping center half ---
        crop_scale = 0.5  # crop 50% of width/height from center
        crop_w = int(img.width * crop_scale)
        crop_h = int(img.height * crop_scale)
        left = (img.width - crop_w) // 2
        top = (img.height - crop_h) // 2
        right = left + crop_w
        bottom = top + crop_h

        cropped = img.crop((left, top, right, bottom))

        # Scale cropped area to final circle display size
        cropped = cropped.resize((size, size), Image.Resampling.LANCZOS)

        # --- Apply mask ---
        if self.color_mask_img:
            mask_resized = self.color_mask_img.resize((size, size), Image.Resampling.LANCZOS)
            cropped.putalpha(mask_resized)

        # --- Darken if selected ---
        if darken:
            enhancer = ImageEnhance.Brightness(cropped)
            cropped = enhancer.enhance(0.7)

        # --- Apply overlay ---
        if self.color_overlay_img:
            overlay_resized = self.color_overlay_img.resize((size, size), Image.Resampling.LANCZOS)
            cropped = Image.alpha_composite(cropped, overlay_resized)

        return ImageTk.PhotoImage(cropped) 
    
    # -------------------------------------------------
    # Rendering
    # -------------------------------------------------
    def redraw(self):
        # In single screen stacked mode, apply the automatic offset
        if (self.single_screen_stacked_mode and 
            self.renderer.screen_manager.screen_mode == "single"):
            rows = self.renderer.GRID_ROWS
            self._apply_stacked_offset(rows)
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return
        
        # Clear any previous folder menu items
        for item_id in self._folder_menu_items:
            self.canvas.delete(item_id)
        self._folder_menu_items = []
        self._folder_color_tk_refs = {}
        
        if not hasattr(self, 'color_mask_img'):
            assets_dir = Path(__file__).parent / "assets"
            color_mask_path = assets_dir / "color mask.png"
            color_overlay_path = assets_dir / "color overlay.png"
            
            self.color_mask_img = None
            self.color_overlay_img = None
            
            if color_mask_path.exists():
                self.color_mask_img = Image.open(color_mask_path).convert("L")
            if color_overlay_path.exists():
                self.color_overlay_img = Image.open(color_overlay_path).convert("RGBA")
        
        self._load_folder_color_previews()
        
        # TEMPORARILY DISABLE BG FOR TESTING - Skip background drawing entirely
        # Don't create/update bg canvas items
        # Get clean content WITHOUT background (so we don't duplicate)
        clean_content = self.renderer.composite((canvas_w, canvas_h), skip_background=True, skip_borders=True, skip_handles=True, skip_magnify=True)
        
        # Get content with background for magnify window
        content_with_bg = self.renderer.composite((canvas_w, canvas_h), skip_background=False, skip_borders=True, skip_handles=True, skip_magnify=True)
        
        # Add borders/handles overlays to a copy for canvas display
        if self.renderer.bezel_edit_mode:
            content_image = self.renderer.draw_overlays(clean_content.copy(), (canvas_w, canvas_h))
        else:
            content_image = clean_content
        
        # Apply canvas zoom to content only (bg stays fitted to canvas)
        canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
        if canvas_zoom != 1.0:
            new_w = int(canvas_w * canvas_zoom)
            new_h = int(canvas_h * canvas_zoom)
            content_image = content_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center positions
        img_x = canvas_w // 2
        img_y = canvas_h // 2
        
        # Generate background image (fitted to canvas, independent of zoom)
        bg_image = self.renderer.get_background_image((canvas_w, canvas_h))
        
        # Draw background first (fitted to canvas, independent of zoom)
        # For scrolling background, we need to create two image items
        self.tk_bg_img = ImageTk.PhotoImage(bg_image)
        
        # Store fitted bg width for scrolling calculations (from renderer)
        self._bg_fitted_width = getattr(self.renderer, '_bg_fitted_width', bg_image.width if bg_image else canvas_w)
        
        # Reset scroll offset when bg changes (new theme loaded)
        if not hasattr(self, '_bg_scroll_offset'):
            self._bg_scroll_offset = 0.0  # Use float for sub-pixel precision
        else:
            # Check if bg changed by comparing sizes
            old_bg = getattr(self, '_last_bg_size', (0, 0))
            new_bg_size = (bg_image.width, bg_image.height) if bg_image else (0, 0)
            if old_bg != new_bg_size:
                self._bg_scroll_offset = 0.0
                self._last_bg_size = new_bg_size
        
        if not hasattr(self, '_bg_scroll_timer'):
            self._bg_scroll_timer = None
        
        # Get background width for scrolling calculations
        bg_width = self._bg_fitted_width
        
        if not hasattr(self, "_canvas_bg_id") or self._canvas_bg_id is None:
            self._canvas_bg_id = self.canvas.create_image(img_x, img_y, anchor="center", image=self.tk_bg_img)
            self._canvas_bg_id_2 = self.canvas.create_image(img_x + bg_width, img_y, anchor="center", image=self.tk_bg_img)
            # Lower bg behind content
            self.canvas.lower(self._canvas_bg_id)
            self.canvas.lower(self._canvas_bg_id_2)
        else:
            self.canvas.coords(self._canvas_bg_id, img_x - self._bg_scroll_offset, img_y)
            self.canvas.coords(self._canvas_bg_id_2, img_x - self._bg_scroll_offset + bg_width, img_y)
            self.canvas.itemconfig(self._canvas_bg_id, image=self.tk_bg_img)
            self.canvas.itemconfig(self._canvas_bg_id_2, image=self.tk_bg_img)
        
        # Lower background to bottom to ensure video is sandwiched between bg and content
        self.canvas.lower(self._canvas_bg_id)
        self.canvas.lower(self._canvas_bg_id_2)
        
        # Start or update background scroll animation
        self._update_bg_scroll()
        
        # Draw content on top (may be zoomed, no background included)
        self.tk_img = ImageTk.PhotoImage(content_image)
        if not hasattr(self, "_canvas_image_id"):
            self._canvas_image_id = self.canvas.create_image(img_x, img_y, anchor="center", image=self.tk_img)
        else:
            self.canvas.coords(self._canvas_image_id, img_x, img_y)
            self.canvas.itemconfig(self._canvas_image_id, image=self.tk_img)
        
        # Raise content above everything (including videos) to ensure correct layering
        self.canvas.tag_raise(self._canvas_image_id)
        
        # Update video positions to match current canvas/zoom state
        self._update_video_positions()
        
        # Update video frames directly to canvas (only if video playback is enabled)
        if hasattr(self, 'video_player_manager') and getattr(self, 'video_playback', True):
            # Check if in single-screen stacked mode for ss_mask
            is_single_stacked = (
                self.renderer.screen_manager.screen_mode == "single" and 
                getattr(self.renderer, '_single_screen_stacked', False)
            )
            ss_mask = getattr(self.renderer, 'ss_mask', None)
            
            bezel_scale = min(
                (canvas_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.width,
                (canvas_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.bezel_img.height
            )
            device_x = self.renderer.DEVICE_PADDING + (canvas_w - 2 * self.renderer.DEVICE_PADDING - round(self.renderer.bezel_img.width * bezel_scale)) // 2
            device_y = self.renderer.DEVICE_PADDING + (canvas_h - 2 * self.renderer.DEVICE_PADDING - round(self.renderer.bezel_img.height * bezel_scale)) // 2
            
            # Get main screen geometry
            main_screen_geometry = None
            main_screen = getattr(self.renderer.screen_manager, 'main', None)
            if main_screen:
                main_screen_geometry = (
                    device_x + round(main_screen.x * bezel_scale),
                    device_y + round(main_screen.y * bezel_scale),
                    round(main_screen.w * bezel_scale),
                    round(main_screen.h * bezel_scale)
                )
                # Apply canvas zoom if needed (to match _get_screen_geometry)
                canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                if canvas_zoom != 1.0:
                    zoomed_w = int(canvas_w * canvas_zoom)
                    zoomed_h = int(canvas_h * canvas_zoom)
                    offset_x = (zoomed_w - canvas_w) // 2
                    offset_y = (zoomed_h - canvas_h) // 2
                    main_screen_geometry = (
                        int(main_screen_geometry[0] * canvas_zoom - offset_x),
                        int(main_screen_geometry[1] * canvas_zoom - offset_y),
                        int(main_screen_geometry[2] * canvas_zoom),
                        int(main_screen_geometry[3] * canvas_zoom)
                    )
            
            # Get external screen geometry for overlap calculation
            external_screen_geometry = None
            ext_screen = getattr(self.renderer.screen_manager, 'external', None)
            if ext_screen:
                external_screen_geometry = (
                    device_x + round(ext_screen.x * bezel_scale),
                    device_y + round(ext_screen.y * bezel_scale),
                    round(ext_screen.w * bezel_scale),
                    round(ext_screen.h * bezel_scale)
                )
                # Apply canvas zoom if needed (to match _get_screen_geometry)
                canvas_zoom = getattr(self, 'canvas_zoom', 1.0)
                if canvas_zoom != 1.0:
                    zoomed_w = int(canvas_w * canvas_zoom)
                    zoomed_h = int(canvas_h * canvas_zoom)
                    offset_x = (zoomed_w - canvas_w) // 2
                    offset_y = (zoomed_h - canvas_h) // 2
                    external_screen_geometry = (
                        int(external_screen_geometry[0] * canvas_zoom - offset_x),
                        int(external_screen_geometry[1] * canvas_zoom - offset_y),
                        int(external_screen_geometry[2] * canvas_zoom),
                        int(external_screen_geometry[3] * canvas_zoom)
                    )
            
            self.video_player_manager.update_canvas_frames(
                self.canvas,
                is_single_stacked=is_single_stacked,
                ss_mask=ss_mask,
                main_screen_geometry=main_screen_geometry,
                external_screen_geometry=external_screen_geometry
            )
        
        # Schedule next frame update for PIL videos (only if not already scheduled and playback enabled)
        if getattr(self, 'video_playback', True):
            if not hasattr(self, '_pil_video_timer_id') or self._pil_video_timer_id is None:
                self._schedule_pil_video_update()
        
        # Create mask overlay for single-screen stacked mode
        self._update_video_mask_overlay()
        
        # Draw magnify window separately (without canvas zoom, at original position)
        if self.renderer.bezel_edit_mode and getattr(self.renderer, 'magnify_window', True):
            # Composite with correct layering: bg -> video -> content
            # Start with just background (no content)
            mag_base = bg_image.copy()
            
            # Add video frames on top of background
            if hasattr(self, 'video_player_manager'):
                for screen_name, player in self.video_player_manager.players.items():
                    frame = player.get_current_frame() if hasattr(player, 'get_current_frame') else None
                    if frame:
                        # Get video position and size for this screen
                        geometry = self._get_screen_geometry(screen_name)
                        if geometry:
                            x, y, w, h = geometry
                            # Scale to canvas size (same as in redraw)
                            x = int(x * canvas_zoom)
                            y = int(y * canvas_zoom)
                            w = int(w * canvas_zoom)
                            h = int(h * canvas_zoom)
                            frame_resized = frame.resize((w, h), Image.Resampling.BILINEAR)
                            mag_base.paste(frame_resized, (x, y), frame_resized)
            
            # Add content (frame + wallpaper, no bg) on top of video
            mag_base.alpha_composite(clean_content, (0, 0))
            
            mag_overlay = self.renderer.get_magnify_window((canvas_w, canvas_h), mag_base)
            if mag_overlay:
                self.tk_mag_img = ImageTk.PhotoImage(mag_overlay)
                mag_margin = 20
                mag_x = canvas_w - mag_overlay.width - mag_margin
                mag_y = canvas_h - mag_overlay.height - mag_margin
                if not hasattr(self, "_canvas_mag_id"):
                    self._canvas_mag_id = self.canvas.create_image(mag_x, mag_y, anchor="nw", image=self.tk_mag_img)
                else:
                    self.canvas.coords(self._canvas_mag_id, mag_x, mag_y)
                    self.canvas.itemconfig(self._canvas_mag_id, image=self.tk_mag_img)
                
                # Raise magnify window to top (above bezel) like canvas zoom buttons
                self.canvas.tag_raise(self._canvas_mag_id)
        elif hasattr(self, "_canvas_mag_id"):
            self.canvas.delete(self._canvas_mag_id)
            delattr(self, "_canvas_mag_id")

        # Force canvas to update, helps maximize responsiveness
        # self.canvas.update_idletasks()
        
        # ----------------------------
        # Draw folder color menu if open
        # ----------------------------
        if self.folder_menu_open and self.folder_menu_anchor_index is not None:
            try:
                x, y, w, h = self.renderer.grid_positions[self.folder_menu_anchor_index]
            except AttributeError:
                x, y, w, h = 100, 100, 50, 50  # fallback

            # ----------------------------
            # Menu layout parameters (scale with cell size)
            # ----------------------------
            cell_size = min(w, h)
            circle_size = max(16, cell_size // 3)
            menu_padding = max(4, circle_size // 3)
            spacing = max(6, circle_size // 2)
            menu_width = menu_padding * 2 + len(self.folder_colors) * (circle_size + spacing) - spacing
            menu_height = circle_size + menu_padding * 2 + max(12, circle_size // 2)

            # Center menu over the folder circle
            folder_center_x = x + w // 2
            OFFSET_X = 0  # tweak this to nudge left/right
            menu_x = folder_center_x - menu_width // 2 + OFFSET_X
            menu_y = y - menu_height - 10  # slightly above folder

            # ----------------------------
            # Optional background
            # ----------------------------
            # bg_id = self.canvas.create_rectangle(
                # menu_x, menu_y, menu_x + menu_width, menu_y + menu_height,
                # fill="#323232", outline="#ffffff", width=1
            # )
            # self._folder_menu_items.append(bg_id)

            # ----------------------------
            # Optional title
            # ----------------------------
            # title_id = self.canvas.create_text(
            #     menu_x + menu_padding, menu_y + menu_padding,
            #     text="Folder Menu", anchor="nw", fill="white", font=("Arial", 10, "bold")
            # )
            # self._folder_menu_items.append(title_id)

            # ----------------------------
            # Draw folder color circles + checkmarks
            # ----------------------------
            # --- Compute dynamic spacing ---
            num_gaps = len(self.folder_colors) - 1
            total_space = menu_width - 2 * menu_padding - len(self.folder_colors) * circle_size
            spacing_dynamic = total_space / num_gaps if num_gaps > 0 else 0

            for i, color_name in enumerate(self.folder_colors):
                # Add half of circle size to start so the circle centers align
                circle_x = menu_x + menu_padding + (circle_size // 2) + i * (circle_size + spacing_dynamic)
                circle_y = menu_y + menu_padding + max(12, circle_size // 2)

                is_selected = self.default_folder_color_var.get() == color_name

                # Build folder circle image
                tk_img = self._build_folder_color_circle(
                    color_name,
                    circle_size,
                    darken=is_selected
                )
                if tk_img:
                    img_id = self.canvas.create_image(circle_x, circle_y, image=tk_img)
                    self._folder_menu_items.append(img_id)
                    self._folder_color_tk_refs[color_name] = tk_img  # prevent GC

                # Draw scaled checkmark if selected
                if is_selected and getattr(self, "checkmark_img_orig", None):
                    CHECK_SCALE = 0.55  # tweak to match native
                    check_size = int(circle_size * CHECK_SCALE)
                    check_img_resized = self.checkmark_img_orig.resize((check_size, check_size), Image.Resampling.LANCZOS)
                    tk_check_img = ImageTk.PhotoImage(check_img_resized)

                    check_id = self.canvas.create_image(circle_x, circle_y, image=tk_check_img)
                    self._folder_menu_items.append(check_id)

                    # Keep reference to prevent GC
                    self._folder_color_tk_refs[f"check_{color_name}"] = tk_check_img


if __name__ == "__main__":
    App().mainloop()