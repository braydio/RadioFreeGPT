import os
import lyricsgenius
from dotenv import load_dotenv

load_dotenv()

GENIUS_TOKEN = os.getenv("GENIUS_API_TOKEN")

genius = lyricsgenius.Genius(
    GENIUS_TOKEN, skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"], timeout=10
)


def get_lyrics(song_name, artist_name):
    """
    Fetch raw (unsynced) lyrics from Genius as a fallback.
    """
    try:
        song = genius.search_song(song_name, artist_name)
        if song and song.lyrics:
            return song.lyrics
        return None
    except Exception as e:
        print(f"[Genius Error] {e}")
        return None
