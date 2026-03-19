import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path


class PlaylistEditor(ttk.Frame):
    """
    Playlist editor with add/remove/reorder functionality.
    Saves as: "music/track1.mp3||music/track2.mp3"
    """
    def __init__(self, parent, theme_path=None, music_folder="music", on_change=None):
        super().__init__(parent)
        
        self.theme_path = theme_path
        self.music_folder = music_folder
        self.on_change = on_change
        self.tracks = []
        
        self._create_ui()
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        
        list_frame = ttk.Frame(self)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(list_frame, height=150, highlightthickness=1)
        self.scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        self.tracks_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.tracks_frame, anchor="nw")
        
        self.tracks_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        ttk.Button(button_frame, text="+ Add Track", command=self._add_track).pack(side="left")
        
        self.rowconfigure(0, weight=1)
    
    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _add_track(self, path=None):
        track_num = len(self.tracks)
        
        track_frame = ttk.Frame(self.tracks_frame)
        track_frame.pack(fill="x", pady=2)
        # Use grid with column weights: up(0), down(0), entry(1), browse(0), x(0)
        track_frame.columnconfigure(0, minsize=0)
        track_frame.columnconfigure(1, minsize=0)
        track_frame.columnconfigure(2, weight=1)
        track_frame.columnconfigure(3, minsize=0)
        track_frame.columnconfigure(4, minsize=0)
        
        up_btn = ttk.Button(track_frame, text="↑", width=3, command=lambda: self._move_track(track_num, -1))
        up_btn.grid(row=0, column=0, sticky="w")
        
        down_btn = ttk.Button(track_frame, text="↓", width=3, command=lambda: self._move_track(track_num, 1))
        down_btn.grid(row=0, column=1, sticky="w", padx=(2, 5))
        
        path_var = tk.StringVar(value=path or "")
        entry = ttk.Entry(track_frame, textvariable=path_var)
        entry.grid(row=0, column=2, sticky="ew", padx=(0, 2))
        
        browse_btn = ttk.Button(track_frame, text="Browse", command=lambda: self._browse_track(path_var), width=8)
        browse_btn.grid(row=0, column=3, sticky="e", padx=(0, 2))
        
        remove_btn = ttk.Button(track_frame, text="X", width=3, command=lambda: self._remove_track(track_frame, track_num))
        remove_btn.grid(row=0, column=4, sticky="e")
        
        track_data = {
            "frame": track_frame,
            "path_var": path_var,
            "entry": entry,
            "up_btn": up_btn,
            "down_btn": down_btn,
            "browse_btn": browse_btn,
            "remove_btn": remove_btn,
            "path": path or ""
        }
        
        self.tracks.append(track_data)
        
        path_var.trace_add("write", lambda *args: self._on_track_change())
    
    def _browse_track(self, path_var):
        if not self.theme_path:
            return
        
        search_dir = self.theme_path / self.music_folder
        if not search_dir.exists():
            search_dir = self.theme_path
        
        filename = filedialog.askopenfilename(
            initialdir=str(search_dir),
            filetypes=[
                ("Audio files", "*.mp3 *.ogg *.wav *.flac *.m4a"),
                ("All files", "*.*")
            ],
            title="Select music track"
        )
        
        if filename:
            path = Path(filename)
            try:
                rel_path = path.relative_to(self.theme_path)
                path_var.set(str(rel_path))
            except ValueError:
                path_var.set(path.name)
    
    def _remove_track(self, track_frame, index):
        track_frame.destroy()
        self.tracks = [t for t in self.tracks if t["frame"] != track_frame]
        self._refresh_track_numbers()
        self._on_track_change()
    
    def _move_track(self, index, direction):
        new_index = index + direction
        if 0 <= new_index < len(self.tracks):
            track_a = self.tracks[index]
            track_b = self.tracks[new_index]
            
            path_a = track_a["path_var"].get()
            path_b = track_b["path_var"].get()
            
            track_a["path_var"].set(path_b)
            track_b["path_var"].set(path_a)
    
    def _refresh_track_numbers(self):
        for i, track in enumerate(self.tracks):
            track["up_btn"].config(command=lambda idx=i: self._move_track(idx, -1))
            track["down_btn"].config(command=lambda idx=i: self._move_track(idx, 1))
            track["browse_btn"].config(command=lambda pv=track["path_var"]: self._browse_track(pv))
            track["remove_btn"].config(command=lambda f=track["frame"], idx=i: self._remove_track(f, idx))
    
    def _on_track_change(self):
        for i, track in enumerate(self.tracks):
            track["path"] = track["path_var"].get()
        
        if self.on_change:
            self.on_change(self.get_value())
    
    def get_value(self):
        """Get playlist as pipe-delimited string."""
        paths = [t["path"] for t in self.tracks if t["path"]]
        if not paths:
            return None
        return "||".join(paths)
    
    def set_value(self, value):
        """Set playlist from pipe-delimited string."""
        for track in self.tracks:
            track["frame"].destroy()
        self.tracks = []
        
        if value:
            paths = value.split("||")
            for path in paths:
                if path:
                    self._add_track(path)
        
        if not self.tracks:
            self._add_track()
    
    def set_theme_path(self, path):
        self.theme_path = path


class TimeScheduleEditor(ttk.Frame):
    """
    Time schedule editor with visual time blocks.
    Saves as: "0:0|music/night.mp3||6:0|music/morning.mp3||18:0|music/evening.mp3"
    """
    def __init__(self, parent, theme_path=None, music_folder="music", on_change=None):
        super().__init__(parent)
        
        self.theme_path = theme_path
        self.music_folder = music_folder
        self.on_change = on_change
        self.blocks = []
        
        self._create_ui()
    
    def _create_ui(self):
        self.columnconfigure(0, weight=1)
        
        list_frame = ttk.Frame(self)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(1, weight=1)
        
        headers = ttk.Frame(list_frame)
        headers.grid(row=0, column=0, columnspan=3, sticky="ew")
        
        self.canvas = tk.Canvas(list_frame, height=150, highlightthickness=1)
        self.scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.grid(row=1, column=2, sticky="ns")
        self.canvas.grid(row=1, column=0, columnspan=2, sticky="nsew")
        
        self.blocks_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.blocks_frame, anchor="nw")
        
        self.blocks_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        ttk.Button(button_frame, text="+ Add Track", command=self._add_block).pack(side="left")
        
        self.rowconfigure(0, weight=1)
    
    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _add_block(self, start_hour=0, start_min=0, path=""):
        block_num = len(self.blocks)
        
        block_frame = ttk.Frame(self.blocks_frame)
        block_frame.pack(fill="x", pady=2)
        # Use grid with column weights: time(0), entry(1), browse(0), x(0)
        block_frame.columnconfigure(0, minsize=0)
        block_frame.columnconfigure(1, weight=1)
        block_frame.columnconfigure(2, minsize=0)
        block_frame.columnconfigure(3, minsize=0)
        
        start_hour_var = tk.IntVar(value=start_hour)
        start_min_var = tk.IntVar(value=start_min)
        path_var = tk.StringVar(value=path)
        
        time_frame = ttk.Frame(block_frame)
        time_frame.grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        hour_spin = ttk.Spinbox(time_frame, from_=0, to=23, width=3, textvariable=start_hour_var)
        hour_spin.pack(side="left")
        ttk.Label(time_frame, text=":").pack(side="left")
        min_spin = ttk.Spinbox(time_frame, from_=0, to=59, width=3, textvariable=start_min_var)
        min_spin.pack(side="left")
        
        entry = ttk.Entry(block_frame, textvariable=path_var)
        entry.grid(row=0, column=1, sticky="ew", padx=(0, 2))
        
        browse_btn = ttk.Button(block_frame, text="Browse", command=lambda: self._browse_file(path_var), width=8)
        browse_btn.grid(row=0, column=2, sticky="e", padx=(0, 2))
        
        remove_btn = ttk.Button(block_frame, text="X", width=3, command=lambda: self._remove_block(block_frame, block_num))
        remove_btn.grid(row=0, column=3, sticky="e")
        
        block_data = {
            "frame": block_frame,
            "start_hour": start_hour_var,
            "start_min": start_min_var,
            "path_var": path_var,
            "path": path
        }
        
        self.blocks.append(block_data)
        
        for var in [start_hour_var, start_min_var]:
            var.trace_add("write", lambda *args: self._on_block_change())
        path_var.trace_add("write", lambda *args: self._on_block_change())
        
        self._refresh_block_numbers()
    
    def _browse_file(self, path_var):
        if not self.theme_path:
            return
        
        search_dir = self.theme_path / self.music_folder
        if not search_dir.exists():
            search_dir = self.theme_path
        
        filename = filedialog.askopenfilename(
            initialdir=str(search_dir),
            filetypes=[
                ("Audio files", "*.mp3 *.ogg *.wav *.flac *.m4a"),
                ("All files", "*.*")
            ],
            title="Select music track"
        )
        
        if filename:
            path = Path(filename)
            try:
                rel_path = path.relative_to(self.theme_path)
                path_var.set(str(rel_path))
            except ValueError:
                path_var.set(path.name)
    
    def _remove_block(self, block_frame, index):
        block_frame.destroy()
        self.blocks = [b for b in self.blocks if b["frame"] != block_frame]
        self._refresh_block_numbers()
        self._on_block_change()
    
    def _refresh_block_numbers(self):
        for i, block in enumerate(self.blocks):
            remove_btn = block["frame"].winfo_children()[-1]
            remove_btn.config(command=lambda f=block["frame"], idx=i: self._remove_block(f, idx))
    
    def _on_block_change(self):
        for block in self.blocks:
            block["path"] = block["path_var"].get()
        
        if self.on_change:
            self.on_change(self.get_value())
    
    def get_value(self):
        """Get schedule as pipe-delimited string."""
        parts = []
        for block in self.blocks:
            start = f"{block['start_hour'].get()}:{block['start_min'].get()}"
            path = block["path"]
            
            if path:
                parts.append(f"{start}|{path}")
        
        if not parts:
            return None
        return "||".join(parts)
    
    def set_value(self, value):
        """Set schedule from pipe-delimited string."""
        for block in self.blocks:
            block["frame"].destroy()
        self.blocks = []
        
        if value:
            entries = value.split("||")
            for entry in entries:
                if "|" in entry:
                    time_part, path = entry.split("|", 1)
                    if ":" in time_part:
                        parts = time_part.split(":")
                        if len(parts) >= 2:
                            start_hour = int(parts[0])
                            start_min = int(parts[1])
                        else:
                            start_hour = 0
                            start_min = 0
                    else:
                        start_hour = 0
                        start_min = 0
                    
                    self._add_block(start_hour, start_min, path)
        
        if not self.blocks:
            self._add_block()
    
    def set_theme_path(self, path):
        self.theme_path = path
