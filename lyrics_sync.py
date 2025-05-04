import time
import re
from rich.text import Text
from genius_utils import get_lyrics
import requests
from requests.exceptions import RequestException


class LyricsSyncManager:
    def __init__(self, spotify_controller):
        self.spotify = spotify_controller
        self.lyrics_lines = []
        self.current_index = 0
        self.current_display = Text(" Loading lyrics...", style="cyan")

    def _parse_lrc(self, lyrics):
        pattern = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
        parsed = []
        for line in lyrics.splitlines():
            match = pattern.match(line)
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                timestamp = int((minutes * 60 + seconds) * 1000)
                text = match.group(3).strip()
                parsed.append((timestamp, text))
        return sorted(parsed)

    def _simulate_timing(self, raw_lyrics):
        lines = raw_lyrics.split("\n")
        return [
            (i * 4000, line.strip()) for i, line in enumerate(lines) if line.strip()
        ]

    def _fetch_from_lrclib(self, song, artist, retries=3):
        url = f"https://api.lrclib.net/api/get?track_name={song}&artist_name={artist}"
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                return response.json()
            except RequestException as e:
                if attempt == retries - 1:
                    print(f"LRC sync failed: {e}")
                    return None
                time.sleep(1)

    def start(self, song_name, artist_name):
        self.current_display = Text(" Loading lyrics...", style="cyan")
        self.current_index = 0

        lrc = self._fetch_from_lrclib(song_name, artist_name)
        if lrc and (lrc.get("syncedLyrics") or lrc.get("rawLyrics")):
            lyrics = lrc.get("syncedLyrics") or lrc.get("rawLyrics")
            self.lyrics_lines = self._parse_lrc(lyrics)
        else:
            fallback = get_lyrics(song_name, artist_name)
            if fallback:
                self.lyrics_lines = self._simulate_timing(fallback)
            else:
                self.current_display = Text(" No lyrics found.", style="red")
                self.lyrics_lines = []

    def sync(self, progress_ms):
        lines = self.lyrics_lines
        if not lines:
            return

        for i in range(len(lines)):
            if i + 1 >= len(lines) or progress_ms < lines[i + 1][0]:
                self.current_index = i
                break

        start = max(0, self.current_index - 4)
        end = min(len(lines), start + 8)
        chunk = lines[start:end]

        display = Text()
        for idx, (ts, line) in enumerate(chunk):
            if start + idx == self.current_index:
                display.append(f"→ {line}\n", style="bold green")
            else:
                display.append(f"  {line}\n", style="dim")

        self.current_display = display

    def get_text(self):
        return self.current_display
