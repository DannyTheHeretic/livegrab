"""In-memory grab jobs, persisted to jobs.json.

yt-dlp is spawned in its own process group. Stop sends SIGTERM only to a
group this process created. A PID Livegrab did not spawn is never signaled,
including an already-running external grab.
"""

from __future__ import annotations

import copy
import json
import os
import re
import signal
import subprocess
import threading
import uuid
from datetime import datetime, timezone

from livegrab_lib.command import DEFAULT_NODE, DEFAULT_YTDLP, build_args
from livegrab_lib.config import (
    CONFIG_DIR,
    ensure_destination,
    is_protected_destination,
    load_config,
)
from livegrab_lib.progress import parse_progress_line

JOBS_PATH = os.path.join(CONFIG_DIR, "jobs.json")
LOG_TAIL = 30
ACTIVE_STATES = {"starting", "downloading", "merging", "external"}
RUNNING_STATES = {"starting", "downloading", "merging"}
# Hard stop: never deliver a signal to the Tartube yt-dlp, even by accident.
NEVER_SIGNAL_PIDS = {149396}

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ID_PATTERNS = (
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"[?&]v=([A-Za-z0-9_-]{11})"),
    re.compile(r"/live/([A-Za-z0-9_-]{11})"),
    re.compile(r"/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"/embed/([A-Za-z0-9_-]{11})"),
    re.compile(r"/v/([A-Za-z0-9_-]{11})"),
)

_PUBLIC_FIELDS = (
    "id",
    "url",
    "destination",
    "template",
    "live_from_start",
    "audio_source",
    "state",
    "owner",
    "pid",
    "size",
    "speed",
    "fragment",
    "fragment_total",
    "percent",
    "video",
    "audio",
    "log_tail",
    "output_path",
    "error",
    "started_at",
)


class JobError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def extract_video_id(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    text = url.strip()
    if not text:
        return None
    for pattern in _ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    if _VIDEO_ID.fullmatch(text):
        return text
    return None


def read_argv(pid: int) -> list[str] | None:
    """Read /proc/<pid>/cmdline. Does not signal the process."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    if not raw:
        return None
    return [part.decode("utf-8", "replace") for part in raw.split(b"\x00") if part]


def pid_alive(pid) -> bool:
    """True when /proc/<pid> exists and the process is not a zombie.

    Existence is checked by reading /proc. Signal 0 is never sent.
    """
    try:
        number = int(pid)
    except (TypeError, ValueError):
        return False
    if number <= 0:
        return False
    try:
        with open(f"/proc/{number}/stat", "r", encoding="utf-8") as handle:
            stat = handle.read()
    except OSError:
        return False
    match = re.search(r"\)\s+([A-Za-z])", stat)
    if not match:
        return True
    return match.group(1) != "Z"


def _is_ytdlp(argv: list[str]) -> bool:
    for part in argv:
        base = os.path.basename(part)
        if base == "yt-dlp" or base.startswith("yt-dlp-"):
            return True
    return False


def _mentions_target(argv: list[str], url: str, video_id: str | None) -> bool:
    for part in argv:
        if url and (part == url or url in part):
            return True
        if video_id and re.search(
            rf"(?<![A-Za-z0-9_-]){re.escape(video_id)}(?![A-Za-z0-9_-])",
            part,
        ):
            return True
    return False


def find_external_ytdlp(url: str, skip_pids: set[int] | None = None) -> list[dict]:
    """Return yt-dlp processes already grabbing this URL or video id.

    Only /proc cmdline is read. Nothing is signaled and no download starts.
    """
    skip = skip_pids or set()
    video_id = extract_video_id(url)
    found = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return found
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid in skip or pid == os.getpid():
            continue
        argv = read_argv(pid)
        if not argv or not _is_ytdlp(argv):
            continue
        if not _mentions_target(argv, url, video_id):
            continue
        destination, template = _output_arg(argv)
        found.append(
            {
                "pid": pid,
                "argv": argv,
                "destination": destination,
                "template": template,
                "live_from_start": "--live-from-start" in argv,
                "exact_url": any(url and (part == url or url in part) for part in argv),
            }
        )
    found.sort(key=lambda item: (not item["exact_url"], item["pid"]))
    return found


def _output_arg(argv: list[str]) -> tuple[str | None, str | None]:
    if "-o" not in argv:
        return None, None
    index = argv.index("-o")
    if index + 1 >= len(argv):
        return None, None
    output = argv[index + 1]
    return os.path.dirname(output), os.path.basename(output)


def _empty_stream() -> dict:
    return {
        "size": None,
        "speed": None,
        "fragment": None,
        "fragment_total": None,
        "percent": None,
    }


def _blank_job() -> dict:
    return {
        "id": uuid.uuid4().hex,
        "url": "",
        "destination": "",
        "template": "",
        "live_from_start": True,
        "audio_source": "rewind",
        "state": "starting",
        "owner": "livegrab",
        "pid": None,
        "size": None,
        "speed": None,
        "fragment": None,
        "fragment_total": None,
        "percent": None,
        "video": _empty_stream(),
        "audio": _empty_stream(),
        "log_tail": [],
        "output_path": None,
        "error": None,
        "started_at": _now(),
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_job(job: dict) -> dict:
    view = {}
    for key in _PUBLIC_FIELDS:
        value = job.get(key)
        if key in ("video", "audio"):
            stream = _empty_stream()
            if isinstance(value, dict):
                for field in stream:
                    if field in value:
                        stream[field] = value[field]
            view[key] = stream
        elif key == "log_tail":
            if isinstance(value, list):
                view[key] = [str(line) for line in value[-LOG_TAIL:]]
            else:
                view[key] = []
        else:
            view[key] = value
    source = view.get("audio_source")
    if source not in ("live", "rewind"):
        source = "live" if view.get("live_from_start") is False else "rewind"
    view["audio_source"] = source
    view["live_from_start"] = source == "rewind"
    return view


class JobManager:
    def __init__(self, path: str = JOBS_PATH):
        self.path = path
        self._lock = threading.Lock()
        self._jobs: list[dict] = []
        self._spawned: set[int] = set()
        self._stop_requested: set[str] = set()
        self._hard_merged: set[str] = set()
        self._load()

    def list_jobs(self) -> list[dict]:
        with self._lock:
            return [public_job(job) for job in self._jobs]

    def start_job(
        self,
        url,
        destination=None,
        template=None,
        live_from_start=None,
        audio_source=None,
        ytdlp_path=None,
        node_path=None,
    ) -> dict:
        if not isinstance(url, str) or not url.strip():
            raise JobError("url is required")
        url = url.strip()
        if isinstance(audio_source, str):
            audio_source = audio_source.strip().lower()
        if audio_source is not None and audio_source not in ("live", "rewind"):
            raise JobError("audio_source must be 'live' or 'rewind'")
        if live_from_start is not None and not isinstance(live_from_start, bool):
            raise JobError("live_from_start must be a boolean")
        config = load_config()
        destination = _choose_text(destination, config["destination"])
        template = _choose_text(template, config["template"])
        if audio_source is not None:
            live_from_start = audio_source == "rewind"
        elif live_from_start is not None:
            audio_source = "rewind" if live_from_start else "live"
        else:
            audio_source = config.get("audio_source") or (
                "rewind" if config["live_from_start"] else "live"
            )
            live_from_start = audio_source == "rewind"
        if not destination:
            raise JobError("destination must be a non-empty string")
        if not template:
            raise JobError("template must be a non-empty string")

        video_id = extract_video_id(url)
        with self._lock:
            existing = self._active_match(url, video_id)
            if existing is not None:
                return public_job(existing)
            skip = set(self._spawned)
        external = find_external_ytdlp(url, skip_pids=skip)
        if external:
            return self._record_external(url, destination, template, live_from_start, external[0])

        if is_protected_destination(destination):
            raise JobError("that destination is not available")

        ensure_destination(destination)
        args = build_args(
            url,
            destination,
            template,
            audio_source,
            ytdlp_path or DEFAULT_YTDLP,
            DEFAULT_NODE if node_path is None else node_path,
        )
        job = _blank_job()
        job.update(
            {
                "url": url,
                "destination": destination,
                "template": template,
                "live_from_start": live_from_start,
                "audio_source": audio_source,
                "state": "starting",
                "owner": "livegrab",
            }
        )
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            job["state"] = "error"
            job["error"] = f"Could not start yt-dlp: {exc}"
            with self._lock:
                self._jobs.append(job)
                self._save_locked()
            return public_job(job)

        job["pid"] = proc.pid
        with self._lock:
            self._spawned.add(proc.pid)
            self._jobs.append(job)
            self._save_locked()
            snapshot = public_job(job)
        thread = threading.Thread(
            target=self._pump,
            args=(job["id"], proc),
            name=f"livegrab-{job['id'][:8]}",
            daemon=True,
        )
        thread.start()
        return snapshot

    def stop_job(self, job_id: str):
        """SIGTERM the process group only when this process spawned it."""
        with self._lock:
            job = self._find(job_id)
            if job is None:
                return 404, {"error": "job not found"}
            if job.get("owner") != "livegrab":
                return 409, {"error": "Livegrab will not stop a download it did not start"}
            if job.get("state") not in RUNNING_STATES:
                return 200, public_job(job)
            pid = job.get("pid")
            if not self._safe_to_signal(pid, job.get("url") or ""):
                return 409, {"error": "Livegrab will not stop a download it did not start"}
            self._stop_requested.add(job_id)
            job["state"] = "interrupted"
            self._save_locked()
            snapshot = public_job(job)
        if pid in NEVER_SIGNAL_PIDS:
            return 409, {"error": "Livegrab will not stop a download it did not start"}
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            return 409, {"error": "Livegrab will not stop a download it did not start"}
        return 200, snapshot

    def _safe_to_signal(self, pid, url: str) -> bool:
        try:
            number = int(pid)
        except (TypeError, ValueError):
            return False
        if number in NEVER_SIGNAL_PIDS or number not in self._spawned:
            return False
        argv = read_argv(number)
        if not argv or not _is_ytdlp(argv):
            return False
        if any("Tartube_videos" in part for part in argv):
            return False
        return _mentions_target(argv, url, extract_video_id(url))

    def _record_external(self, url, destination, template, live_from_start, match) -> dict:
        external_destination = match.get("destination") or destination
        external_template = match.get("template") or template
        job = _blank_job()
        job.update(
            {
                "url": url,
                "destination": external_destination,
                "template": external_template,
                "live_from_start": bool(match.get("live_from_start", live_from_start)),
                "audio_source": "rewind" if match.get("live_from_start", live_from_start) else "live",
                "state": "external",
                "owner": "external",
                "pid": match.get("pid"),
            }
        )
        with self._lock:
            existing = self._active_match(url, extract_video_id(url))
            if existing is not None:
                return public_job(existing)
            self._jobs.append(job)
            self._save_locked()
            return public_job(job)

    def _active_match(self, url: str, video_id: str | None) -> dict | None:
        for job in reversed(self._jobs):
            if job.get("state") not in ACTIVE_STATES:
                continue
            if job.get("state") == "external" and not pid_alive(job.get("pid")):
                continue
            if _same_target(job.get("url"), url, video_id):
                return job
        return None

    def _find(self, job_id: str) -> dict | None:
        for job in self._jobs:
            if job.get("id") == job_id:
                return job
        return None

    def _pump(self, job_id: str, proc: subprocess.Popen) -> None:
        tail: list[str] = []
        try:
            stream = proc.stdout
            if stream is not None:
                for line in stream:
                    text = line.rstrip("\r\n")
                    tail.append(text)
                    if len(tail) > LOG_TAIL:
                        del tail[:-LOG_TAIL]
                    self._on_line(job_id, list(tail), parse_progress_line(text))
        finally:
            rc = proc.wait()
            self._on_exit(job_id, rc)

    def _on_line(self, job_id: str, tail: list[str], parsed) -> None:
        with self._lock:
            job = self._find(job_id)
            if job is None or job.get("owner") != "livegrab":
                return
            job["log_tail"] = tail[-LOG_TAIL:]
            if parsed:
                self._apply_progress(job, parsed)
            self._save_locked()

    def _apply_progress(self, job: dict, parsed: dict) -> None:
        if job.get("state") in ("finished", "interrupted", "external"):
            return
        phase = parsed.get("phase")
        if phase == "downloading":
            if job["id"] not in self._hard_merged and job.get("state") in (
                "starting",
                "downloading",
                "merging",
            ):
                job["state"] = "downloading"
            if job.get("state") in ("starting", "downloading", "merging"):
                _copy_metrics(job, parsed)
                _copy_stream(job, parsed)
        elif phase == "merging":
            if parsed.get("output_path"):
                job["output_path"] = parsed["output_path"]
            if parsed.get("reason") == "merge" and job.get("state") not in (
                "finished",
                "error",
                "interrupted",
                "external",
            ):
                self._hard_merged.add(job["id"])
                job["state"] = "merging"
        elif phase == "error":
            job["state"] = "error"
            job["error"] = parsed.get("message") or "yt-dlp reported an error"

    def _on_exit(self, job_id: str, rc: int) -> None:
        with self._lock:
            job = self._find(job_id)
            if job is None:
                return
            pid = job.get("pid")
            if isinstance(pid, int):
                self._spawned.discard(pid)
            if job_id in self._stop_requested or (isinstance(rc, int) and rc < 0):
                job["state"] = "interrupted"
            elif rc == 0 and job.get("state") != "error":
                job["state"] = "finished"
            else:
                job["state"] = "error"
                if not job.get("error"):
                    job["error"] = f"yt-dlp exited with status {rc}"
            self._save_locked()

    def _load(self) -> None:
        raw_jobs = []
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, json.JSONDecodeError):
            stored = None
        if isinstance(stored, dict) and isinstance(stored.get("jobs"), list):
            raw_jobs = stored["jobs"]
        elif isinstance(stored, list):
            raw_jobs = stored
        changed = False
        for item in raw_jobs:
            if not isinstance(item, dict):
                continue
            job = public_job(item)
            if not job.get("id"):
                job["id"] = uuid.uuid4().hex
                changed = True
            if job.get("state") in RUNNING_STATES and not pid_alive(job.get("pid")):
                job["state"] = "interrupted"
                changed = True
            self._jobs.append(job)
        if changed:
            self._save_locked()

    def _save_locked(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temporary = self.path + ".tmp"
        payload = {"jobs": [public_job(job) for job in self._jobs]}
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)


def _choose_text(value, fallback: str) -> str:
    if value is None:
        return fallback if isinstance(fallback, str) else ""
    if not isinstance(value, str):
        raise JobError("expected a string")
    text = value.strip()
    return text or (fallback if isinstance(fallback, str) else "")


def _same_target(left, right, video_id: str | None) -> bool:
    if isinstance(left, str) and isinstance(right, str) and left.strip() == right.strip():
        return True
    if not video_id:
        return False
    return extract_video_id(left if isinstance(left, str) else "") == video_id


def _copy_metrics(job: dict, parsed: dict) -> None:
    for key in ("size", "speed", "fragment", "fragment_total", "percent"):
        if parsed.get(key) is not None:
            job[key] = parsed[key]


def _copy_stream(job: dict, parsed: dict) -> None:
    name = parsed.get("stream")
    if name not in ("video", "audio"):
        return
    stream = job.get(name)
    if not isinstance(stream, dict):
        stream = _empty_stream()
        job[name] = stream
    for key in ("size", "speed", "fragment", "fragment_total", "percent"):
        if parsed.get(key) is not None:
            stream[key] = parsed[key]
