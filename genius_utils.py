import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):
        return False
from logger_utils import setup_logger

load_dotenv()

GENIUS_TOKEN = os.getenv("GENIUS_API_TOKEN")
logger = setup_logger(__name__)

_genius_client = None


def _get_genius_client():
    """Return a cached lyricsgenius client, or None when unavailable."""

    global _genius_client

    if _genius_client is not None:
        return _genius_client

    if not GENIUS_TOKEN:
        logger.debug("GENIUS_API_TOKEN not set; skipping Genius lyrics lookup")
        return None

    try:
        import lyricsgenius  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        logger.debug("lyricsgenius is not installed; skipping Genius lyrics lookup")
        return None

    _genius_client = lyricsgenius.Genius(
        GENIUS_TOKEN,
        skip_non_songs=True,
        excluded_terms=["(Remix)", "(Live)"],
        timeout=10,
    )
    return _genius_client


def get_lyrics(song_name, artist_name):
    """
    Fetch raw (unsynced) lyrics from Genius as a fallback.
    """
    try:
        genius = _get_genius_client()
        if genius is None:
            return None
        song = genius.search_song(song_name, artist_name)
        if song and song.lyrics:
            return song.lyrics
        return None
    except Exception as e:
        logger.error("Genius error: %s", e)
        return None
