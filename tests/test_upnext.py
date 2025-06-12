import sys, os

os.environ.setdefault("GENIUS_API_TOKEN", "dummy")
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from upnext import UpNextManager


class DummyDJ:
    def __init__(self):
        class L:
            def info(self, *a, **k):
                pass

            def warning(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        self.logger = L()

    def ask(self, prompt):
        return "{}"


class DummySpotify:
    def search_track(self, track, artist):
        return f"uri:{track}:{artist}"

    def add_to_queue(self, uri):
        pass


class UpNextTest(unittest.TestCase):
    def test_recent_track_skip(self):
        mgr = UpNextManager(DummyDJ(), DummySpotify(), {})
        mgr.recent_tracks.append(("Song", "Artist"))
        added = mgr._queue_track("Song", "Artist")
        self.assertFalse(added)

    def test_maintain_queue_caps_length(self):
        mgr = UpNextManager(DummyDJ(), DummySpotify(), {})
        mgr.auto_dj_enabled = True
        tracks = [(f"Song{i}", f"Artist{i}") for i in range(6)]
        gen = (t for t in tracks)

        def fake_auto_dj(curr_song, curr_artist):
            try:
                t = next(gen)
            except StopIteration:
                return False
            return mgr._queue_track(*t)

        mgr.auto_dj_transition = fake_auto_dj
        mgr.maintain_queue("Current", "Artist")
        self.assertEqual(len(mgr.queue), 5)
        self.assertIn(("Current", "Artist"), mgr.recent_tracks)

    def test_config_loading(self):
        cfg = {"host_name": "Sid", "intro_count": 2, "chatter_level": "talkative"}
        mgr = UpNextManager(DummyDJ(), DummySpotify(), {}, cfg)
        self.assertEqual(mgr.host_name, "Sid")
        self.assertEqual(mgr.intro_count, 2)
        self.assertEqual(mgr.chatter_level, "talkative")


if __name__ == "__main__":
    unittest.main()
