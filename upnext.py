import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


class UpNextManager:
    @property
    def playlist_mode(self):
        return self.mode == "playlist"

    def __init__(self, gpt_dj, spotify_controller, prompt_templates):
        self.dj = gpt_dj
        self.sp = spotify_controller
        self.templates = prompt_templates
        self.queue = []
        self.mode = "smart"
        self.console = Console()

    def toggle_playlist_mode(self):
        self.mode = "playlist" if self.mode == "smart" else "smart"
        self.console.print(Panel(f"[bold cyan]Switched to [green]{self.mode}[/green] mode.[/bold cyan]"))

    def auto_dj_transition(self, current_song, current_artist):
        prompt = self.templates["auto_dj"].format(song_name=current_song, artist_name=current_artist)
        resp = self.dj.ask(prompt)
        self.dj.logger.info(f"[auto_dj_transition] Prompt:\n{prompt}")
        self.dj.logger.info(f"[auto_dj_transition] Raw Response:\n{resp}")

        try:
            parsed = json.loads(resp.replace("'", '"'))
            track_name = parsed.get("track_name")
            artist_name = parsed.get("artist_name")
            if track_name and artist_name:
                self.queue.insert(0, {"track_name": track_name, "artist_name": artist_name})
                self.dj.logger.info(f"Queued track: {track_name} by {artist_name}")
            else:
                self.dj.logger.warning("Missing track data in GPT response.")
        except Exception as e:
            self.dj.logger.error(f"Error parsing GPT response as JSON: {e}")
            return

        if not self.queue:
            return

        next_track = self.queue.pop(0)
        intro = self._generate_radio_intro(next_track["track_name"], next_track["artist_name"])
        self.console.print(Panel(intro, title=" DJ Intro", border_style="blue"))

        track_uri = self.sp.search_track(next_track["track_name"], next_track["artist_name"])
        if track_uri:
            self.sp.play_track(track_uri)
        else:
            self.console.print(
                f"[red] Could not find: {next_track['track_name']} by {next_track['artist_name']}[/red]"
            )

    def queue_one_song(self, song_name, artist_name):
        prompt = self.templates["recommend_next_song"].format(song_name=song_name, artist_name=artist_name)
        response = self.dj.ask(prompt)
        if response:
            try:
                track = json.loads(response.replace("'", '"'))
                self.queue.append(track)
                self.console.print(f"[green]➕ Queued:[/green] {track['track_name']} by {track['artist_name']}")
            except json.JSONDecodeError:
                self.console.print("[red]Failed to parse GPT response.[/red]")
        else:
            self.console.print("[red]No song queued.[/red]")

    def queue_ten_songs(self, song_name, artist_name):
        prompt = self.templates["recommend_next_ten_songs"].format(song_name=song_name, artist_name=artist_name)
        response = self.dj.ask(prompt)
        if response:
            lines = response.strip().split("\n")
            count = 0
            for line in lines:
                if "." in line and " by " in line:
                    try:
                        title = line.split(". ", 1)[1]
                        track, artist = title.rsplit(" by ", 1)
                        self.queue.append({"track_name": track.strip(), "artist_name": artist.strip()})
                        count += 1
                    except Exception:
                        continue
            self.console.print(f"[green]➕ Queued {count} songs.[/green]")
        else:
            self.console.print("[red]No songs queued.[/red]")

    def queue_playlist(self, song_name, artist_name):
        prompt = self.templates["create_playlist"].format(song_name=song_name, artist_name=artist_name)
        self._parse_and_queue_playlist(prompt)

    def queue_theme_playlist(self):
        theme = Prompt.ask("Enter a theme (e.g., focus, happy, roadtrip)").strip()
        prompt = self.templates["theme_based_playlist"].format(theme=theme)
        self._parse_and_queue_playlist(prompt)

    def _parse_and_queue_playlist(self, prompt):
        response = self.dj.ask(prompt)
        if response:
            lines = response.strip().split("\n")
            count = 0
            for line in lines:
                if "." in line and " by " in line:
                    try:
                        title = line.split(". ", 1)[1]
                        track, artist = title.rsplit(" by ", 1)
                        self.queue.append({"track_name": track.strip(), "artist_name": artist.strip()})
                        count += 1
                    except Exception:
                        continue
            self.mode = "playlist"
            self.console.print(f"[green]📀 Playlist queued with {count} tracks.[/green]")
        else:
            self.console.print("[red]Playlist creation failed.[/red]")

    def song_insight(self, song_name, artist_name):
        prompt = self.templates["song_insights"].format(song_name=song_name, artist_name=artist_name)
        response = self.dj.ask(prompt)
        if response:
            self.console.print(Panel(response, title=" Insight", border_style="cyan"))
        else:
            self.console.print("[red]No insight generated.[/red]")

    def _generate_radio_intro(self, track_name, artist_name):
        prompt = self.templates["generate_radio_intro"].format(track_name=track_name, artist_name=artist_name)
        response = self.dj.ask(prompt)
        return response or " [DJ dead air] No intro available."
