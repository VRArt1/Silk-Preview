import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import webbrowser
import re

# Pillow resampling compatibility
RESAMPLE = (
    Image.Resampling.LANCZOS
    if hasattr(Image, "Resampling")
    else Image.LANCZOS
)

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
URL_RE = re.compile(r"^https?://")


class PreviewPanel(ttk.Frame):
    # Field order for display
    FIELD_ORDER = [
        "name", "author", "version", "description", "credits", "website",
        "theme_mode", "color_scheme",
        "wallpaper_main", "wallpaper_external",
        "music_mode", "music_playback_mode", "music_playlist", "music_time_schedule",
        "sfx_volume", "music_volume"
    ]

    def __init__(self, parent, renderer, width=300):
        super().__init__(parent, width=width)
        self.renderer = renderer
        self.preview_img_tk = None
        self._theme_data_hash = None  # Track if theme data changed

        self.grid_propagate(False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # --------------------------------------------------
        # Preview image (fixed, non-scrolling)
        # --------------------------------------------------
        self.preview_frame = ttk.Frame(self)
        self.preview_frame.grid(row=0, column=0, sticky="n", padx=10, pady=(10, 6))
        self.preview_image_label = ttk.Label(self.preview_frame)
        self.preview_image_label.pack(anchor="center")

        # --------------------------------------------------
        # Scrollable info area
        # --------------------------------------------------
        self.scroll_container = ttk.Frame(self)
        self.scroll_container.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 10))
        self.scroll_container.columnconfigure(0, weight=1)
        self.scroll_container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.scroll_container,
            highlightthickness=0,
            borderwidth=0
        )
        self.scrollbar = ttk.Scrollbar(
            self.scroll_container,
            orient="vertical",
            command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.content_frame = ttk.Frame(self.canvas)
        self.content_frame.columnconfigure(0, weight=1)
        self.content_window = self.canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw"
        )

        self.content_frame.bind(
            "<Configure>",
            self._on_content_configure
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self.content_window, width=e.width)
        )

        # Mouse wheel support
        self._bind_mousewheel(self.canvas)

        self.load_theme_info()
    
    def _on_content_configure(self, event):
        """Update scrollregion, but debounce during rapid events."""
        # Get the bbox - if None, skip update
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    # ------------------------------
    # Mouse wheel scrolling
    # ------------------------------
    def _bind_mousewheel(self, widget):
        widget.bind_all("<MouseWheel>", lambda e: self._on_mousewheel(e, widget))
        widget.bind_all("<Button-4>", lambda e: self._on_mousewheel(e, widget))
        widget.bind_all("<Button-5>", lambda e: self._on_mousewheel(e, widget))

    def _on_mousewheel(self, event, widget):
        # Get current scroll position
        scroll_pos = widget.yview()
        
        if event.num == 5 or event.delta < 0:
            # Scrolling down - only if not at bottom
            if scroll_pos[1] < 1.0:
                widget.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            # Scrolling up - only if not at top
            if scroll_pos[0] > 0.0:
                widget.yview_scroll(-1, "units")

    # ------------------------------
    # Theme loading
    # ------------------------------
    def load_theme_info(self):
        theme = self.renderer.theme_data or {}
        
        # Only rebuild if theme data actually changed
        import json
        try:
            new_hash = hash(json.dumps(theme, sort_keys=True, default=str))
        except (TypeError, ValueError):
            new_hash = None
        
        # Skip rebuild entirely if hash matches - keep content visible
        if new_hash == self._theme_data_hash:
            return
        
        self._theme_data_hash = new_hash
        self._clear_content()

        # Preview image
        img = getattr(self.renderer, "preview_image", None)
        if img:
            max_width = 220
            scale = max_width / img.width
            new_size = (max_width, int(img.height * scale))
            img_resized = img.resize(new_size, RESAMPLE)
            self.preview_img_tk = ImageTk.PhotoImage(img_resized)
            self.preview_image_label.configure(image=self.preview_img_tk, text="")
        else:
            self.preview_image_label.configure(image="", text="No Preview")

        # Render JSON with ordered fields
        self._render_dict_ordered(theme, self.content_frame)

    def refresh(self):
        self._theme_data_hash = None  # Force rebuild
        self.load_theme_info()

    # ------------------------------
    # Rendering helpers
    # ------------------------------
    def _clear_content(self):
        for child in self.content_frame.winfo_children():
            child.destroy()

    def _render_dict_ordered(self, data: dict, parent, indent=0):
        """Render dict with specific field order."""
        rendered_keys = set()
        
        # First render fields in the specified order
        for key in self.FIELD_ORDER:
            if key in data:
                rendered_keys.add(key)
                value = data[key]
                if isinstance(value, dict):
                    self._render_collapsible_section(key, value, parent, indent)
                else:
                    self._render_row(key, value, parent, indent)
        
        # Then render any remaining fields not in the order list
        for key, value in data.items():
            if key not in rendered_keys:
                if isinstance(value, dict):
                    self._render_collapsible_section(key, value, parent, indent)
                else:
                    self._render_row(key, value, parent, indent)

    def _render_dict(self, data: dict, parent, indent=0):
        for key, value in data.items():
            if isinstance(value, dict):
                self._render_collapsible_section(key, value, parent, indent)
            else:
                self._render_row(key, value, parent, indent)

    def _render_collapsible_section(self, title, data, parent, indent):
        container = ttk.Frame(parent)
        container.pack(fill="x", padx=(indent * 12, 4), pady=(6, 2))

        header = ttk.Frame(container)
        header.pack(fill="x")

        expanded = tk.BooleanVar(value=True)

        body = ttk.Frame(container)
        body.pack(fill="x")

        def toggle():
            if expanded.get():
                body.pack_forget()
                toggle_btn.config(text="▶")
                expanded.set(False)
            else:
                body.pack(fill="x")
                toggle_btn.config(text="▼")
                expanded.set(True)

        toggle_btn = ttk.Label(
            header,
            text="▼",
            width=2,
            cursor="hand2"
        )
        toggle_btn.pack(side="left")
        toggle_btn.bind("<Button-1>", lambda e: toggle())

        title_label = ttk.Label(
            header,
            text=title,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        title_label.pack(side="left", anchor="w")
        title_label.bind("<Button-1>", lambda e: toggle())

        # Render nested items
        self._render_dict(data, body, indent + 1)

    def _render_row(self, key, value, parent, indent):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=(indent * 12, 8), pady=2)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        key_label = ttk.Label(
            row,
            text=f"{key}:",
            font=("Segoe UI", 9, "bold"),
            wraplength=180,
            justify="left"
        )
        key_label.grid(row=0, column=0, sticky="nw")  # top-left

        value_frame = ttk.Frame(row)

        value_str = str(value)

        # Decide sticky alignment
        if key in ("description", "credits"):
            value_frame.grid(row=0, column=1, sticky="nw")  # top-left
        else:
            value_frame.grid(row=0, column=1, sticky="ne")  # top-right (includes URLs)

        # Hex color preview
        if isinstance(value, str) and HEX_COLOR_RE.match(value_str):
            value_label = ttk.Label(value_frame, text=value_str, wraplength=140)
            value_label.pack(side="left", padx=(0, 6), anchor="n")
            swatch = self._make_color_swatch(value_str)
            swatch_label = ttk.Label(value_frame, image=swatch)
            swatch_label.image = swatch
            swatch_label.pack(side="right", anchor="n")

        # Clickable URL
        elif isinstance(value, str) and re.match(r"^https?://", value_str):
            link = ttk.Label(
                value_frame,
                text=value_str,
                foreground="#4ea1ff",
                cursor="hand2",
                wraplength=200
            )
            link.pack(anchor="ne")  # top-right for URL
            link.bind("<Button-1>", lambda e, url=value_str: webbrowser.open(url))
            link.bind("<Enter>", lambda e: link.config(cursor="hand2"))
            link.bind("<Leave>", lambda e: link.config(cursor="arrow"))

        # Long text fields
        elif key in ("description", "credits"):
            value_label = ttk.Label(
                value_frame,
                text=value_str,
                wraplength=200,
                justify="left"
            )
            value_label.pack(anchor="nw")

        # Normal text
        else:
            value_label = ttk.Label(
                value_frame,
                text=value_str,
                wraplength=200,
                justify="right"
            )
            value_label.pack(anchor="ne")  # top-right for normal text
    
    # ------------------------------
    # Color swatch
    # ------------------------------
    def _make_color_swatch(self, hex_color, size=14):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((1, 1, size - 2, size - 2), fill=hex_color, outline="#000000")
        return ImageTk.PhotoImage(img)