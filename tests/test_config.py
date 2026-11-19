"""Default destination and loading of saved settings."""

import json
import os
import tempfile
import unittest
from unittest import mock

from livegrab_lib.config import default_config, load_config, save_config


class DestinationDefaultTests(unittest.TestCase):
    def test_default_destination_is_empty(self):
        self.assertEqual(default_config()["destination"], "")

    def test_saved_absolute_destination_is_unchanged(self):
        saved_paths = ("/tmp/livegrab-dest", "C:\\Users\\someone\\Videos")
        for destination in saved_paths:
            with self.subTest(destination=destination):
                with tempfile.TemporaryDirectory() as directory:
                    path = os.path.join(directory, "config.json")
                    with open(path, "w", encoding="utf-8") as handle:
                        json.dump(
                            {
                                "destination": destination,
                                "template": "%(id)s.%(ext)s",
                            },
                            handle,
                        )
                    with mock.patch("livegrab_lib.config.CONFIG_PATH", path):
                        loaded = load_config()
                self.assertEqual(loaded["destination"], destination)

    def test_other_destination_is_kept(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            destination = os.path.join(directory, "videos")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"destination": destination}, handle)
            with mock.patch("livegrab_lib.config.CONFIG_PATH", path):
                loaded = load_config()
        self.assertEqual(loaded["destination"], destination)

    def test_blank_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "config.json")
            with mock.patch("livegrab_lib.config.CONFIG_PATH", path):
                with self.assertRaises(ValueError) as caught:
                    save_config(
                        {
                            "destination": "   ",
                            "template": "%(id)s.%(ext)s",
                            "audio_source": "live",
                        }
                    )
                saved = save_config(
                    {
                        "destination": os.path.join(directory, "videos"),
                        "template": "%(id)s.%(ext)s",
                        "audio_source": "live",
                    }
                )
        self.assertEqual(str(caught.exception), "Choose a folder before starting")
        self.assertEqual(saved["destination"], os.path.join(directory, "videos"))
        self.assertEqual(saved["audio_source"], "live")
        self.assertIs(saved["live_from_start"], False)


if __name__ == "__main__":
    unittest.main()
