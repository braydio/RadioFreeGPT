"""Manage upcoming tracks and integrate GPT recommendations with Spotify."""

import json
from gpt_utils import parse_json_response
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from genius_utils import get_lyrics


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
        self.auto_dj_enabled = False
        self.recent_tracks: list[tuple[str, str]] = []

    def _queue_track(self, track_name: str, artist_name: str) -> bool:
        """Search Spotify and queue the track if found."""
        if not track_name or not artist_name:
            return False
        if (track_name, artist_name) in self.recent_tracks:
            self.dj.logger.info(
                f"Skipping recently played track: {track_name} by {artist_name}"
            )
            return False
        if any(
            t["track_name"] == track_name and t["artist_name"] == artist_name
            for t in self.queue
        ):
            return False
        uri = self.sp.search_track(track_name, artist_name)
        if uri:
            self.sp.add_to_queue(uri)
            self.queue.append({"track_name": track_name, "artist_name": artist_name})
            self.dj.logger.info(f"Queued track: {track_name} by {artist_name}")
            return True
        self.dj.logger.warning(
            f"Track not found for queueing: {track_name} by {artist_name}"
        )
        return False

    def show_queue(self):
        if not self.queue:
            self.console.print("[dim]Queue is empty.[/dim]")
            return
        lines = [
            f"{i}. {t['track_name']} - {t['artist_name']}"
            for i, t in enumerate(self.queue, 1)
        ]
        self.console.print(
            Panel("\n".join(lines), title="Up Next", border_style="blue")
        )

    def _queue_track(self, track_name: str, artist_name: str) -> bool:
        """Search Spotify and queue the track if found."""
        uri = self.sp.search_track(track_name, artist_name)
        if uri:
            self.sp.add_to_queue(uri)
            self.queue.append({"track_name": track_name, "artist_name": artist_name})
            self.dj.logger.info(f"Queued track: {track_name} by {artist_name}")
            return True
        self.dj.logger.warning(
            f"Track not found for queueing: {track_name} by {artist_name}"
        )
        return False

    def show_queue(self):
        if not self.queue:
            self.console.print("[dim]Queue is empty.[/dim]")
            return
        lines = [
            f"{i}. {t['track_name']} - {t['artist_name']}"
            for i, t in enumerate(self.queue, 1)
        ]
        self.console.print(
            Panel("\n".join(lines), title="Up Next", border_style="blue")
        )

    def _queue_track(self, track_name: str, artist_name: str) -> bool:
        """Search Spotify and queue the track if found."""
        if not track_name or not artist_name:
            return False
        if (track_name, artist_name) in self.recent_tracks:
            self.dj.logger.info(
                f"Skipping recently played track: {track_name} by {artist_name}"
            )
            return False
        if any(
            t["track_name"] == track_name and t["artist_name"] == artist_name
            for t in self.queue
        ):
            return False
        uri = self.sp.search_track(track_name, artist_name)
        if uri:
            self.sp.add_to_queue(uri)
            self.queue.append({"track_name": track_name, "artist_name": artist_name})
            self.dj.logger.info(f"Queued track: {track_name} by {artist_name}")
            return True
        self.dj.logger.warning(
            f"Track not found for queueing: {track_name} by {artist_name}"
        )
        return False

    def show_queue(self):
        if not self.queue:
            self.console.print("[dim]Queue is empty.[/dim]")
            return
        lines = [
            f"{i}. {t['track_name']} - {t['artist_name']}"
            for i, t in enumerate(self.queue, 1)
        ]
        self.console.print(
            Panel("\n".join(lines), title="Up Next", border_style="blue")
        )

    def toggle_playlist_mode(self):
        self.mode = "playlist" if self.mode == "smart" else "smart"
        self.console.print(
            Panel(
                f"[bold cyan]Switched to [green]{self.mode}[/green] mode.[/bold cyan]"
            )
        )

    def maintain_queue(self, current_song: str, current_artist: str) -> None:
        """Ensure the queue is populated when Auto-DJ mode is active."""

        if current_song and current_artist:
            track = (current_song, current_artist)
            if not self.recent_tracks or self.recent_tracks[-1] != track:
                self.recent_tracks.append(track)
                if len(self.recent_tracks) > 100:
                    self.recent_tracks.pop(0)

        if self.auto_dj_enabled and not self.queue:
            self._auto_dj_batch(current_song, current_artist)

        if len(self.queue) > 5:
            self.queue = self.queue[-5:]

    def auto_dj_transition(self, current_song, current_artist) -> bool:
        prompt = self.templates["auto_dj"].format(
            song_name=current_song, artist_name=current_artist
        )
        resp = self.dj.ask(prompt)
        self.dj.logger.info(f"[auto_dj_transition] Prompt:\n{prompt}")
        self.dj.logger.info(f"[auto_dj_transition] Raw Response:\n{resp}")

        try:
            parsed = parse_json_response(resp)
            track_name = parsed.get("track_name") if parsed else None
            artist_name = parsed.get("artist_name") if parsed else None
            if track_name and artist_name:
                if self._queue_track(track_name, artist_name):
                    intro = self._generate_radio_intro(track_name, artist_name)
                    self.console.print(
                        Panel(intro, title=" DJ Intro", border_style="blue")
                    )
                    return True
                self.console.print(
                    f"[red] Could not find: {track_name} by {artist_name}[/red]"
                )
                return False
            else:
                self.dj.logger.warning("Missing track data in GPT response.")
        except Exception as e:
            self.dj.logger.error(f"Error parsing GPT response as JSON: {e}")
        return False

    def _auto_dj_batch(self, current_song: str, current_artist: str) -> None:
        """Queue a batch of tracks returned by the GPT Auto-DJ."""

        prompt = self.templates["auto_dj_batch"].format(
            song_name=current_song, artist_name=current_artist
        )
        resp = self.dj.ask(prompt)
        self.dj.logger.info(f"[auto_dj_batch] Prompt:\n{prompt}")
        self.dj.logger.info(f"[auto_dj_batch] Raw Response:\n{resp}")

        try:
            items = json.loads(resp)
            if isinstance(items, dict):
                items = [items]
        except Exception as e:
            self.dj.logger.error(f"Error parsing GPT batch response: {e}")
            return

        for item in items:
            track_name = item.get("track_name")
            artist_name = item.get("artist_name")
            intro = item.get("intro")
            if self._queue_track(track_name, artist_name):
                if intro:
                    self.console.print(
                        Panel(intro, title=" DJ Intro", border_style="blue")
                    )
            if len(self.queue) >= 5:
                break

    def queue_one_song(self, song_name, artist_name):
        prompt = self.templates["recommend_next_song"].format(
            song_name=song_name, artist_name=artist_name
        )
        response = self.dj.ask(prompt)
        if not response:
            self.console.print("[red]No song queued.[/red]")
            return

        try:
            track = json.loads(response.replace("'", '"'))
            t_name = track.get("track_name") if isinstance(track, dict) else None
            a_name = track.get("artist_name") if isinstance(track, dict) else None
            if self._queue_track(t_name, a_name):
                self.console.print(
                    f"[green]➕ Queued:[/green] {t_name or 'Unknown'} by {a_name or 'Unknown'}"
                )
            else:
                self.console.print(
                    f"[red]Could not find: {t_name or 'Unknown'} by {a_name or 'Unknown'}[/red]"
                )
        except json.JSONDecodeError:
            self.console.print("[red]Failed to parse GPT response.[/red]")
        self.show_queue()

    def queue_ten_songs(self, song_name, artist_name):
        prompt = self.templates["recommend_next_ten_songs"].format(
            song_name=song_name, artist_name=artist_name
        )
        response = self.dj.ask(prompt)
        if not response:
            self.console.print("[red]No songs queued.[/red]")
            return

        lines = response.strip().split("\n")
        count = 0
        for line in lines:
            if "." in line and " by " in line:
                try:
                    title = line.split(". ", 1)[1]
                    track, artist = title.rsplit(" by ", 1)
                    if self._queue_track(track.strip(), artist.strip()):
                        count += 1
                except Exception:
                    continue
        self.console.print(f"[green]➕ Queued {count} songs.[/green]")
        self.show_queue()

    def queue_playlist(self, song_name, artist_name):
        prompt = self.templates["create_playlist"].format(
            song_name=song_name, artist_name=artist_name
        )
        self._parse_and_queue_playlist(prompt)

    def queue_theme_playlist(self):
        theme = Prompt.ask("Enter a theme (e.g., focus, happy, roadtrip)").strip()
        prompt = self.templates["theme_based_playlist"].format(theme=theme)
        self._parse_and_queue_playlist(prompt)

    def _parse_and_queue_playlist(self, prompt):
        response = self.dj.ask(prompt)
        if not response:
            self.console.print("[red]Playlist creation failed.[/red]")
            return

        lines = response.strip().split("\n")
        count = 0
        for line in lines:
            if "." in line and " by " in line:
                try:
                    title = line.split(". ", 1)[1]
                    track, artist = title.rsplit(" by ", 1)
                    if self._queue_track(track.strip(), artist.strip()):
                        count += 1
                except Exception:
                    continue
        self.mode = "playlist"
        self.console.print(f"[green]📀 Playlist queued with {count} tracks.[/green]")
        self.show_queue()

    def song_insight(self, song_name, artist_name):
        prompt = self.templates["song_insights"].format(
            song_name=song_name, artist_name=artist_name
        )
        response = self.dj.ask(prompt)
        if response:
            self.console.print(Panel(response, title=" Insight", border_style="cyan"))
        else:
            self.console.print("[red]No insight generated.[/red]")

    def explain_lyrics(self, song_name, artist_name):
        """Generate a detailed explanation of the song's lyrics via GPT."""
        lyrics = get_lyrics(song_name, artist_name)
        if not lyrics:
            self.console.print("[red]Lyrics not found.[/red]")
            return
        prompt = self.templates["explain_lyrics"].format(
            song_name=song_name, artist_name=artist_name, lyrics=lyrics
        )
        response = self.dj.ask(prompt)
        if response:
            self.console.print(
                Panel(response, title=" Lyric Breakdown", border_style="cyan")
            )
        else:
            self.console.print("[red]No lyric explanation generated.[/red]")

    def _generate_radio_intro(self, track_name, artist_name):
        prompt = self.templates["generate_radio_intro"].format(
            track_name=track_name, artist_name=artist_name
        )
        response = self.dj.ask(prompt)
        return response or " [DJ dead air] No intro available."

    def dj_commentary(
        self, last_song: tuple[str, str], next_song: tuple[str, str]
    ) -> str:
        """Generate short DJ commentary between tracks."""

        prompt = self.templates["dj_commentary"].format(
            last_song=f"{last_song[0]} by {last_song[1]}",
            next_song=f"{next_song[0]} by {next_song[1]}",
        )
        response = self.dj.ask(prompt)
        if response:
            self.console.print(Panel(response, title=" DJ", border_style="blue"))
        else:
            self.console.print("[red]No DJ commentary generated.[/red]")
        return response or ""
