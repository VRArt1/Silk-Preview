import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk


class MusicDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Music")
        self.geometry("300x220")
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
