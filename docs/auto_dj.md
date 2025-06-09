# Auto-DJ Command

The **Auto-DJ** feature lets RadioFreeDJ automatically select and queue the next track using GPT. When you press **`1`** in the menu, the program:

1. Builds a prompt from `prompts.json` under the `auto_dj` key.
2. Sends the prompt to the configured GPT model via `RadioFreeDJ.ask`.
3. Expects a JSON response containing `track_name` and `artist_name`.
4. Searches Spotify for the track and queues it if found.
5. Generates a short radio‑style intro for the queued track using the `generate_radio_intro` prompt and prints it in the console.

If the response cannot be parsed or the track isn't found, a warning is logged and nothing is queued.

This command integrates GPT recommendations with the real Spotify queue so that the station keeps playing new songs without manual search.
