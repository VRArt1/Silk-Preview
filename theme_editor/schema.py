"""
Theme.json Schema Definition
Based on Cocoon Wiki documentation
"""

THEME_SCHEMA = {
    "metadata": {
        "section_label": "Metadata",
        "fields": {
            "name": {
                "type": "string",
                "label": "Name",
                "required": True,
                "placeholder": "My Custom Theme"
            },
            "author": {
                "type": "string",
                "label": "Author",
                "placeholder": "YourName"
            },
            "version": {
                "type": "string",
                "label": "Version",
                "placeholder": "1.0"
            },
            "description": {
                "type": "text",
                "label": "Description",
                "placeholder": "A custom theme for Cocoon"
            },
            "credits": {
                "type": "text",
                "label": "Credits",
                "placeholder": "Music by..., SFX from..."
            },
            "website": {
                "type": "url",
                "label": "Website",
                "placeholder": "https://example.com"
            }
        }
    },
    "theme_mode": {
        "section_label": "Theme Mode",
        "fields": {
            "theme_mode": {
                "type": "enum",
                "label": "Theme Mode",
                "options": ["", "light", "dark", "oled", "system"],
                "default": "dark"
            }
        }
    },
    "color_scheme": {
        "section_label": "Color Scheme",
        "fields": {
            "color_scheme": {
                "type": "nested",
                "label": "Color Scheme",
                "fields": {
                    "background_gradient_start": {"type": "color", "label": "Background Gradient Start"},
                    "background_gradient_end": {"type": "color", "label": "Background Gradient End"},
                    "card_gradient_start": {"type": "color", "label": "Card Gradient Start"},
                    "card_gradient_end": {"type": "color", "label": "Card Gradient End"},
                    "text_primary": {"type": "color", "label": "Text Primary"},
                    "text_secondary": {"type": "color", "label": "Text Secondary"},
                    "icon_tint": {"type": "color", "label": "Icon Tint"},
                    "tile_background": {"type": "color", "label": "Tile Background"},
                    "tile_border": {"type": "color", "label": "Tile Border"},
                    "toggle_off_gradient_start": {"type": "color", "label": "Toggle Off Gradient Start"},
                    "toggle_off_gradient_end": {"type": "color", "label": "Toggle Off Gradient End"},
                    "toggle_thumb_gradient_start": {"type": "color", "label": "Toggle Thumb Gradient Start"},
                    "toggle_thumb_gradient_end": {"type": "color", "label": "Toggle Thumb Gradient End"},
                    "drop_shadow": {"type": "color", "label": "Drop Shadow"},
                    "inner_shadow_light": {"type": "color", "label": "Inner Shadow Light"},
                    "inner_shadow_dark": {"type": "color", "label": "Inner Shadow Dark"},
                    "success": {"type": "color", "label": "Success"},
                    "warning": {"type": "color", "label": "Warning"},
                    "divider": {"type": "color", "label": "Divider"},
                    "accent_gradient_start": {"type": "color", "label": "Accent Gradient Start"},
                    "accent_gradient_end": {"type": "color", "label": "Accent Gradient End"},
                    "accent_glow": {"type": "color", "label": "Accent Glow"}
                }
            }
        }
    },
    "wallpapers": {
        "section_label": "Wallpapers",
        "fields": {
            "wallpaper_main": {
                "type": "file",
                "label": "Main",
                "folder": "wallpapers",
                "name_pattern": "main",
                "extensions": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"]
            },
            "wallpaper_external": {
                "type": "file",
                "label": "External",
                "folder": "wallpapers",
                "name_pattern": "external",
                "extensions": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".webm"]
            }
        }
    },
    "music": {
        "section_label": "Music",
        "fields": {
            "music_mode": {
                "type": "enum",
                "label": "Music Mode",
                "options": ["", "TIME", "PLAYLIST", "DISABLED"],
                "default": "DISABLED"
            },
            "music_playback_mode": {
                "type": "enum",
                "label": "Playback Mode",
                "options": ["", "IN ORDER", "SHUFFLE"],
                "default": "IN ORDER"
            },
            "music_playlist": {
                "type": "playlist",
                "label": "Playlist",
                "folder": "music"
            },
            "music_time_schedule": {
                "type": "timeschedule",
                "label": "Time Schedule",
                "folder": "music"
            },
            "music_volume": {
                "type": "volume",
                "label": "Music Volume",
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "default": 1.0
            },
            "sfx_volume": {
                "type": "volume",
                "label": "SFX Volume",
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "default": 1.0
            }
        }
    }
}

SFX_ACTIONS = [
    "select",
    "back",
    "navigate",
    "folder_open",
    "folder_close",
    "launch",
    "error",
    "notification",
    "discord_open",
    "discord_close",
    "screen_swap",
    "grid_zoom_in",
    "grid_zoom_out",
    "reorder_pickup",
    "reorder_place"
]

def get_all_fields():
    """Flatten all fields from schema for iteration."""
    fields = {}
    for section_key, section in THEME_SCHEMA.items():
        section_fields = section.get("fields", {})
        for field_key, field_def in section_fields.items():
            if field_def.get("type") == "nested" and "fields" in field_def:
                for nested_key, nested_def in field_def["fields"].items():
                    fields[f"{field_key}.{nested_key}"] = {
                        **nested_def,
                        "parent": field_key,
                        "path": f"{field_key}.{nested_key}"
                    }
            else:
                fields[field_key] = {
                    **field_def,
                    "path": field_key
                }
    return fields

def get_required_fields():
    """Get list of required field names."""
    all_fields = get_all_fields()
    return [key for key, field in all_fields.items() if field.get("required", False)]
