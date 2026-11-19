"""Build yt-dlp argument lists.

This module never executes yt-dlp. Callers that spawn a process must keep
the result as an argv list and must not pass it through a shell.
"""

from __future__ import annotations

import os

DEFAULT_YTDLP = "/usr/bin/yt-dlp"
DEFAULT_NODE = "/home/random/.local/bin/node"


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
    ytdlp_path=DEFAULT_YTDLP,
    node_path=DEFAULT_NODE,
):
    """Return the argv for one grab.

    ``--live-from-start`` is added only for the rewind choice. JavaScript
    runtime flags are omitted when node_path is missing or is not an
    existing file. Nothing is downloaded here.
    """
    ytdlp = ytdlp_path or DEFAULT_YTDLP
    args = [ytdlp, "--newline", "--no-update"]
    if wants_live_from_start(live_from_start):
        args.append("--live-from-start")
    if node_path and os.path.isfile(node_path):
        args.extend(
            [
                "--js-runtimes",
                "node:" + node_path,
                "--remote-components",
                "ejs:github",
            ]
        )
    output = os.path.join(destination, template)
    args.extend(["--remux-video", "mp4", "-o", output, url])
    return args
