import unittest
from unittest.mock import MagicMock

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from spotify_utils import SpotifyController

class SpotifyControllerTest(unittest.TestCase):
    def setUp(self):
        self.ctrl = SpotifyController.__new__(SpotifyController)
        self.ctrl.sp = MagicMock()
        self.ctrl.logger = MagicMock()

    def test_restart_track_calls_seek(self):
        self.ctrl.restart_track()
        self.ctrl.sp.seek_track.assert_called_with(0)

    def test_skip_to_end_uses_duration(self):
        self.ctrl.sp.current_playback.return_value = {"item": {"duration_ms": 10000}}
        self.ctrl.skip_to_end()
        self.ctrl.sp.seek_track.assert_called_with(9000)

if __name__ == '__main__':
    unittest.main()
