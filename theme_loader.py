import json
from pathlib import Path
from config import PLACEHOLDER_THEME_PATH

class Theme:
    def __init__(self, path):
        self.path = Path(path)
        self.json_path = self.path / "theme.json"
        self.data = self._load_json()

    def _load_json(self):
        if self.json_path.exists():
            try:
                return json.loads(self.json_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # fallback to placeholder
        placeholder = PLACEHOLDER_THEME_PATH / "theme.json"
        if placeholder.exists():
            return json.loads(placeholder.read_text(encoding="utf-8"))

        return {}

    @property
    def name(self):
        return self.data.get("name", "Unknown Theme")

    @property
    def author(self):
        return self.data.get("author", "Unknown")

    @property
    def version(self):
        return self.data.get("version", "N/A")

    @property
    def description(self):
        return self.data.get("description", "")