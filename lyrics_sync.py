"""Fetch and synchronize track lyrics using `lrclib.net`."""

import time
import re
import json
from rich.text import Text
from genius_utils import get_lyrics
import requests
from requests.exceptions import RequestException
from logger_utils import setup_logger

logger = setup_logger(__name__)


class LyricsSyncManager:
    API_URL = "https://lrclib.net/api/get"

    def __init__(self, spotify_controller):
        self.spotify = spotify_controller
        self.timestamps = []
        self.lines = []
        self.current_index = 0
        self.logger = logger

    def start(self, track_name, artist_name, album_name="", duration_ms=0):
        self.current_index = 0
        try:
            ts, ls = self.fetch_lyrics(
                artist_name=artist_name,
                track_name=track_name,
                album_name=album_name,
                duration_ms=duration_ms,
            )
            if ts and ls:
                self.timestamps, self.lines = ts, ls
            else:
                raise ValueError("Empty LRC result")
        except Exception as e:
            self.logger.warning(f"No lyrics for '{track_name}' by '{artist_name}': {e}")
            self.timestamps = [0]
            self.lines = ["[dim]No lyrics found[/dim]"]

    def fetch_lyrics(self, artist_name, track_name, album_name, duration_ms):
        # skip any sub‑one‑second durations
        if duration_ms < 1000:
            self.logger.debug("duration_ms < 1000 (%d), skipping fetch", duration_ms)
            return [], []

        # convert to seconds and clamp
        secs = max(1, min(duration_ms // 1000, 3600))
        params = {
            "artist_name": artist_name,
            "track_name": track_name,
            "album_name": album_name,
            "duration": secs,
        }
        self.logger.debug("Requesting LRC: %s with %s", self.API_URL, params)

        try:
            resp = requests.get(self.API_URL, params=params, timeout=5)
            self.logger.debug("HTTP %s %s", resp.status_code, resp.url)
            snippet = resp.text.strip().splitlines()[:3]
            self.logger.debug("Body snippet:\n%s", "\n".join(snippet))

            resp.raise_for_status()
            text = resp.text.strip()

            # if JSON, extract the syncedLyrics field
            if text.startswith("{"):
                data = json.loads(text)
                lrc_text = data.get("syncedLyrics") or data.get("plainLyrics", "")
                if not lrc_text:
                    raise ValueError("No 'syncedLyrics' in JSON response")
            else:
                lrc_text = text

            return self.parse_lrc(lrc_text)

        except requests.RequestException as err:
            self.logger.error("LRC fetch error: %s", err)
            return [], []
        except json.JSONDecodeError:
            # not JSON, fall back to raw LRC parse
            return self.parse_lrc(resp.text)

    def parse_lrc(self, lrc_text):
        """
        Parse LRC “[MM:SS.ss] line” into ([ms…], [str…]).
        """
        pattern = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
        ts, lines = [], []
        for line in lrc_text.splitlines():
            m = pattern.match(line)
            if not m:
                continue
            mins = int(m.group(1))
            secs = float(m.group(2))
            ts.append(int((mins * 60 + secs) * 1000))
            lines.append(m.group(3).strip())
        return ts, lines

    def sync(self, progress_ms):
        while (
            self.current_index + 1 < len(self.timestamps)
            and progress_ms >= self.timestamps[self.current_index + 1]
        ):
            self.current_index += 1

    def get_text(self):
        return self.lines[self.current_index] if self.lines else ""
