# spotify_utils.py
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from logger_utils import setup_logger

# Load environment variables
load_dotenv()


class SpotifyController:
    def __init__(self):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope=(
                    "user-read-playback-state "
                    "user-modify-playback-state "
                    "user-read-currently-playing "
                    "user-read-private "
                    "user-library-read"
                ),
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            )
        )
        self.logger = setup_logger(self.__class__.__name__)

    def get_current_song(self):
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return None, None
            song_name = current["item"]["name"]
            artist_name = current["item"]["artists"][0]["name"]
            return song_name, artist_name
        except Exception as e:
            self.logger.error("Error fetching current song: %s", e)
            return None, None

    def search_track(self, track_name, artist_name):
        try:
            query = f"track:{track_name} artist:{artist_name}"
            result = self.sp.search(q=query, type="track", limit=1)
            tracks = result.get("tracks", {}).get("items", [])
            return tracks[0]["uri"] if tracks else None
        except Exception as e:
            self.logger.error("Error searching track: %s", e)
            return None

    def play_track(self, track_uri):
        try:
            devices = self.sp.devices().get("devices", [])
            if not devices:
                self.logger.warning("No active Spotify device")
                return
            device_id = devices[0]["id"]
            self.sp.transfer_playback(device_id, force_play=True)
            self.sp.start_playback(uris=[track_uri])
        except Exception as e:
            self.logger.error("Error playing track: %s", e)

    def pause(self):
        try:
            self.sp.pause_playback()
        except Exception as e:
            self.logger.error("Error pausing: %s", e)

    def resume(self):
        try:
            self.sp.start_playback()
        except Exception as e:
            self.logger.error("Error resuming: %s", e)

    def next(self):
        try:
            self.sp.next_track()
        except Exception as e:
            self.logger.error("Error skipping: %s", e)

    def previous(self):
        try:
            self.sp.previous_track()
        except Exception as e:
            self.logger.error("Error going back: %s", e)

    def set_volume(self, vol_percent):
        try:
            self.sp.volume(vol_percent)
        except Exception as e:
            self.logger.error("Error setting volume: %s", e)

    def add_to_queue(self, track_uri):
        try:
            self.sp.add_to_queue(track_uri)
        except Exception as e:
            self.logger.error("Error adding to queue: %s", e)

    def pause(self):
        try:
            self.sp.pause_playback()
        except Exception as e:
            self.logger.error("Error pausing playback: %s", e)

    def resume(self):
        try:
            self.sp.start_playback()
        except Exception as e:
            self.logger.error("Error resuming playback: %s", e)

    def next_track(self):
        try:
            self.sp.next_track()
        except Exception as e:
            self.logger.error("Error skipping to next track: %s", e)

    def previous_track(self):
        try:
            self.sp.previous_track()
        except Exception as e:
            self.logger.error("Error going to previous track: %s", e)

    def change_volume(self, delta):
        try:
            playback = self.sp.current_playback()
            if not playback or "device" not in playback:
                self.logger.warning("No active device")
                return
            current_vol = playback["device"]["volume_percent"]
            new_vol = min(100, max(0, current_vol + delta))
            self.sp.volume(new_vol)
            self.logger.info("Volume set to %d%%", new_vol)
        except Exception as e:
            self.logger.error("Error changing volume: %s", e)

