from config import PLACEHOLDER_THEME_PATH
from theme_loader import load_theme_json

class ThemeResolver:
    def __init__(self, theme_path):
        self.theme_path = theme_path
        self.placeholder_path = PLACEHOLDER_THEME_PATH

        self.theme_json = load_theme_json(theme_path)
        if self.theme_json is None:
            self.theme_json = load_theme_json(self.placeholder_path)

    def get_metadata(self):
        return {
            "name": self.theme_json.get("name", "—"),
            "author": self.theme_json.get("author", "—"),
            "version": self.theme_json.get("version", "—"),
            "description": self.theme_json.get("description", "—"),
        }