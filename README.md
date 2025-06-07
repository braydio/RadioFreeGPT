Save this to .env in the root dir

```
# === REQUIRED FOR GPT FUNCTIONALITY ===
OPENAI_API_KEY=your-openai-api-key-here
GPT_MODEL=gpt-4o-mini  # or gpt-4, gpt-3.5-turbo, etc.

# === REQUIRED FOR GENIUS LYRICS SYNC ===
GENIUS_API_TOKEN=your-genius-api-token-here

# === REQUIRED FOR SPOTIFY INTEGRATION ===
SPOTIPY_CLIENT_ID=your-spotify-client-id
SPOTIPY_CLIENT_SECRET=your-spotify-client-secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback  # or your actual callback URI

```

Using `spotifyd` on Linux
-------------------------
On systems like Arch Linux you can run a headless Spotify client with
[`spotifyd`](https://github.com/Spotifyd/spotifyd). Start `spotifyd` before
running RadioFreeDJ so that the Spotify Web API has an active device to queue
tracks to.

Last.fm Integration
-------------------
To enable scrobbling, set these variables in your `.env` file:

```
LASTFM_API_KEY=your-lastfm-api-key
LASTFM_API_SECRET=your-lastfm-api-secret
LASTFM_SESSION_KEY=your-lastfm-session-key
```
The session key can be obtained by creating an API account on Last.fm and authenticating your user.
