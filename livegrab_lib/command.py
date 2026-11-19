"""Build yt-dlp argument lists.

This module never executes yt-dlp. Callers that spawn a process must keep
the result as an argv list and must not pass it through a shell.

Livegrab is Python only. ``--no-js-runtimes`` clears yt-dlp's default
JavaScript runtimes so a grab does not launch one.
"""

from __future__ import annotations

from pathlib import Path

from livegrab_lib.platform import ffmpeg_path as platform_ffmpeg_path
from livegrab_lib.platform import ytdlp_path as platform_ytdlp_path

# Resolved when this module is imported. Not a fixed install path.
DEFAULT_YTDLP = platform_ytdlp_path()
# Kept so existing callers can still import the name. Never a runtime path.
DEFAULT_NODE = None


def wants_live_from_start(choice) -> bool:
    """True only for the rewind copy.

    A boolean still works: True is rewind, False is the live edge.
    The strings "rewind" and "live" select those same copies.
    """
    if isinstance(choice, str):
        name = choice.strip().lower()
        if name == "rewind":
            return True
        if name == "live":
            return False
        raise ValueError("audio_source must be 'live' or 'rewind'")
    return bool(choice)


def build_args(
    url,
    destination,
    template,
    live_from_start,
    ytdlp_path=None,
    node_path=None,
):
    """Return the argv for one grab.

    ``--live-from-start`` is added only for the rewind choice.
    ``--no-js-runtimes`` is always set. When ffmpeg is found, its directory
    is passed as ``--ffmpeg-location``. ``node_path`` is accepted and
    ignored so older callers keep working; it is never placed on argv.
    Nothing is downloaded here.
    """
    del node_path
    binary = ytdlp_path or platform_ytdlp_path()
    args = [binary, "--newline", "--no-update", "--no-js-runtimes"]
    ffmpeg = platform_ffmpeg_path()
    if ffmpeg:
        args.extend(["--ffmpeg-location", str(Path(ffmpeg).parent)])
    if wants_live_from_start(live_from_start):
        args.append("--live-from-start")
    output = str(Path(destination) / template)
    args.extend(["--remux-video", "mp4", "-o", output, url])
    return args
