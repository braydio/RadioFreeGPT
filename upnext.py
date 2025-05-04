# upnext.py

import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


class UpNextManager:
    @property
    def playlist_mode(self):
        return self.mode == "playlist"

    def __init__(self, gpt_dj, spotify_controller):
        self.gpt_dj = gpt_dj
        self.spotify = spotify_controller
        self.queue = []
        self.mode = "smart"  # "smart" or "playlist"

        self.console = Console()

    def toggle_playlist_mode(self):
        self.mode = "playlist" if self.mode == "smart" else "smart"
        self.console.print(
            Panel(
                f"[bold cyan]Switched to [green]{self.mode}[/green] mode.[/bold cyan]"
            )
        )

    def auto_dj_transition(self, current_song, current_artist):
        if not self.queue:
            self.queue_one_song(current_song, current_artist)

        if not self.queue:
            self.console.print("[red] Queue is empty. Cannot auto-transition.[/red]")
            return

        next_track = self.queue.pop(0)
        intro = self._generate_radio_intro(
            next_track["track_name"], next_track["artist_name"]
        )
        self.console.print(Panel(intro, title=" DJ Intro", border_style="blue"))

        track_uri = self.spotify.search_track(
            next_track["track_name"], next_track["artist_name"]
        )
        if track_uri:
            self.spotify.play_track(track_uri)
        else:
            self.console.print(
                f"[red] Could not find: {next_track['track_name']} by {next_track['artist_name']}[/red]"
            )

    def queue_one_song(self, song_name, artist_name):
        prompt = (
            f"Reference song: '{song_name}' by {artist_name}. "
            "Recommend a similar song. Respond ONLY in JSON format:\n"
            "{'track_name': '<TRACK NAME>', 'artist_name': '<ARTIST NAME>'}"
        )
        response = self.gpt_dj.ask(prompt)
        if response:
            try:
                track = json.loads(response)
                self.queue.append(track)
                self.console.print(
                    f"[green]➕ Queued:[/green] {track['track_name']} by {track['artist_name']}"
                )
            except json.JSONDecodeError:
                self.console.print("[red]Failed to parse GPT response.[/red]")
        else:
            self.console.print("[red]No song queued.[/red]")

    def queue_ten_songs(self, song_name, artist_name):
        prompt = (
            f"Reference song: '{song_name}' by {artist_name}. "
            "List 10 similar songs in the format:\n1. [Track Title] by [Artist Name]"
        )
        response = self.gpt_dj.ask(prompt)
        if response:
            lines = response.strip().split("\n")
            count = 0
            for line in lines:
                if "." in line and " by " in line:
                    try:
                        title = line.split(". ", 1)[1]
                        track, artist = title.rsplit(" by ", 1)
                        self.queue.append(
                            {"track_name": track.strip(), "artist_name": artist.strip()}
                        )
                        count += 1
                    except Exception:
                        continue
            self.console.print(f"[green]➕ Queued {count} songs.[/green]")
        else:
            self.console.print("[red]No songs queued.[/red]")

    def queue_playlist(self, song_name, artist_name):
        prompt = (
            f"The current song is '{song_name}' by {artist_name}. "
            "Create a playlist of 15 songs matching the same vibe."
        )
        self._parse_and_queue_playlist(prompt)

    def queue_theme_playlist(self):
        theme = Prompt.ask("Enter a theme (e.g., focus, happy, roadtrip)").strip()
        prompt = (
            f"Create a playlist of 10 songs fitting the theme '{theme}'. "
            "Format:\n1. [Track Title] by [Artist Name]"
        )
        self._parse_and_queue_playlist(prompt)

    def _parse_and_queue_playlist(self, prompt):
        response = self.gpt_dj.ask(prompt)
        if response:
            lines = response.strip().split("\n")
            count = 0
            for line in lines:
                if "." in line and " by " in line:
                    try:
                        title = line.split(". ", 1)[1]
                        track, artist = title.rsplit(" by ", 1)
                        self.queue.append(
                            {"track_name": track.strip(), "artist_name": artist.strip()}
                        )
                        count += 1
                    except Exception:
                        continue
            self.mode = "playlist"
            self.console.print(
                f"[green]📀 Playlist queued with {count} tracks.[/green]"
            )
        else:
            self.console.print("[red]Playlist creation failed.[/red]")

    def song_insight(self, song_name, artist_name):
        prompt = (
            f"Provide an interesting radio host style insight about '{song_name}' by {artist_name}. "
            "Keep it short and engaging."
        )
        response = self.gpt_dj.ask(prompt)
        if response:
            self.console.print(Panel(response, title=" Insight", border_style="cyan"))
        else:
            self.console.print("[red]No insight generated.[/red]")

    def _generate_radio_intro(self, track_name, artist_name):
        prompt = (
            f"Create a short and engaging radio-style intro for the song '{track_name}' by {artist_name}. "
            "It should sound like a real DJ on a talk show introducing it. Keep it under 30 words."
        )
        response = self.gpt_dj.ask(prompt)
        return response or " [DJ dead air] No intro available."
