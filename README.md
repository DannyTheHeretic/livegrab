# Livegrab

Livegrab is a local page that drives the system `yt-dlp`. It starts grabs on this machine and shows their progress in the browser. It does not upload anything and it does not talk to a remote Livegrab service.

## Run

From `/home/random/Projects/livegrab`:

```bash
python3 livegrab.py
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765).

## Defaults

- **Folder:** `~/Videos/Livegrab`
- **Filename:** `%(title)s [%(id)s].%(ext)s`
- **Audio:** From the start

Finished files land in the folder above, named from the title and the video id. **From the start** rewinds a livestream to the beginning. On Twitch, that copy already has copyrighted music removed. **Live player audio** keeps the mix you hear in the player, including music, and starts from the current moment.

## Folder and filename

Change the folder and the filename in the form on the page before you press **Start grab**.

- Under **Destination**, edit the **Folder** field. That path is the directory yt-dlp writes into. The default is `~/Videos/Livegrab`. Use another directory when you want these grabs kept separate from other video folders.
- Under **Filename**, pick a preset or edit the **Template** field. That value is the yt-dlp output template. The default is `%(title)s [%(id)s].%(ext)s`. `%(title)s`, `%(id)s`, and `%(ext)s` are filled in by yt-dlp. The line under the field shows the exact template that will be sent.

The folder, the filename template, and the audio choice are stored in the settings file `~/.config/livegrab/config.json` and reused the next time you open the page.

## One grab per URL

Do not start a second download of a URL that is already running. If that URL is already in progress, leave the running grab alone instead of submitting it again.

## What Livegrab will not touch

The current H3 grab in `~/Videos/Tartube_videos` is external. Leave it alone. Livegrab did not start it, and nothing in this page should stop, move, or rewrite that download.

Files whose names end in `.part` are unfinished. They are still downloading or were interrupted before yt-dlp finished them.

**Stop** only stops grabs Livegrab itself started. It does not stop yt-dlp processes that Tartube or anything else started, including the H3 grab in `~/Videos/Tartube_videos`.

## Tests

From `/home/random/Projects/livegrab`:

```bash
python3 -m unittest tests.test_command tests.test_progress
```

`tests/test_command.py` checks the yt-dlp argument list. `tests/test_progress.py` checks progress-line parsing. A download line with no numeric stream prefix is treated as the video stream.
