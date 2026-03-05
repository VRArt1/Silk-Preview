def __init__(self, theme=None):
    self.theme = theme

    # Load device frame
    self.device_frame = Image.open(DEVICE_FRAME_PATH).convert("RGBA")

    # Load UI overlay
    ui_path = ASSETS_PATH / "device_ui.png"
    self.device_ui = Image.open(ui_path).convert("RGBA") if ui_path.exists() else None
    self.show_ui_layer = True

    # Grid settings
    self.grid_zoom = 4
    self.grid_rows = 3
    self.selected_tile = (0, 0)
    self.grid_tiles = []

    # Placeholder theme path MUST be set before loading placeholder tile
    self.placeholder_theme = PLACEHOLDER_THEME_PATH
    self.tile_placeholder = self._load_placeholder_tile()