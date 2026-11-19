# Livegrab

Livegrab records a livestream URL with yt-dlp. Choose live player audio or from-the-start audio. Follow Twitch channels and Livegrab auto-grabs them with live player audio when they go live.

## Requirements

On Windows, macOS, and Linux:

- Python 3
- `yt-dlp` on `PATH`
- `ffmpeg` on `PATH`

The Windows installer and the Debian package bring yt-dlp and ffmpeg in with the app. A checkout you run yourself still needs them on `PATH`.

## Downloads

- [Livegrab-Setup.exe](https://github.com/Unaware-Kerbin/livegrab/releases/download/v0.1.1/Livegrab-Setup.exe). The Windows setup includes Livegrab, yt-dlp, and ffmpeg.
- [livegrab_0.1.1_all.deb](https://github.com/Unaware-Kerbin/livegrab/releases/download/v0.1.1/livegrab_0.1.1_all.deb). The Debian package depends on python3, ffmpeg, and yt-dlp.

The release page is https://github.com/Unaware-Kerbin/livegrab/releases/tag/v0.1.1.

`pip` and `pipx` remain an alternative once the PyPI package is published.

## Installer

**Windows:** [Livegrab-Setup.exe](https://github.com/Unaware-Kerbin/livegrab/releases/download/v0.1.1/Livegrab-Setup.exe) installs the app, yt-dlp, and ffmpeg into one folder. It does not need Python, pip, yt-dlp, or ffmpeg to be installed already. Python is inside the application.

**Debian and Ubuntu:** [livegrab_0.1.1_all.deb](https://github.com/Unaware-Kerbin/livegrab/releases/download/v0.1.1/livegrab_0.1.1_all.deb) depends on python3, ffmpeg, and yt-dlp. After downloading it, `sudo apt install ./livegrab_0.1.1_all.deb` installs Livegrab plus those packages. A package built in this tree is `sudo apt install ./dist/livegrab_0.1.1_all.deb`.

**Linux folder:** `packaging/build-linux-bundle.sh` downloads a static ffmpeg (and ffprobe) and the yt-dlp Linux binary into `dist/livegrab-linux/`, with a launcher that puts those binaries first on `PATH`.

**macOS:** `packaging/build-macos.sh` would download the macOS yt-dlp binary and a macOS ffmpeg build and lay out `Livegrab.app`. That script is not built on this machine.

## Install

These commands work once the PyPI package name `livegrab` is published.

**pipx** (preferred; it isolates the app):

```bash
pipx install livegrab
```

Then run `livegrab` and open http://127.0.0.1:8765

**pip:**

```bash
python -m pip install livegrab
```

On macOS and Linux, use `python3 -m pip install livegrab`. Then run the same `livegrab` command.

A git checkout can still use `livegrab.bat` and `livegrab.sh`.

## Windows

Double-click `livegrab.bat`, or from this folder run:

```bat
py livegrab.py
```

or:

```bat
python livegrab.py
```

Then open http://127.0.0.1:8765

## macOS

From this folder run:

```bash
./livegrab.sh
```

or:

```bash
python3 livegrab.py
```

Then open http://127.0.0.1:8765

## Linux

From this folder run:

```bash
./livegrab.sh
```

or:

```bash
python3 livegrab.py
```

Then open http://127.0.0.1:8765

## First run

The folder field is empty. Type a full folder path before starting a grab. Livegrab does not pick a folder for you.

Examples only:

- Windows: `C:\Users\you\Videos\Livegrab`
- macOS: `/Users/you/Movies`
- Linux: `/home/you/Videos`

## Audio

**Live player audio** matches the player and starts now.

**From the start** rewinds. On Twitch that copy already has copyrighted music removed.

Automatic follows always use live player audio.

## Security

The server binds to localhost only (`127.0.0.1`).
