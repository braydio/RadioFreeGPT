import os
import time
from dotenv import load_dotenv
import pylast
from logger_utils import setup_logger

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")
SESSION_KEY = os.getenv("LASTFM_SESSION_KEY")

logger = setup_logger(__name__)

_network = None


def get_network():
    global _network
    if _network is None:
        if not (API_KEY and API_SECRET and SESSION_KEY):
            logger.warning("Last.fm credentials not configured")
            return None
        _network = pylast.LastFMNetwork(
            api_key=API_KEY,
            api_secret=API_SECRET,
            session_key=SESSION_KEY,
        )
    return _network


def update_now_playing(track_name: str, artist_name: str):
    network = get_network()
    if not network:
        return
    try:
        network.update_now_playing(artist=artist_name, title=track_name)
        logger.info("Updated now playing: %s - %s", artist_name, track_name)
    except Exception as e:
        logger.error("Last.fm now playing error: %s", e)


def scrobble(track_name: str, artist_name: str, timestamp: int | None = None):
    network = get_network()
    if not network:
        return
    if timestamp is None:
        timestamp = int(time.time())
    try:
        network.scrobble(artist=artist_name, title=track_name, timestamp=timestamp)
        logger.info("Scrobbled: %s - %s", artist_name, track_name)
    except Exception as e:
        logger.error("Last.fm scrobble error: %s", e)
