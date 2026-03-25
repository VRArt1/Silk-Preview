import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import webbrowser
import re
import json
import shutil
from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# Pillow resampling compatibility
RESAMPLE = (
    Image.Resampling.LANCZOS
    if hasattr(Image, "Resampling")
    else Image.LANCZOS
)

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
URL_RE = re.compile(r"^https?://")

from theme_editor.schema import THEME_SCHEMA, SFX_ACTIONS


class PreviewPanel(ttk.Frame):
    def __init__(self, parent, renderer, app=None, width=None):
        super().__init__(parent)
        self.renderer = renderer
        self.app = app
        self.preview_img_tk = None
        self._theme_data_hash = None
        
        self.edit_mode = False
        self._has_unsaved_changes = False
        self._edit_widgets = {}
        
        self.grid_propagate(False)
        self.pack_propagate(False)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        self._create_ui()
        self.load_theme_info()
    
    def _create_ui(self):
        self.preview_frame = ttk.Frame(self)
        self.preview_frame.grid(row=0, column=0, sticky="n", padx=10, pady=(10, 6))
        
        # Use tk.Label for DND support
        self.preview_image_label = tk.Label(self.preview_frame)
        self.preview_image_label.pack(anchor="center")
        
        # Add click handler for browsing preview image
        self.preview_image_label.bind("<Button-1>", lambda e: self._browse_preview_image())
        
        # Add drag-drop support
        if DND_AVAILABLE:
            try:
                self.preview_image_label.drop_target_register(DND_FILES)
                self.preview_image_label.dnd_bind('<<Drop>>', self._on_preview_image_drop)
            except:
                pass
        
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
        self.canvas.configure(yscrollcommand=self._on_scroll)
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
    
    def _on_content_configure(self, event):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _on_scroll(self, *args):
        self.scrollbar.set(*args)
        if float(args[0]) == 0.0 and float(args[1]) == 1.0:
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid(row=0, column=1, sticky="ns")

    def set_edit_mode(self, enabled):
        """Toggle edit mode."""
        if enabled == self.edit_mode:
            return
        
        self.edit_mode = enabled
        
        if enabled:
            self._edit_widgets.clear()
            self._has_unsaved_changes = False
        else:
            self._edit_widgets.clear()
            self._has_unsaved_changes = False
            self._theme_data_hash = None
        
        self.load_theme_info()
    
    def is_editing_focused(self):
        """Check if any edit field currently has focus."""
        try:
            focus_widget = self.focus_get()
            if focus_widget is None:
                return False
            
            current = focus_widget
            while current is not None:
                if current == self.content_frame:
                    return True
                current = current.master
            
            return False
        except:
            return False
    
    def has_unsaved_changes(self):
        """Check if current values differ from saved theme.json file."""
        if not self.edit_mode:
            return False
        
        theme_path = getattr(self.renderer, "theme_path", None)
        if not theme_path:
            return False
        
        json_path = theme_path / "theme.json"
        
        if not json_path.exists():
            return False
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
        except:
            return False
        
        current_data = self._collect_edit_values()
        
        # Check if music/sounds folders exist (same logic as _save_theme)
        music_folder = theme_path / "music" if theme_path else None
        has_music = bool(music_folder and music_folder.exists() and list(music_folder.glob("*")))
        
        sounds_folder = theme_path / "sounds" if theme_path else None
        has_sounds = bool(sounds_folder and sounds_folder.exists() and list(sounds_folder.glob("*")))
        
        # If saved data doesn't have music_volume and user hasn't changed it from default (1.0), don't flag as change
        if "music_volume" not in saved_data and "music_volume" in current_data:
            current_vol = current_data.get("music_volume", 1.0)
            # Normalize for comparison (string "1.0" vs float 1.0)
            try:
                current_vol = float(current_vol)
            except (ValueError, TypeError):
                pass
            if current_vol == 1.0:
                del current_data["music_volume"]
        
        # If saved data doesn't have sfx_volume and user hasn't changed it from default (1.0), don't flag as change
        if "sfx_volume" not in saved_data and "sfx_volume" in current_data:
            current_vol = current_data.get("sfx_volume", 1.0)
            try:
                current_vol = float(current_vol)
            except (ValueError, TypeError):
                pass
            if current_vol == 1.0:
                del current_data["sfx_volume"]
        
        saved_clean = self._clean_theme_data(saved_data)
        current_clean = self._clean_theme_data(current_data)
        
        return saved_clean != current_clean
    
    def _block_arrow_keys(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right"):
            return "break"
    
    def _save_theme(self):
        self._play_save_loop_sound()
        
        theme_data = self._collect_edit_values()
        
        if "name" not in theme_data or not theme_data.get("name"):
            tk.messagebox.showerror("Error", "Theme name is required.")
            return
        
        theme_path = getattr(self.renderer, "theme_path", None)
        
        music_folder = theme_path / "music" if theme_path else None
        has_music = False
        if music_folder and music_folder.exists():
            has_music = bool(list(music_folder.glob("*")))
        
        sounds_folder = theme_path / "sounds" if theme_path else None
        has_sounds = False
        if sounds_folder and sounds_folder.exists():
            has_sounds = bool(list(sounds_folder.glob("*")))
        
        if not has_music and "music_volume" in theme_data:
            del theme_data["music_volume"]
        
        if not has_sounds and "sfx_volume" in theme_data:
            del theme_data["sfx_volume"]
        
        if not has_sounds or not theme_data.get("sounds"):
            sounds_dict = theme_data.get("sounds", {})
            has_any_sound = False
            for v in sounds_dict.values():
                if v and isinstance(v, str) and v.strip():
                    has_any_sound = True
                    break
            if not has_any_sound:
                if "sounds" in theme_data:
                    del theme_data["sounds"]
                if sounds_folder and sounds_folder.exists() and not list(sounds_folder.glob("*")):
                    sounds_folder.rmdir()
        
        cleaned = self._clean_theme_data(theme_data)
        
        if theme_path:
            json_path = theme_path / "theme.json"
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(self._format_theme_json(cleaned))
                
                self.renderer.theme_data = cleaned
                self._theme_data_hash = None
                self._has_unsaved_changes = False
                self.load_theme_info()
                
                self._stop_save_loop_and_play_complete()
                
                print(f"Theme saved successfully at: {json_path}")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Failed to save theme: {e}")
    
    def _browse_preview_image(self):
        """Browse for a preview image."""
        theme_path = getattr(self.renderer, "theme_path", None)
        if not theme_path:
            return
        
        if not self.edit_mode:
            return
        
        filename = filedialog.askopenfilename(
            initialdir=str(theme_path),
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.webp"),
                ("All files", "*.*")
            ],
            title="Select preview image"
        )
        
        if filename:
            self._set_preview_image(filename)
    
    def _on_preview_image_drop(self, event):
        """Handle dropped preview image file."""
        if not self.edit_mode:
            return
        
        theme_path = getattr(self.renderer, "theme_path", None)
        if not theme_path:
            return
        
        files = self.tk.splitlist(event.data)
        if files:
            dropped_file = Path(files[0])
            if dropped_file.exists():
                self._set_preview_image(str(dropped_file))
    
    def _set_preview_image(self, filepath):
        """Set preview image from file path."""
        theme_path = getattr(self.renderer, "theme_path", None)
        if not theme_path:
            return
        
        src_path = Path(filepath)
        if not src_path.exists():
            return
        
        # Validate it's an image
        allowed_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        ext = src_path.suffix.lower()
        if ext not in allowed_exts:
            return
        
        # Delete any existing preview files first
        for old_ext in allowed_exts:
            old_preview = theme_path / f"preview{old_ext}"
            if old_preview.exists():
                old_preview.unlink()
        
        # Copy to theme folder as preview.<ext>
        dst_path = theme_path / f"preview{ext}"
        shutil.copy2(src_path, dst_path)
        
        # Reload just the preview image (not the whole theme)
        self._load_preview_image()
    
    def _load_preview_image(self):
        """Load and display the preview image."""
        theme_path = getattr(self.renderer, "theme_path", None)
        if not theme_path:
            return
        
        # Try to find preview image
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
            preview_path = theme_path / f"preview{ext}"
            if preview_path.exists():
                try:
                    img = Image.open(preview_path)
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    self.preview_img_tk = ImageTk.PhotoImage(img)
                    
                    # Also update the renderer so it persists after save
                    full_img = Image.open(preview_path)
                    self.renderer.preview_image = full_img
                    
                    cursor = "hand2" if self.edit_mode else ""
                    self.preview_image_label.configure(image=self.preview_img_tk, text="", cursor=cursor)
                    return
                except Exception:
                    pass
        
        # No preview found - also clear renderer
        self.renderer.preview_image = None
        cursor = "hand2" if self.edit_mode else ""
        self.preview_image_label.configure(image="", text="No Preview", cursor=cursor)
    
    def _refresh_sound_preview(self, action):
        """Refresh the sound preview when a sound file is changed."""
        theme_path = getattr(self.renderer, "theme_path", None)
        if theme_path and hasattr(self.renderer, 'sound_manager'):
            # Reload sounds from the theme folder
            self.renderer.sound_manager.load_theme_sounds(theme_path)
    
    def _refresh_wallpaper_preview(self, field_key):
        """Refresh the wallpaper preview when a file is changed."""
        theme_path = getattr(self.renderer, "theme_path", None)
        if theme_path:
            scroll_pos = self.canvas.yview()
            collapsed_sections = self._get_collapsed_sections()
            
            current_values = {}
            for path, widget_info in self._edit_widgets.items():
                if "widget" not in widget_info:
                    continue
                widget = widget_info["widget"]
                if hasattr(widget, "get_value"):
                    current_values[path] = widget.get_value()
                elif hasattr(widget, "get"):
                    if isinstance(widget, tk.Text):
                        current_values[path] = widget.get("1.0", "end-1c").strip()
                    else:
                        try:
                            current_values[path] = widget.get()
                        except:
                            pass
            
            is_video_wallpaper = False
            if field_key in ("wallpaper_main", "wallpaper_external") and current_values.get(field_key):
                filename = current_values[field_key]
                ext = Path(filename).suffix.lower()
                if ext in (".mp4", ".webm"):
                    is_video_wallpaper = True
            
            if hasattr(self.renderer, "load_theme"):
                self.renderer.load_theme(theme_path)
            
            self._theme_data_hash = None
            self.load_theme_info()
            
            if is_video_wallpaper and hasattr(self, 'app') and self.app:
                self.app._force_redraw()
            
            for path, value in current_values.items():
                if path in self._edit_widgets and "widget" in self._edit_widgets[path]:
                    widget = self._edit_widgets[path]["widget"]
                    if hasattr(widget, "set_value"):
                        widget.set_value(value)
                    elif isinstance(widget, tk.Text):
                        widget.delete("1.0", "end")
                        widget.insert("1.0", value)
                    elif hasattr(widget, "set"):
                        widget.set(value)
            
            self.after(10, lambda: self._restore_ui_state(scroll_pos, collapsed_sections))
    
    def _get_collapsed_sections(self):
        """Get list of collapsed section titles."""
        collapsed = []
        for child in self.content_frame.winfo_children():
            try:
                for subchild in child.winfo_children():
                    if hasattr(subchild, 'winfo_class'):
                        # Check if this is a toggle button showing ▶ (collapsed)
                        if subchild.winfo_class() == 'TLabel':
                            try:
                                text = subchild.cget("text")
                                if text == "▶":
                                    # Get the title from the next label
                                    for sibling in child.winfo_children():
                                        if hasattr(sibling, 'winfo_class'):
                                            if sibling.winfo_class() == 'TLabel' and sibling.cget("text") != "▼" and sibling.cget("text") != "▶":
                                                collapsed.append(sibling.cget("text"))
                            except:
                                pass
            except:
                pass
        return collapsed
    
    def _restore_ui_state(self, scroll_pos, collapsed_sections):
        """Restore scroll position and collapsed sections."""
        # Restore scroll position
        self.canvas.yview_moveto(scroll_pos[0])
        
        # Restore collapsed sections
        self._collapse_sections(collapsed_sections)
    
    def _collapse_sections(self, section_titles):
        """Collapse sections by their titles."""
        for child in self.content_frame.winfo_children():
            try:
                # Find the header frame
                for subchild in child.winfo_children():
                    if hasattr(subchild, 'winfo_class') and subchild.winfo_class() == 'TFrame':
                        # Check each widget in the header
                        for widget in subchild.winfo_children():
                            if hasattr(widget, 'winfo_class') and widget.winfo_class() == 'TLabel':
                                try:
                                    text = widget.cget("text")
                                    if text in section_titles:
                                        # Find and click the toggle button
                                        for toggle in subchild.winfo_children():
                                            if hasattr(toggle, 'winfo_class') and toggle.winfo_class() == 'TLabel':
                                                try:
                                                    if toggle.cget("text") == "▼":
                                                        toggle.invoke()
                                                except:
                                                    pass
                                except:
                                    pass
            except:
                pass
    
    def _clean_theme_data(self, data):
        """Remove empty fields and normalize values for consistent comparison."""
        cleaned = {}
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and len(value) == 0:
                continue
            
            # Normalize types for comparison consistency
            if isinstance(value, str):
                stripped = value.strip()
                # Convert numeric strings to floats (JSON numbers are floats)
                try:
                    if '.' in stripped or (stripped.lstrip('-').isdigit() and stripped):
                        value = float(stripped)
                except (ValueError, AttributeError):
                    pass  # Keep as string
            
            if isinstance(value, dict):
                nested = self._clean_theme_data(value)
                if nested:
                    cleaned[key] = nested
            else:
                cleaned[key] = value
        return cleaned
    
    def _format_theme_json(self, data):
        """Format theme data as JSON with Cocoon's spacing conventions."""
        if not getattr(self.app, 'cocoon_json_format', True):
            return json.dumps(data, indent=2, ensure_ascii=False)
        return format_theme_json_string(data)
    
    def _collect_edit_values(self):
        """Collect values from all edit widgets."""
        values = {}
        
        nested_paths = self._edit_widgets.get("_nested_paths", {})
        
        for path, widget_info in self._edit_widgets.items():
            if path == "_nested_paths":
                continue
            
            if "widget" not in widget_info:
                continue
            
            widget = widget_info["widget"]
            field_type = widget_info.get("type", "string")
            
            if field_type == "text":
                value = widget.get("1.0", "end-1c").strip()
            elif hasattr(widget, "get_value"):
                value = widget.get_value()
            elif hasattr(widget, "get"):
                value = widget.get()
            else:
                continue
            
            if path in nested_paths:
                parent_key = nested_paths[path]["parent"]
                nested_key = nested_paths[path]["nested_key"]
                
                # Skip empty values for nested fields (like sounds)
                if value:
                    if parent_key not in values:
                        values[parent_key] = {}
                    values[parent_key][nested_key] = value
            else:
                values[path] = value
        
        return values
    
    def _play_save_sound(self):
        """Play the save sound effect."""
        if not PYGAME_AVAILABLE:
            return
        
        try:
            sound_path = Path(__file__).parent.parent / "assets" / "audio" / "sfx_saving_end.ogg"
            if sound_path.exists():
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                sound = pygame.mixer.Sound(str(sound_path))
                sound.play()
        except Exception:
            pass
    
    def _play_save_loop_sound(self):
        """Start playing the save loop sound."""
        if not PYGAME_AVAILABLE:
            return
        
        try:
            sound_path = Path(__file__).parent.parent / "assets" / "audio" / "sfx_saving.ogg"
            if sound_path.exists():
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                # Stop any existing save loop
                if hasattr(self, '_save_loop_sound') and self._save_loop_sound:
                    self._save_loop_sound.stop()
                self._save_loop_sound = pygame.mixer.Sound(str(sound_path))
                self._save_loop_sound.play(loops=-1)
        except Exception:
            pass
    
    def _stop_save_loop_and_play_complete(self):
        """Stop save loop and play complete sound."""
        if not PYGAME_AVAILABLE:
            return
        
        try:
            # Stop the looping sound
            if hasattr(self, '_save_loop_sound') and self._save_loop_sound:
                self._save_loop_sound.stop()
                self._save_loop_sound = None
            
            # Play complete sound
            sound_path = Path(__file__).parent.parent / "assets" / "audio" / "sfx_saving_end.ogg"
            if sound_path.exists():
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                sound = pygame.mixer.Sound(str(sound_path))
                sound.play()
        except Exception:
            pass
    
    def _revert_changes(self):
        self._has_unsaved_changes = False
        self._theme_data_hash = None
        self.load_theme_info()
    
    def load_theme_info(self):
        theme = self.renderer.theme_data or {}
        
        try:
            new_hash = hash(json.dumps(theme, sort_keys=True, default=str))
        except (TypeError, ValueError):
            new_hash = None
        
        if new_hash == self._theme_data_hash and not self.edit_mode:
            return
        
        self._theme_data_hash = new_hash
        self._clear_content()
        self.canvas.yview_moveto(0)
        
        img = getattr(self.renderer, "preview_image", None)
        if img:
            max_width = 220
            scale = max_width / img.width
            new_size = (max_width, int(img.height * scale))
            img_resized = img.resize(new_size, RESAMPLE)
            self.preview_img_tk = ImageTk.PhotoImage(img_resized)
            cursor = "hand2" if self.edit_mode else ""
            self.preview_image_label.configure(image=self.preview_img_tk, text="", cursor=cursor)
        else:
            cursor = "hand2" if self.edit_mode else ""
            self.preview_image_label.configure(image="", text="No Preview", cursor=cursor)
        
        if self.edit_mode:
            self._render_edit_mode(theme)
        else:
            self._render_read_only(theme)

    def refresh(self):
        self._theme_data_hash = None
        self.load_theme_info()

    def _clear_content(self):
        for child in self.content_frame.winfo_children():
            child.destroy()
        self._edit_widgets.clear()

    def _render_edit_mode(self, theme):
        """Render editable fields."""
        self._has_unsaved_changes = False
        theme_path = getattr(self.renderer, "theme_path", None)
        
        for section_key, section in THEME_SCHEMA.items():
            section_label = section.get("section_label", section_key)
            fields = section.get("fields", {})
            
            section_frame = self._create_section_header(section_label)
            
            for field_key, field_def in fields.items():
                value = theme.get(field_key)
                
                # For nested fields (like color_scheme), render fields directly in section
                if field_def.get("type") == "nested":
                    nested_fields = field_def.get("fields", {})
                    for nested_key, nested_def in nested_fields.items():
                        nested_value = value.get(nested_key) if value else None
                        self._render_field_edit(
                            f"{field_key}.{nested_key}",
                            nested_def,
                            nested_value,
                            section_frame,
                            theme_path,
                            parent_key=field_key,
                            nested_key=nested_key
                        )
                else:
                    self._render_field_edit(field_key, field_def, value, section_frame, theme_path)
        
        self._render_sfx_section(theme, theme_path)

    def _render_nested_edit(self, field_key, field_def, value, parent, theme_path):
        """Render nested field (like color_scheme)."""
        container = ttk.Frame(parent)
        container.pack(fill="x", pady=(4, 0))
        
        header = ttk.Frame(container)
        header.pack(fill="x")
        
        expanded = tk.BooleanVar(value=True)
        
        def toggle():
            if expanded.get():
                body.pack_forget()
                toggle_btn.config(text="▶")
                expanded.set(False)
            else:
                body.pack(fill="x")
                toggle_btn.config(text="▼")
                expanded.set(True)
        
        toggle_btn = ttk.Label(header, text="▼", width=2, cursor="hand2")
        toggle_btn.pack(side="left")
        toggle_btn.bind("<Button-1>", lambda e: toggle())
        
        title_label = ttk.Label(header, text=field_def.get("label", field_key), font=("Segoe UI", 10, "bold"))
        title_label.pack(side="left", anchor="w")
        
        body = ttk.Frame(container)
        body.pack(fill="x")
        
        nested_fields = field_def.get("fields", {})
        for nested_key, nested_def in nested_fields.items():
            nested_value = value.get(nested_key) if value else None
            self._render_field_edit(
                f"{field_key}.{nested_key}",
                nested_def,
                nested_value,
                body,
                theme_path,
                parent_key=field_key,
                nested_key=nested_key
            )

    def _render_field_edit(self, path, field_def, value, parent, theme_path, parent_key=None, nested_key=None):
        """Render a single editable field."""
        field_type = field_def.get("type", "string")
        label = field_def.get("label", path)
        
        widget_info = {"type": field_type, "path": path}
        
        if field_type == "playlist":
            widget_frame = self._create_playlist_section(parent, field_def, value, theme_path, path)
            widget_info["widget"] = widget_frame
            self._edit_widgets[path] = widget_info
            return
        
        if field_type == "timeschedule":
            widget_frame = self._create_timeschedule_section(parent, field_def, value, theme_path, path)
            widget_info["widget"] = widget_frame
            self._edit_widgets[path] = widget_info
            return
        
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        
        ttk.Label(row, text=f"{label}:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        
        widget_frame = ttk.Frame(row)
        widget_frame.pack(side="left", fill="x", expand=True)
        
        if field_type == "string" or field_type == "url":
            var = tk.StringVar(value=value or "")
            entry = ttk.Entry(widget_frame, textvariable=var)
            entry.pack(side="left", fill="x", expand=True)
            var.trace_add("write", lambda *a: None)
            entry.bind("<Key>", self._block_arrow_keys)
            widget_info["widget"] = var
        
        elif field_type == "text":
            text = tk.Text(widget_frame, height=3, wrap="word")
            text.pack(side="left", fill="x", expand=True)
            text.insert("1.0", value or "")
            text.bind("<<Modified>>", lambda e: None)
            text.bind("<Key>", self._block_arrow_keys)
            widget_info["widget"] = text
        
        elif field_type == "enum":
            var = tk.StringVar(value=value or "")
            options = field_def.get("options", [])
            combo = ttk.Combobox(widget_frame, textvariable=var, values=options, state="readonly", width=20)
            combo.pack(side="left", fill="x", expand=True)
            combo.bind("<<ComboboxSelected>>", lambda e: None)
            combo.bind("<Key>", self._block_arrow_keys)
            widget_info["widget"] = var
        
        elif field_type == "color":
            from widgets.file_picker import ColorInputWidget
            color_widget = ColorInputWidget(widget_frame, on_change=lambda v: None)
            color_widget.pack(side="left", fill="x", expand=True)
            color_widget.set_value(value)
            widget_info["widget"] = color_widget
        
        elif field_type == "file":
            from widgets.file_picker import FilePickerWidget
            name_pattern = field_def.get("name_pattern")
            
            # Create callback to refresh theme preview when file changes
            def make_file_changed_callback(key):
                def file_changed_callback():
                    self._refresh_wallpaper_preview(key)
                return file_changed_callback
            
            file_widget = FilePickerWidget(
                widget_frame,
                theme_path=theme_path,
                allowed_extensions=field_def.get("extensions", []),
                relative_folder=field_def.get("folder"),
                on_change=lambda v: None,
                name_pattern=name_pattern,
                on_file_changed=make_file_changed_callback(path),
                width=18
            )
            file_widget.pack(side="left", fill="x", expand=True)
            file_widget.set_value(value)
            widget_info["widget"] = file_widget
        
        elif field_type == "volume":
            from widgets.file_picker import VolumeSliderWidget
            vol_widget = VolumeSliderWidget(
                widget_frame,
                min_val=field_def.get("min", 0.0),
                max_val=field_def.get("max", 1.0),
                step=field_def.get("step", 0.1),
                on_change=lambda v: None
            )
            vol_widget.pack(side="left", fill="x", expand=True)
            vol_widget.set_value(value)
            widget_info["widget"] = vol_widget
        
        self._edit_widgets[path] = widget_info
        
        if parent_key and nested_key:
            if "_nested_paths" not in self._edit_widgets:
                self._edit_widgets["_nested_paths"] = {}
            self._edit_widgets["_nested_paths"][path] = {"parent": parent_key, "nested_key": nested_key}
    
    def _create_collapsible_sub_section(self, parent, title):
        """Create a collapsible sub-section within a section."""
        container = ttk.Frame(parent)
        container.pack(fill="x", pady=(5, 0))
        
        header = ttk.Frame(container)
        header.pack(fill="x")
        
        body = ttk.Frame(container)
        body.pack(fill="x")
        
        expanded = tk.BooleanVar(value=True)
        
        def toggle():
            if expanded.get():
                body.pack_forget()
                toggle_btn.config(text="▶")
                expanded.set(False)
            else:
                body.pack(fill="x")
                toggle_btn.config(text="▼")
                expanded.set(True)
        
        toggle_btn = ttk.Label(header, text="▼", width=2, cursor="hand2")
        toggle_btn.pack(side="left")
        toggle_btn.bind("<Button-1>", lambda e: toggle())
        
        label = ttk.Label(
            header,
            text=title,
            font=("Segoe UI", 9),
            cursor="hand2"
        )
        label.pack(side="left", anchor="w")
        label.bind("<Button-1>", lambda e: toggle())
        
        return body
    
    def _create_playlist_section(self, parent, field_def, value, theme_path, path):
        """Create a collapsible playlist editor section."""
        body = self._create_collapsible_sub_section(parent, "Playlist")
        
        from widgets.playlist_editor import PlaylistEditor
        playlist_widget = PlaylistEditor(
            body,
            theme_path=theme_path,
            music_folder=field_def.get("folder", "music"),
            on_change=lambda v: None
        )
        playlist_widget.pack(fill="x", expand=True)
        playlist_widget.set_value(value)
        
        return playlist_widget
    
    def _create_timeschedule_section(self, parent, field_def, value, theme_path, path):
        """Create a collapsible time schedule editor section."""
        body = self._create_collapsible_sub_section(parent, "Time Schedule")
        
        from widgets.playlist_editor import TimeScheduleEditor
        sched_widget = TimeScheduleEditor(
            body,
            theme_path=theme_path,
            music_folder=field_def.get("folder", "music"),
            on_change=lambda v: None
        )
        sched_widget.pack(fill="x", expand=True)
        sched_widget.set_value(value)
        
        return sched_widget

    def _render_sfx_section(self, theme, theme_path):
        """Render SFX section with all 16 actions."""
        sounds_folder = theme_path / "sounds" if theme_path else None
        
        section_frame = self._create_section_header("Sound Effects")
        
        sound_data = theme.get("sounds", {})
        
        for action in SFX_ACTIONS:
            row = ttk.Frame(section_frame)
            row.pack(fill="x", pady=1)
            
            ttk.Label(row, text=action.replace("_", " ").title() + ":").pack(side="left", padx=(0, 5))
            
            # Create callback to refresh sound preview when file changes
            def make_sound_changed_callback(act):
                def sound_changed_callback():
                    self._refresh_sound_preview(act)
                return sound_changed_callback
            
            from widgets.file_picker import FilePickerWidget
            file_widget = FilePickerWidget(
                row,
                theme_path=theme_path,
                allowed_extensions=[".ogg", ".mp3", ".wav"],
                relative_folder="sounds",
                on_change=lambda v, act=action: None,
                allow_empty=True,
                name_pattern=action,
                on_file_changed=make_sound_changed_callback(action),
                on_file_deleted=make_sound_changed_callback(action),
                width=12
            )
            file_widget.pack(side="left", fill="x", expand=True)
            file_widget.set_value(sound_data.get(action, ""))
            
            path = f"sounds.{action}"
            parent_key = "sounds"
            nested_key = action
            self._edit_widgets[path] = {"type": "string", "widget": file_widget}
            
            # Register nested path for sounds
            if "_nested_paths" not in self._edit_widgets:
                self._edit_widgets["_nested_paths"] = {}
            self._edit_widgets["_nested_paths"][path] = {"parent": parent_key, "nested_key": nested_key}

    def _browse_sfx(self, var):
        from widgets.file_picker import FilePickerWidget
        theme_path = getattr(self.renderer, "theme_path", None)
        
        if not theme_path:
            return
        
        search_dir = theme_path / "sounds"
        if not search_dir.exists():
            search_dir = theme_path
        
        filename = filedialog.askopenfilename(
            initialdir=str(search_dir),
            filetypes=[
                ("Audio files", "*.mp3 *.ogg *.wav *.flac *.m4a"),
                ("All files", "*.*")
            ],
            title="Select sound file"
        )
        
        if filename:
            path = Path(filename)
            try:
                rel_path = path.relative_to(theme_path / "sounds")
                var.set(str(rel_path))
            except ValueError:
                var.set(path.name)

    def _create_section_header(self, title, collapsible=True):
        """Create a collapsible section header."""
        container = ttk.Frame(self.content_frame)
        container.pack(fill="x", pady=(10, 5))
        
        sep = ttk.Separator(container, orient="horizontal")
        sep.pack(fill="x", pady=(0, 5))
        
        if collapsible:
            header = ttk.Frame(container)
            header.pack(fill="x")
            
            body = ttk.Frame(container)
            body.pack(fill="x")
            
            expanded = tk.BooleanVar(value=True)
            
            def toggle():
                if expanded.get():
                    body.pack_forget()
                    toggle_btn.config(text="▶")
                    expanded.set(False)
                else:
                    body.pack(fill="x")
                    toggle_btn.config(text="▼")
                    expanded.set(True)
            
            toggle_btn = ttk.Label(header, text="▼", width=2, cursor="hand2")
            toggle_btn.pack(side="left")
            toggle_btn.bind("<Button-1>", lambda e: toggle())
            
            label = ttk.Label(
                header,
                text=title,
                font=("Segoe UI", 11, "bold"),
                cursor="hand2"
            )
            label.pack(side="left", anchor="w")
            label.bind("<Button-1>", lambda e: toggle())
            
            return body
        else:
            label = ttk.Label(
                container,
                text=title,
                font=("Segoe UI", 11, "bold")
            )
            label.pack(anchor="w")
            
            body = ttk.Frame(container)
            body.pack(fill="x")
            
            return body

    # Field order for read-only display (old format)
    FIELD_ORDER = [
        "name", "author", "version", "description", "credits", "website",
        "theme_mode", "color_scheme",
        "wallpaper_main", "wallpaper_external",
        "music_mode", "music_playback_mode", "music_playlist", "music_time_schedule",
        "sfx_volume", "music_volume"
    ]
    
    def _render_read_only(self, theme):
        """Render read-only display using FIELD_ORDER."""
        rendered_keys = set()
        
        # First render fields in the specified order
        for key in self.FIELD_ORDER:
            if key in theme:
                rendered_keys.add(key)
                value = theme[key]
                
                if key == "color_scheme" and isinstance(value, dict):
                    self._render_color_scheme_read_only(value)
                elif isinstance(value, dict):
                    self._render_dict_read_only(key, value)
                else:
                    self._render_simple_row_read_only(key, value)
        
        # Then render any remaining fields not in the order list
        for key, value in theme.items():
            if key not in rendered_keys:
                if isinstance(value, dict):
                    self._render_dict_read_only(key, value)
                else:
                    self._render_simple_row_read_only(key, value)

    def _render_color_scheme_read_only(self, color_scheme, parent=None):
        """Render color scheme section in read-only mode."""
        if parent is None:
            parent = self.content_frame
        
        for key, value in color_scheme.items():
            self._render_simple_row_read_only(key, value, parent)
    
    def _render_dict_read_only(self, title, data, parent=None):
        """Render a dictionary in read-only mode."""
        if parent is None:
            parent = self.content_frame
        
        for key, value in data.items():
            self._render_simple_row_read_only(key, value, parent)
    
    def _render_simple_row_read_only(self, key, value, parent=None):
        """Render a simple key-value row in read-only mode."""
        if parent is None:
            parent = self.content_frame
        
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        
        key_label = ttk.Label(
            row,
            text=f"{key}:",
            font=("Segoe UI", 9, "bold"),
            wraplength=100,
            justify="left"
        )
        key_label.grid(row=0, column=0, sticky="nw")
        
        value_frame = ttk.Frame(row)
        
        value_str = str(value) if value is not None else ""
        
        if key in ("description", "credits"):
            value_frame.grid(row=0, column=1, sticky="nw")
        else:
            value_frame.grid(row=0, column=1, sticky="ne")
        
        # Check if it's a hex color
        if isinstance(value, str) and HEX_COLOR_RE.match(value_str):
            value_label = ttk.Label(value_frame, text=value_str, wraplength=120)
            value_label.pack(side="left", padx=(0, 6), anchor="n")
            swatch = self._make_color_swatch(value_str)
            swatch_label = ttk.Label(value_frame, image=swatch)
            swatch_label.image = swatch
            swatch_label.pack(side="right", anchor="n")
        
        # Check if it's a URL
        elif isinstance(value, str) and re.match(r"^https?://", value_str):
            link = ttk.Label(
                value_frame,
                text=value_str,
                foreground="#4ea1ff",
                cursor="hand2",
                wraplength=150
            )
            link.pack(anchor="ne")
            link.bind("<Button-1>", lambda e, u=value_str: webbrowser.open(u))
        
        # Long text fields
        elif key in ("description", "credits"):
            value_label = ttk.Label(
                value_frame,
                text=value_str,
                wraplength=150,
                justify="left"
            )
            value_label.pack(anchor="nw")
        
        # Normal text
        else:
            value_label = ttk.Label(
                value_frame,
                text=value_str,
                wraplength=150,
                justify="right"
            )
            value_label.pack(anchor="ne")
    
    def _make_color_swatch(self, hex_color, size=14):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((1, 1, size - 2, size - 2), fill=hex_color, outline="#000000")
        return ImageTk.PhotoImage(img)


THEME_SECTIONS = [
    ("metadata", ["name", "author", "version", "description", "credits", "website"]),
    ("theme_mode", ["theme_mode"]),
    ("color_scheme", ["color_scheme"]),
    ("wallpapers", ["wallpaper_main", "wallpaper_external"]),
    ("music", ["music_mode", "music_playback_mode", "music_playlist", "music_time_schedule", "sfx_volume", "music_volume"]),
]

COLOR_SCHEME_GROUPS = [
    ["background_gradient_start", "background_gradient_end"],
    ["card_gradient_start", "card_gradient_end"],
    ["text_primary", "text_secondary"],
    ["icon_tint"],
    ["tile_background", "tile_border"],
    ["toggle_off_gradient_start", "toggle_off_gradient_end", "toggle_thumb_gradient_start", "toggle_thumb_gradient_end"],
    ["drop_shadow", "inner_shadow_light", "inner_shadow_dark"],
    ["success", "warning", "divider"],
    ["accent_gradient_start", "accent_gradient_end", "accent_glow"],
]


def _section_exists(data, keys):
    """Check if any of the keys exist in the data."""
    for key in keys:
        if key in data:
            return True
    return False


def _get_last_metadata_key(data):
    """Get the last metadata key that exists in data."""
    metadata_keys = ["name", "author", "version", "description", "credits", "website"]
    for key in reversed(metadata_keys):
        if key in data:
            return key
    return None


def _get_first_music_key(data):
    """Get the first music key that exists in data."""
    music_keys = ["music_mode", "music_playback_mode", "music_playlist", "music_time_schedule", "sfx_volume", "music_volume"]
    for key in music_keys:
        if key in data:
            return key
    return None


def _format_color_scheme_section(json_str):
    """Add blank lines between color scheme groups."""
    for i, group in enumerate(COLOR_SCHEME_GROUPS):
        last_key = group[-1]
        if i < len(COLOR_SCHEME_GROUPS) - 1:
            next_group = COLOR_SCHEME_GROUPS[i + 1]
            next_key = next_group[0]
            
            pattern = rf'("{last_key}": "[^"]*",)(\n    "{next_key}")'
            replacement = r'\1\n\2'
            json_str = re.sub(pattern, replacement, json_str)
    
    return json_str


def format_theme_json_string(data):
    """Format theme data as JSON with Cocoon's spacing conventions."""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    present_sections = []
    for section_name, section_keys in THEME_SECTIONS:
        if _section_exists(data, section_keys):
            present_sections.append((section_name, section_keys))
    
    for i, (section_name, section_keys) in enumerate(present_sections):
        if section_name == "metadata":
            if _section_exists(data, ["website"]) and _section_exists(data, ["theme_mode"]):
                json_str = re.sub(
                    r'(\n  "website": "[^"]*",)(\n  "theme_mode")',
                    r'\1\n\2',
                    json_str
                )
            
            if not _section_exists(data, ["theme_mode"]) and i < len(present_sections) - 1:
                next_section_name = present_sections[i + 1][0]
                last_meta = _get_last_metadata_key(data)
                if last_meta:
                    if next_section_name == "color_scheme":
                        json_str = re.sub(
                            rf'("{last_meta}": "[^"]*",)(\n  "{next_section_name}")',
                            r'\1\n\2',
                            json_str
                        )
                    elif next_section_name == "wallpapers":
                        next_key = "wallpaper_main" if _section_exists(data, ["wallpaper_main"]) else "wallpaper_external"
                        json_str = re.sub(
                            rf'("{last_meta}": "[^"]*",)(\n  "{next_key}")',
                            r'\1\n\2',
                            json_str
                        )
                    elif next_section_name == "music":
                        next_key = _get_first_music_key(data)
                        if next_key:
                            json_str = re.sub(
                                rf'("{last_meta}": "[^"]*",)(\n  "{next_key}")',
                                r'\1\n\2',
                                json_str
                            )
        
        elif section_name == "theme_mode":
            if i < len(present_sections) - 1:
                next_section_name, next_section_keys = present_sections[i + 1]
                if next_section_name == "color_scheme":
                    json_str = re.sub(
                        r'(\n  "theme_mode": "[^"]*",)(\n  "color_scheme")',
                        r'\1\n\2',
                        json_str
                    )
                elif next_section_name == "wallpapers":
                    json_str = re.sub(
                        r'(\n  "theme_mode": "[^"]*",)(\n  "wallpaper_main")',
                        r'\1\n\2',
                        json_str
                    )
                elif next_section_name == "music":
                    json_str = re.sub(
                        r'(\n  "theme_mode": "[^"]*",)(\n  "music_mode")',
                        r'\1\n\2',
                        json_str
                    )
        
        elif section_name == "color_scheme":
            json_str = _format_color_scheme_section(json_str)
            
            if i < len(present_sections) - 1:
                next_section_name, next_section_keys = present_sections[i + 1]
                if next_section_name == "wallpapers" and _section_exists(data, next_section_keys):
                    json_str = re.sub(
                        r'("accent_glow": "[^"]*"\n  },)(\n  "wallpaper_main")',
                        r'\1\n\2',
                        json_str
                    )
                elif next_section_name == "music":
                    json_str = re.sub(
                        r'("accent_glow": "[^"]*"\n  },)(\n  "music_mode")',
                        r'\1\n\2',
                        json_str
                    )
        
        elif section_name == "wallpapers":
            if _section_exists(data, ["wallpaper_external"]) and _section_exists(data, ["music_mode"]):
                json_str = re.sub(
                    r'(\n  "wallpaper_external": "[^"]*",)(\n  "music_mode")',
                    r'\1\n\2',
                    json_str
                )
    
    return json_str
