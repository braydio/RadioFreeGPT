import json
import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from mystery_mode import MysteryModeManager


class DummyLogger:
    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class DummyDJ:
    def __init__(self, response: str):
        self.response = response
        self.logger = DummyLogger()

    def ask(self, prompt, cancel_event=None):
        return self.response


class DummySpotify:
    def __init__(self):
        self.queued: list[str] = []
        self.played: list[str] = []

    def search_track(self, track, artist):
        return f"uri:{track}:{artist}"

    def add_to_queue(self, uri):
        self.queued.append(uri)

    def play_track(self, uri):
        self.played.append(uri)


class MysteryModeManagerTest(unittest.TestCase):
    def test_activate_round_queues_secret_pick(self):
        response = json.dumps(
            {
                "options": [
                    {"track_name": "Song A", "artist_name": "Artist A"},
                    {"track_name": "Song B", "artist_name": "Artist B"},
                    {"track_name": "Song C", "artist_name": "Artist C"},
                    {"track_name": "Song D", "artist_name": "Artist D"},
                    {"track_name": "Song E", "artist_name": "Artist E"},
                ],
                "selected_index": 2,
            }
        )
        dj = DummyDJ(response)
        sp = DummySpotify()
        manager = MysteryModeManager(dj, sp, "{song_name} - {artist_name}")
        manager.enabled = True

        display = manager.activate_round("Now", "Artist")

        self.assertIsNotNone(display)
        self.assertIn("1. Song A", display)
        self.assertNotIn("selected_index", display)
        self.assertTrue(manager.awaiting_choice)
        self.assertEqual(sp.queued, ["uri:Song B:Artist B"])

    def test_play_choice_starts_selected_track(self):
        response = json.dumps(
            {
                "options": [
                    {"track_name": "Song A", "artist_name": "Artist A"},
                    {"track_name": "Song B", "artist_name": "Artist B"},
                    {"track_name": "Song C", "artist_name": "Artist C"},
                    {"track_name": "Song D", "artist_name": "Artist D"},
                    {"track_name": "Song E", "artist_name": "Artist E"},
                ],
                "selected_index": 1,
            }
        )
        dj = DummyDJ(response)
        sp = DummySpotify()
        manager = MysteryModeManager(dj, sp, "{song_name} - {artist_name}")
        manager.enabled = True
        manager.activate_round("Now", "Artist")

        success, message = manager.play_choice(3)

        self.assertTrue(success)
        self.assertIn("Song C", message)
        self.assertFalse(manager.awaiting_choice)
        self.assertEqual(sp.played, ["uri:Song C:Artist C"])

    def test_activate_round_handles_bad_json(self):
        dj = DummyDJ("not json")
        sp = DummySpotify()
        manager = MysteryModeManager(dj, sp, "{song_name}")
        manager.enabled = True

        display = manager.activate_round("Now", "Artist")

        self.assertIsNone(display)
        self.assertFalse(manager.awaiting_choice)
        self.assertEqual(sp.queued, [])


if __name__ == "__main__":
    unittest.main()
