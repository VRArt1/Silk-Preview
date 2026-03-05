class UIState:
    def __init__(self):
        self.theme_path = None
        self.selected_type = None     # None | "platform" | "smart_folder"
        self.selected_id = None
        self.grid_mode = "mid"
        self.focus_screen = "both"    # both | top | bottom