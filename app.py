import tkinter as tk
import configparser
from datetime import datetime
from tkinter import filedialog, StringVar
from tkinter import PhotoImage
from tkinter import ttk
from pathlib import Path
from PIL import ImageTk, Image, ImageEnhance

from renderer import Renderer
from widgets.preview_panel import PreviewPanel


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Silk Preview")
        self.minsize(900, 700)
        
        icon_path = Path(__file__).parent / "assets/favicon.png"
        if icon_path.exists():
            self.icon_img = PhotoImage(file=icon_path)
            self.iconphoto(False, self.icon_img)
        
        checkmark_path = Path(__file__).parent / "assets/checkmark.png"
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

        # ----------------------------
        # Zoom levels (rows, cols)
        # ----------------------------
        self.zoom_levels = [
            (4, 5),  # large
            (3, 4),  # default
            (2, 3),  # small
        ]
        self.zoom_index = self.config.getint("Settings", "zoom_index", fallback=1)

        # Maximum number of grid slots across all zoom levels
        self.max_grid_slots = max(r * c for r, c in self.zoom_levels)

        # ----------------------------
        # Renderer
        # ----------------------------
        self.renderer = Renderer(self.max_grid_slots)
        self._load_folder_color_previews()
        
        # Load last theme folder if allowed
        self.remember_last_theme = self.config.getboolean(
            "Settings", "remember_last_theme", fallback=True
        )
        self.last_theme_path = self.config.get(
            "Settings", "last_theme_path", fallback=None
        )
        
        # Load default folder color from settings, fallback to "blue"
        self.default_folder_color_var = tk.StringVar()
        saved_color = self.config.get("Settings", "default_folder_color", fallback="blue")
        self.default_folder_color_var.set(saved_color)

        # Fix: apply saved color to renderer immediately
        self.renderer.set_default_folder_color(saved_color)
        
        # Ensure Settings section exists
        if "Settings" not in self.config:
            self.config["Settings"] = {}

        # Ensure default for show_empty_slots exists
        if "show_empty_slots" not in self.config["Settings"]:
            self.config["Settings"]["show_empty_slots"] = "True"

        # Now load it into memory
        self.show_empty_slots = self.config.getboolean(
            "Settings", "show_empty_slots", fallback=True
        )
        
        # ----------------------------
        # Folder menu state
        # ----------------------------
        self.folder_menu_open = False
        self.folder_menu_anchor_index = None  # which grid index the menu is attached to
        self.folder_colors = ["blue", "red", "gray", "orange", "yellow", "green", "purple", "pink"]
        self._folder_menu_items = []
        
        # ----------------------------
        # Folder color menu assets
        # ----------------------------
        assets_dir = Path(__file__).parent / "assets"

        mask_path = assets_dir / "color mask.png"
        overlay_path = assets_dir / "color overlay.png"

        self.color_mask_img = Image.open(mask_path).convert("L") if mask_path.exists() else None
        self.color_overlay_img = Image.open(overlay_path).convert("RGBA") if overlay_path.exists() else None

        # Keep references to generated circle images
        self._folder_color_tk_refs = {}

        # Determine which folder to load initially
        if self.remember_last_theme and self.last_theme_path and Path(self.last_theme_path).exists():
            initial_theme_folder = Path(self.last_theme_path)
        else:
            initial_theme_folder = Path(__file__).parent / "Placeholder Assets"
        
        # Load UI toggle from settings (default True)
        self.renderer.ui_visible = self.config.getboolean("Settings", "ui_visible", fallback=True)

        self.show_empty_slots = self.config.getboolean(
            "Settings", "show_empty_slots", fallback=True
        )

        # Create renderer
        self.renderer = Renderer(self.max_grid_slots)

        # Assign the value so Renderer knows
        self.renderer.show_empty_slots = self.show_empty_slots
        
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

        # Preview panel
        self.preview_panel = PreviewPanel(self.main_frame, renderer=self.renderer, width=300)
        self.preview_panel.grid(row=0, column=1, sticky="ns")
        
        # Load initial theme now that preview panel exists
        if initial_theme_folder.exists():
            self.renderer.load_theme(initial_theme_folder, max_grid_items=self.max_grid_slots)
            self.preview_panel.load_theme_info()

        # Controls
        self.controls = tk.Frame(self.main_frame)
        self.controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=8)

        # ----------------------------
        # Frame color selector
        # ----------------------------
        self.frame_options = ["Black", "Clear Purple", "Rainbow", "White", "Custom"]
        self.frame_var = StringVar(value="Rainbow")  # default
        saved_frame = self.config.get("UI", "frame", fallback="Rainbow")
        if saved_frame in self.frame_options:
            self.frame_var.set(saved_frame)
            self.renderer.set_frame(saved_frame)

        self.frame_dropdown = ttk.Combobox(
            self.controls,
            textvariable=self.frame_var,
            values=self.frame_options,
            state="readonly",
            width=12,
        )
        self.frame_dropdown.pack(side="left", padx=(0, 5))
        self.frame_dropdown.bind("<<ComboboxSelected>>", lambda e: self.change_frame(self.frame_var.get()))

        # ----------------------------
        # Buttons
        # ----------------------------
        ttk.Button(self.controls, text="Load", command=self.load_theme).pack(side="left", padx=4)
        ttk.Button(self.controls, text="Refresh", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(self.controls, text="Toggle UI", command=self.toggle_ui).pack(side="left", padx=4)
        
        
        #tk.Button(self.controls, text="Screenshot", command=self.take_screenshot).pack(side="left", padx=4)

        self.screenshot_button = ttk.Button(self.controls, text="Screenshot")
        self.screenshot_button.pack(side="left", padx=4)
        self.screenshot_button.bind("<Button-1>", self._handle_screenshot_click)
        
        # Zoom controls
        ttk.Button(self.controls, text="−", width=3, command=self.zoom_out).pack(side="left", padx=(4))
        ttk.Button(self.controls, text="+", width=3, command=self.zoom_in).pack(side="left", padx=0)

        # ----------------------------
        # Remember Last Theme Checkbox
        # ----------------------------
        self.remember_var = tk.BooleanVar(value=self.remember_last_theme)
        self.remember_frame = tk.Frame(self.controls)
        self.remember_frame.pack(side="right", padx=(12, 4))

        self.remember_check = tk.Checkbutton(
            self.remember_frame,
            text="Remember Theme",
            variable=self.remember_var,
            command=self.toggle_remember_last_theme
        )
        self.remember_check.pack()
        
        # ----------------------------
        # Show Empty Slots Checkbox
        # ----------------------------
        self.show_empty_slots_var = tk.BooleanVar(value=self.show_empty_slots)

        self.empty_frame = tk.Frame(self.controls)
        self.empty_frame.pack(side="right", padx=(12, 4))

        self.empty_check = tk.Checkbutton(
            self.empty_frame,
            text="Empty Slots",
            variable=self.show_empty_slots_var,
            command=self.toggle_empty_slots  # callback when toggled
        )
        self.empty_check.pack()        


        

        # ----------------------------
        # Canvas and keyboard binds
        # ----------------------------
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.bind("<Button-1>", self.on_canvas_left_click)

        # Right-click opens the folder menu
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

        self.bind("<Left>", lambda e: self.move_selection(-1, 0))
        self.bind("<Right>", lambda e: self.move_selection(1, 0))
        self.bind("<Up>", lambda e: self.move_selection(0, -1))
        self.bind("<Down>", lambda e: self.move_selection(0, 1))
        self.bind("<plus>", lambda e: self.zoom_in())
        self.bind("<minus>", lambda e: self.zoom_out())
        self.bind("<KP_Add>", lambda e: self.zoom_in())
        self.bind("<KP_Subtract>", lambda e: self.zoom_out())
        self.bind("<r>", lambda e: self.refresh())
        self.bind("<R>", lambda e: self.refresh())
        self.bind("<Tab>", self.cycle_frame)
        self.bind("<Shift-Tab>", self.cycle_frame_backward)
        self.bind("u", lambda e: self.toggle_ui())
        self.bind("U", lambda e: self.toggle_ui())
        self.bind("s", lambda e: self.take_screenshot(clean=False))
        self.bind("S", lambda e: self.take_screenshot(clean=False))
        self.bind("<Control-s>", lambda e: self.take_screenshot(clean=True))
        self.bind("<Control-S>", lambda e: self.take_screenshot(clean=True))
        self.bind("l", lambda e: self.load_theme())
        self.bind("L", lambda e: self.load_theme())


        # ----------------------------
        # Apply zoom and start loop
        # ----------------------------
        self._apply_zoom()
        self.update_idletasks()
        self.redraw()
        self._schedule_gif_redraw()
        
    # ----------------------------
    # Canvas resize with debounce
    # ----------------------------
    def _on_canvas_resize(self, event):
        """Debounced resize that waits for a valid canvas size before redrawing."""
        if hasattr(self, "_resize_after_id"):
            self.after_cancel(self._resize_after_id)

        def check_and_resize():
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()

            # Only redraw if canvas has a valid size
            if canvas_w > 1 and canvas_h > 1:
                self._do_resize()
            else:
                # Try again shortly until a valid size is available
                self._resize_after_id = self.after(10, check_and_resize)

        # Use short delay to debounce initial rapid <Configure> events
        self._resize_after_id = self.after(50, check_and_resize)

    def _do_resize(self):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        size = (canvas_w, canvas_h)

        # Only rebuild if size changed
        if getattr(self, "_last_canvas_size", None) != size:
            self._last_canvas_size = size

            # Force renderer static cache to rebuild
            if hasattr(self.renderer, "_static_cache_dirty"):
                self.renderer._static_cache_dirty = True
                # Clear any old resize cache
                if hasattr(self.renderer, "_resize_cache"):
                    self.renderer._resize_cache.clear()

            self.redraw()
    
    def cycle_frame(self, event):
        # Get current index
        current_index = self.frame_options.index(self.frame_var.get())
        # Move to next index, wrap around
        next_index = (current_index + 1) % len(self.frame_options)
        # Update dropdown and renderer
        self.frame_var.set(self.frame_options[next_index])
        self.change_frame(self.frame_options[next_index])
        return "break"  # Prevent default tab behavior (focus change)
    
    def cycle_frame_backward(self, event):
        # Get current index
        current_index = self.frame_options.index(self.frame_var.get())
        # Move to previous index, wrap around
        prev_index = (current_index - 1) % len(self.frame_options)
        # Update dropdown and renderer
        self.frame_var.set(self.frame_options[prev_index])
        self.change_frame(self.frame_options[prev_index])
        return "break"  # Prevent default focus change
    
    def toggle_remember_last_theme(self):
        self.remember_last_theme = self.remember_var.get()
        self.save_settings()
    
    def toggle_empty_slots(self):
        # Update both App and Renderer
        self.show_empty_slots = self.show_empty_slots_var.get()
        self.renderer.show_empty_slots = self.show_empty_slots
        
        # Save to settings.ini immediately
        if "Settings" not in self.config:
            self.config["Settings"] = {}
        self.config["Settings"]["show_empty_slots"] = str(self.show_empty_slots)
        with open(self.settings_path, "w") as f:
            self.config.write(f)

        # Redraw UI to reflect change immediately
        self.redraw()
    
    def _load_folder_color_previews(self):
        """
        Loads all default folder color images once for menu preview use.
        """
        from pathlib import Path
        from PIL import Image

        self.folder_color_previews = {}

        folder_dir = Path("assets/default folder")

        for img_path in folder_dir.glob("*.png"):
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
        # print("Loaded:", list(self.folder_color_previews.keys()))
        # print("Loaded preview keys:", self.folder_color_previews.keys())
    
    # -------------------------------------------------
    # Automatic GIF/WebP redraw for top screen
    # -------------------------------------------------
    def _schedule_gif_redraw(self):
        """
        Automatically advance and redraw top/bottom wallpapers and selected hero.
        Animations now run independently at their own speed.
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

        # Redraw canvas
        self.redraw()

        # Run again after ~16ms (~60 FPS)
        self.after(16, self._schedule_gif_redraw)

    # -------------------------------------------------
    # Frame color callback
    # -------------------------------------------------
    def change_frame(self, selection):
        self.renderer.set_frame(selection)
        self.save_settings()
        self.redraw()
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
            (canvas_w - 2 * self.renderer.DEVICE_PADDING) / self.renderer.frame_img.width,
            (canvas_h - 2 * self.renderer.DEVICE_PADDING) / self.renderer.frame_img.height
        )

        device_w = round(self.renderer.frame_img.width * scale * RES_FACTOR)
        device_h = round(self.renderer.frame_img.height * scale * RES_FACTOR)
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
            self.renderer.load_theme(Path(folder), max_grid_items=self.max_grid_slots)
            self.preview_panel.load_theme_info()
            self.redraw()
            self.last_theme_path = folder
            self.save_settings()

    def refresh(self):
        # Also pass max_grid_slots when refreshing
        self.renderer.load_theme(self.renderer.theme_path, max_grid_items=self.max_grid_slots)
        self.preview_panel.load_theme_info()
        self.redraw()
        
    def toggle_ui(self):
        self.renderer.ui_visible = not self.renderer.ui_visible
        self.save_settings()
        self.redraw()
        
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

        self.save_settings()
        self.redraw()

    # -------------------------------------------------
    # Save settings
    # -------------------------------------------------
    
    def save_settings(self):
        if "Settings" not in self.config:
            self.config["Settings"] = {}

        self.config["Settings"]["frame"] = self.frame_var.get()
        self.config["Settings"]["zoom_index"] = str(self.zoom_index)
        self.config["Settings"]["ui_visible"] = str(self.renderer.ui_visible)
        self.config["Settings"]["remember_last_theme"] = str(self.remember_last_theme)
        if self.last_theme_path:
            self.config["Settings"]["last_theme_path"] = self.last_theme_path
        self.config["Settings"]["default_folder_color"] = self.default_folder_color_var.get()
        self.config["Settings"]["show_empty_slots"] = str(getattr(self, "show_empty_slots", True))
        

        with open(self.settings_path, "w") as f:
            self.config.write(f)
    
    # -------------------------------------------------
    # Grid selection
    # -------------------------------------------------

    def move_selection(self, dx, dy):
        """Keyboard movement (instant, grid-locked)."""
        cols = self.renderer.GRID_COLS
        rows = self.renderer.GRID_ROWS

        idx = self.renderer.selected_index
        row = idx // cols
        col = idx % cols

        new_row = max(0, min(rows - 1, row + dy))
        new_col = max(0, min(cols - 1, col + dx))
        new_idx = new_row * cols + new_col

        if hasattr(self.renderer, "grid_items") and self.renderer.grid_items:
            new_idx = min(new_idx, len(self.renderer.grid_items) - 1)

        self.renderer.selected_index = new_idx
        self.redraw()

    
    # --- Canvis clicking ---

    def on_canvas_left_click(self, event):
        """Handle left-click for both grid selection and folder menu."""

        clicked_on_menu = False
        if self.folder_menu_open and self.folder_menu_anchor_index is not None:
            # Check if click is on a color circle
            try:
                x, y, w, h = self.renderer.grid_positions[self.folder_menu_anchor_index]
            except AttributeError:
                x, y, w, h = 100, 100, 50, 50

            menu_padding = 8
            circle_size = 24
            spacing = 12
            menu_width = menu_padding*2 + len(self.folder_colors) * (circle_size + spacing) - spacing
            menu_height = circle_size + menu_padding*2 + 20
            menu_x = x + w//2 - menu_width//2
            menu_y = y - menu_height - 10

            for i, color_name in enumerate(self.folder_colors):
                circle_x = menu_x + menu_padding + i*(circle_size + spacing)
                circle_y = menu_y + menu_padding + 20
                if (event.x - circle_x)**2 + (event.y - circle_y)**2 <= (circle_size//2)**2:
                    # clicked a color
                    self.default_folder_color_var.set(color_name)
                    self.renderer.set_default_folder_color(color_name)
                    self.save_settings()
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
            if idx is not None:
                self.renderer.selected_index = idx
                self.redraw()
    
    def on_canvas_right_click(self, event):
        """Open folder menu on right-click if clicked on the default folder (index 0)."""
        idx = self.get_grid_index_at(event.x, event.y)
        if idx == 0:  # only default folder opens menu
            self.folder_menu_open = True
            self.folder_menu_anchor_index = idx
            self.redraw()
    
    # --- Grid index ---
    def get_grid_index_at(self, click_x, click_y):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        pad = self.renderer.DEVICE_PADDING

        scale = min(
            (canvas_w - 2 * pad) / self.renderer.frame_img.width,
            (canvas_h - 2 * pad) / self.renderer.frame_img.height
        )

        device_w = round(self.renderer.frame_img.width * scale)
        device_h = round(self.renderer.frame_img.height * scale)
        device_x = pad + (canvas_w - 2 * pad - device_w) // 2
        device_y = pad + (canvas_h - 2 * pad - device_h) // 2

        grid_x = device_x + round(205 * scale)
        grid_y = device_y + round(540 * scale)
        grid_w = round(392 * scale)
        grid_h = round(340 * scale) - round(40 * scale)
        GRID_OUTER_PADDING = 6

        cell_w = (grid_w - 2 * GRID_OUTER_PADDING - (self.renderer.GRID_COLS - 1) * self.renderer.GRID_PADDING) // self.renderer.GRID_COLS
        cell_h = (grid_h - 2 * GRID_OUTER_PADDING - (self.renderer.GRID_ROWS - 1) * self.renderer.GRID_PADDING) // self.renderer.GRID_ROWS

        for row in range(self.renderer.GRID_ROWS):
            for col in range(self.renderer.GRID_COLS):
                x0 = grid_x + GRID_OUTER_PADDING + col * (cell_w + self.renderer.GRID_PADDING)
                y0 = grid_y + GRID_OUTER_PADDING + row * (cell_h + self.renderer.GRID_PADDING)
                x1 = x0 + cell_w
                y1 = y0 + cell_h
                if x0 <= click_x <= x1 and y0 <= click_y <= y1:
                    return row * self.renderer.GRID_COLS + col
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
        cropped = cropped.resize((size, size), Image.LANCZOS)

        # --- Apply mask ---
        if self.color_mask_img:
            mask_resized = self.color_mask_img.resize((size, size), Image.LANCZOS)
            cropped.putalpha(mask_resized)

        # --- Darken if selected ---
        if darken:
            enhancer = ImageEnhance.Brightness(cropped)
            cropped = enhancer.enhance(0.7)

        # --- Apply overlay ---
        if self.color_overlay_img:
            overlay_resized = self.color_overlay_img.resize((size, size), Image.LANCZOS)
            cropped = Image.alpha_composite(cropped, overlay_resized)

        return ImageTk.PhotoImage(cropped) 
    
    # -------------------------------------------------
    # Rendering
    # -------------------------------------------------
    def redraw(self):
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return
        
        # Clear any previous folder menu items
        for item_id in self._folder_menu_items:
            self.canvas.delete(item_id)
        self._folder_menu_items = []
        
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
            # Menu layout parameters
            # ----------------------------
            menu_padding = 8
            circle_size = 24
            spacing = 12
            menu_width = menu_padding * 2 + len(self.folder_colors) * (circle_size + spacing) - spacing
            menu_height = circle_size + menu_padding * 2 + 20

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
                circle_y = menu_y + menu_padding + 20

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
                    check_img_resized = self.checkmark_img_orig.resize((check_size, check_size), Image.LANCZOS)
                    tk_check_img = ImageTk.PhotoImage(check_img_resized)

                    check_id = self.canvas.create_image(circle_x, circle_y, image=tk_check_img)
                    self._folder_menu_items.append(check_id)

                    # Keep reference to prevent GC
                    self._folder_color_tk_refs[f"check_{color_name}"] = tk_check_img
                    
if __name__ == "__main__":
    App().mainloop()