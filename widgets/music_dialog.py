import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk

from widgets.utils import center_to_parent


class MusicDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.withdraw()
        self.app = app
        self.title("Music")
        self.geometry("350x400")
        self.resizable(False, False)
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / "assets" / "favicon_music.png"
        if icon_path.exists():
            try:
                icon_img = Image.open(icon_path)
                if icon_img.mode != 'RGBA':
                    icon_img = icon_img.convert('RGBA')
                self._music_icon = ImageTk.PhotoImage(icon_img)
                self.iconphoto(False, self._music_icon)
            except Exception:
                pass
        
        self.transient(parent)
        
        self._create_widgets()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start update timer
        self._update_timer = None
        self._start_update_timer()
        
        center_to_parent(self, parent)
        self.deiconify()
    
    def _start_update_timer(self):
        """Periodically update UI to show current track."""
        if hasattr(self.app.renderer, 'music_manager'):
            # Just update the UI (track name, status) - don't call update() as app handles that
            self.update_from_app()
        self._update_timer = self.after(500, self._start_update_timer)
    
    def _on_close(self):
        """Clean up timer when closing."""
        if self._update_timer:
            self.after_cancel(self._update_timer)
            self._update_timer = None
        self.destroy()
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Not Playing", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=(0, 5))
        
        # Current track name label
        self.track_name_label = ttk.Label(main_frame, text="", font=("Arial", 9), foreground="gray")
        self.track_name_label.pack(pady=(0, 15))
        
        # Control buttons frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(pady=10)
        
        # Previous button
        self.prev_button = ttk.Button(
            controls_frame,
            text="⏮",
            width=5,
            command=self._on_prev
        )
        self.prev_button.pack(side="left", padx=5)
        
        # Play/Pause button
        self.play_pause_button = ttk.Button(
            controls_frame,
            text="▶",
            width=8,
            command=self._on_play_pause
        )
        self.play_pause_button.pack(side="left", padx=5)
        
        # Next button
        self.next_button = ttk.Button(
            controls_frame,
            text="⏭",
            width=5,
            command=self._on_next
        )
        self.next_button.pack(side="left", padx=5)
        
        # Shuffle button
        self.shuffle_button = ttk.Button(
            main_frame,
            text="Shuffle: OFF",
            width=15,
            command=self._on_shuffle
        )
        self.shuffle_button.pack(pady=10)
        
        # Mode label
        self.mode_label = ttk.Label(main_frame, text="Mode: DISABLED", font=("Arial", 9))
        self.mode_label.pack(pady=(5, 0))
        
        # Volume controls section
        vol_sep = ttk.Separator(main_frame, orient="horizontal")
        vol_sep.pack(fill="x", pady=15)
        
        vol_label = ttk.Label(main_frame, text="Volume Settings", font=("Arial", 10, "bold"))
        vol_label.pack(pady=(0, 10))
        
        # Master Volume
        master_vol_frame = ttk.Frame(main_frame)
        master_vol_frame.pack(fill="x", pady=2)
        ttk.Label(master_vol_frame, text="Master:").pack(side="left")
        self.master_volume_var = tk.DoubleVar(value=getattr(self.app, 'master_volume', 1.0))
        master_slider = ttk.Scale(
            master_vol_frame,
            from_=0,
            to=1,
            variable=self.master_volume_var,
            orient="horizontal",
            command=self._on_master_volume_change
        )
        master_slider.pack(side="left", fill="x", expand=True, padx=(10, 5))
        self.master_volume_label = ttk.Label(master_vol_frame, text=f"{int(self.master_volume_var.get() * 100)}%")
        self.master_volume_label.pack(side="left", padx=(5, 0))
        
        # SFX Volume
        sfx_vol_frame = ttk.Frame(main_frame)
        sfx_vol_frame.pack(fill="x", pady=2)
        ttk.Label(sfx_vol_frame, text="SFX:").pack(side="left")
        self.sfx_volume_var = tk.DoubleVar(value=getattr(self.app, 'sfx_volume', 1.0))
        sfx_slider = ttk.Scale(
            sfx_vol_frame,
            from_=0,
            to=1,
            variable=self.sfx_volume_var,
            orient="horizontal",
            command=self._on_sfx_volume_change
        )
        sfx_slider.pack(side="left", fill="x", expand=True, padx=(10, 5))
        self.sfx_volume_label = ttk.Label(sfx_vol_frame, text=f"{int(self.sfx_volume_var.get() * 100)}%")
        self.sfx_volume_label.pack(side="left", padx=(5, 0))
        
        # Music Volume
        music_vol_frame = ttk.Frame(main_frame)
        music_vol_frame.pack(fill="x", pady=2)
        ttk.Label(music_vol_frame, text="Music:").pack(side="left")
        self.music_volume_var = tk.DoubleVar(value=getattr(self.app, 'music_volume', 1.0))
        music_slider = ttk.Scale(
            music_vol_frame,
            from_=0,
            to=1,
            variable=self.music_volume_var,
            orient="horizontal",
            command=self._on_music_volume_change
        )
        music_slider.pack(side="left", fill="x", expand=True, padx=(10, 5))
        self.music_volume_label = ttk.Label(music_vol_frame, text=f"{int(self.music_volume_var.get() * 100)}%")
        self.music_volume_label.pack(side="left", padx=(5, 0))
    
    def _on_master_volume_change(self, value):
        val = float(value)
        self.app.master_volume = val
        if hasattr(self.app.renderer, 'sound_manager'):
            self.app.renderer.sound_manager.set_master_volume(val)
        self.master_volume_label.config(text=f"{int(val * 100)}%")
        self.app.save_settings()
    
    def _on_sfx_volume_change(self, value):
        val = float(value)
        self.app.sfx_volume = val
        if hasattr(self.app.renderer, 'sound_manager'):
            self.app.renderer.sound_manager.set_sfx_volume(val)
        self.sfx_volume_label.config(text=f"{int(val * 100)}%")
        self.app.save_settings()
    
    def _on_music_volume_change(self, value):
        val = float(value)
        self.app.music_volume = val
        if hasattr(self.app.renderer, 'sound_manager'):
            self.app.renderer.sound_manager.set_music_volume(val)
        self.music_volume_label.config(text=f"{int(val * 100)}%")
        self.app.save_settings()
    
    def _on_play_pause(self):
        if hasattr(self.app.renderer, 'music_manager'):
            mm = self.app.renderer.music_manager
            if mm.is_playing:
                mm.pause()
            else:
                mm.play()
            self.update_from_app()
    
    def _on_next(self):
        if hasattr(self.app.renderer, 'music_manager'):
            self.app.renderer.music_manager.next_track()
    
    def _on_prev(self):
        if hasattr(self.app.renderer, 'music_manager'):
            self.app.renderer.music_manager.previous_track()
    
    def _on_shuffle(self):
        if hasattr(self.app.renderer, 'music_manager'):
            mm = self.app.renderer.music_manager
            mm.toggle_shuffle()
            self.update_from_app()
    
    def update_from_app(self):
        if not hasattr(self.app.renderer, 'music_manager'):
            return
        
        mm = self.app.renderer.music_manager
        
        # Update status - show Playing if we have a track name even if briefly between tracks
        if mm.mode == "DISABLED":
            self.status_label.config(text="Disabled")
            self.play_pause_button.config(text="▶")
            self.track_name_label.config(text="")
        elif mm.is_paused:
            self.status_label.config(text="Paused")
            self.play_pause_button.config(text="▶")
        elif mm.is_playing or mm.current_track_name:
            # Show Playing if music is playing OR if we have a track (even during brief transition)
            self.status_label.config(text="Playing")
            self.play_pause_button.config(text="⏸")
        else:
            self.status_label.config(text="Stopped")
            self.play_pause_button.config(text="▶")
        
        # Update track name
        track_name = mm.current_track_name
        if track_name:
            self.track_name_label.config(text=track_name)
        else:
            self.track_name_label.config(text="")
        
        # Update shuffle
        if mm.is_shuffle:
            self.shuffle_button.config(text="Shuffle: ON")
        else:
            self.shuffle_button.config(text="Shuffle: OFF")
        
        # Update mode
        self.mode_label.config(text=f"Mode: {mm.mode}")
        
        # Update volume sliders
        if hasattr(self, 'master_volume_var'):
            self.master_volume_var.set(getattr(self.app, 'master_volume', 1.0))
            self.master_volume_label.config(text=f"{int(self.master_volume_var.get() * 100)}%")
        
        if hasattr(self, 'sfx_volume_var'):
            self.sfx_volume_var.set(getattr(self.app, 'sfx_volume', 1.0))
            self.sfx_volume_label.config(text=f"{int(self.sfx_volume_var.get() * 100)}%")
        
        if hasattr(self, 'music_volume_var'):
            self.music_volume_var.set(getattr(self.app, 'music_volume', 1.0))
            self.music_volume_label.config(text=f"{int(self.music_volume_var.get() * 100)}%")
