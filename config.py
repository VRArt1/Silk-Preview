from pathlib import Path

BASE_DIR = Path(__file__).parent

APP_NAME = "Cocoon Preview"

ASSETS_PATH = BASE_DIR / "assets"
PLACEHOLDER_THEME_PATH = BASE_DIR / "Placeholder Assets"

DEVICE_FRAME_PATH = ASSETS_PATH / "device_frame.png"
UI_IMAGE_PATH = ASSETS_PATH / "device_ui.png"
SELECTED_TILE_PATH = ASSETS_PATH / "selected.png"

# Bottom screen coordinates relative to frame
BOTTOM_SCREEN_RECT = (205, 540, 392, 340)  # x, y, width, height
BOTTOM_SCREEN_PADDING = 8
BOTTOM_SCREEN_UI_HEIGHT = 40

# Top screen coordinates (for future use if needed)
TOP_SCREEN_RECT = (41, 24, 718, 404)

# Native screen resolutions
TOP_SCREEN_RES = (1920, 1080)
BOTTOM_SCREEN_RES = (1240, 1080)

# Config file for auto-save
CONFIG_FILE = BASE_DIR / "settings.ini"



# Screen positions and sizes
TOP_SCREEN_POS = (41, 24)
TOP_SCREEN_SIZE = (718, 404)

BOTTOM_SCREEN_POS = (205, 540)
BOTTOM_SCREEN_SIZE = (392, 300)  # minus 40px reserved for grid

PREVIEW_SIZE = (150, 150)  # size for preview.png in preview panel