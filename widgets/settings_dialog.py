import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Settings")
        self.geometry("450x500")
        self.resizable(False, False)
        
        self.transient(parent)
        
        self._load_assets()
        
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        top_frame = ttk.LabelFrame(main_frame, text="Appearance", padding="10")
        top_frame.pack(fill="x", pady=(0, 10))
        
        accent_frame = ttk.Frame(top_frame)
        accent_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(accent_frame, text="Accent Color:").pack(side="left")
        self.accent_colors_frame = ttk.Frame(accent_frame)
        self.accent_colors_frame.pack(side="left", padx=(10, 0))
        
        dock_apps_frame = ttk.Frame(top_frame)
        dock_apps_frame.pack(fill="x", pady=(5, 0))
        
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
        scale_frame.pack(fill="x")
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
        single_check.pack(anchor="w")
        
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
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
        
        bezel_edit_frame = ttk.LabelFrame(main_frame, text="Bezel Edit Mode", padding="10")
        bezel_edit_frame.pack(fill="x", pady=(0, 10))
        
        magnify_frame = ttk.Frame(bezel_edit_frame)
        magnify_frame.pack(fill="x")
        ttk.Label(magnify_frame, text="Magnify Size:").pack(side="left")
        self.magnify_size_var = tk.IntVar(value=getattr(app.renderer, 'magnify_size', 200))
        self.magnify_size_slider = ttk.Scale(
            magnify_frame,
            from_=100,
            to=300,
            orient="horizontal",
            variable=self.magnify_size_var,
            command=self._on_magnify_size_change
        )
        self.magnify_size_slider.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        self.magnify_size_label = ttk.Label(magnify_frame, text=f"{self.magnify_size_var.get()}%")
        self.magnify_size_label.pack(side="left", padx=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        close_btn = ttk.Button(button_frame, text="Close", command=self.destroy)
        close_btn.pack(side="right")
        
        self._build_accent_color_picker()
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
    
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
        
        for i, color_name in enumerate(self.app.folder_colors):
            is_selected = self.app.default_folder_color_var.get() == color_name
            
            tk_img = self._build_folder_color_circle(color_name, circle_size, darken=is_selected, is_selected=is_selected)
            if tk_img:
                frame = ttk.Frame(self.accent_colors_frame)
                frame.pack(side="left", padx=2)
                
                label = ttk.Label(frame, image=tk_img)
                label.pack()
                label.bind("<Button-1>", lambda e, c=color_name: self._on_accent_color_click(c))
                
                self._accent_color_refs[color_name] = tk_img
    
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
    
    def _on_magnify_size_change(self, value):
        size = int(float(value))
        size = round(size / 10) * 10  # Snap to 10 increments
        size = max(100, min(300, size))
        self.magnify_size_var.set(size)
        self.app.magnify_size = size
        self.app.renderer.magnify_size = size
        self.app.renderer.magnify_zoom = 2.0 * (size / 150)  # Scale zoom with size
        self.magnify_size_label.config(text=f"{size}%")
        
        if "Settings" not in self.app.config:
            self.app.config["Settings"] = {}
        self.app.config["Settings"]["magnify_size"] = str(size)
        with open(self.app.settings_path, "w") as f:
            self.app.config.write(f)
        
        self.app.redraw()
    
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
        self.magnify_size_var.set(getattr(self.app.renderer, 'magnify_size', 200))
        self.magnify_size_label.config(text=f"{self.magnify_size_var.get()}")
        self._rebuild_accent_color_picker()
