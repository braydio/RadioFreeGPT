# Auto-DJ Command

The **Auto-DJ** feature can keep the queue populated with GPT suggestions. Press **`1`** to toggle the mode. When enabled, the program will:

1. Builds a prompt from `prompts.json` under the `auto_dj` key.
2. Sends the prompt to the configured GPT model via `RadioFreeDJ.ask`.
3. Expects a JSON response containing `track_name` and `artist_name`.
4. Searches Spotify for the track and queues it if found.
5. Generate a short radio‑style intro for each queued track using the `generate_radio_intro` prompt and print it in the console.

If the response cannot be parsed or the track isn't found, a warning is logged and nothing is queued. Recently played tracks are remembered so the DJ avoids immediate repeats.

When Auto-DJ is turned off, no additional songs are queued automatically.
