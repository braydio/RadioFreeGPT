# Lyrics Breakdown Feature

Press **`7`** in the main menu to ask GPT for a lyrical interpretation of the currently playing song.

The program will:
1. Fetch the full lyrics from Genius.
2. Send them along with the song title and artist to the GPT model using the `explain_lyrics` prompt from `prompts.json`.
3. Display GPT's creative but accurate analysis in the console.

If lyrics cannot be found, you'll receive a message indicating that no analysis is available.
