import tkinter as tk

class Toolbar(tk.Frame):
    def __init__(self, parent, refresh_callback):
        super().__init__(parent)
        tk.Button(self, text="Refresh", command=refresh_callback).pack(side="right")