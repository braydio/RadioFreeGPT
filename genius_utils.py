import os
import logging
import lyricsgenius
from dotenv import load_dotenv
from logger_utils import setup_logger

load_dotenv()

GENIUS_TOKEN = os.getenv("GENIUS_API_TOKEN")
logger = setup_logger(__name__)

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
        logger.error("Genius error: %s", e)
        return None
