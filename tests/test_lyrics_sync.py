import unittest
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("GENIUS_API_TOKEN", "dummy")

from lyrics_sync import LyricsSyncManager


class DummySpotify:
    pass


class LyricsSyncTest(unittest.TestCase):
    def test_start_returns_immediately_and_loads(self):
        mgr = LyricsSyncManager(DummySpotify())

        def fake_fetch(*a, **k):
            time.sleep(0.1)
            return [0, 1000], ["line1", "line2"]

        mgr.fetch_lyrics = fake_fetch

        start_time = time.time()
        mgr.start("Song", "Artist", duration_ms=2000)
        duration = time.time() - start_time
        self.assertLess(duration, 0.05)

        # wait for background thread to finish
        timeout = time.time() + 1
        while mgr.fetching and time.time() < timeout:
            time.sleep(0.05)

        self.assertTrue(mgr.ready)
        self.assertEqual(mgr.lines, ["line1", "line2"])


if __name__ == "__main__":
    unittest.main()
