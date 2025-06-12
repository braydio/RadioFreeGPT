"""Helper functions for integrating with the Last.fm API.

This module provides a thin wrapper around :mod:`pylast` for submitting
"now playing" updates and scrobbles. It handles storing the user's
session key so that authentication only needs to occur once.
"""

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
    """Return an authenticated :class:`pylast.LastFMNetwork` instance."""

    global _network
    if _network is not None:
        return _network

    if not (API_KEY and API_SECRET):
        logger.warning("Last.fm credentials not configured")
        return None

    if SESSION_KEY:
        _network = pylast.LastFMNetwork(
            api_key=API_KEY,
            api_secret=API_SECRET,
            session_key=SESSION_KEY,
        )
        return _network

    network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)
    sg = pylast.SessionKeyGenerator(network)
    url = sg.get_web_auth_url()
    print(f"Authorize RadioFreeGPT with Last.fm: {url}")
    input("Press Enter after authorization...")
    try:
        session_key = sg.get_web_auth_session_key(url)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to obtain Last.fm session key: %s", e)
        return None

    os.environ["LASTFM_SESSION_KEY"] = session_key
    try:
        with open(".env", "a", encoding="utf-8") as env_file:
            env_file.write(f"\nLASTFM_SESSION_KEY={session_key}\n")
        logger.info("Stored Last.fm session key in .env")
    except OSError as e:  # noqa: PERF203
        logger.error("Could not save session key to .env: %s", e)

    _network = pylast.LastFMNetwork(
        api_key=API_KEY,
        api_secret=API_SECRET,
        session_key=session_key,
    )
    return _network


def update_now_playing(track_name: str, artist_name: str) -> None:
    """Submit the currently playing track to Last.fm."""

    network = get_network()
    if not network:
        return
    try:
        network.update_now_playing(artist=artist_name, title=track_name)
        logger.info("Updated now playing: %s - %s", artist_name, track_name)
    except Exception as e:  # noqa: BLE001
        logger.error("Last.fm now playing error: %s", e)


def scrobble(track_name: str, artist_name: str, timestamp: int | None = None) -> None:
    """Record that a track finished playing on Last.fm."""

    network = get_network()
    if not network:
        return
    if timestamp is None:
        timestamp = int(time.time())
    try:
        network.scrobble(
            artist=artist_name,
            title=track_name,
            timestamp=timestamp,
        )
        logger.info("Scrobbled: %s - %s", artist_name, track_name)
    except Exception as e:  # noqa: BLE001
        logger.error("Last.fm scrobble error: %s", e)
