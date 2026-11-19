"""Tests for livegrab_lib.command.build_args."""

import os
import unittest

from livegrab_lib.command import build_args

URL = "https://www.youtube.com/watch?v=example"
DESTINATION = "/home/random/Videos/Livegrab"
TEMPLATE = "%(title)s [%(id)s].%(ext)s"
YTDLP = "/usr/bin/yt-dlp"
NODE_EXISTS = "/usr/bin/python3"
NODE_MISSING = "/tmp/livegrab-node-does-not-exist"

JS_FLAGS = ("--js-runtimes", "--remote-components", "ejs:github")


class BuildArgsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(NODE_EXISTS):
            raise unittest.SkipTest(f"{NODE_EXISTS} is not on disk")
        if os.path.exists(NODE_MISSING):
            raise unittest.SkipTest(f"{NODE_MISSING} unexpectedly exists")

    def _args(self, live_from_start, node_path):
        return build_args(
            URL,
            DESTINATION,
            TEMPLATE,
            live_from_start,
            YTDLP,
            node_path,
        )

    def test_starts_with_ytdlp_newline_and_no_update(self):
        args = self._args(False, "")
        self.assertEqual(args[:3], [YTDLP, "--newline", "--no-update"])

    def test_live_from_start_only_when_enabled(self):
        self.assertNotIn("--live-from-start", self._args(False, ""))
        self.assertIn("--live-from-start", self._args(True, ""))

    def test_live_choice_omits_live_from_start(self):
        self.assertNotIn("--live-from-start", self._args("live", ""))

    def test_rewind_choice_includes_live_from_start(self):
        self.assertIn("--live-from-start", self._args("rewind", ""))

    def test_node_flags_absent_when_node_path_empty(self):
        args = self._args(True, "")
        for flag in JS_FLAGS:
            self.assertNotIn(flag, args)
        self.assertFalse(any(arg.startswith("node:") for arg in args))

    def test_node_flags_present_when_path_exists(self):
        args = self._args(False, NODE_EXISTS)
        js = args.index("--js-runtimes")
        self.assertEqual(args[js + 1], "node:" + NODE_EXISTS)
        remote = args.index("--remote-components")
        self.assertEqual(args[remote + 1], "ejs:github")

    def test_node_flags_absent_when_path_does_not_exist(self):
        args = self._args(True, NODE_MISSING)
        for flag in JS_FLAGS:
            self.assertNotIn(flag, args)
        self.assertFalse(any(arg.startswith("node:") for arg in args))

    def test_remux_output_template_and_url(self):
        args = self._args(True, "")
        remux = args.index("--remux-video")
        self.assertEqual(args[remux + 1], "mp4")
        output = args.index("-o")
        self.assertEqual(args[output + 1], DESTINATION + "/" + TEMPLATE)
        self.assertIn(URL, args)
        self.assertEqual(args[-1], URL)


if __name__ == "__main__":
    unittest.main()
