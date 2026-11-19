"""Parse one line of yt-dlp progress output."""

from __future__ import annotations

import re

_PREFIX = re.compile(r"^([12])\s*:\s*(.*)$", re.DOTALL)
_SIZE_SPEED = re.compile(
    r"(?P<size>\d+(?:\.\d+)?(?:[KMGT]i?B|B))\s+at\s+"
    r"(?P<speed>\d+(?:\.\d+)?(?:[KMGT]i?B|B)/s)",
    re.IGNORECASE,
)
_FRAG = re.compile(
    r"\(frag\s+(?P<fragment>\d+)\s*/\s*(?P<fragment_total>\d+)\)",
    re.IGNORECASE,
)
_PERCENT = re.compile(r"(?P<percent>\d+(?:\.\d+)?)\s*%")
_INTO = re.compile(r'into\s+"([^"]+)"')
_DESTINATION = re.compile(r"Destination:\s*(.+)$", re.IGNORECASE)
_ERROR = re.compile(r"^(?:\[[^\]]+\]\s*)?ERROR\b", re.IGNORECASE)

_STREAMS = {"1": "video", "2": "audio"}
_MERGE_TOKENS = ("merger", "ffmpeg", "remux")


def parse_progress_line(line):
    """Return a progress dict, or None when the line is not progress.

    An optional ``1:`` or ``2:`` prefix selects the video or audio stream.
    A download line with no prefix is the video stream. Merger, ffmpeg,
    remux, and Destination lines are phase ``merging``. ``ERROR`` lines are
    phase ``error``.
    """
    if not isinstance(line, str):
        return None
    text = line.strip()
    if not text:
        return None

    stream = None
    prefix = _PREFIX.match(text)
    if prefix:
        stream = _STREAMS[prefix.group(1)]
        text = prefix.group(2).strip()
        if not text:
            return None

    if _ERROR.match(text):
        return _event(
            stream=stream,
            phase="error",
            message=text,
        )

    lowered = text.lower()
    if any(token in lowered for token in _MERGE_TOKENS) or "destination" in lowered:
        output_path = _output_path(text)
        hard_merge = any(token in lowered for token in _MERGE_TOKENS)
        return _event(
            stream=stream,
            phase="merging",
            output_path=output_path,
            reason="merge" if hard_merge else "destination",
        )

    lowered_download = text.lower()
    if "[download]" not in lowered_download and not lowered_download.startswith("download"):
        return None

    size_speed = _SIZE_SPEED.search(text)
    frag = _FRAG.search(text)
    percent_match = _PERCENT.search(text)
    if not size_speed and not frag and not percent_match:
        return None

    fragment = int(frag.group("fragment")) if frag else None
    fragment_total = int(frag.group("fragment_total")) if frag else None
    percent = float(percent_match.group("percent")) if percent_match else None
    if percent is None and fragment is not None and fragment_total:
        percent = round(fragment * 100.0 / fragment_total, 1)

    return _event(
        stream=stream or "video",
        phase="downloading",
        size=size_speed.group("size") if size_speed else None,
        speed=size_speed.group("speed") if size_speed else None,
        fragment=fragment,
        fragment_total=fragment_total,
        percent=percent,
    )


def _output_path(text: str):
    into = _INTO.search(text)
    if into:
        return into.group(1)
    destination = _DESTINATION.search(text)
    if destination:
        return destination.group(1).strip().strip('"')
    return None


def _event(
    stream,
    phase,
    size=None,
    speed=None,
    fragment=None,
    fragment_total=None,
    percent=None,
    message=None,
    output_path=None,
    reason=None,
):
    event = {
        "stream": stream,
        "phase": phase,
        "size": size,
        "speed": speed,
        "fragment": fragment,
        "fragment_total": fragment_total,
        "percent": percent,
        "message": message,
        "output_path": output_path,
    }
    if reason is not None:
        event["reason"] = reason
    return event
