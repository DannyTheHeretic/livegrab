"""Tests for livegrab_lib.progress.parse_progress_line.

A download line with no numeric stream prefix is treated as stream "video".
"""

import unittest

from livegrab_lib.progress import parse_progress_line

VIDEO_LINE = (
    "1: [download] 617.61MiB at 859.41KiB/s (00:17:31) (frag 858/1474)"
)
AUDIO_LINE = (
    "2: [download] 120.56MiB at 163.70KiB/s (00:17:16) (frag 1543/1610)"
)
UNPREFIXED_LINE = (
    "[download] 1.00MiB at 100.00KiB/s (00:00:01) (frag 10/20)"
)


class ParseProgressLineTests(unittest.TestCase):
    def assert_fields(self, line, **expected):
        result = parse_progress_line(line)
        self.assertIsInstance(result, dict, msg=line)
        for key, value in expected.items():
            self.assertIn(key, result, msg=f"{line} missing {key}")
            self.assertEqual(result[key], value, msg=f"{line} field {key}")
        return result

    def test_prefixed_video_download(self):
        self.assert_fields(
            VIDEO_LINE,
            stream="video",
            size="617.61MiB",
            speed="859.41KiB/s",
            fragment=858,
            fragment_total=1474,
            phase="downloading",
        )

    def test_prefixed_audio_download(self):
        self.assert_fields(
            AUDIO_LINE,
            stream="audio",
            size="120.56MiB",
            speed="163.70KiB/s",
            fragment=1543,
            fragment_total=1610,
            phase="downloading",
        )

    def test_unprefixed_download_is_video_stream(self):
        """No "N:" prefix: stream is "video", and frag 10/20 is returned."""
        self.assert_fields(
            UNPREFIXED_LINE,
            stream="video",
            size="1.00MiB",
            speed="100.00KiB/s",
            fragment=10,
            fragment_total=20,
            phase="downloading",
        )

    def test_merger_line_is_merging(self):
        result = parse_progress_line('[Merger] Merging formats into "out.mp4"')
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("phase"), "merging")

    def test_ffmpeg_line_is_merging(self):
        result = parse_progress_line("Invoking ffmpeg to process the file")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("phase"), "merging")

    def test_ffmpeg_stats_are_downloading(self):
        line = (
            "frame=  480 fps= 40 q=-1.0 size=    8960KiB time=00:00:15.93 "
            "bitrate=4606.8kbits/s speed=1.33x elapsed=0:00:12.00"
        )
        self.assert_fields(
            line,
            stream="video",
            phase="downloading",
            size="8960KiB",
            speed="4606.8kbits/s",
        )

    def test_ffmpeg_stats_ignore_na_metrics(self):
        line = "frame=    0 fps=0.0 q=-1.0 size=       0KiB time=N/A bitrate=N/A speed=N/A"
        self.assert_fields(
            line,
            stream="video",
            phase="downloading",
            size="0KiB",
            speed=None,
        )

    def test_remux_line_is_merging(self):
        result = parse_progress_line("[VideoRemuxer] remux into mp4")
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("phase"), "merging")

    def test_unrelated_text_returns_none(self):
        self.assertIsNone(parse_progress_line("nothing to see here"))
        self.assertIsNone(parse_progress_line("Waiting for the page"))


if __name__ == "__main__":
    unittest.main()
