"""Load and save Livegrab settings.

The destination directory is created only when a job starts, never at import.
"""

from __future__ import annotations

import json
import os

CONFIG_DIR = "/home/random/.config/livegrab"
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_DESTINATION = "/home/random/Videos/Livegrab"
DEFAULT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
DEFAULT_LIVE_FROM_START = True
DEFAULT_AUDIO_SOURCE = "rewind"
AUDIO_SOURCES = ("live", "rewind")

DESTINATION_CHOICES = (
    DEFAULT_DESTINATION,
    "/home/random/Videos",
)

TEMPLATE_PRESETS = {
    "Title [id]": "%(title)s [%(id)s].%(ext)s",
    "Title": "%(title)s.%(ext)s",
    "Id": "%(id)s.%(ext)s",
}

# The Tartube grab lives here. Livegrab never creates or writes inside it.
PROTECTED_DESTINATION = "/home/random/Videos/Tartube_videos"


def is_protected_destination(path: str) -> bool:
    """True when path is the Tartube download directory or something inside it."""
    if not isinstance(path, str) or not path.strip():
        return False
    candidate = os.path.normpath(os.path.abspath(path))
    banned = os.path.normpath(PROTECTED_DESTINATION)
    return candidate == banned or candidate.startswith(banned + os.sep)


def source_from_flag(live_from_start: bool) -> str:
    return "rewind" if live_from_start else "live"


def flag_from_source(audio_source: str) -> bool:
    return audio_source == "rewind"


def default_config() -> dict:
    return {
        "destination": DEFAULT_DESTINATION,
        "template": DEFAULT_TEMPLATE,
        "live_from_start": DEFAULT_LIVE_FROM_START,
        "audio_source": DEFAULT_AUDIO_SOURCE,
    }


def load_config() -> dict:
    """Return saved settings, or the defaults when the file is missing."""
    data = default_config()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return data
    if not isinstance(stored, dict):
        return data
    destination = stored.get("destination")
    template = stored.get("template")
    live_from_start = stored.get("live_from_start")
    audio_source = stored.get("audio_source")
    if isinstance(destination, str) and destination.strip():
        data["destination"] = destination.strip()
    if isinstance(template, str) and template.strip():
        data["template"] = template.strip()
    if audio_source in AUDIO_SOURCES:
        data["audio_source"] = audio_source
        data["live_from_start"] = flag_from_source(audio_source)
    elif isinstance(live_from_start, bool):
        data["live_from_start"] = live_from_start
        data["audio_source"] = source_from_flag(live_from_start)
    return data


def normalize_audio_source(value) -> str:
    """Return ``live`` or ``rewind``. Reject anything else."""
    if isinstance(value, str):
        choice = value.strip().lower()
        if choice in AUDIO_SOURCES:
            return choice
    raise ValueError("audio_source must be 'live' or 'rewind'")


def save_config(config: dict) -> dict:
    """Persist destination, template, and the recording choice."""
    current = default_config()
    destination = config.get("destination", current["destination"])
    template = config.get("template", current["template"])
    if "audio_source" in config:
        audio_source = normalize_audio_source(config.get("audio_source"))
    elif "live_from_start" in config:
        live_from_start = config.get("live_from_start")
        if not isinstance(live_from_start, bool):
            raise ValueError("live_from_start must be a boolean")
        audio_source = source_from_flag(live_from_start)
    else:
        audio_source = current["audio_source"]
    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("destination must be a non-empty string")
    if not isinstance(template, str) or not template.strip():
        raise ValueError("template must be a non-empty string")
    if is_protected_destination(destination):
        raise ValueError("that destination is not available")
    stored = {
        "destination": destination.strip(),
        "template": template.strip(),
        "audio_source": audio_source,
        "live_from_start": flag_from_source(audio_source),
    }
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _atomic_json(CONFIG_PATH, stored)
    return stored


def update_config(updates: dict) -> dict:
    """Apply a partial settings update and return the API view."""
    if not isinstance(updates, dict):
        raise ValueError("config must be a JSON object")
    config = load_config()
    if "destination" in updates:
        config["destination"] = updates["destination"]
    if "template" in updates:
        config["template"] = updates["template"]
    if "audio_source" in updates:
        audio_source = normalize_audio_source(updates["audio_source"])
        config["audio_source"] = audio_source
        config["live_from_start"] = flag_from_source(audio_source)
    elif "live_from_start" in updates:
        live_from_start = updates["live_from_start"]
        if not isinstance(live_from_start, bool):
            raise ValueError("live_from_start must be a boolean")
        config["live_from_start"] = live_from_start
        config["audio_source"] = source_from_flag(live_from_start)
    save_config(config)
    return config_view(load_config())


def config_view(config: dict | None = None) -> dict:
    """Settings plus the folder and template choices the page shows."""
    current = config if config is not None else load_config()
    audio_source = current.get("audio_source")
    if audio_source in AUDIO_SOURCES:
        live_from_start = flag_from_source(audio_source)
    else:
        live_from_start = current.get("live_from_start")
        if not isinstance(live_from_start, bool):
            live_from_start = DEFAULT_LIVE_FROM_START
        audio_source = source_from_flag(live_from_start)
    return {
        "destination": current["destination"],
        "template": current["template"],
        "audio_source": audio_source,
        "live_from_start": live_from_start,
        "destination_choices": list(DESTINATION_CHOICES),
        "template_presets": dict(TEMPLATE_PRESETS),
    }


def ensure_destination(path: str) -> None:
    """Create a destination directory. Call this only when a job starts."""
    if is_protected_destination(path):
        raise ValueError("that destination is not available")
    os.makedirs(path, exist_ok=True)


def _atomic_json(path: str, payload: dict) -> None:
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
