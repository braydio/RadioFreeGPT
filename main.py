import threading
import shutil
import time
import os
import subprocess
import json
from dotenv import load_dotenv
from time import sleep

from gpt_dj import RadioFreeDJ
from spotify_utils import SpotifyController
from upnext import UpNextManager

from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt
from rich.text import Text

# === Load Environment Variables ===
load_dotenv()

# === Initialize Components ===
api_key = os.getenv("OPENAI_API_KEY")
gpt_model = os.getenv("GPT_MODEL", "gpt-4o-mini")
log_path = os.path.join(os.path.dirname(__file__), "requests.log")
show_lyrics = True
show_gpt_log = True
command_log_buffer = []
notifications = []

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in .env!")

gpt_dj = RadioFreeDJ(api_key=api_key, active_model=gpt_model, log_path=log_path)
spotify_controller = SpotifyController()
upnext = UpNextManager(gpt_dj, spotify_controller)

console = Console()
lyrics_proc = None
lyrics_thread = None
lyrics_text = Text(" Waiting for lyrics...", style="cyan")
last_song = (None, None)

gpt_log_buffer = []  # Scrollback buffer for GPT logs


# ─────────────────────────────────────────────────────────────
# Lyrics Streaming
# ─────────────────────────────────────────────────────────────


def stream_lyrics():
    global lyrics_proc, lyrics_text
    try:
        for line in iter(lyrics_proc.stdout.readline, b""):
            decoded = line.decode("utf-8").strip()
            if decoded:
                lyrics_text = Text(f" {decoded}", style="bold cyan")
    except Exception as e:
        console.print(f"[red] Lyrics stream error:[/red] {e}")


def start_lyrics_process():
    global lyrics_proc, lyrics_thread, lyrics_text
    stop_lyrics_process()

    lyrics_path = shutil.which("lyricstify")
    if not lyrics_path:
        console.print("[bold red] 'lyricstify' not found in PATH.[/bold red]")
        return

    lyrics_proc = subprocess.Popen(
        [lyrics_path, "pipe"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    lyrics_text = Text(" Fetching lyrics...", style="cyan")
    lyrics_thread = threading.Thread(target=stream_lyrics, daemon=True)
    lyrics_thread.start()


def stop_lyrics_process():
    global lyrics_proc
    if lyrics_proc and lyrics_proc.poll() is None:
        lyrics_proc.terminate()
        try:
            lyrics_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            lyrics_proc.kill()


# ─────────────────────────────────────────────────────────────
# Event Notifications
# ─────────────────────────────────────────────────────────────


def notify(message: str, style="bold yellow"):
    notifications.append(Text(message, style=style))
    if len(notifications) > 3:
        notifications.pop(0)


# ─────────────────────────────────────────────────────────────
# Rich UI Layout
# ─────────────────────────────────────────────────────────────


def create_layout(song_name, artist_name):
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="lyrics", ratio=2),
        Layout(name="lower", ratio=3),
    )

    layout["lower"].split_row(
        Layout(name="menu", ratio=1),
        Layout(name="gpt", ratio=2),
        Layout(name="cmds", ratio=1),
    )

    notif_text = Text()
    for note in notifications[-3:]:
        notif_text.append(note + "\n")

    layout["header"].update(
        Panel(
            f"[bold green] Now Playing:[/bold green] [yellow]{song_name}[/yellow] by [cyan]{artist_name}[/cyan]",
            title="RadioFreeDJ",
            subtitle=notif_text.plain if notif_text else "",
            subtitle_align="right",
        )
    )

    if show_lyrics:
        layout["lyrics"].update(
            Panel(lyrics_text, title=" Lyrics", border_style="cyan")
        )
    else:
        layout["lyrics"].update(
            Panel(
                "[dim]Lyrics hidden (press [bold]l[/bold] to show)[/dim]",
                title=" Lyrics",
                border_style="cyan",
            )
        )

    layout["menu"].update(
        Panel(get_menu_text(), title="  Main Menu", border_style="green")
    )

    if show_gpt_log:
        gpt_panel_text = Text()
        for _, response in gpt_log_buffer[-5:]:
            gpt_panel_text.append(Text(" " + response + "\n\n", style="cyan"))
        layout["gpt"].update(
            Panel(gpt_panel_text, title=" GPT Log", border_style="magenta")
        )
    else:
        layout["gpt"].update(
            Panel(
                "[dim]GPT log hidden (press [bold]g[/bold] to show)[/dim]",
                title=" GPT Log",
                border_style="magenta",
            )
        )

    command_panel_text = Text()
    for cmd in command_log_buffer[-5:]:
        command_panel_text.append(Text(f"> {cmd}\n", style="bold green"))

    layout["cmds"].update(
        Panel(command_panel_text, title=" Commands", border_style="blue")
    )

    return layout


def get_menu_text():
    mode_label = "(Playlist)" if upnext.mode == "playlist" else "(Smart)"

    return Text.from_markup(
        "\n".join(
            [
                f"[bold]1.[/bold] Auto-play from UpNext queue {mode_label}",
                "[bold]2.[/bold] Queue 1 recommended song",
                "[bold]3.[/bold] Queue 10 recommendations",
                "[bold]4.[/bold] Queue 15-song playlist",
                "[bold]5.[/bold] Queue 10-song theme playlist",
                "[bold]6.[/bold] Get info on current song",
                "[bold]t.[/bold] Toggle playlist mode",
                "[bold]0.[/bold] Quit",
            ]
        )
    )


# ─────────────────────────────────────────────────────────────
# GPT Actions
# ─────────────────────────────────────────────────────────────


def log_gpt(prompt, response):
    gpt_log_buffer.append((prompt.strip(), (response or "[No response]").strip()))
    if len(gpt_log_buffer) > 50:
        gpt_log_buffer.pop(0)


def recommend_next_song(song_name, artist_name):
    prompt = (
        f"Reference song: '{song_name}' by {artist_name}. "
        "Recommend a similar song. Respond ONLY in JSON format:\n"
        "{'track_name': '<TRACK NAME>', 'artist_name': '<ARTIST NAME>'}"
    )
    response = gpt_dj.ask(prompt)
    log_gpt(prompt, response)
    if response:
        console.print(
            Panel(response, title=" RadioFree Recommendation", border_style="magenta")
        )
    else:
        console.print("[bold red] No recommendation received.[/bold red]")
    return response


def recommend_next_ten_songs(song_name, artist_name):
    prompt = (
        f"Reference song: '{song_name}' by {artist_name}. "
        "List 10 similar songs in the format:\n"
        "1. [Track Title] by [Artist Name]"
    )
    response = gpt_dj.ask(prompt)
    log_gpt(prompt, response)
    if response:
        console.print(
            Panel(response, title=" Top 10 Recommendations", border_style="magenta")
        )
    else:
        console.print("[bold red] No response received for top 10.[/bold red]")


def create_playlist(song_name, artist_name):
    prompt = (
        f"The current song is '{song_name}' by {artist_name}. "
        "Create a playlist of 15 songs matching the same vibe."
    )
    response = gpt_dj.ask(prompt)
    log_gpt(prompt, response)
    if response:
        console.print(
            Panel(response, title=" FreeRadio Playlist", border_style="magenta")
        )
    else:
        console.print("[bold red] Playlist creation failed.[/bold red]")


def theme_based_playlist():
    theme = Prompt.ask("Enter a theme (e.g., focus, happy, sad)").strip()
    prompt = (
        f"Create a playlist of 10 songs fitting the theme '{theme}'. "
        "Format:\n1. [Track Title] by [Artist Name]"
    )
    response = gpt_dj.ask(prompt)
    log_gpt(prompt, response)
    if response:
        console.print(
            Panel(response, title=f" Themed Playlist: {theme}", border_style="magenta")
        )
    else:
        console.print("[bold red] No themed playlist returned.[/bold red]")


def generate_radio_intro(track_name, artist_name):
    prompt = (
        f"Create a short and engaging radio-style intro for the song '{track_name}' by {artist_name}. "
        "It should sound like a real DJ on a talk show introducing it. Keep it under 30 words."
    )
    response = gpt_dj.ask(prompt)
    log_gpt(prompt, response)
    return response or " [DJ dead air] No intro available."


def song_insights(song_name, artist_name):
    prompt = (
        f"Provide an interesting radio host style insight about '{song_name}' by {artist_name}. "
        "Keep it short and engaging."
    )
    response = gpt_dj.ask(prompt)
    log_gpt(prompt, response)
    if response:
        console.print(Panel(response, title=" Insight", border_style="cyan"))
    else:
        console.print("[bold red] No insight generated.[/bold red]")


# ─────────────────────────────────────────────────────────────
# User Interaction Loop
# ─────────────────────────────────────────────────────────────


def main():
    global last_song, show_lyrics, show_gpt_log
    try:
        while True:
            song_name, artist_name = spotify_controller.get_current_song()

            if not song_name or not artist_name:
                console.print(
                    "[yellow]Waiting for Spotify to start playback...[/yellow]"
                )
                time.sleep(5)
                continue

            if (song_name, artist_name) != last_song:
                stop_lyrics_process()
                last_song = (song_name, artist_name)
                start_lyrics_process()

            with Live(refresh_per_second=2, screen=True) as live:
                while True:
                    new_song, new_artist = spotify_controller.get_current_song()

                    if not new_song or not new_artist:
                        time.sleep(5)
                        continue

                    if (new_song, new_artist) != last_song:
                        stop_lyrics_process()
                        last_song = (new_song, new_artist)
                        start_lyrics_process()
                        notify(f"New track: {new_song} by {new_artist}", style="cyan")

                    live.update(create_layout(new_song, new_artist))

                    console.print(
                        "[dim]Press [bold]l[/bold] to toggle lyrics, [bold]g[/bold] for GPT log, or enter menu option (0-6, t).[/dim]"
                    )
                    choice = Prompt.ask(
                        "[bold green]  Select an option[/bold green]"
                    ).strip()

                    command_labels = {
                        "1": "Auto-DJ",
                        "2": "Queue One Song",
                        "3": "Queue Ten Songs",
                        "4": "Queue Playlist",
                        "5": "Queue Theme Playlist",
                        "6": "Song Insight",
                        "t": "Toggle Mode",
                        "0": "Quit",
                        "l": "Toggle Lyrics",
                        "g": "Toggle GPT Log",
                    }

                    command_log_buffer.append(
                        f"{choice} → {command_labels.get(choice, 'Unknown')}"
                    )
                    if len(command_log_buffer) > 50:
                        command_log_buffer.pop(0)

                    if choice == "l":
                        show_lyrics = not show_lyrics
                    elif choice == "g":
                        show_gpt_log = not show_gpt_log
                    elif choice == "0":
                        raise KeyboardInterrupt
                    elif choice == "1":
                        upnext.auto_dj_transition(new_song, new_artist)
                    elif choice == "2":
                        upnext.queue_one_song(new_song, new_artist)
                    elif choice == "3":
                        upnext.queue_ten_songs(new_song, new_artist)
                    elif choice == "4":
                        upnext.queue_playlist(new_song, new_artist)
                    elif choice == "5":
                        upnext.queue_theme_playlist()
                    elif choice == "6":
                        upnext.song_insight(new_song, new_artist)
                    elif choice == "t":
                        upnext.toggle_playlist_mode()
                        notify(
                            f"Queue mode: {'Themed' if upnext.playlist_mode else 'Smart'}",
                            style="magenta",
                        )
                    else:
                        notify("Invalid menu option.", style="red")

    except KeyboardInterrupt:
        console.print("\n[bold red] Shutting down FreeRadio...[/bold red]")
    finally:
        stop_lyrics_process()


if __name__ == "__main__":
    main()
