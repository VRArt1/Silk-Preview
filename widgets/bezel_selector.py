import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from widgets.utils import center_to_parent
from renderer import ASSETS_DIR


class BezelSelectorDialog(tk.Toplevel):
    def __init__(self, parent, app, current_bezel=None):
        super().__init__(parent)
        self.withdraw()
        self.app = app
        
        self.thumb_size = 120
        self.square_display_size = int(self.thumb_size * 0.7619)
        self.bezel_display_size = int(self.thumb_size * 0.60)
        self._thumbnail_cache = {}
        self._last_cols = 0
        
        default_cols = 5
        spacing = 10
        scrollbar_width = 25
        frame_padding = 20
        item_total = default_cols * self.thumb_size + (default_cols - 1) * spacing
        default_width = item_total + scrollbar_width + frame_padding + 60
        self.geometry(f"{default_width}x550")
        self.minsize(500, 400)
        
        self.transient(parent)
        
        self.current_bezel = current_bezel or app.bezel_var.get()
        
        self._load_assets()
        self._create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.bind("<FocusIn>", self._on_focus_in)
        
        icon_path = ASSETS_DIR / "favicon_device.png"
        if icon_path.exists():
            try:
                icon_img = Image.open(icon_path)
                if icon_img.mode != 'RGBA':
                    icon_img = icon_img.convert('RGBA')
                self._icon = ImageTk.PhotoImage(icon_img)
                self.iconphoto(False, self._icon)
            except Exception:
                pass
        
        center_to_parent(self, parent)
        self.deiconify()
        
        app.bezel_selector_dialog = self
    
    def _load_assets(self):
        self.square_base = Image.open(ASSETS_DIR / "square.png")
        self.selected_base = Image.open(ASSETS_DIR / "selected.png")
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(main_frame, highlightthickness=0, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.inner_frame = tk.Frame(self.canvas, bg="#f0f0f0")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        
        def on_inner_configure(event):
            bbox = self.canvas.bbox("all")
            if bbox:
                self.canvas.configure(scrollregion=bbox)
        
        self.inner_frame.bind("<Configure>", on_inner_configure)
        
        def on_canvas_configure(event):
            scrollbar_width = scrollbar.winfo_width()
            if scrollbar_width < 1:
                scrollbar_width = 17
            width = event.width - scrollbar_width
            if width > 100:
                self.inner_frame.configure(width=width)
                self.canvas.itemconfig(self.canvas_window, width=width)
                self._check_rebuild_grid(width)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.after(100, self._build_grid)
        
        self._bind_mousewheel()
    
    def _bind_mousewheel(self):
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.inner_frame.bind("<MouseWheel>", _on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
    
    def _bind_item_mousewheel(self, widget):
        widget.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
    
    def _unbind_mousewheel(self):
        try:
            self.canvas.unbind("<MouseWheel>")
        except:
            pass
    
    def _on_focus_in(self, event):
        if self.current_bezel != self.app.renderer.current_bezel_name:
            self._rebuild_grid()
    
    def _get_display_name(self, folder_name):
        devices = self.app.renderer.DEVICES
        if folder_name in devices:
            return devices[folder_name].get("display_name", folder_name.title())
        return folder_name.title()
    
    def _split_bezel_name(self, full_name):
        parts = full_name.split(" - ", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return full_name, ""
    
    def _get_sorted_items(self):
        bezel_options = self.app.renderer.BEZEL_OPTIONS
        bezel_info = self.app.renderer.BEZEL_INFO
        
        items = []
        for name, relative_path in bezel_options.items():
            folder_name = bezel_info.get(name, (None, ""))[1]
            display_name = self._get_display_name(folder_name)
            device_name, color_name = self._split_bezel_name(name)
            items.append({
                'full_name': name,
                'relative_path': relative_path,
                'folder_name': folder_name,
                'display_name': display_name,
                'device_name': device_name,
                'color_name': color_name
            })
        
        items.sort(key=lambda x: (x['display_name'].lower(), x['full_name'].lower()))
        return items
    
    def _check_rebuild_grid(self, width):
        spacing = 10
        cols = max(1, (width - spacing) // (self.thumb_size + spacing))
        if cols != self._last_cols:
            self._last_cols = cols
            self._rebuild_grid()
    
    def _build_grid(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        
        self.current_bezel = self.app.renderer.current_bezel_name
        items = self._get_sorted_items()
        
        if not items:
            return
        
        spacing = 10
        
        width = self.inner_frame.winfo_width()
        if width < 100:
            width = 680
        cols = max(1, (width - spacing) // (self.thumb_size + spacing))
        self._last_cols = cols
        
        row_height = self.thumb_size + 30
        padx_total = width - cols * (self.thumb_size + spacing) + spacing
        start_padx = max(0, padx_total // 2)
        
        for i, item in enumerate(items):
            row = i // cols
            col = i % cols
            
            item_frame = tk.Frame(
                self.inner_frame,
                bg="#f0f0f0",
                width=self.thumb_size,
                height=row_height
            )
            item_frame.pack_propagate(False)
            self._bind_item_mousewheel(item_frame)
            
            bezel_path = ASSETS_DIR / item['relative_path']
            
            is_selected = (item['full_name'] == self.current_bezel)
            
            if is_selected:
                thumbnail = self._create_selected_thumbnail(bezel_path)
            else:
                thumbnail = self._create_bezel_thumbnail(bezel_path)
            
            btn = tk.Button(
                item_frame,
                image=thumbnail,
                borderwidth=0,
                highlightthickness=0,
                bg="#f0f0f0",
                command=lambda n=item['full_name']: self._select_bezel(n)
            )
            btn.pack(fill="both", expand=True)
            btn.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            
            display_name = item['display_name']
            color_name = item['color_name']
            
            if display_name == color_name:
                label_text = display_name
            else:
                label_text = f"{display_name}\n{color_name}"
            
            label = tk.Label(
                item_frame,
                text=label_text,
                font=("Segoe UI", 7),
                bg="#f0f0f0",
                justify="center"
            )
            label.pack(pady=(2, 0))
            label.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            
            item_frame.grid(
                row=row,
                column=col,
                padx=(start_padx + spacing // 2 if col == 0 else spacing // 2, spacing // 2),
                pady=spacing // 2,
                sticky=""
            )
    
    def _rebuild_grid(self):
        self._thumbnail_cache.clear()
        self._build_grid()
    
    def _create_bezel_thumbnail(self, bezel_path):
        cache_key = ("normal", str(bezel_path))
        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]
        
        thumb = Image.new("RGBA", (self.thumb_size, self.thumb_size), (0, 0, 0, 0))
        
        try:
            square = self.square_base.copy()
            square_resized = square.resize((self.square_display_size, self.square_display_size), Image.Resampling.LANCZOS)
            square_offset_x = (self.thumb_size - self.square_display_size) // 2
            square_offset_y = (self.thumb_size - self.square_display_size) // 2
            thumb.paste(square_resized, (square_offset_x, square_offset_y), square_resized)
            
            bezel = Image.open(bezel_path).convert("RGBA")
            bezel_w, bezel_h = bezel.size
            display_size = self.bezel_display_size
            
            if bezel_w > bezel_h:
                new_w = display_size
                new_h = int(bezel_h * (display_size / bezel_w))
            else:
                new_h = display_size
                new_w = int(bezel_w * (display_size / bezel_h))
            
            bezel_resized = bezel.resize((new_w, new_h), Image.Resampling.LANCZOS)
            bezel_offset_x = (self.thumb_size - new_w) // 2
            bezel_offset_y = (self.thumb_size - new_h) // 2
            thumb.paste(bezel_resized, (bezel_offset_x, bezel_offset_y), bezel_resized)
            
        except Exception as e:
            print(f"Failed to load bezel {bezel_path}: {e}")
        
        photo = ImageTk.PhotoImage(thumb)
        self._thumbnail_cache[cache_key] = photo
        return photo
    
    def _create_selected_thumbnail(self, bezel_path):
        cache_key = ("selected", str(bezel_path))
        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]
        
        thumb = self.selected_base.copy()
        thumb = thumb.resize((self.thumb_size, self.thumb_size), Image.Resampling.LANCZOS)
        
        try:
            square = self.square_base.copy()
            square_resized = square.resize((self.square_display_size, self.square_display_size), Image.Resampling.LANCZOS)
            square_offset_x = (self.thumb_size - self.square_display_size) // 2
            square_offset_y = (self.thumb_size - self.square_display_size) // 2
            thumb.paste(square_resized, (square_offset_x, square_offset_y), square_resized)
            
            bezel = Image.open(bezel_path).convert("RGBA")
            bezel_w, bezel_h = bezel.size
            display_size = self.bezel_display_size
            
            if bezel_w > bezel_h:
                new_w = display_size
                new_h = int(bezel_h * (display_size / bezel_w))
            else:
                new_h = display_size
                new_w = int(bezel_w * (display_size / bezel_h))
            
            bezel_resized = bezel.resize((new_w, new_h), Image.Resampling.LANCZOS)
            bezel_offset_x = (self.thumb_size - new_w) // 2
            bezel_offset_y = (self.thumb_size - new_h) // 2
            thumb.paste(bezel_resized, (bezel_offset_x, bezel_offset_y), bezel_resized)
            
        except Exception as e:
            print(f"Failed to load bezel {bezel_path}: {e}")
        
        photo = ImageTk.PhotoImage(thumb)
        self._thumbnail_cache[cache_key] = photo
        return photo
    
    def _select_bezel(self, name):
        self.app.change_bezel(name)
        self._on_close()
    
    def _on_close(self):
        self.app.bezel_selector_dialog = None
        self._unbind_mousewheel()
        self.destroy()
    
    def refresh_bezel_options(self):
        self._thumbnail_cache.clear()
        self._rebuild_grid()
