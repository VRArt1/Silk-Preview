import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import re
import math

HEX_COLOR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


class ColorPickerDialog(tk.Toplevel):
    def __init__(self, parent, initial_color="#000000", title="Pick Color"):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        
        self.title(title)
        self.geometry("400x500")
        self.resizable(False, False)
        
        self.initial_color = initial_color
        self.result_color = initial_color
        self._apply_callback = None
        
        self._parse_color(initial_color)
        self._create_ui()
        self._update_selector_from_rgb()
        self._update_preview()
        
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.wait_window()
    
    def _parse_color(self, color_str):
        """Parse color string to RGB values."""
        color_str = color_str.strip()
        if not color_str.startswith("#"):
            color_str = "#" + color_str
        
        if len(color_str) >= 7:
            self.r = int(color_str[1:3], 16)
            self.g = int(color_str[3:5], 16)
            self.b = int(color_str[5:7], 16)
        else:
            self.r = self.g = self.b = 0
    
    def _create_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        self._create_color_wheel(main_frame)
        self._create_rgb_sliders(main_frame)
        self._create_preview(main_frame)
        self._create_buttons(main_frame)
    
    def _create_color_wheel(self, parent):
        frame = ttk.LabelFrame(parent, text="Color Wheel", padding=8)
        frame.pack(fill="x", pady=(0, 10))
        
        self.wheel_size = 150
        self.wheel_canvas = tk.Canvas(frame, width=self.wheel_size, height=self.wheel_size, 
                                       highlightthickness=0)
        self.wheel_canvas.pack()
        self._draw_color_wheel()
        
        self.wheel_canvas.bind("<B1-Motion>", self._on_wheel_click)
        self.wheel_canvas.bind("<Button-1>", self._on_wheel_click)
        
        self.selector_x = self.wheel_size // 2
        self.selector_y = self.wheel_size // 2
        self._draw_selector()
    
    def _draw_color_wheel(self):
        """Draw a smooth color wheel on the canvas."""
        size = self.wheel_size
        center = size // 2
        radius = size // 2
        inner_radius = int(radius * 0.15)
        
        # Use RGBA for transparency
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw radial wedges for each hue (every 2 degrees for smoothness)
        for angle in range(0, 360, 2):
            # Convert angle to radians
            start_rad = angle * math.pi / 180
            end_rad = (angle + 2) * math.pi / 180
            
            # Calculate polygon points for this wedge
            points = [
                center + inner_radius * math.cos(start_rad),
                center + inner_radius * math.sin(start_rad),
                center + radius * math.cos(start_rad),
                center + radius * math.sin(start_rad),
                center + radius * math.cos(end_rad),
                center + radius * math.sin(end_rad),
                center + inner_radius * math.cos(end_rad),
                center + inner_radius * math.sin(end_rad),
            ]
            
            color = self._hsv_to_rgb(angle, 1.0, 1.0)
            draw.polygon(points, fill=color + (255,), outline=color + (255,))
        
        # Draw white inner circle (center)
        draw.ellipse(
            [center - inner_radius, center - inner_radius,
             center + inner_radius, center + inner_radius],
            fill=(255, 255, 255, 255),
            outline=(255, 255, 255, 255)
        )
        
        self.wheel_image = ImageTk.PhotoImage(img)
        self.wheel_canvas.create_image(0, 0, anchor="nw", image=self.wheel_image)
    
    def _draw_selector(self):
        """Draw selection indicator on color wheel."""
        self.wheel_canvas.delete("selector")
        
        r = 8
        # Draw black outer ring then white inner ring for visibility on any color
        self.wheel_canvas.create_oval(
            self.selector_x - r - 1, self.selector_y - r - 1,
            self.selector_x + r + 1, self.selector_y + r + 1,
            outline="black", width=2, tags="selector"
        )
        self.wheel_canvas.create_oval(
            self.selector_x - r, self.selector_y - r,
            self.selector_x + r, self.selector_y + r,
            outline="white", width=2, tags="selector"
        )
    
    def _on_wheel_click(self, event):
        """Handle click on color wheel."""
        center = self.wheel_size // 2
        radius = self.wheel_size // 2
        inner_radius = int(radius * 0.15)
        
        dx = event.x - center
        dy = event.y - center
        dist = (dx * dx + dy * dy) ** 0.5
        
        # Only allow selection within the color ring (not in center or outside)
        if inner_radius < dist <= radius:
            self.selector_x = event.x
            self.selector_y = event.y
            self._draw_selector()
            
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
            
            saturation = dist / radius
            
            self.r, self.g, self.b = self._hsv_to_rgb(angle, saturation, 1.0)
            self._update_all()
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB."""
        h = h / 360.0
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        
        i = i % 6
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q
        
        return int(r * 255), int(g * 255), int(b * 255)
    
    def _create_rgb_sliders(self, parent):
        frame = ttk.LabelFrame(parent, text="RGB Sliders", padding=8)
        frame.pack(fill="x", pady=(0, 10))
        
        self.r_slider = self._create_slider_row(frame, "R:", self.r, "#FF0000")
        self.g_slider = self._create_slider_row(frame, "G:", self.g, "#00FF00")
        self.b_slider = self._create_slider_row(frame, "B:", self.b, "#0000FF")
    
    def _create_slider_row(self, parent, label, value, color):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        
        ttk.Label(frame, text=label, width=3).pack(side="left")
        
        var = tk.IntVar(value=value)
        slider = ttk.Scale(frame, from_=0, to=255, variable=var, orient="horizontal",
                          command=lambda v, rv=var: self._on_slider_change("rgb"))
        slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        value_label = ttk.Label(frame, text=str(value), width=3)
        value_label.pack(side="left")
        
        preview = tk.Canvas(frame, width=20, height=20, highlightthickness=0)
        preview.pack(side="left", padx=(5, 0))
        preview.create_oval(1, 1, 19, 19, fill=color, outline="black")
        
        return {"var": var, "label": value_label, "preview": preview}
    
    def _on_slider_change(self, source):
        """Handle slider change."""
        self.r = self.r_slider["var"].get()
        self.g = self.g_slider["var"].get()
        self.b = self.b_slider["var"].get()
        
        self.r_slider["label"].config(text=str(self.r))
        self.g_slider["label"].config(text=str(self.g))
        self.b_slider["label"].config(text=str(self.b))
        
        self._update_selector_from_rgb()
        self._update_preview()
    
    def _update_selector_from_rgb(self):
        """Update color wheel selector position from RGB values."""
        h, s, v = self._rgb_to_hsv(self.r, self.g, self.b)
        
        center = self.wheel_size // 2
        radius = self.wheel_size // 2
        inner_radius = int(radius * 0.15)
        
        # Position at saturation distance from center
        dist = s * radius
        
        angle_rad = h / 360 * 2 * math.pi
        
        self.selector_x = center + int(dist * math.cos(angle_rad))
        self.selector_y = center + int(dist * math.sin(angle_rad))
        self._draw_selector()
    
    def _rgb_to_hsv(self, r, g, b):
        """Convert RGB to HSV."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        
        if diff == 0:
            h = 0
        elif max_val == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_val == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360
        
        s = 0 if max_val == 0 else (diff / max_val)
        v = max_val
        
        return h, s, v
    
    def _get_hex(self):
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
    
    def _on_hex_change(self):
        """Handle hex input change."""
        hex_val = self.hex_var.get().strip()
        if not hex_val.startswith("#"):
            hex_val = "#" + hex_val
        
        if HEX_COLOR_RE.match(hex_val):
            self.hex_error.config(text="")
            self._parse_color(hex_val)
            self._update_all()
        else:
            self.hex_error.config(text="Invalid")
    
    def _create_preview(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 10))
        
        preview_lf = ttk.LabelFrame(frame, text="Preview", padding=8)
        preview_lf.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.preview_canvas = tk.Canvas(preview_lf, width=40, height=40, highlightthickness=0)
        self.preview_canvas.pack()
        self.preview_canvas.create_oval(2, 2, 38, 38, fill=self._get_hex(), outline="#000000")
        
        hex_lf = ttk.LabelFrame(frame, text="Hex", padding=8)
        hex_lf.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        self.hex_var = tk.StringVar(value=self._get_hex())
        hex_entry = ttk.Entry(hex_lf, textvariable=self.hex_var, width=10)
        hex_entry.pack()
        hex_entry.bind("<FocusOut>", lambda e: self._on_hex_change())
        hex_entry.bind("<Return>", lambda e: self._on_hex_change())
        
        self.hex_error = ttk.Label(hex_lf, text="", foreground="red")
        self.hex_error.pack()
    
    def _update_preview(self):
        color = self._get_hex()
        if hasattr(self, 'preview_canvas'):
            self.preview_canvas.delete("all")
            self.preview_canvas.create_oval(2, 2, 38, 38, fill=color, outline="#000000")
        
        if hasattr(self, 'hex_var'):
            self.hex_var.set(color)
    
    def _update_all(self):
        """Update all UI elements from RGB values."""
        self.r_slider["var"].set(self.r)
        self.r_slider["label"].config(text=str(self.r))
        
        self.g_slider["var"].set(self.g)
        self.g_slider["label"].config(text=str(self.g))
        
        self.b_slider["var"].set(self.b)
        self.b_slider["label"].config(text=str(self.b))
        
        self._update_selector_from_rgb()
        self._update_preview()
    
    def _create_buttons(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(frame, text="Apply", command=self._on_apply, width=10).pack(side="left", padx=5)
        ttk.Button(frame, text="Cancel", command=self._on_cancel, width=10).pack(side="right", padx=5)
    
    def _on_cancel(self):
        self.result_color = self.initial_color
        self.destroy()
    
    def _on_apply(self):
        self.result_color = self._get_hex()
        self.destroy()
    
    def get_color(self):
        return self.result_color
    
    def set_apply_callback(self, callback):
        self._apply_callback = callback
