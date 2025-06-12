import sys, os

os.environ.setdefault("GENIUS_API_TOKEN", "dummy")
import unittest
import json

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


class BatchDJ(DummyDJ):
    def __init__(self, response):
        super().__init__()
        self.calls = 0
        self.response = response

    def ask(self, prompt):
        self.calls += 1
        return self.response


class DummySpotify:
    def search_track(self, track, artist):
        return f"uri:{track}:{artist}"

    def add_to_queue(self, uri):
        pass


class CaptureSpotify(DummySpotify):
    def __init__(self):
        self.added = []

    def add_to_queue(self, uri):
        self.added.append(uri)


class UpNextTest(unittest.TestCase):
    def test_recent_track_skip(self):
        mgr = UpNextManager(DummyDJ(), DummySpotify(), {})
        mgr.recent_tracks.append(("Song", "Artist"))
        added = mgr._queue_track("Song", "Artist")
        self.assertFalse(added)

    def test_maintain_queue_caps_length(self):
        response = json.dumps(
            [
                {"track_name": f"Song{i}", "artist_name": f"Artist{i}", "intro": ""}
                for i in range(6)
            ]
        )
        dj = BatchDJ(response)
        sp = CaptureSpotify()
        mgr = UpNextManager(dj, sp, {"auto_dj_batch": ""})
        mgr.auto_dj_enabled = True
        mgr.maintain_queue("Current", "Artist")
        self.assertEqual(len(mgr.queue), 5)
        self.assertEqual(dj.calls, 1)
        self.assertIn(("Current", "Artist"), mgr.recent_tracks)

    def test_batch_called_once(self):
        response = json.dumps(
            [
                {"track_name": "Song1", "artist_name": "Artist1", "intro": "hi"},
                {"track_name": "Song2", "artist_name": "Artist2", "intro": "hi"},
            ]
        )
        dj = BatchDJ(response)
        sp = CaptureSpotify()
        mgr = UpNextManager(dj, sp, {"auto_dj_batch": ""})
        mgr.auto_dj_enabled = True
        mgr.maintain_queue("Song0", "Artist0")
        self.assertEqual(dj.calls, 1)
        mgr.maintain_queue("Song0", "Artist0")
        self.assertEqual(dj.calls, 1)


if __name__ == "__main__":
    unittest.main()
