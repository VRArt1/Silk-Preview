import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
import re

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


class FilePickerWidget(ttk.Frame):
    """
    File picker widget with browse button and optional drag-drop support.
    """
    def __init__(self, parent, theme_path=None, allowed_extensions=None, 
                 relative_folder=None, on_change=None, allow_empty=True, name_pattern=None,
                 on_file_changed=None, on_file_deleted=None, on_file_replacing=None, width=20):
        super().__init__(parent)
        
        self.theme_path = theme_path
        self.allowed_extensions = allowed_extensions or []
        self.relative_folder = relative_folder
        self.on_change = on_change
        self.allow_empty = allow_empty
        self.name_pattern = name_pattern  # e.g., "main" or "external" for wallpapers
        self.on_file_changed = on_file_changed  # Callback when file is added/changed
        self.on_file_deleted = on_file_deleted  # Callback when file is deleted
        self.on_file_replacing = on_file_replacing  # Callback before old file is deleted
        self.width = width  # Width for entry field
        
        self.current_value = ""
        
        self._create_ui()
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        
        self.entry_frame = ttk.Frame(self)
        self.entry_frame.pack(side="left", fill="x", expand=True)
        
        self.path_var = tk.StringVar()
        entry_kwargs = {"textvariable": self.path_var, "state": "readonly"}
        if self.width:
            entry_kwargs["width"] = self.width
        self.entry = ttk.Entry(self.entry_frame, **entry_kwargs)
        self.entry.pack(side="left", fill="x", expand=True)
        
        self.browse_btn = ttk.Button(self.entry_frame, text="Browse", command=self._on_browse, width=8)
        self.browse_btn.pack(side="left", padx=(3, 0))
        
        self.clear_btn = ttk.Button(self.entry_frame, text="X", command=self._on_clear, width=3)
        self.clear_btn.pack(side="left", padx=(2, 0))
        
        self.grid_columnconfigure(0, weight=1)
        
        if DND_AVAILABLE:
            try:
                self.entry.drop_target_register(DND_FILES)
                self.entry.dnd_bind('<<Drop>>', self._on_drop)
            except:
                pass
    
    def _on_browse(self):
        if not self.theme_path:
            return
        
        if self.relative_folder:
            search_dir = self.theme_path / self.relative_folder
        else:
            search_dir = self.theme_path
        
        if not search_dir.exists():
            search_dir = self.theme_path
        
        if self.allowed_extensions:
            ext_pattern = " ".join([f"*{ext}" for ext in self.allowed_extensions])
            filetypes = [
                (f"Audio/Video/Image files", ext_pattern),
                ("All files", "*.*")
            ]
        else:
            filetypes = [("All files", "*.*")]
        
        filename = filedialog.askopenfilename(
            initialdir=str(search_dir),
            filetypes=filetypes,
            title="Select file"
        )
        
        if filename:
            self._set_path(filename, copy_to_theme=True)
    
    def _on_drop(self, event):
        """Handle file drop."""
        if not self.theme_path:
            return
        
        files = self.tk.splitlist(event.data)
        if files:
            dropped_file = Path(files[0])
            if dropped_file.exists():
                self._set_path(str(dropped_file), copy_to_theme=True)
    
    def _set_path(self, full_path, copy_to_theme=False):
        """Set the file path, converting to relative if within theme."""
        import shutil
        path = Path(full_path)
        file_copied = False
        
        # If file is outside theme folder and we should copy it
        if copy_to_theme and self.theme_path and path.exists():
            # Determine destination folder
            dest_folder = self.theme_path
            if self.relative_folder:
                dest_folder = self.theme_path / self.relative_folder
                dest_folder.mkdir(exist_ok=True)
            
            # Determine destination filename
            if self.name_pattern:
                ext = path.suffix
                dest_path = dest_folder / f"{self.name_pattern}{ext}"
                
                # Delete any existing file with same name but different extension
                for old_ext in self.allowed_extensions:
                    if old_ext != ext:
                        old_file = dest_folder / f"{self.name_pattern}{old_ext}"
                        if old_file.exists():
                            # Call callback before deleting (e.g., to stop video player)
                            if self.on_file_replacing:
                                self.on_file_replacing(str(old_file))
                            old_file.unlink()
            else:
                dest_path = dest_folder / path.name
            
            # Copy the file
            shutil.copy2(path, dest_path)
            file_copied = True
            
            # Set current value to just the filename
            self.current_value = dest_path.name
            
            # Immediately update the display
            self.path_var.set(self.current_value)
            
            # Call on_change with the new value
            if self.on_change:
                self.on_change(self.current_value)
            
            # Call file changed callback to trigger save/reload
            if self.on_file_changed:
                self.on_file_changed()
            
            # Return early since we've handled everything
            return
            
        elif path.exists() and self.theme_path:
            try:
                rel_path = path.relative_to(self.theme_path)
                self.current_value = str(rel_path)
            except ValueError:
                self.current_value = str(path.name)
        else:
            self.current_value = str(path.name)
        
        # Remove folder prefix from display (just show filename)
        if self.current_value and "/" in self.current_value:
            self.current_value = self.current_value.split("/")[-1]
        
        self.path_var.set(self.current_value)
        
        if self.on_change:
            self.on_change(self.current_value)
    
    def _on_clear(self):
        """Clear the file selection and delete the file."""
        folder_deleted = False
        folder_path = None
        
        if self.current_value and self.theme_path:
            file_path = None
            if self.relative_folder:
                file_path = self.theme_path / self.relative_folder / self.current_value
                folder_path = self.theme_path / self.relative_folder
            else:
                file_path = self.theme_path / self.current_value
                folder_path = self.theme_path
            
            if file_path:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except:
                    if self.name_pattern:
                        for ext in ['.ogg', '.mp3', '.wav', '.flac', '.m4a', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.mp4', '.webm']:
                            alt_path = file_path.parent / f"{self.name_pattern}{ext}"
                            try:
                                if alt_path.exists():
                                    alt_path.unlink()
                            except:
                                pass
        
        self.current_value = ""
        self.path_var.set("")
        
        if self.on_change:
            self.on_change("")
        
        if self.on_file_deleted:
            self.on_file_deleted()
        
        if folder_path and folder_path.exists() and not list(folder_path.glob("*")):
            try:
                folder_path.rmdir()
            except:
                pass
    
    def get_value(self):
        """Get the current value."""
        return self.current_value if self.current_value else None
    
    def set_value(self, value):
        """Set the value programmatically."""
        self.current_value = value or ""
        # Strip folder prefix for display (just show filename)
        if self.current_value and "/" in self.current_value:
            self.current_value = self.current_value.split("/")[-1]
        self.path_var.set(self.current_value)
    
    def set_theme_path(self, path):
        """Update the theme path for file resolution."""
        self.theme_path = path


class ColorInputWidget(ttk.Frame):
    """
    Color input with hex entry and circular color swatch.
    """
    def __init__(self, parent, on_change=None, on_pick=None):
        super().__init__(parent)
        
        self.on_change = on_change
        self.on_pick = on_pick
        self.current_color = "#000000"
        
        self.columnconfigure(0, weight=1)
        
        self.color_var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.color_var)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.swatch = tk.Canvas(self, width=24, height=24, highlightthickness=0)
        self.swatch.grid(row=0, column=1, padx=(0, 3))
        self._draw_swatch()
        
        self.swatch.bind("<Button-1>", lambda e: self._on_pick())
        
        self.grid_columnconfigure(0, weight=1)
        
        self.color_var.trace_add("write", self._on_entry_change)
        
        self.entry.bind("<Key>", self._block_arrow_keys)
        self.swatch.bind("<Key>", self._block_arrow_keys)
    
    def _block_arrow_keys(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right"):
            return "break"
    
    def _strip_alpha(self, color):
        """Strip alpha channel from color (convert #RRGGBBAA to #RRGGBB)."""
        if color and len(color) == 9 and color.startswith("#"):
            return color[:7]  # Strip last 2 chars (alpha)
        return color
    
    def _draw_swatch(self):
        self.swatch.delete("all")
        display_color = self._strip_alpha(self.current_color)
        self.swatch.create_oval(2, 2, 22, 22, fill=display_color, outline="#000000")
    
    def _on_entry_change(self, *args):
        color = self.color_var.get().strip()
        if not color.startswith("#"):
            color = "#" + color
        
        import re
        # Accept both 6-digit (#RRGGBB) and 8-digit (#RRGGBBAA) colors
        if re.match(r"^#[0-9a-fA-F]{6}$", color) or re.match(r"^#[0-9a-fA-F]{8}$", color):
            self.current_color = color
            self._draw_swatch()
            if self.on_change:
                self.on_change(color)
    
    def _on_pick(self):
        from widgets.color_picker import ColorPickerDialog
        
        dialog = ColorPickerDialog(self.winfo_toplevel(), self.current_color, "Color Picker")
        color = dialog.get_color()
        
        if color:
            self.current_color = color
            self.color_var.set(color)
            self._draw_swatch()
            if self.on_change:
                self.on_change(color)
    
    def get_value(self):
        return self.color_var.get() or None
    
    def set_value(self, value):
        if value:
            self.current_color = value
            self.color_var.set(value)
            self._draw_swatch()


class VolumeSliderWidget(ttk.Frame):
    """
    Volume slider with 0.1 increments and value display.
    """
    def __init__(self, parent, min_val=0.0, max_val=1.0, step=0.1, on_change=None):
        super().__init__(parent)
        
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.on_change = on_change
        self.current_value = max_val
        self._initializing = True  # Flag to prevent callback during init
        
        self.columnconfigure(0, weight=1)
        
        self.slider = ttk.Scale(self, from_=min_val, to=max_val, orient="horizontal",
                               command=self._on_slider_change)
        self.slider.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.value_label = ttk.Label(self, text=f"{max_val:.1f}", width=4)
        self.value_label.grid(row=0, column=1)
        
        self.grid_columnconfigure(0, weight=1)
        
        self.slider.set(max_val)
        self._initializing = False
    
    def _on_slider_change(self, value):
        if self._initializing:
            return
            
        val = float(value)
        snapped = round(val / self.step) * self.step
        snapped = max(self.min_val, min(self.max_val, snapped))
        
        self.current_value = snapped
        self.value_label.config(text=f"{snapped:.1f}")
        
        if self.on_change:
            self.on_change(snapped)
    
    def get_value(self):
        return self.current_value
    
    def set_value(self, value):
        if value is None:
            value = self.max_val
        self.current_value = value
        self.slider.set(value)
        self.value_label.config(text=f"{value:.1f}")
