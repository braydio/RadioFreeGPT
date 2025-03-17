
import os
import re
import subprocess
import openai

from dotenv import load_dotenv
from time import sleep
from pydbus import SessionBus


# Load environment variables
project_dir = os.path.dirname(__file__)
print(f"Project directory: {project_dir}")
env_path = os.path.join(project_dir, ".env")
load_dotenv(env_path)
active_gpt_model = "gpt-4o-mini"
requests_log = os.path.join(project_dir, "RadioFreeGPT.log")

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set or failed to load from .env.")

# Path to ncspot logs
ncspot_log_path = os.path.join(os.getenv("USER_CACHE_PATH", "/home/braydenchaffee/.cache/ncspot"), "ncspot.log")

class RadioFreeGPT:
    def __init__(self):
        print("🎵 Welcome to RadioFreeGPT! All Ads -> No Music! Go Fuck Yourself! 🎵")

    def log_gpt_request(self, prompt, token_count):
        with open(requests_log, "a") as log_file:
            log_file.write(f"--- GPT Request ---\n")
            log_file.write(f"Token Count: {token_count}\n")
            log_file.write(f"Prompt Sent:\n{prompt}\n")
            log_file.write(f"--- End of Request ---\n\n")
    
    def log_gpt_response(self, response):
        with open(RadioFreeGPT_log, "a") as log_file:
            log_file.write(f" RadioFreeGPT: ")
            log_file.write(response)

    def ask_gpt(self, prompt):
        RadioFreeGPT.log_gpt_request(self, prompt, len(prompt))
        
        # Make sure API key is not None before calling
        if not openai.api_key:
            raise RuntimeError("OpenAI API key is not set. Please check .env and environment variables.")
        
        response = openai.ChatCompletion.create(
            model=active_gpt_model,
            messages=[{"role": "user", "content": prompt}]
        )      
        return response['choices'][0]['message']['content']

    def recommend_next_song(self, song_name, artist):
        """Uses ChatGPT to recommend the next song."""
        if not song_name or not artist:
            print("No song or artist provided for recommendation.")
            return None

        prompt = (
        f"The current song is '{song_name}' by {artist}. "
        "Suggest the next track that matches the mood, style, or genre, but avoid repeating the same artist. "
        "Focus on unique or underrated tracks that might not be overly mainstream. "
        "Respond in this json format: {{'track_name': '<TRACK NAME>', 'artist_name': '<ARTIST NAME>'}}"
        "Only provide the track and artist name, with no additional text."
        )

        print(f" > User Prompt Sent to ChatGPT : {prompt}")
        try:
            RadioFreeGPT.ask_gpt(self, prompt)
            response = openai.ChatCompletion.create(
                model=active_gpt_model,   
                messages=[{"role": "user", "content": prompt}]
            )
            next_song = response["choices"][0]["message"]["content"].strip()
            print(f"🎵 Recommended Next Song: {next_song}")
            return next_song 
        except Exception as e:
            print(f"Unexpected error: {e}")
        return None

    def play_song(self, song):
        """Plays a given song using ncspot CLI."""
        try:
            print(f"🎧 Playing: {song}")
            command = f"ncspot-cli play '{song}'"
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error playing song with MOTHrRFUckinG ncspot-cli: {e}")
        except Exception as e:
            print(f"Unexpected error playing song: {e}")

 
    def get_current_song(self):
        """Fetch the current song from the ncspot MPRIS instance."""
        bus = SessionBus()
        instance = self.get_ncspot_instance()
        if not instance:
            print("ncspot is not running or MPRIS is not enabled.")
            return None, None

        try:
            # Use fixed object path for MPRIS
            player = bus.get(instance, '/org/mpris/MediaPlayer2')
            metadata = player.Metadata
            song_name = metadata.get("xesam:title", "Unknown Title")
            artist = metadata.get("xesam:artist", ["Unknown Artist"])[0]
            print(f"🎶 Now Playing: '{song_name}' by {artist}")
            return song_name, artist
        except Exception as e:
            print(f"Error fetching song data: {e}")
            return None, None

    def get_ncspot_instance(self):
        """Find the active ncspot MPRIS instance."""
        bus = SessionBus()
        try:
            dbus_proxy = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
            names = dbus_proxy.ListNames()
            for name in names:
                if name.startswith("org.mpris.MediaPlayer2.ncspot"):
                    print(f"Found Spotify instance running in ncspot.")
                    return name
        except Exception as e:
            print(f"Error querying D-Bus for ncspot instance: {e}")
        print("No ncspot instance found.")
        return None

    def run(self):
        """Main loop for the DJ."""
        try:
            while True:
                song_name, artist = self.get_current_song()
                if not song_name or not artist:
                    print("Just tried... Retrying in 10 seconds...")
                    sleep(10)
                    continue

                next_song = self.recommend_next_song(song_name, artist)
                if next_song:
                    self.play_song(next_song)

                user_input = input("\nCommand (next, quit): ").strip().lower()
                if user_input == "next":
                    continue
                elif user_input == "quit":
                    print("🎧 See ya later crocogator! 🎧")
                    break
                else:
                    print("Invalid command. Try 'next' or 'quit'.")
        except KeyboardInterrupt:
            print("\n🎧 Hasta la Vista, Baby! 🎧")

if __name__ == "__main__":
    dj = RadioFreeGPT()
    dj.run()
