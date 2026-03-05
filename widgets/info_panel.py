import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk

class InfoPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.preview_label = tk.Label(self)
        self.preview_label.pack(pady=5)

        self.meta_labels = {}
        for key in ("Name", "Author", "Version"):
            lbl = tk.Label(self, anchor="w")
            lbl.pack(fill="x")
            self.meta_labels[key.lower()] = lbl

        self.description = tk.Label(self, wraplength=280, justify="left")
        self.description.pack(pady=5)

        self.json_view = ScrolledText(self, height=15, state="disabled")
        self.json_view.pack(fill="both", expand=True)

        self.preview_image = None

    def update_info(self, resolver, preview_path):
        meta = resolver.get_metadata()

        self.meta_labels["name"].config(text=f"Name: {meta['name']}")
        self.meta_labels["author"].config(text=f"Author: {meta['author']}")
        self.meta_labels["version"].config(text=f"Version: {meta['version']}")
        self.description.config(text=meta["description"])

        if preview_path:
            img = Image.open(preview_path).resize((300, 170))
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.preview_image)
        else:
            self.preview_label.config(image="")

        self.json_view.config(state="normal")
        self.json_view.delete("1.0", "end")
        self.json_view.insert("end", resolver.theme_json)
        self.json_view.config(state="disabled")