import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Settings")
        self.geometry("420x550")
        self.resizable(True, True)
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / "assets" / "favicon_settings.png"
        if icon_path.exists():
            try:
                icon_img = Image.open(icon_path)
                if icon_img.mode != 'RGBA':
                    icon_img = icon_img.convert('RGBA')
                self._settings_icon = ImageTk.PhotoImage(icon_img)
                self.iconphoto(False, self._settings_icon)
            except Exception:
                pass
        
        self.transient(parent)
        
        self._load_assets()
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas, padding="10")
        
        def on_scroll(*args):
            scrollbar.set(*args)
            if float(args[0]) == 0.0 and float(args[1]) == 1.0:
                scrollbar.pack_forget()
            else:
                scrollbar.pack(side="right", fill="y")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=on_scroll)
        
        canvas.pack(side="left", fill="both", expand=True)
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            # Scroll only if not at top/bottom bounds
            current = canvas.yview()[0]
            if event.delta > 0 and current > 0:
                canvas.yview_scroll(-1, "units")
            elif event.delta < 0 and current < 1:
                canvas.yview_scroll(1, "units")
        
        self.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Use scrollable_frame as parent for all widgets
        top_frame = ttk.LabelFrame(self.scrollable_frame, text="Appearance", padding="10")
        top_frame.pack(fill="x", pady=(0, 10))
        
        accent_frame = ttk.Frame(top_frame)
        accent_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(accent_frame, text="Accent Color:").pack(side="left")
        self.accent_colors_frame = tk.Frame(accent_frame, bg=self._get_bg_color())
        self.accent_colors_frame.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self._build_accent_color_picker()
        
        dock_apps_frame = ttk.Frame(top_frame)
        dock_apps_frame.pack(fill="x", pady=(0, 5))
        
        dock_frame = ttk.Frame(dock_apps_frame)
        dock_frame.pack(side="left", fill="x", expand=True)
        self.dock_var = tk.BooleanVar(value=app.dock_var.get())
        dock_check = ttk.Checkbutton(
            dock_frame,
            text="Dock Background",
            variable=self.dock_var,
            command=self._on_dock_change
        )
        dock_check.pack(anchor="w")
        
        scale_frame = ttk.Frame(top_frame)
        scale_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(scale_frame, text="Logo Size:").pack(side="left")
        self.scale_var = tk.IntVar(value=app._icon_scale_var.get())
        self.scale_slider = ttk.Scale(
            scale_frame,
            from_=30,
            to=200,
            orient="horizontal",
            variable=self.scale_var,
            command=self._on_scale_change
        )
        self.scale_slider.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        self.scale_display = ttk.Label(scale_frame, text=f"{self.scale_var.get()}%", width=5)
        self.scale_display.pack(side="left", padx=(5, 0))
        self.scale_display.bind("<Button-1>", self._on_scale_display_click)
        
        self.scale_entry = ttk.Entry(scale_frame, textvariable=self.scale_var, width=5)
        self.scale_entry.bind("<Return>", self._on_scale_entry_change)
        self.scale_entry.bind("<FocusOut>", self._on_scale_entry_change)
        
        self.corner_hints_var = tk.BooleanVar(value=app.corner_hints_var.get())
        corner_check = ttk.Checkbutton(
            top_frame,
            text="Show Corner Hints",
            variable=self.corner_hints_var,
            command=self._on_corner_hints_change
        )
        corner_check.pack(anchor="w", pady=(5, 0))
        
        self.single_screen_var = tk.BooleanVar(value=app.single_stacked_var.get())
        single_check = ttk.Checkbutton(
            top_frame,
            text="Single Screen Mode",
            variable=self.single_screen_var,
            command=self._on_single_screen_change
        )
        single_check.pack(anchor="w", pady=(0, 5))
        
        options_frame = ttk.LabelFrame(self.scrollable_frame, text="Options", padding="10")
        options_frame.pack(fill="x", pady=(0, 10))
        
        self.populated_apps_var = tk.BooleanVar(value=getattr(app, 'populated_apps_visible', True))
        populated_apps_check = ttk.Checkbutton(
            options_frame,
            text="Apps",
            variable=self.populated_apps_var,
            command=self._on_populated_apps_change
        )
        populated_apps_check.pack(anchor="w")
        
        self.empty_apps_var = tk.BooleanVar(value=getattr(app, 'app_grid_visible', True))
        self.empty_apps_check = ttk.Checkbutton(
            options_frame,
            text="Empty Apps",
            variable=self.empty_apps_var,
            command=self._on_empty_apps_change
        )
        self.empty_apps_check.pack(anchor="w")
        
        self.empty_slots_var = tk.BooleanVar(value=app.empty_slots_var.get())
        empty_check = ttk.Checkbutton(
            options_frame,
            text="Empty Slots",
            variable=self.empty_slots_var,
            command=self._on_empty_slots_change
        )
        empty_check.pack(anchor="w")
        
        self.remember_var = tk.BooleanVar(value=app.remember_var.get())
        remember_check = ttk.Checkbutton(
            options_frame,
            text="Remember Last Theme",
            variable=self.remember_var,
            command=self._on_remember_change
        )
        remember_check.pack(anchor="w")
        
        self.video_playback_var = tk.BooleanVar(value=getattr(app, 'video_playback', True))
        video_playback_check = ttk.Checkbutton(
            options_frame,
            text="Video Playback",
            variable=self.video_playback_var,
            command=self._on_video_playback_change
        )
        video_playback_check.pack(anchor="w")
        
        bg_frame = ttk.LabelFrame(self.scrollable_frame, text="UI", padding="10")
        bg_frame.pack(fill="x", pady=(0, 10))
        
        bg_scroll_frame = ttk.Frame(bg_frame)
        bg_scroll_frame.pack(fill="x")
        ttk.Label(bg_scroll_frame, text="Scroll Speed:").pack(side="left")
        self.bg_scroll_speed_var = tk.IntVar(value=getattr(app, 'bg_scroll_speed', 1))
        bg_scroll_slider = ttk.Scale(
            bg_scroll_frame,
            from_=0,
            to=10,
            orient="horizontal",
            variable=self.bg_scroll_speed_var,
            command=self._on_bg_scroll_speed_change
        )
        bg_scroll_slider.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        self.bg_scroll_speed_label = ttk.Label(bg_scroll_frame, text=f"{self.bg_scroll_speed_var.get()}")
        self.bg_scroll_speed_label.pack(side="left", padx=(5, 0))
        
        self.reverse_direction_var = tk.BooleanVar(value=getattr(app, 'reverse_direction', False))
        reverse_direction_check = ttk.Checkbutton(
            bg_frame,
            text="Reverse Direction",
            variable=self.reverse_direction_var,
            command=self._on_reverse_direction_change
        )
        reverse_direction_check.pack(anchor="w", pady=(5, 0))
        
        folders_frame = ttk.LabelFrame(self.scrollable_frame, text="Folders", padding="10")
        folders_frame.pack(fill="x", pady=(0, 0))
        
        assets_btn = ttk.Button(folders_frame, text="Open Assets Folder", command=self._open_assets_folder)
        assets_btn.pack(fill="x", pady=(0, 5))
        
        my_themes_btn = ttk.Button(folders_frame, text="Open My Themes Folder", command=self._open_my_themes_folder)
        my_themes_btn.pack(fill="x", pady=(0, 5))
        
        screenshots_btn = ttk.Button(folders_frame, text="Open Screenshots Folder", command=self._open_screenshots_folder)
        screenshots_btn.pack(fill="x")
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
    
    def _get_bg_color(self):
        try:
            return self.cget("bg")
        except:
            return "#f0f0f0"
    
    def _load_assets(self):
        assets_dir = Path(__file__).parent.parent / "assets"
        
        self.folder_color_previews = {}
        folder_dir = assets_dir / "default folder"
        for img_path in folder_dir.glob("icon*.png"):
            stem = img_path.stem.lower()
            if "_" in stem:
                color_name = stem.split("_")[-1]
            else:
                color_name = "blue"
            try:
                img = Image.open(img_path).convert("RGBA")
                self.folder_color_previews[color_name] = img
            except Exception:
                pass
        
        color_mask_path = assets_dir / "color mask.png"
        self.color_mask_img = None
        if color_mask_path.exists():
            self.color_mask_img = Image.open(color_mask_path).convert("L")
        
        color_overlay_path = assets_dir / "color overlay.png"
        self.color_overlay_img = None
        if color_overlay_path.exists():
            self.color_overlay_img = Image.open(color_overlay_path).convert("RGBA")
        
        checkmark_path = assets_dir / "ui" / "checkmark.png"
        self.checkmark_img = None
        if checkmark_path.exists():
            self.checkmark_img = Image.open(checkmark_path).convert("RGBA")
    
    def _build_folder_color_circle(self, color_name, size, darken=False, is_selected=False):
        base_img = self.folder_color_previews.get(color_name)
        if base_img is None:
            return None
        
        img = base_img.convert("RGBA")
        
        crop_scale = 0.5
        crop_w = int(img.width * crop_scale)
        crop_h = int(img.height * crop_scale)
        left = (img.width - crop_w) // 2
        top = (img.height - crop_h) // 2
        right = left + crop_w
        bottom = top + crop_h
        
        cropped = img.crop((left, top, right, bottom))
        cropped = cropped.resize((size, size), Image.Resampling.LANCZOS)
        
        if self.color_mask_img:
            mask_resized = self.color_mask_img.resize((size, size), Image.Resampling.LANCZOS)
            cropped.putalpha(mask_resized)
        
        if darken:
            enhancer = ImageEnhance.Brightness(cropped)
            cropped = enhancer.enhance(0.85)
        
        if self.color_overlay_img:
            overlay_resized = self.color_overlay_img.resize((size, size), Image.Resampling.LANCZOS)
            cropped = Image.alpha_composite(cropped, overlay_resized)
        
        if is_selected and self.checkmark_img:
            check_size = int(size * 0.55)
            check_resized = self.checkmark_img.resize((check_size, check_size), Image.Resampling.LANCZOS)
            check_x = (size - check_size) // 2
            check_y = (size - check_size) // 2
            cropped.paste(check_resized, (check_x, check_y), check_resized)
        
        return ImageTk.PhotoImage(cropped, master=self)
    
    def _build_accent_color_picker(self):
        self._accent_color_refs = {}
        circle_size = 24
        bg_color = self._get_bg_color()
        
        # Use grid to space colors evenly across the row
        for i, color_name in enumerate(self.app.folder_colors):
            is_selected = self.app.default_folder_color_var.get() == color_name
            
            tk_img = self._build_folder_color_circle(color_name, circle_size, darken=is_selected, is_selected=is_selected)
            if tk_img:
                label = tk.Label(self.accent_colors_frame, image=tk_img, bg=bg_color)
                label.grid(row=0, column=i, padx=4, sticky="ew")
                label.bind("<Button-1>", lambda e, c=color_name: self._on_accent_color_click(c))
                
                self._accent_color_refs[color_name] = tk_img
        
        # Configure columns to expand evenly
        num_colors = len(self.app.folder_colors)
        self.accent_colors_frame.columnconfigure(tuple(range(num_colors)), weight=1, uniform="color")
    
    def _rebuild_accent_color_picker(self):
        for widget in self.accent_colors_frame.winfo_children():
            widget.destroy()
        self._accent_color_refs = {}
        self._build_accent_color_picker()
    
    def _on_accent_color_click(self, color_name):
        self.app.default_folder_color_var.set(color_name)
        self.app.renderer.set_default_folder_color(color_name)
        self.app.save_settings()
        self._rebuild_accent_color_picker()
    
    def _on_corner_hints_change(self):
        self.app.corner_hints_var.set(self.corner_hints_var.get())
        self.app.toggle_corner_hints()
    
    def _on_dock_change(self):
        self.app.dock_var.set(self.dock_var.get())
        self.app.toggle_dock()
    
    def _on_populated_apps_change(self):
        was_on = self.populated_apps_var.get()
        if not was_on:
            # Store previous Empty Apps state before turning off
            self._empty_apps_prev_state = self.app.app_grid_visible
            # Hide empty apps in software
            self.app.app_grid_visible = False
            self.app.toggle_app_grid()
            # Disable Empty Apps checkbox but keep it showing current state
            self.empty_apps_check.config(state="disabled")
        else:
            # Restore Empty Apps to its previous state
            prev_state = getattr(self, '_empty_apps_prev_state', True)
            self.empty_apps_var.set(prev_state)
            self.app.app_grid_visible = prev_state
            self.app.toggle_app_grid()
            # Re-enable Empty Apps checkbox
            self.empty_apps_check.config(state="normal")
        self.app.populated_apps_visible = was_on
        self.app.toggle_populated_apps()
    
    def _on_empty_apps_change(self):
        self.app.app_grid_visible = self.empty_apps_var.get()
        self.app.toggle_app_grid()
    
    def _on_empty_slots_change(self):
        self.app.empty_slots_var.set(self.empty_slots_var.get())
        self.app.toggle_empty_slots()
    
    def _on_single_screen_change(self):
        self.app.single_stacked_var.set(self.single_screen_var.get())
        self.app.toggle_single_screen_stacked()
    
    def _on_scale_change(self, value):
        scale_value = int(float(value))
        scale_value = round(scale_value / 10) * 10
        scale_value = max(30, min(200, scale_value))
        self.scale_var.set(scale_value)
        self.scale_display.config(text=f"{scale_value}%")
        self.app._icon_scale_var.set(scale_value)
        self.app._on_icon_scale_change(scale_value)
    
    def _on_scale_display_click(self, event):
        self.scale_display.pack_forget()
        self.scale_entry.pack(side="left", padx=(5, 0))
        self.scale_entry.focus_set()
        self.scale_entry.select_range(0, tk.END)
    
    def _on_scale_entry_change(self, event):
        try:
            scale_value = int(self.scale_var.get())
            scale_value = round(scale_value / 10) * 10
            scale_value = max(30, min(200, scale_value))
            self.scale_var.set(scale_value)
            self.scale_display.config(text=f"{scale_value}%")
            self.scale_slider.set(scale_value)
            self.app._icon_scale_var.set(scale_value)
            self.app._on_icon_scale_change(scale_value)
        except ValueError:
            self.scale_var.set(self.app._icon_scale_var.get())
            self.scale_display.config(text=f"{self.scale_var.get()}%")
        
        self.scale_entry.pack_forget()
        self.scale_display.pack(side="left", padx=(5, 0))
    
    def _on_remember_change(self):
        self.app.remember_var.set(self.remember_var.get())
        self.app.toggle_remember_last_theme()
    
    def _on_video_playback_change(self):
        self.app.video_playback = self.video_playback_var.get()
        
        if "Settings" not in self.app.config:
            self.app.config["Settings"] = {}
        self.app.config["Settings"]["video_playback"] = str(self.video_playback_var.get())
        with open(self.app.settings_path, "w") as f:
            self.app.config.write(f)
        
        if self.video_playback_var.get():
            # Re-enable video playback - re-enable video wallpaper mode and setup videos
            self.app.renderer.screen_manager.main.reenable_video_wallpaper()
            self.app.renderer.screen_manager.external.reenable_video_wallpaper()
            # Setup videos
            self.app._try_setup_videos_with_retry(on_video_ready_callback=self.app._on_video_playing)
        else:
            # Disable video playback - show static first frame
            self.app.renderer.screen_manager.main.disable_video_wallpaper()
            self.app.renderer.screen_manager.external.disable_video_wallpaper()
            if hasattr(self.app, 'video_player_manager'):
                self.app.video_player_manager.cleanup()
            self.app._stop_pil_video_updates()
            self.app.renderer._invalidate_static_cache()
            self.app.redraw()
    
    def _on_bg_scroll_speed_change(self, value):
        speed = int(float(value))
        self.bg_scroll_speed_var.set(speed)
        self.app.bg_scroll_speed = speed
        self.bg_scroll_speed_label.config(text=f"{speed}")
        
        if "Settings" not in self.app.config:
            self.app.config["Settings"] = {}
        self.app.config["Settings"]["bg_scroll_speed"] = str(speed)
        with open(self.app.settings_path, "w") as f:
            self.app.config.write(f)
        
        self.app._update_bg_scroll()
    
    def _on_reverse_direction_change(self):
        self.app.reverse_direction = self.reverse_direction_var.get()
        
        if "Settings" not in self.app.config:
            self.app.config["Settings"] = {}
        self.app.config["Settings"]["reverse_direction"] = str(self.reverse_direction_var.get())
        with open(self.app.settings_path, "w") as f:
            self.app.config.write(f)
        
        self.app._update_bg_scroll()
        with open(self.app.settings_path, "w") as f:
            self.app.config.write(f)
    
    def update_from_app(self):
        self.corner_hints_var.set(self.app.corner_hints_var.get())
        self.dock_var.set(self.app.dock_var.get())
        self.populated_apps_var.set(getattr(self.app, 'populated_apps_visible', True))
        self.empty_apps_var.set(self.app.app_grid_visible)
        self.empty_slots_var.set(self.app.empty_slots_var.get())
        self.single_screen_var.set(self.app.single_stacked_var.get())
        self.scale_var.set(self.app._icon_scale_var.get())
        self.scale_display.config(text=f"{self.scale_var.get()}%")
        self.remember_var.set(self.app.remember_var.get())
        self.bg_scroll_speed_var.set(getattr(self.app, 'bg_scroll_speed', 1))
        self.bg_scroll_speed_label.config(text=f"{self.app.bg_scroll_speed}")
        self.reverse_direction_var.set(getattr(self.app, 'reverse_direction', False))
        self.video_playback_var.set(getattr(self.app, 'video_playback', True))
        
        self._rebuild_accent_color_picker()
    
    def _open_my_themes_folder(self):
        import os
        program_dir = Path(__file__).parent.parent
        my_themes_dir = program_dir / "My Themes"
        my_themes_dir.mkdir(exist_ok=True)
        os.startfile(my_themes_dir)
        if hasattr(self.app, '_play_folder_open_sound'):
            self.app._play_folder_open_sound()
    
    def _open_assets_folder(self):
        import os
        assets_dir = Path(__file__).parent.parent / "assets"
        os.startfile(assets_dir)
        if hasattr(self.app, '_play_folder_open_sound'):
            self.app._play_folder_open_sound()
    
    def _open_screenshots_folder(self):
        import os
        screenshots_dir = Path(__file__).parent.parent / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        os.startfile(screenshots_dir)
        if hasattr(self.app, '_play_folder_open_sound'):
            self.app._play_folder_open_sound()
