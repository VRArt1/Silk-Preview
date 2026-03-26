import tkinter as tk
from tkinter import ttk, filedialog, messagebox, PhotoImage, BooleanVar
from PIL import Image, ImageTk
from pathlib import Path
import shutil

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from widgets.file_picker import FilePickerWidget
from widgets.utils import center_to_parent


class AssetEditorPanel(ttk.Frame):
    def __init__(self, parent, renderer, app=None, last_system_list=None):
        super().__init__(parent)
        self.renderer = renderer
        self.app = app
        self.theme_path = getattr(renderer, 'theme_path', None)
        self._last_system_list = last_system_list
        
        self._system_lists = []
        self._global_overlay = {"overlay": None, "mask": None}
        self._console_overrides = {}
        self._smart_folders = []
        self._smart_folders_by_platform = {}
        self._initialized = False
    
    def _initialize_content(self):
        """Create UI content on demand when entering edit mode."""
        if self._initialized:
            return
        
        self._load_system_lists()
        self._create_ui()
        self._scan_all_assets()
        self._initialized = True
    
    def _save_system_list(self, list_name):
        """Save the selected system list to config."""
        if self.app and hasattr(self.app, 'config'):
            self.app.config["Misc"]["last_system_list"] = list_name
            self._last_system_list = list_name
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid_propagate(False)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        
        self.icon_overlay_tab = IconOverlayEditor(self.notebook, self, self._last_system_list)
        self.notebook.add(self.icon_overlay_tab, text="Icon Overlays")
        
        self.smart_folder_root_tab = SmartFolderEditor(self.notebook, self, mode="root")
        self.notebook.add(self.smart_folder_root_tab, text="Smart Folders")
        
        self.smart_folder_platform_tab = SmartFolderEditor(self.notebook, self, mode="by_platform")
        self.notebook.add(self.smart_folder_platform_tab, text="By Platform")
        
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", side="bottom", pady=(5, 0))
        
        ttk.Button(toolbar, text="Refresh", command=lambda: self._refresh(force_rescan=False)).pack(side="left", padx=5)
    
    def _trigger_bulk_add(self):
        """Trigger bulk add only if Icon Overrides tab is active."""
        if hasattr(self, 'icon_overlay_tab') and hasattr(self.icon_overlay_tab, '_add_bulk_overrides'):
            self.icon_overlay_tab._add_bulk_overrides()
        else:
            messagebox.showinfo("Bulk Add", "Bulk Add is only available in Icon Overrides tab.")
    
    def _trigger_bulk_remove(self):
        """Trigger bulk remove only if Icon Overrides tab is active."""
        if hasattr(self, 'icon_overlay_tab') and hasattr(self.icon_overlay_tab, '_bulk_remove_duplicates'):
            self.icon_overlay_tab._bulk_remove_duplicates()
        else:
            messagebox.showinfo("Bulk Remove", "Bulk Remove is only available in Icon Overrides tab.")
    
    def _load_system_lists(self):
        base_dir = Path(__file__).parent.parent / "assets" / "system_lists"
        if not base_dir.exists():
            self._system_lists = ["Cocoon"]
            return
        
        self._system_lists = []
        for f in sorted(base_dir.glob("*.txt")):
            self._system_lists.append(f.stem)
        
        if not self._system_lists:
            self._system_lists = ["Cocoon"]
        
        if hasattr(self, 'icon_overlay_tab'):
            self.icon_overlay_tab._sync_system_lists()
    
    def _scan_all_assets(self):
        """Scan theme folder for all assets: icon overlays, smart folders, by platform."""
        self._console_overrides = {}
        self._smart_folders = []
        self._smart_folders_by_platform = {}
        
        if not self.theme_path:
            self._refresh_tabs()
            return
        
        icon_dir = self.theme_path / "icon_overlays"
        
        if icon_dir.exists():
            for folder in icon_dir.iterdir():
                if folder.is_dir() and folder.name not in ("by_platform", "_global"):
                    overlay_path = folder / "overlay.png"
                    mask_path = folder / "mask.png"
                    if overlay_path.exists() and mask_path.exists():
                        self._console_overrides[folder.name] = {
                            "overlay": overlay_path,
                            "mask": mask_path
                        }
        
        smart_root = self.theme_path / "smart_folders"
        
        if smart_root.exists():
            for folder in smart_root.iterdir():
                if folder.is_dir() and folder.name not in ("by_platform", "_global"):
                    assets = self._scan_folder_assets(folder)
                    self._smart_folders.append({
                        "name": folder.name,
                        "path": folder,
                        **assets
                    })
            
            by_platform_dir = smart_root / "by_platform"
            if by_platform_dir.exists():
                for platform_folder in by_platform_dir.iterdir():
                    if platform_folder.is_dir() and platform_folder.name != "_global":
                        assets = self._scan_folder_assets(platform_folder)
                        self._smart_folders_by_platform[platform_folder.name] = {
                            "path": platform_folder,
                            **assets
                        }
        
        self._refresh_tabs()
    
    def _scan_folder_assets(self, folder_path):
        """Scan a folder for icon.png, hero.png, logo.png assets."""
        return {
            "icon": folder_path / "icon.png" if (folder_path / "icon.png").exists() else None,
            "hero": folder_path / "hero.png" if (folder_path / "hero.png").exists() else None,
            "logo": folder_path / "logo.png" if (folder_path / "logo.png").exists() else None,
        }
    
    def _refresh_tabs(self):
        """Refresh all tabs to show current data."""
        if not self._initialized:
            return
        self.update_idletasks()
        if hasattr(self, 'notebook'):
            self.notebook.select(self.icon_overlay_tab)
        if hasattr(self, 'icon_overlay_tab'):
            self.icon_overlay_tab.refresh()
        if hasattr(self, 'smart_folder_root_tab'):
            self.smart_folder_root_tab.refresh()
        if hasattr(self, 'smart_folder_platform_tab'):
            self.smart_folder_platform_tab.refresh()
    
    def _refresh(self, force_rescan=False):
        if not self._initialized:
            return
        self.theme_path = getattr(self.renderer, 'theme_path', None)
        
        if force_rescan or self.theme_path:
            self._scan_all_assets()
        else:
            self._refresh_tabs()
        
        if self.app:
            self.app._force_redraw()


class IconOverlayEditor(ttk.Frame):
    def __init__(self, parent, asset_panel, default_list=None):
        super().__init__(parent)
        self.asset_panel = asset_panel
        self.renderer = asset_panel.renderer
        self.theme_path = asset_panel.theme_path
        
        self._current_list_name = default_list or "Cocoon"
        self._current_consoles = []
        self._filtered_consoles = []
        self._active_console = None
        
        self._create_ui()
        self._load_console_list(self._current_list_name)
        self._sync_system_lists()
    
    def _sync_system_lists(self):
        """Sync the combobox with the asset panel's system lists."""
        if hasattr(self, 'list_combo') and hasattr(self.asset_panel, '_system_lists'):
            self.list_combo['values'] = self.asset_panel._system_lists
            if self._current_list_name not in self.asset_panel._system_lists:
                self._current_list_name = self.asset_panel._system_lists[0] if self.asset_panel._system_lists else "Cocoon"
            self.list_var.set(self._current_list_name)
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        self.grid_propagate(False)
        
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        self.list_var = tk.StringVar()
        self.list_combo = ttk.Combobox(
            list_frame, textvariable=self.list_var,
            values=self.asset_panel._system_lists,
            state="readonly", width=20
        )
        self.list_combo.pack(side="left", fill="x", expand=True)
        self.list_combo.bind("<<ComboboxSelected>>", self._on_list_changed)
        

        
        global_frame = ttk.LabelFrame(self, text="Global Overlay", padding=5)
        global_frame.pack(fill="x", padx=5, pady=(5, 0))
        
        overlay_row = ttk.Frame(global_frame)
        overlay_row.pack(fill="x")
        ttk.Label(overlay_row, text="overlay:", width=8).pack(side="left")
        self.global_overlay_picker = FilePickerWidget(
            overlay_row, theme_path=self.theme_path,
            relative_folder="icon_overlays/_global",
            allowed_extensions=[".png"],
            name_pattern="overlay",
            on_change=self._on_global_changed,
            width=12
        )
        self.global_overlay_picker.pack(side="left", fill="x", expand=True)
        
        mask_row = ttk.Frame(global_frame)
        mask_row.pack(fill="x", pady=(3, 0))
        ttk.Label(mask_row, text="mask:", width=8).pack(side="left")
        self.global_mask_picker = FilePickerWidget(
            mask_row, theme_path=self.theme_path,
            relative_folder="icon_overlays/_global",
            allowed_extensions=[".png"],
            name_pattern="mask",
            on_change=self._on_global_changed,
            width=12
        )
        self.global_mask_picker.pack(side="left", fill="x", expand=True)
        
        preview_row = ttk.Frame(global_frame)
        preview_row.pack(fill="x", pady=(5, 0))
        ttk.Label(preview_row, text="Preview:").pack(side="left")
        self.global_preview = tk.Label(preview_row, text="(no preview)")
        self.global_preview.pack(side="left", padx=(5, 0))
        
        self.console_frame = ttk.LabelFrame(self, text="Console Overrides", padding=5)
        self.console_frame.pack(fill="both", expand=True, padx=5, pady=(5, 5))
        
        self.console_scroll = ScrollFrame(self.console_frame)
        self.console_scroll.pack(fill="both", expand=True)
        self.console_container = self.console_scroll.interior
        self.console_container.columnconfigure(0, weight=1)
        
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", side="bottom", pady=(5, 0))
        
        bulk_left = ttk.Frame(toolbar)
        bulk_left.pack(side="left")
        ttk.Button(bulk_left, text="+ Bulk Add", 
                  command=self._add_bulk_overrides).pack(side="left")
        
        bulk_right = ttk.Frame(toolbar)
        bulk_right.pack(side="right")
        ttk.Button(bulk_right, text="- Bulk Remove", 
                  command=self._bulk_remove_duplicates).pack(side="right")
    
    def _load_console_list(self, list_name):
        base_dir = Path(__file__).parent.parent / "assets" / "system_lists"
        list_file = base_dir / f"{list_name}.txt"
        
        self._current_consoles = []
        if list_file.exists():
            with open(list_file, 'r') as f:
                for line in f:
                    name = line.strip()
                    if name:
                        self._current_consoles.append(name)
        
        self._current_list_name = list_name
        self._filtered_consoles = list(self._current_consoles)
        
        if self.asset_panel and hasattr(self.asset_panel, '_save_system_list'):
            self.asset_panel._save_system_list(list_name)
    
    def _on_list_changed(self, event=None):
        selected = self.list_var.get()
        if selected:
            self._load_console_list(selected)
            self._rebuild_console_grid()
    
    def _refresh_override_list(self):
        """Refresh the override list to detect changes and rescan assets."""
        self.asset_panel._scan_all_assets()
        if self.asset_panel.app:
            self.asset_panel.app._force_redraw()
    
    def _has_override(self, console):
        """Check if console has override files (overlay.png and mask.png)."""
        if not self.theme_path:
            return False
        folder = self.theme_path / "icon_overlays" / console
        return (folder / "overlay.png").exists() and (folder / "mask.png").exists()
    
    def _get_file_hash(self, path):
        """Get MD5 hash of a file for comparison."""
        import hashlib
        h = hashlib.md5()
        with open(path, 'rb') as f:
            h.update(f.read())
        return h.hexdigest()
    
    def _is_same_as_global(self, console):
        """Check if console's files are identical to global files."""
        if not self.theme_path:
            return False
        global_dir = self.theme_path / "icon_overlays" / "_global"
        console_dir = self.theme_path / "icon_overlays" / console
        
        global_overlay = global_dir / "overlay.png"
        global_mask = global_dir / "mask.png"
        console_overlay = console_dir / "overlay.png"
        console_mask = console_dir / "mask.png"
        
        if not (global_overlay.exists() and global_mask.exists() and 
                console_overlay.exists() and console_mask.exists()):
            return False
        
        try:
            return (self._get_file_hash(global_overlay) == self._get_file_hash(console_overlay) and
                    self._get_file_hash(global_mask) == self._get_file_hash(console_mask))
        except:
            return False
    
    def _has_custom_override(self, console):
        """Check if console has custom override different from global."""
        if not self._has_folder(console):
            return False
        return not self._is_same_as_global(console)
    
    def _has_folder(self, console):
        """Check if console folder exists (regardless of files)."""
        if not self.theme_path:
            return False
        folder = self.theme_path / "icon_overlays" / console
        return folder.exists() and folder.is_dir()
    
    def _get_consoles_without_overrides(self):
        """Get list of consoles that don't have custom overrides (different from global)."""
        return [c for c in self._current_consoles if not self._has_custom_override(c)]
    
    def _rebuild_console_grid(self):
        for widget in self.console_container.winfo_children():
            widget.destroy()
        
        if not self._current_consoles:
            ttk.Label(self.console_container, text="(no consoles in system list)", foreground="#666666").pack(pady=10)
            return
        
        add_frame = ttk.Frame(self.console_container)
        add_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(add_frame, text="Add:", font=("Segoe UI", 8)).pack(side="left")
        
        no_override_consoles = self._get_consoles_without_overrides()
        
        if no_override_consoles:
            self._add_console_var = tk.StringVar(value=no_override_consoles[0] if no_override_consoles else "")
            add_combo = ttk.Combobox(add_frame, textvariable=self._add_console_var, 
                                    values=no_override_consoles, state="readonly", width=15)
            add_combo.pack(side="left", padx=(5, 0))
            ttk.Button(add_frame, text="+", width=2, 
                      command=self._add_override_from_combo).pack(side="left", padx=(2, 0))
            ttk.Button(add_frame, text="+ Custom", width=9, 
                      command=self._add_custom_console).pack(side="left", padx=(5, 0))
        else:
            ttk.Label(add_frame, text="(all have overrides)", foreground="#666666", font=("Segoe UI", 8)).pack(side="left")
            ttk.Button(add_frame, text="+ Custom", width=9, 
                      command=self._add_custom_console).pack(side="left", padx=(5, 0))
        
        # Only show consoles with custom overrides (different from global)
        override_consoles = [c for c in self._current_consoles if self._has_custom_override(c)]
        
        if not override_consoles:
            ttk.Label(self.console_container, text="(no overrides yet)", foreground="#666666").pack(pady=10)
            return
        
        for console in sorted(override_consoles):
            self._build_inline_editor(console)
        
        self.console_container.update_idletasks()
        if hasattr(self.console_scroll, 'update_scrollregion'):
            self.console_scroll.update_scrollregion()
    
    def _build_inline_editor(self, console):
        row = ttk.LabelFrame(self.console_container, text="", padding=2)
        row.pack(fill="x", pady=2)
        
        # Header with delete button
        header = ttk.Frame(row)
        header.pack(fill="x", padx=2, pady=(0, 2))
        
        ttk.Label(header, text=console, font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(header, text="X", width=2, command=lambda c=console: self._delete_override(c)).pack(side="right")
        
        slots_frame = ttk.Frame(row)
        slots_frame.pack(fill="x")
        slots_frame.columnconfigure(0, weight=1)
        slots_frame.columnconfigure(1, weight=1)
        
        overlay_frame = ttk.LabelFrame(slots_frame, text="overlay", padding=2)
        overlay_frame.grid(row=0, column=0, padx=2, sticky="ew")
        
        overlay_label = ttk.Label(overlay_frame, text="+", anchor="center")
        overlay_label.pack(fill="both", expand=True)
        overlay_label.bind("<Button-1>", lambda e, c=console: self._browse_console_file(c, "overlay"))
        if DND_AVAILABLE:
            try:
                overlay_label.drop_target_register(DND_FILES)
                overlay_label.dnd_bind('<<Drop>>', lambda e, c=console: self._on_console_drop(e, c, "overlay"))
            except:
                pass
        
        self._load_canvas_thumbnail(overlay_label, console, "overlay")
        
        mask_frame = ttk.LabelFrame(slots_frame, text="mask", padding=2)
        mask_frame.grid(row=0, column=1, padx=2, sticky="ew")
        
        mask_label = ttk.Label(mask_frame, text="+", anchor="center")
        mask_label.pack(fill="both", expand=True)
        mask_label.bind("<Button-1>", lambda e, c=console: self._browse_console_file(c, "mask"))
        if DND_AVAILABLE:
            try:
                mask_label.drop_target_register(DND_FILES)
                mask_label.dnd_bind('<<Drop>>', lambda e, c=console: self._on_console_drop(e, c, "mask"))
            except:
                pass
        
        self._load_canvas_thumbnail(mask_label, console, "mask")
    
    def _load_canvas_thumbnail(self, label, console, file_type):
        if not self.theme_path:
            return
        folder = self.theme_path / "icon_overlays" / console
        path = folder / f"{file_type}.png"
        if path and path.exists():
            try:
                img = Image.open(path).convert("RGBA")
                img = img.resize((48, 48), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                label.configure(image=photo, text="")
                label.image = photo
            except:
                label.configure(image="", text="!")
        else:
            label.configure(image="", text="+")
    
    def _add_override_from_combo(self):
        console = self._add_console_var.get()
        if console:
            folder = self.theme_path / "icon_overlays" / console
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
            else:
                # Remove existing overlay/mask files to clear any global copies
                overlay_file = folder / "overlay.png"
                mask_file = folder / "mask.png"
                if overlay_file.exists():
                    overlay_file.unlink()
                if mask_file.exists():
                    mask_file.unlink()
            self._rebuild_console_grid()
    
    def _add_custom_console(self):
        root = self.winfo_toplevel()
        
        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title("Add Custom Icon Overlay")
        dialog.geometry("220x90")
        dialog.resizable(False, False)
        
        icon_path = Path(__file__).parent.parent / "assets/favicon_icon_overlay.png"
        if icon_path.exists():
            icon_img = PhotoImage(file=icon_path)
            dialog.iconphoto(False, icon_img)
        
        dialog.transient(root)
        
        name_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=name_var, width=25)
        entry.pack(pady=(15, 8))
        
        def on_ok():
            name = name_var.get().strip()
            if name:
                if name not in self._current_consoles:
                    self._current_consoles.append(name)
                folder = self.theme_path / "icon_overlays" / name
                folder.mkdir(parents=True, exist_ok=True)
                dialog.destroy()
                self._rebuild_console_grid()
            else:
                dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="OK", width=6, command=on_ok).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Cancel", width=6, command=on_cancel).pack(side="left", padx=3)
        
        entry.bind("<Return>", lambda e: on_ok())
        entry.bind("<Escape>", lambda e: on_cancel())
        
        center_to_parent(dialog, root)
        dialog.deiconify()
        entry.focus()
    
    def _add_bulk_overrides(self):
        """Create folders for all consoles without overrides, copying from global if available."""
        if not self.theme_path:
            return
        
        global_dir = self.theme_path / "icon_overlays" / "_global"
        global_overlay = global_dir / "overlay.png"
        global_mask = global_dir / "mask.png"
        
        created_count = 0
        for console in self._current_consoles:
            if not self._has_folder(console):
                folder = self.theme_path / "icon_overlays" / console
                folder.mkdir(parents=True, exist_ok=True)
                
                if global_overlay.exists():
                    shutil.copy2(global_overlay, folder / "overlay.png")
                if global_mask.exists():
                    shutil.copy2(global_mask, folder / "mask.png")
                created_count += 1
        
        if created_count > 0:
            messagebox.showinfo("Bulk Add", f"Created {created_count} console overrides from global assets.")
        
        self._rebuild_console_grid()
    
    def _bulk_remove_duplicates(self):
        """Delete all console override folders that are identical to global."""
        if not self.theme_path:
            return
        
        deleted = []
        for console in self._current_consoles:
            if self._is_same_as_global(console):
                folder = self.theme_path / "icon_overlays" / console
                if folder.exists():
                    shutil.rmtree(folder)
                    deleted.append(console)
        
        if deleted:
            messagebox.showinfo("Bulk Remove", f"Removed {len(deleted)} duplicate override(s).")
        else:
            messagebox.showinfo("Bulk Remove", "No duplicate overrides found.")
        
        self._rebuild_console_grid()
    
    def _build_editor_frame(self, console):
        self.editor_frame = ttk.LabelFrame(self.console_frame, text=f"{console}", padding=8)
        self.editor_frame.pack(fill="x")
        
        header = ttk.Frame(self.editor_frame)
        header.pack(fill="x")
        ttk.Button(header, text="X", width=3, command=self._close_editor).pack(side="right")
        
        drop_frame = ttk.Frame(self.editor_frame)
        drop_frame.pack(fill="x", pady=(8, 0))
        
        drop_frame.columnconfigure(0, weight=1)
        drop_frame.columnconfigure(1, weight=1)
        
        overlay_frame = ttk.LabelFrame(drop_frame, text="overlay.png", padding=3)
        overlay_frame.grid(row=0, column=0, padx=3, sticky="ew")
        
        self.overlay_canvas = tk.Canvas(overlay_frame, width=48, height=48, bg="#2a2a2a", highlightthickness=0)
        self.overlay_canvas.pack()
        self.overlay_canvas.bind("<Button-1>", lambda e: self._browse_console_file(console, "overlay"))
        if DND_AVAILABLE:
            try:
                self.overlay_canvas.drop_target_register(DND_FILES)
                self.overlay_canvas.dnd_bind('<<Drop>>', lambda e: self._on_console_drop(e, console, "overlay"))
            except:
                pass
        
        mask_frame = ttk.LabelFrame(drop_frame, text="mask.png", padding=3)
        mask_frame.grid(row=0, column=1, padx=3, sticky="ew")
        
        self.mask_canvas = tk.Canvas(mask_frame, width=48, height=48, bg="#2a2a2a", highlightthickness=0)
        self.mask_canvas.pack()
        self.mask_canvas.bind("<Button-1>", lambda e: self._browse_console_file(console, "mask"))
        if DND_AVAILABLE:
            try:
                self.mask_canvas.drop_target_register(DND_FILES)
                self.mask_canvas.dnd_bind('<<Drop>>', lambda e: self._on_console_drop(e, console, "mask"))
            except:
                pass
        
        btn_frame = ttk.Frame(self.editor_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        if self._has_override(console):
            ttk.Button(btn_frame, text="Delete Override", 
                      command=lambda: self._delete_override(console)).pack(side="right")
        
        self._load_console_thumbnails(console)
    
    def _load_console_thumbnails(self, console):
        if not self.theme_path:
            return
        
        folder = self.theme_path / "icon_overlays" / console
        
        overlay_path = folder / "overlay.png"
        mask_path = folder / "mask.png"
        
        self._show_thumbnail(self.overlay_canvas, overlay_path)
        self._show_thumbnail(self.mask_canvas, mask_path)
    
    def _show_thumbnail(self, canvas, path):
        canvas.delete("all")
        if path and path.exists():
            try:
                img = Image.open(path).convert("RGBA")
                img.thumbnail((60, 60), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                canvas.create_image(32, 32, image=photo, anchor="center")
                canvas.image = photo
            except:
                canvas.create_text(32, 32, text="!", fill="red", anchor="center")
        else:
            canvas.configure(bg="#2a2a2a")
            canvas.create_text(32, 32, text="+", fill="#666666", anchor="center", font=("Segoe UI", 16))
    
    def _on_console_drop(self, event, console, file_type):
        if not self.theme_path:
            return
        files = self.tk.splitlist(event.data)
        if files:
            dropped_file = Path(files[0])
            if dropped_file.exists():
                folder = self.theme_path / "icon_overlays" / console
                folder.mkdir(parents=True, exist_ok=True)
                dest = folder / f"{file_type}.png"
                shutil.copy2(dropped_file, dest)
                self._rebuild_console_grid()
    
    def _browse_console_file(self, console, file_type):
        if not self.theme_path:
            return
        
        folder = self.theme_path / "icon_overlays" / console
        folder.mkdir(parents=True, exist_ok=True)
        
        exts = [("PNG files", "*.png")]
        path = filedialog.askopenfilename(title=f"Select {file_type}.png", filetypes=exts)
        
        if path:
            dest = folder / f"{file_type}.png"
            shutil.copy2(path, dest)
            self._rebuild_console_grid()
    
    def _delete_override(self, console):
        folder = self.theme_path / "icon_overlays" / console
        if folder.exists():
            shutil.rmtree(folder)
            self._close_editor()
            self.after(50, self._rebuild_console_grid)
    
    def _close_editor(self):
        self._active_console = None
        if hasattr(self, 'editor_frame') and self.editor_frame:
            self.editor_frame.destroy()
            self.editor_frame = None
        self.console_scroll.pack(fill="both", expand=True)
        self._rebuild_console_grid()
    
    def _on_global_changed(self):
        self.theme_path = self.asset_panel.theme_path
        self.global_overlay_picker.set_theme_path(self.theme_path)
        self.global_mask_picker.set_theme_path(self.theme_path)
        self._update_global_preview()
        self._save_global_to_theme()
        self.asset_panel._refresh(force_rescan=True)
    
    def _update_global_preview(self):
        overlay_val = self.global_overlay_picker.get_value()
        mask_val = self.global_mask_picker.get_value()
        
        if overlay_val and mask_val:
            overlay_path = self.theme_path / "icon_overlays" / "_global" / overlay_val
            mask_path = self.theme_path / "icon_overlays" / "_global" / mask_val
            
            if overlay_path.exists() and mask_path.exists():
                try:
                    overlay_img = Image.open(overlay_path).convert("RGBA")
                    mask_img = Image.open(mask_path).convert("RGBA")
                    
                    overlay_img.thumbnail((48, 48), Image.Resampling.LANCZOS)
                    mask_img.thumbnail((48, 48), Image.Resampling.LANCZOS)
                    
                    preview = ImageTk.PhotoImage(overlay_img)
                    self.global_preview.configure(image=preview, text="")
                    self.global_preview.image = preview
                    return
                except:
                    pass
        
        self.global_preview.configure(image="", text="(no preview)")
    
    def _save_global_to_theme(self):
        if not self.theme_path:
            return
        
        overlay_val = self.global_overlay_picker.get_value()
        mask_val = self.global_mask_picker.get_value()
        
        global_dir = self.theme_path / "icon_overlays" / "_global"
        global_dir.mkdir(parents=True, exist_ok=True)
        
        self.asset_panel._global_overlay = {
            "overlay": overlay_val,
            "mask": mask_val
        }
    
    def refresh(self):
        self.theme_path = self.asset_panel.theme_path
        self.global_overlay_picker.set_theme_path(self.theme_path)
        self.global_mask_picker.set_theme_path(self.theme_path)
        
        if self.theme_path:
            global_dir = self.theme_path / "icon_overlays" / "_global"
            if global_dir.exists():
                overlay_file = global_dir / "overlay.png"
                mask_file = global_dir / "mask.png"
                if overlay_file.exists():
                    self.global_overlay_picker.set_value("overlay.png")
                if mask_file.exists():
                    self.global_mask_picker.set_value("mask.png")
        
        self._update_global_preview()
        self._rebuild_console_grid()
        
        self.console_container.update_idletasks()
        
        # Find the parent ScrollFrame and update its scrollregion
        parent = self.console_container.master
        if hasattr(parent, 'update_scrollregion'):
            parent.update_scrollregion()


class IconOverlayDialog(tk.Toplevel):
    def __init__(self, parent, theme_path, folder, console_name):
        super().__init__(parent)
        self.theme_path = theme_path
        self.folder = folder
        self.console_name = console_name
        
        self.title(f"Icon Overlay: {console_name}")
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        self._load_existing()
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        
        ttk.Label(self, text=f"Console: {self.console_name}", font=("Segoe UI", 11, "bold")).pack(pady=(10, 10))
        
        overlay_row = ttk.Frame(self)
        overlay_row.pack(fill="x", padx=20, pady=5)
        ttk.Label(overlay_row, text="overlay.png:", width=12).pack(side="left")
        self.overlay_picker = FilePickerWidget(
            overlay_row, theme_path=self.theme_path,
            relative_folder=f"icon_overlays/{self.console_name}",
            allowed_extensions=[".png"],
            width=20
        )
        self.overlay_picker.pack(side="left", fill="x", expand=True)
        
        mask_row = ttk.Frame(self)
        mask_row.pack(fill="x", padx=20, pady=5)
        ttk.Label(mask_row, text="mask.png:", width=12).pack(side="left")
        self.mask_picker = FilePickerWidget(
            mask_row, theme_path=self.theme_path,
            relative_folder=f"icon_overlays/{self.console_name}",
            allowed_extensions=[".png"],
            width=20
        )
        self.mask_picker.pack(side="left", fill="x", expand=True)
        
        preview_row = ttk.Frame(self)
        preview_row.pack(pady=10)
        self.preview_label = tk.Label(preview_row, text="(preview will appear here)")
        self.preview_label.pack()
        
        btn_row = ttk.Frame(self)
        btn_row.pack(pady=10)
        ttk.Button(btn_row, text="OK", command=self.destroy, width=10).pack(side="left", padx=5)
    
    def _load_existing(self):
        overlay_path = self.folder / "overlay.png"
        mask_path = self.folder / "mask.png"
        
        if overlay_path.exists():
            self.overlay_picker.set_value("overlay.png")
        if mask_path.exists():
            self.mask_picker.set_value("mask.png")
        
        self._update_preview()
    
    def _update_preview(self):
        overlay_val = self.overlay_picker.get_value()
        mask_val = self.mask_picker.get_value()
        
        if overlay_val and mask_val:
            overlay_file = self.theme_path / "icon_overlays" / self.console_name / overlay_val
            mask_file = self.theme_path / "icon_overlays" / self.console_name / mask_val
            
            if overlay_file.exists() and mask_file.exists():
                try:
                    overlay_img = Image.open(overlay_file).convert("RGBA")
                    mask_img = Image.open(mask_file).convert("RGBA")
                    
                    overlay_img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                    mask_img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                    
                    preview = ImageTk.PhotoImage(overlay_img)
                    self.preview_label.configure(image=preview, text="")
                    self.preview_label.image = preview
                    return
                except:
                    pass
        
        self.preview_label.configure(image="", text="(preview will appear here)")


class SmartFolderEditor(ttk.Frame):
    def __init__(self, parent, asset_panel, mode="root"):
        super().__init__(parent)
        self.asset_panel = asset_panel
        self.renderer = asset_panel.renderer
        self.theme_path = asset_panel.theme_path
        self.mode = mode
        self._toggle_funcs = []
        
        self._create_ui()
        self.refresh()
    
    def _toggle_all_folders(self):
        """Toggle all folders: collapse if any are open, otherwise expand all."""
        if not self._toggle_funcs:
            return
        
        for toggle_func in self._toggle_funcs:
            toggle_func()
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        self.grid_propagate(False)
        
        if self.mode == "root":
            frame_label = "Root Folders"
            add_label = "Add Folder"
        else:
            frame_label = "By Platform"
            add_label = "Add Folder"
        
        main_frame = ttk.LabelFrame(self, text=frame_label, padding=5)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=(0, 5))
        
        self.add_btn = ttk.Button(toolbar, text=f"+ {add_label}", command=self._add_folder)
        self.add_btn.pack(side="left")
        
        self.collapse_all_btn = ttk.Button(toolbar, text="Collapse All", command=self._toggle_all_folders)
        self.collapse_all_btn.pack(side="left", padx=(5, 0))
        
        scroll = ScrollFrame(main_frame)
        scroll.pack(fill="both", expand=True)
        self.folder_container = scroll.interior
        self.folder_container.columnconfigure(0, weight=1)
    
    def _get_base_path(self):
        if not self.theme_path:
            return Path("")
        return self.theme_path / "smart_folders"
    
    def _get_folders(self):
        """Get folders from cached data in asset panel."""
        if self.mode == "root":
            return getattr(self.asset_panel, '_smart_folders', [])
        else:
            by_platform = getattr(self.asset_panel, '_smart_folders_by_platform', {})
            result = []
            for folder_name, data in by_platform.items():
                result.append({
                    "name": folder_name,
                    "path": data.get("path"),
                    "icon": data.get("icon"),
                    "hero": data.get("hero"),
                    "logo": data.get("logo"),
                })
            return result
    
    def _get_folders_from_disk(self):
        """Scan disk for folders (used for adding new folders)."""
        if not self.theme_path:
            return []
        base = self._get_base_path()
        if not base.exists():
            return []
        
        if self.mode == "root":
            folders = [f for f in base.iterdir() if f.is_dir() and f.name != "by_platform"]
        else:
            by_platform = base / "by_platform"
            folders = []
            if by_platform.exists():
                for folder in by_platform.iterdir():
                    if folder.is_dir():
                        folders.append(folder)
        
        return sorted(folders, key=lambda x: x.name.lower())
    
    def _add_folder(self):
        dialog = SmartFolderDialog(self.winfo_toplevel(), self.mode, self.theme_path)
        self.wait_window(dialog)
        self.asset_panel._refresh(force_rescan=True)
    
    def _edit_folder(self, folder_path):
        dialog = SmartFolderDialog(self.winfo_toplevel(), self.mode, self.theme_path, folder_path)
        self.wait_window(dialog)
        self.asset_panel._refresh(force_rescan=True)
    
    def _delete_folder(self, folder_path):
        name = folder_path.name
        if messagebox.askyesno("Delete Folder", f"Delete folder '{name}' and all contents?"):
            shutil.rmtree(folder_path)
        self.asset_panel._refresh(force_rescan=True)
    
    def _add_platform_override(self, parent_folder):
        console = self._select_console()
        if not console:
            return
        
        folder = parent_folder / console
        folder.mkdir(parents=True, exist_ok=True)
        
        dialog = SmartFolderDialog(self.winfo_toplevel(), "platform_override", self.theme_path, folder, parent_folder.name)
        self.wait_window(dialog)
        self.asset_panel._refresh(force_rescan=True)
    
    def _select_console(self):
        dialog = tk.Toplevel(self.winfo_toplevel())
        dialog.title("Select Console")
        dialog.geometry("300x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        result = {"value": None}
        
        scroll = ScrollFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        container = scroll.interior
        container.columnconfigure(0, weight=1)
        
        system_lists_dir = Path(__file__).parent.parent / "assets" / "system_lists"
        consoles = []
        if system_lists_dir.exists():
            for f in system_lists_dir.glob("*.txt"):
                with open(f, 'r') as file:
                    for line in file:
                        name = line.strip()
                        if name and name not in consoles:
                            consoles.append(name)
        
        consoles.sort()
        
        def select(name):
            result["value"] = name
            dialog.destroy()
        
        for console in consoles:
            ttk.Button(container, text=console, command=lambda n=console: select(n)).pack(fill="x", pady=1)
        
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)
        
        self.wait_window(dialog)
        return result["value"]
    
    def refresh(self):
        self.theme_path = self.asset_panel.theme_path
        self._toggle_funcs = []
        for widget in self.folder_container.winfo_children():
            widget.destroy()
        
        folders = self._get_folders()
        
        if not folders:
            ttk.Label(self.folder_container, text="(no folders)", foreground="#666666").pack(pady=10)
            return
        
        for folder in folders:
            self._create_folder_row(folder)
        
        # Force scrollregion update for ScrollFrame
        self.folder_container.update_idletasks()
        parent = self.folder_container.master
        if hasattr(parent, 'update_scrollregion'):
            parent.update_scrollregion()
    
    def _load_thumbnail(self, path, label, size, frame=None):
        """Load and display thumbnail preview on label."""
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label.configure(image=photo, text="")
            label.image = photo
            if frame:
                frame.configure(width=size, height=size)
        except Exception:
            label.configure(image="", text="!")
            if frame:
                frame.configure(width=size, height=size)
    
    def _create_folder_row(self, folder_data):
        """Create a row for a smart folder.
        
        folder_data can be:
        - dict with name, path, icon, hero, logo (root folders)
        - dict with name, platforms (by_platform folders)
        """
        if self.mode == "root":
            self._create_root_folder_row(folder_data)
        else:
            self._create_platform_folder_row(folder_data)
    
    def _create_root_folder_row(self, folder_data):
        folder_name = folder_data.get("name", "unknown")
        folder_path = folder_data.get("path")
        
        frame = ttk.LabelFrame(self.folder_container, text="", padding=5)
        frame.pack(fill="x", padx=5, pady=3)
        
        header = ttk.Frame(frame)
        header.pack(fill="x", padx=2, pady=(0, 2))
        
        expanded = tk.BooleanVar(value=True)
        
        collapsed_frame = ttk.Frame(frame)
        
        expanded_frame = ttk.Frame(frame)
        expanded_frame.pack(fill="x", pady=2)
        
        def toggle():
            if expanded.get():
                expanded_frame.pack_forget()
                collapsed_frame.pack(fill="x", pady=2)
                toggle_btn.config(text="▶")
                expanded.set(False)
            else:
                collapsed_frame.pack_forget()
                expanded_frame.pack(fill="x", pady=2)
                toggle_btn.config(text="▼")
                expanded.set(True)
        
        self._toggle_funcs.append(toggle)
        
        toggle_btn = ttk.Label(header, text="▼", width=2, cursor="hand2")
        toggle_btn.pack(side="left")
        toggle_btn.bind("<Button-1>", lambda e: toggle())
        
        ttk.Label(header, text=folder_name, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(5, 0))
        
        folder_path_for_btn = folder_path if folder_path else (self.theme_path / "smart_folders" / folder_name)
        ttk.Button(header, text="X", width=2, command=lambda: self._delete_folder(folder_path_for_btn)).pack(side="right")
        
        preview_size = 48
        
        icon_data = folder_data.get("icon")
        
        collapsed_preview_frame = ttk.Frame(collapsed_frame, width=preview_size, height=preview_size)
        collapsed_preview_frame.pack(side="left", padx=(0, 5))
        collapsed_preview_frame.propagate(False)
        
        collapsed_preview_label = ttk.Label(collapsed_preview_frame, text="icon", anchor="center")
        collapsed_preview_label.pack(fill="both", expand=True)
        
        if icon_data and icon_data.exists():
            self._load_thumbnail(icon_data, collapsed_preview_label, preview_size, collapsed_preview_frame)
        else:
            collapsed_preview_frame.configure(width=preview_size, height=preview_size)
        
        asset_frame = ttk.Frame(expanded_frame)
        asset_frame.pack(fill="x", pady=2)
        
        preview_frame = ttk.Frame(asset_frame, width=preview_size, height=preview_size)
        preview_frame.pack(side="left", padx=(0, 5))
        preview_frame.propagate(False)
        
        preview_label = ttk.Label(preview_frame, text="icon", anchor="center")
        preview_label.pack(fill="both", expand=True)
        
        if icon_data and icon_data.exists():
            self._load_thumbnail(icon_data, preview_label, preview_size, preview_frame)
        else:
            preview_frame.configure(width=preview_size, height=preview_size)
        
        picker = FilePickerWidget(
            asset_frame,
            theme_path=self.theme_path,
            relative_folder=f"smart_folders/{folder_name}",
            allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
            width=10
        )
        if icon_data and icon_data.exists():
            picker.set_value("icon.png")
        picker.pack(side="left", fill="x", expand=True)
        
        hero_data = folder_data.get("hero")
        
        hero_frame = ttk.Frame(expanded_frame)
        hero_frame.pack(fill="x", pady=2)
        
        hero_preview_frame = ttk.Frame(hero_frame, width=preview_size, height=preview_size)
        hero_preview_frame.pack(side="left", padx=(0, 5))
        hero_preview_frame.propagate(False)
        
        hero_preview_label = ttk.Label(hero_preview_frame, text="hero", anchor="center")
        hero_preview_label.pack(fill="both", expand=True)
        
        if hero_data and hero_data.exists():
            self._load_thumbnail(hero_data, hero_preview_label, preview_size, hero_preview_frame)
        else:
            hero_preview_frame.configure(width=preview_size, height=preview_size)
        
        hero_picker = FilePickerWidget(
            hero_frame,
            theme_path=self.theme_path,
            relative_folder=f"smart_folders/{folder_name}",
            allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
            width=10
        )
        if hero_data and hero_data.exists():
            hero_picker.set_value("hero.png")
        hero_picker.pack(side="left", fill="x", expand=True)
        
        logo_data = folder_data.get("logo")
        
        logo_frame = ttk.Frame(expanded_frame)
        logo_frame.pack(fill="x", pady=2)
        
        logo_preview_frame = ttk.Frame(logo_frame, width=preview_size, height=preview_size)
        logo_preview_frame.pack(side="left", padx=(0, 5))
        logo_preview_frame.propagate(False)
        
        logo_preview_label = ttk.Label(logo_preview_frame, text="logo", anchor="center")
        logo_preview_label.pack(fill="both", expand=True)
        
        if logo_data and logo_data.exists():
            self._load_thumbnail(logo_data, logo_preview_label, preview_size, logo_preview_frame)
        else:
            logo_preview_frame.configure(width=preview_size, height=preview_size)
        
        logo_picker = FilePickerWidget(
            logo_frame,
            theme_path=self.theme_path,
            relative_folder=f"smart_folders/{folder_name}",
            allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
            width=10
        )
        if logo_data and logo_data.exists():
            logo_picker.set_value("logo.png")
        logo_picker.pack(side="left", fill="x", expand=True)
    
    def _create_platform_folder_row(self, folder_data):
        folder_name = folder_data.get("name", "unknown")
        folder_path = folder_data.get("path")
        
        frame = ttk.LabelFrame(self.folder_container, text="", padding=5)
        frame.pack(fill="x", padx=5, pady=3)
        
        header = ttk.Frame(frame)
        header.pack(fill="x", padx=2, pady=(0, 2))
        
        expanded = tk.BooleanVar(value=True)
        
        collapsed_frame = ttk.Frame(frame)
        
        expanded_frame = ttk.Frame(frame)
        expanded_frame.pack(fill="x", pady=2)
        
        def toggle():
            if expanded.get():
                expanded_frame.pack_forget()
                collapsed_frame.pack(fill="x", pady=2)
                toggle_btn.config(text="▶")
                expanded.set(False)
            else:
                collapsed_frame.pack_forget()
                expanded_frame.pack(fill="x", pady=2)
                toggle_btn.config(text="▼")
                expanded.set(True)
        
        self._toggle_funcs.append(toggle)
        
        toggle_btn = ttk.Label(header, text="▼", width=2, cursor="hand2")
        toggle_btn.pack(side="left")
        toggle_btn.bind("<Button-1>", lambda e: toggle())
        
        ttk.Label(header, text=folder_name, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(5, 0))
        
        folder_path_for_btn = folder_path if folder_path else (self.theme_path / "smart_folders" / "by_platform" / folder_name)
        ttk.Button(header, text="X", width=2, command=lambda: self._delete_folder(folder_path_for_btn)).pack(side="right")
        
        preview_size = 48
        
        icon_data = folder_data.get("icon")
        
        collapsed_preview_frame = ttk.Frame(collapsed_frame, width=preview_size, height=preview_size)
        collapsed_preview_frame.pack(side="left", padx=(0, 5))
        collapsed_preview_frame.propagate(False)
        
        collapsed_preview_label = ttk.Label(collapsed_preview_frame, text="icon", anchor="center")
        collapsed_preview_label.pack(fill="both", expand=True)
        
        if icon_data and icon_data.exists():
            self._load_thumbnail(icon_data, collapsed_preview_label, preview_size, collapsed_preview_frame)
        else:
            collapsed_preview_frame.configure(width=preview_size, height=preview_size)
        
        asset_frame = ttk.Frame(expanded_frame)
        asset_frame.pack(fill="x", pady=2)
        
        preview_frame = ttk.Frame(asset_frame, width=preview_size, height=preview_size)
        preview_frame.pack(side="left", padx=(0, 5))
        preview_frame.propagate(False)
        
        preview_label = ttk.Label(preview_frame, text="icon", anchor="center")
        preview_label.pack(fill="both", expand=True)
        
        if icon_data and icon_data.exists():
            self._load_thumbnail(icon_data, preview_label, preview_size, preview_frame)
        else:
            preview_frame.configure(width=preview_size, height=preview_size)
        
        picker = FilePickerWidget(
            asset_frame,
            theme_path=self.theme_path,
            relative_folder=f"smart_folders/by_platform/{folder_name}",
            allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
            width=10
        )
        if icon_data and icon_data.exists():
            picker.set_value("icon.png")
        picker.pack(side="left", fill="x", expand=True)
        
        hero_data = folder_data.get("hero")
        
        hero_frame = ttk.Frame(expanded_frame)
        hero_frame.pack(fill="x", pady=2)
        
        hero_preview_frame = ttk.Frame(hero_frame, width=preview_size, height=preview_size)
        hero_preview_frame.pack(side="left", padx=(0, 5))
        hero_preview_frame.propagate(False)
        
        hero_preview_label = ttk.Label(hero_preview_frame, text="hero", anchor="center")
        hero_preview_label.pack(fill="both", expand=True)
        
        if hero_data and hero_data.exists():
            self._load_thumbnail(hero_data, hero_preview_label, preview_size, hero_preview_frame)
        else:
            hero_preview_frame.configure(width=preview_size, height=preview_size)
        
        hero_picker = FilePickerWidget(
            hero_frame,
            theme_path=self.theme_path,
            relative_folder=f"smart_folders/by_platform/{folder_name}",
            allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
            width=10
        )
        if hero_data and hero_data.exists():
            hero_picker.set_value("hero.png")
        hero_picker.pack(side="left", fill="x", expand=True)
        
        logo_data = folder_data.get("logo")
        
        logo_frame = ttk.Frame(expanded_frame)
        logo_frame.pack(fill="x", pady=2)
        
        logo_preview_frame = ttk.Frame(logo_frame, width=preview_size, height=preview_size)
        logo_preview_frame.pack(side="left", padx=(0, 5))
        logo_preview_frame.propagate(False)
        
        logo_preview_label = ttk.Label(logo_preview_frame, text="logo", anchor="center")
        logo_preview_label.pack(fill="both", expand=True)
        
        if logo_data and logo_data.exists():
            self._load_thumbnail(logo_data, logo_preview_label, preview_size, logo_preview_frame)
        else:
            logo_preview_frame.configure(width=preview_size, height=preview_size)
        
        logo_picker = FilePickerWidget(
            logo_frame,
            theme_path=self.theme_path,
            relative_folder=f"smart_folders/by_platform/{folder_name}",
            allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
            width=10
        )
        if logo_data and logo_data.exists():
            logo_picker.set_value("logo.png")
        logo_picker.pack(side="left", fill="x", expand=True)


class SmartFolderDialog(tk.Toplevel):
    def __init__(self, parent, mode, theme_path, folder_path=None, parent_name=None):
        super().__init__(parent)
        self.withdraw()
        self.mode = mode
        self.theme_path = theme_path
        self.folder_path = folder_path
        self.parent_name = parent_name
        self.new_folder_name = None
        
        if mode == "by_platform":
            icon_name = "favicon_by_platform.png"
            title = "Add By Platform"
        else:
            icon_name = "favicon_smart_folder.png"
            title = "Add Smart Folder"
        
        icon_path = Path(__file__).parent.parent / "assets" / icon_name
        if icon_path.exists():
            icon_img = PhotoImage(file=icon_path)
            self.iconphoto(False, icon_img)
        
        if folder_path:
            self.title(f"Edit Smart Folder: {folder_path.name}")
            self.geometry("450x280")
        else:
            self.title(title)
            self.geometry("220x90")
        
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        
        center_to_parent(self, parent)
        self.deiconify()
        
        if not self.folder_path:
            self.after(10, lambda: self.name_entry.focus())
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        
        if not self.folder_path:
            self.name_var = tk.StringVar()
            self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=25)
            self.name_entry.pack(pady=(15, 8))
            
            btn_row = ttk.Frame(self)
            btn_row.pack(pady=8)
            ttk.Button(btn_row, text="OK", width=6, command=self._on_create).pack(side="left", padx=3)
            ttk.Button(btn_row, text="Cancel", width=6, command=self.destroy).pack(side="left", padx=3)
            
            self.name_entry.bind("<Return>", lambda e: self._on_create())
            self.name_entry.bind("<Escape>", lambda e: self.destroy())
        else:
            ttk.Label(self, text=f"Folder: {self.folder_path.name}", font=("Segoe UI", 10, "bold")).pack(pady=10)
            
            assets = ["icon.png", "hero.png", "logo.png"]
            
            for asset_name in assets:
                row = ttk.Frame(self)
                row.pack(fill="x", padx=20, pady=3)
                ttk.Label(row, text=f"{asset_name}:", width=10).pack(side="left")
                
                if self.mode == "platform_override":
                    rel_folder = f"smart_folders/by_platform/{self.parent_name}/{self.folder_path.name}"
                else:
                    rel_folder = f"smart_folders/{self.folder_path.name}"
                
                picker = FilePickerWidget(
                    row, theme_path=self.theme_path,
                    relative_folder=rel_folder,
                    allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
                    width=25
                )
                
                if (self.folder_path / asset_name).exists():
                    picker.set_value(asset_name)
                
                picker.pack(side="left", fill="x", expand=True)
            
            ttk.Button(self, text="Done", command=self.destroy, width=10).pack(pady=15)
    
    def _on_create(self):
        name = self.name_var.get().strip()
        if not name:
            return
        
        self.new_folder_name = name
        
        if self.mode == "root":
            base = self.theme_path / "smart_folders"
        elif self.mode == "by_platform":
            base = self.theme_path / "smart_folders" / "by_platform"
        else:
            base = self.theme_path / "smart_folders"
        
        base.mkdir(parents=True, exist_ok=True)
        self.folder_path = base / name
        self.folder_path.mkdir(parents=True, exist_ok=True)
        
        self.destroy()
        
        dialog = SmartFolderDialog(self.winfo_toplevel(), self.mode, self.theme_path, self.folder_path)
        self.wait_window(dialog)


class ScrollFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = ttk.Frame(self.canvas)
        
        self.canvas.create_window(0, 0, window=self.interior, anchor="nw")
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.interior.bind("<Configure>", self._on_interior_configure)
    
    def _on_interior_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def update_scrollregion(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
