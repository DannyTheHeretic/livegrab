"""Cross-platform config paths and external-tool lookup.

Download destinations are supplied by the caller. This module does not
choose one, and importing it does not create directories.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = [
    "config_dir",
    "ensure_config_dir",
    "ffmpeg_path",
    "ffprobe_path",
    "find_tool",
    "subprocess_kwargs",
    "ytdlp_path",
]


def config_dir() -> Path:
    """Return the Livegrab config directory without creating it.

    Windows uses ``%APPDATA%/livegrab`` (or ``~/AppData/Roaming/livegrab``
    when ``APPDATA`` is unset). macOS uses Application Support. Other
    systems use ``$XDG_CONFIG_HOME/livegrab`` or ``~/.config/livegrab``.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "").strip()
        if appdata:
            return Path(os.path.expanduser(appdata)) / "livegrab"
        return Path.home() / "AppData" / "Roaming" / "livegrab"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "livegrab"
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(os.path.expanduser(xdg)) / "livegrab"
    return Path.home() / ".config" / "livegrab"


def ensure_config_dir() -> Path:
    """Create the config directory, including parents, and return it."""
    config_dir().mkdir(parents=True, exist_ok=True)
    return config_dir()


def find_tool(names: list[str]) -> str | None:
    """Return the first existing executable for ``names``, or None.

    Directories beside the running program are checked before PATH.
    ``shutil.which`` is next. A short list of well-known install
    directories is checked only when those have no match.
    """
    found = _find_in(_program_dirs(), names)
    if found:
        return found
    for name in names:
        if not name:
            continue
        found = shutil.which(name)
        if found:
            return found
    return _find_in(_install_dirs(), names)


def ytdlp_path() -> str:
    """Return a yt-dlp executable, or ``yt-dlp`` when none is installed."""
    return find_tool(["yt-dlp", "yt-dlp.exe"]) or "yt-dlp"


def ffmpeg_path() -> str | None:
    """Return an ffmpeg executable beside the program or on PATH."""
    return find_tool(["ffmpeg", "ffmpeg.exe"])


def ffprobe_path() -> str | None:
    """Return an ffprobe executable beside the program or on PATH."""
    return find_tool(["ffprobe", "ffprobe.exe"])


def subprocess_kwargs() -> dict:
    """Return extra subprocess arguments for the current platform.

    On Windows, include ``creationflags`` set to ``CREATE_NO_WINDOW`` when
    that attribute exists. Otherwise return an empty dict.
    """
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", None)
        if creationflags is not None:
            return {"creationflags": creationflags}
    return {}


def _program_dirs() -> list[Path]:
    """Directories that may hold a copy shipped next to Livegrab.

    A frozen build looks beside ``sys.executable`` and inside
    ``sys._MEIPASS``. A source tree looks next to ``livegrab.py`` and in
    ``tools/`` and ``bin/``.
    """
    dirs: list[Path] = []
    if _is_frozen():
        executable = getattr(sys, "executable", "") or ""
        if executable:
            dirs.append(Path(executable).resolve().parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass))
    root = _source_root()
    if root is not None:
        dirs.append(root)
        dirs.append(root / "tools")
        dirs.append(root / "bin")
    unique: list[Path] = []
    seen: set[str] = set()
    for directory in dirs:
        key = str(directory)
        if key in seen:
            continue
        seen.add(key)
        unique.append(directory)
    return unique


def _is_frozen() -> bool:
    """True for a PyInstaller program or any other frozen interpreter."""
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def _source_root() -> Path | None:
    """Directory containing ``livegrab.py``, when this module is in that tree."""
    candidate = Path(__file__).resolve().parent.parent
    try:
        if (candidate / "livegrab.py").is_file():
            return candidate
    except OSError:
        return None
    return None


def _find_in(directories: list[Path], names: list[str]) -> str | None:
    for directory in directories:
        for name in names:
            if not _is_plain_name(name):
                continue
            found = _executable_in(directory, name)
            if found:
                return found
    return None


def _install_dirs() -> list[Path]:
    """Install directories checked after PATH."""
    if sys.platform == "win32":
        dirs: list[Path] = []
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        if local_appdata:
            dirs.append(Path(os.path.expanduser(local_appdata)) / "Programs")
        profile = os.environ.get("USERPROFILE", "").strip()
        if profile:
            dirs.append(
                Path(os.path.expanduser(profile))
                / "AppData"
                / "Local"
                / "Microsoft"
                / "WinGet"
                / "Links"
            )
        if sys.executable:
            dirs.append(Path(sys.executable).parent)
        return dirs
    if sys.platform == "darwin":
        return [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    return [Path("/usr/bin"), Path("/usr/local/bin")]


def _is_plain_name(name: str) -> bool:
    """True when ``name`` is a single path component."""
    return bool(name) and name not in {".", ".."} and Path(name).name == name


def _executable_in(directory: Path, name: str) -> str | None:
    candidate = directory / name
    try:
        if not candidate.is_file():
            return None
        if os.access(candidate, os.X_OK):
            return str(candidate)
        # Windows copies of .exe files are runnable without a Unix mode bit.
        if os.name == "nt" and candidate.suffix.lower() == ".exe":
            return str(candidate)
    except OSError:
        return None
    return None
