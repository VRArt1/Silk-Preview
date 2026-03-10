import tkinter as tk
import configparser
from datetime import datetime
from tkinter import filedialog, StringVar
from tkinter import PhotoImage
from tkinter import ttk
from pathlib import Path
from PIL import ImageTk, Image, ImageEnhance
import time

from tkinterdnd2 import DND_FILES, TkinterDnD

from renderer import Renderer
from widgets.preview_panel import PreviewPanel


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

        if "Settings" not in self.config:
            self.config["Settings"] = {}

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
        
        # Stacked mode offset percentages (how much of top screen is visible)
        # Based on measurements: 597px image height, visible top screen at each zoom level
        # 3 rows: 239px (40.0%), 2 rows: 292px (48.9%), 1 row: 372px (62.3%)
        self.stacked_offset_percentages = {
            3: 0.400,   # 3 rows → 40.0% visible
            2: 0.489,   # 2 rows → 48.9% visible
            1: 0.623,   # 1 row → 62.3% visible
        }
        
        # Single screen stacked mode (top screen visible above grid)
        self.single_screen_stacked_mode = self.config.getboolean("Settings", "single_screen_mode", fallback=True)
        
        # Calculate max values from zoom levels
        self.max_rows_dual = max(r for r, c in self.zoom_levels_dual)
        self.max_cols_dual = max(c for r, c in self.zoom_levels_dual)
        self.max_rows_single_dual = max(r for r, c in self.zoom_levels_single_dual)
        self.max_cols_single_dual = max(c for r, c in self.zoom_levels_single_dual)
        self.max_rows_single_stacked = max(r for r, c in self.zoom_levels_single_stacked)
        self.max_cols_single_stacked = max(c for r, c in self.zoom_levels_single_stacked)
        
        # Use appropriate zoom levels based on screen mode (default to dual)
        self.zoom_levels = self.zoom_levels_dual
        self.zoom_index = self.config.getint("Settings", "zoom_index", fallback=1)
        # Clamp zoom_index to valid range for default mode
        if self.zoom_index >= len(self.zoom_levels):
            self.zoom_index = len(self.zoom_levels) - 1

        # Maximum number of grid slots across all zoom levels
        self.max_grid_slots_dual = self.max_rows_dual * self.max_cols_dual
        self.max_grid_slots_single = max(
            self.max_rows_single_dual * self.max_cols_single_dual,
            self.max_rows_single_stacked * self.max_cols_single_stacked
        )
        self.max_grid_slots = max(self.max_grid_slots_dual, self.max_grid_slots_single)
        
        # Total columns for extended grid navigation (use max of all modes)
        self.total_cols = max(self.max_cols_dual, self.max_cols_single_dual, self.max_cols_single_stacked)

        # Load show_empty_slots setting early (needed before renderer init)
        if "show_empty_slots" not in self.config["Settings"]:
            self.config["Settings"]["show_empty_slots"] = "True"
        self.show_empty_slots = self.config.getboolean("Settings", "show_empty_slots", fallback=True)

        # Load remember_last_theme setting
        self.remember_last_theme = self.config.getboolean("Settings", "remember_last_theme", fallback=True)
        self.last_theme_path = self.config.get("Settings", "last_theme_path", fallback=None)
        
        # Load top screen icon scale (default 60%)
        self.top_screen_icon_scale = self.config.getint("Settings", "top_screen_icon_scale", fallback=60)
        
        # App grid settings are now loaded from device.json in each bezel folder
        # These are just initial defaults that will be overwritten by device settings
        self.app_grid_x_offset = 0
        self.app_grid_y_offset = -40
        self.app_grid_width = 400
        self.app_grid_icon_size = 50
        self.app_grid_icon_scale = 1.0
        
        # Load default folder color from settings, fallback to "blue"
        self.default_folder_color = self.config.get("Settings", "default_folder_color", fallback="blue")
        self.default_folder_color_var = tk.StringVar(value=self.default_folder_color)

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
        self.renderer.show_empty_slots = self.show_empty_slots
        self.renderer._single_screen_stacked = self.single_screen_stacked_mode
        self.renderer.app_grid_x_offset = self.app_grid_x_offset
        self.renderer.app_grid_y_offset = self.app_grid_y_offset
        self.renderer.app_grid_width = self.app_grid_width
        self.renderer.app_grid_icon_size = self.app_grid_icon_size
        self.renderer.app_grid_icon_scale = self.app_grid_icon_scale
        self.renderer.default_folder_color = self.default_folder_color
        
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
        
        # Bezel Edit Overlay Frame (initially hidden)
        self.bezel_edit_overlay = tk.Frame(self.canvas, bg="#2a2a2a", bd=2, relief="raised")
        self._create_bezel_edit_controls()
        
        # Register the root window as drop target for drag-and-drop (delayed to ensure window is ready)
        self.after(100, self._setup_dnd)

        # Preview panel
        self.preview_panel = PreviewPanel(self.main_frame, renderer=self.renderer, width=300)
        self.preview_panel.grid(row=0, column=1, sticky="ns")
        
        # Load initial theme now that preview panel exists
        if initial_theme_folder.exists():
            self.renderer.load_theme(initial_theme_folder, max_grid_items=self.max_grid_slots)
            self.preview_panel.refresh()

        # Controls
        self.controls = tk.Frame(self.main_frame)
        self.controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=8)

        # ----------------------------
        # Frame/Bezel selector - auto-discover available bezels
        # ----------------------------
        self.bezel_options = list(self.renderer.BEZEL_OPTIONS.keys())
        self.bezel_var = StringVar(value=self.bezel_options[0] if self.bezel_options else "Rainbow")
        saved_frame = self.config.get("Settings", "frame", fallback=self.bezel_var.get())
        if saved_frame in self.bezel_options:
            self.bezel_var.set(saved_frame)
            self.renderer.set_bezel(saved_frame)
        
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
        ttk.Button(self.controls, text="Load", command=self.load_theme).pack(side="left", padx=4)
        ttk.Button(self.controls, text="Refresh", command=self.refresh).pack(side="left", padx=4)
        
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
        self.app_grid_visible = getattr(self.renderer, 'app_grid_visible', True)
        self.populated_apps_visible = getattr(self.renderer, 'populated_apps_visible', True)
        self.single_stacked_var = tk.BooleanVar(value=self.single_screen_stacked_mode)
        self._icon_scale_var = tk.IntVar(value=self.top_screen_icon_scale)
        self.show_empty_slots_var = tk.BooleanVar(value=self.show_empty_slots)
        self.remember_var = tk.BooleanVar(value=self.remember_last_theme)
        self.bezel_edit_var = tk.BooleanVar(value=False)
        
        # ----------------------------
        # Settings button (right-aligned)
        # ----------------------------
        self.settings_button = ttk.Button(
            self.controls,
            text="Settings",
            command=self.open_settings
        )
        self.settings_button.pack(side="right", padx=(12, 4))
        
        # ----------------------------
        # Canvas and keyboard binds
        # ----------------------------
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)  # Track mouse position for magnify window
        
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
        self.update_idletasks()
        self.redraw()
        self._schedule_gif_redraw()
        
    # ----------------------------
    # Canvas resize
    # ----------------------------
    def _on_canvas_resize(self, event):
        """Canvas configure event - schedule redraw."""
        w, h = event.width, event.height
        
        if w > 1 and h > 1:
            self.after_idle(lambda: self._do_resize_with_size(w, h))
    
    def _do_resize_with_size(self, w, h):
        """Redraw with specific dimensions."""
        if w > 1 and h > 1:
            size = (w, h)
            if getattr(self, "_last_canvas_size", None) != size:
                self._last_canvas_size = size
                if hasattr(self.renderer, "_static_cache_dirty"):
                    self.renderer._static_cache_dirty = True
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
        self.show_empty_slots = self.show_empty_slots_var.get()
        self.renderer.show_empty_slots = self.show_empty_slots
        self.renderer._grid_items_dirty = True
        
        # Save to settings.ini immediately
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        self.config["Settings"]["show_empty_slots"] = str(self.show_empty_slots)
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
        
        # Force redraw to populate correct grid dimensions in renderer
        # (CRITICAL for proper spacing when switching bezels)
        self.renderer._static_cache_dirty = True
        self.redraw()
        
        # Save the bezel selection to settings
        self.save_settings()
        
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
        # Render full composite at high-res
        # -----------------------------
        full_image = self.renderer.composite((render_w, render_h), skip_background=clean)

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

    def _load_theme_from_path(self, theme_path: Path):
        """Load a theme from a given path (used by both button and drag-drop)."""
        if theme_path.is_dir():
            self.renderer.load_theme(theme_path, max_grid_items=self.max_grid_slots)
            self.preview_panel.refresh()
            self.redraw()
            self.last_theme_path = str(theme_path)
            self.save_settings()
    
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
        # Also pass max_grid_slots when refreshing
        self.renderer.load_theme(self.renderer.theme_path, max_grid_items=self.max_grid_slots)
        self.preview_panel.refresh()
        self.redraw()
        
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
        self.redraw()
    
    def toggle_populated_apps(self):
        self.renderer.populated_apps_visible = self.populated_apps_visible
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
        
        # Center screens button
        self.center_screens_btn = tk.Button(main_frame, text="Center Screens to Device", command=self._center_screens_to_device)
        self.center_screens_btn.pack(pady=5)
        
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
        """Update top screen icon scale from slider."""
        scale = int(value)
        self.top_screen_icon_scale = scale
        self.renderer.top_screen_icon_scale = scale / 100.0
        self.save_settings()
        self.redraw()
    
    # -------------------------------------------------
    # Save settings
    # -------------------------------------------------
    
    def save_settings(self):
        if "Settings" not in self.config:
            self.config["Settings"] = {}

        self.config["Settings"]["frame"] = self.bezel_var.get()
        self.config["Settings"]["zoom_index"] = str(self.zoom_index)
        self.config["Settings"]["corner_hints_visible"] = str(self.renderer.corner_hints_visible)
        self.config["Settings"]["dock_visible"] = str(self.renderer.dock_visible)
        self.config["Settings"]["remember_last_theme"] = str(self.remember_last_theme)
        if self.last_theme_path:
            self.config["Settings"]["last_theme_path"] = self.last_theme_path
        self.config["Settings"]["default_folder_color"] = self.default_folder_color_var.get()
        self.config["Settings"]["show_empty_slots"] = str(getattr(self, "show_empty_slots", True))
        self.config["Settings"]["top_screen_icon_scale"] = str(getattr(self, "top_screen_icon_scale", 60))
        self.config["Settings"]["single_screen_mode"] = str(getattr(self, "single_screen_stacked_mode", False))        

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
        """Track mouse position for magnify window."""
        self.renderer.mouse_x = event.x
        self.renderer.mouse_y = event.y
    
    # --- Canvis clicking ---

    def on_canvas_left_click(self, event):
        """Handle left-click for both grid selection and folder menu."""
        
        # Don't process grid clicks when in bezel edit mode
        if self.renderer.bezel_edit_mode:
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
    
    # --- Grid index ---
    def get_grid_index_at(self, click_x, click_y):
        """Click detection - only works on visible items within grid bounds."""
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
        
        # Generate the current frame via Renderer (handles static cache internally)
        frame_image = self.renderer.composite((canvas_w, canvas_h))

        # Correct Tkinter handling: update or create image once
        self.tk_img = ImageTk.PhotoImage(frame_image)
        if not hasattr(self, "_canvas_image_id"):
            self._canvas_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        else:
            self.canvas.itemconfig(self._canvas_image_id, image=self.tk_img)

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