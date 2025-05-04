# spotify_utils.py

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SpotifyController:
    def __init__(self):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope="user-read-playback-state user-modify-playback-state user-read-currently-playing",
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            )
        )

    def get_current_song(self):
        """Fetches the currently playing song from Spotify."""
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return None, None
            song_name = current["item"]["name"]
            artist_name = current["item"]["artists"][0]["name"]
            print(f"🎶 Now Playing: '{song_name}' by {artist_name}")
            return song_name, artist_name
        except Exception as e:
            print(f"Error fetching current song: {e}")
            return None, None

    def search_track(self, track_name, artist_name):
        """Search for a track by name and artist."""
        try:
            query = f"track:{track_name} artist:{artist_name}"
            result = self.sp.search(q=query, type="track", limit=1)
            tracks = result.get("tracks", {}).get("items", [])
            if tracks:
                track_uri = tracks[0]["uri"]
                print(f"🎵 Found track URI: {track_uri}")
                return track_uri
            else:
                print(f"No matching track found for '{track_name}' by '{artist_name}'.")
                return None
        except Exception as e:
            print(f"Error searching track: {e}")
            return None

    def play_track(self, track_uri):
        """Play a track immediately given its URI."""
        if not track_uri:
            print("No track URI provided to play.")
            return
        try:
            self.sp.start_playback(uris=[track_uri])
            print(f"🎧 Playing track: {track_uri}")
        except Exception as e:
            print(f"Error starting playback: {e}")

