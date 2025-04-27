# main.py

import os
from dotenv import load_dotenv
from time import sleep
from gpt_dj import RadioFreeDJ
from spotify_utils import SpotifyController

# === Load Environment Variables ===
load_dotenv()

# === Initialize Components ===
api_key = os.getenv("OPENAI_API_KEY")
gpt_model = os.getenv("GPT_MODEL", "gpt-4o-mini")
log_path = os.path.join(os.path.dirname(__file__), "requests.log")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in .env!")

gpt_dj = RadioFreeDJ(api_key=api_key, active_model=gpt_model, log_path=log_path)
spotify_controller = SpotifyController()


# === Display Menu ===
def display_menu():
    print("\n🎛️  FreeRadio Main Menu 🎛️")
    print("1. Let GPT recommend and auto-play next song")
    print("2. Recommend the next song (manual)")
    print("3. Recommend the next 10 songs")
    print("4. Create a playlist")
    print("5. Create a themed playlist")
    print("6. Get FreeFact about current song")
    print("0. Quit")


# === GPT Actions ===
def recommend_next_song(song_name, artist_name):
    """Use GPT to recommend the next song."""
    prompt = (
        f"Reference song: '{song_name}' by {artist_name}. "
        "Recommend a similar song. Respond ONLY in JSON format:\n"
        "{'track_name': '<TRACK NAME>', 'artist_name': '<ARTIST NAME>'}"
    )
    response = gpt_dj.ask(prompt)
    print(f"\n🎶 GPT Recommendation:\n{response}")
    return response


def recommend_next_ten_songs(song_name, artist_name):
    """Use GPT to recommend next 10 songs."""
    prompt = (
        f"Reference song: '{song_name}' by {artist_name}. "
        "List 10 similar songs in the format:\n"
        "1. [Track Title] by [Artist Name]\n"
        "2. [Track Title] by [Artist Name]\n"
        "..."
    )
    response = gpt_dj.ask(prompt)
    print(f"\n🎶 GPT Recommendations:\n{response}")


def create_playlist(song_name, artist_name):
    """Create playlist based on current song."""
    prompt = (
        f"The current song is '{song_name}' by {artist_name}. "
        "Create a playlist of 15 songs matching the same vibe."
    )
    response = gpt_dj.ask(prompt)
    print(f"\n📻 FreeRadio Playlist:\n{response}")


def song_insights(song_name, artist_name):
    """Get GPT insight about the current song."""
    prompt = (
        f"Provide an interesting radio host style insight about '{song_name}' by {artist_name}. "
        "Keep it short and engaging."
    )
    response = gpt_dj.ask(prompt)
    print(f"\n🎙️ FreeFact:\n{response}")


def theme_based_playlist():
    """Generate a themed playlist."""
    theme = input("\nEnter a theme (e.g., focus, happy, sad): ").strip()
    prompt = (
        f"Create a playlist of 10 songs fitting the theme '{theme}'. "
        "Format:\n1. [Track Title] by [Artist Name]"
    )
    response = gpt_dj.ask(prompt)
    print(f"\n🎶 Themed Playlist:\n{response}")


# === Main Event Loop ===
def main():
    try:
        while True:
            print("\n🎵 Welcome to FreeRadioGPT! All Ads → No Music 🎵")
            print("-" * 45)

            song_name, artist_name = spotify_controller.get_current_song()

            if not song_name or not artist_name:
                print("🎶 No song playing currently. Retrying in 10 seconds...")
                sleep(10)
                continue

            print(f"\n🎶 Now Playing: '{song_name}' by {artist_name}")
            display_menu()

            choice = input("\nSelect an option (0-6): ").strip()

            if choice == "1":
                print("\n🎛️ Auto-DJ activated...")
                json_response = recommend_next_song(song_name, artist_name)
                if json_response:
                    try:
                        import json

                        recommendation = json.loads(json_response)
                        track_name = recommendation.get("track_name")
                        artist_name = recommendation.get("artist_name")
                        if track_name and artist_name:
                            track_uri = spotify_controller.search_track(
                                track_name, artist_name
                            )
                            if track_uri:
                                spotify_controller.play_track(track_uri)
                    except json.JSONDecodeError:
                        print("⚠️ Failed to parse GPT response. Try again.")

            elif choice == "2":
                recommend_next_song(song_name, artist_name)

            elif choice == "3":
                recommend_next_ten_songs(song_name, artist_name)

            elif choice == "4":
                create_playlist(song_name, artist_name)

            elif choice == "5":
                theme_based_playlist()

            elif choice == "6":
                song_insights(song_name, artist_name)

            elif choice == "0":
                print("\n👋 Thanks for tuning in to FreeRadioGPT!")
                break

            else:
                print("\n⚠️ Invalid option. Please select 0-6.")

    except KeyboardInterrupt:
        print("\n👋 Exiting FreeRadioGPT!")


# === Entry Point ===
if __name__ == "__main__":
    main()
