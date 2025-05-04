import threading
import time
import os
import json
import re
from dotenv import load_dotenv
from time import sleep

from gpt_dj import RadioFreeDJ
from spotify_utils import SpotifyController
from upnext import UpNextManager
from genius_utils import get_lyrics
from lyrics_sync import LyricsSyncManager
from requests.exceptions import ReadTimeout, RequestException

from queue import Queue
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt
from rich.text import Text

# === Load Environment Variables ==
load_dotenv()

# === Initialize UI State ===
show_lyrics = True
show_gpt_log = True
command_log_buffer = []
notifications = []
user_input_queue = Queue()

# === API & Model Setup ===
api_key = os.getenv("OPENAI_API_KEY")
gpt_model = os.getenv("GPT_MODEL", "gpt-4o-mini")
log_path = os.path.join(os.path.dirname(__file__), "requests.log")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in .env!")

# === GPT Log Buffer & Callback ===
gpt_log_buffer = []


def log_gpt(prompt: str, response: str):
    entry = (prompt.strip(), (response or "[No response]").strip())
    gpt_log_buffer.append(entry)
    if len(gpt_log_buffer) > 50:
        gpt_log_buffer.pop(0)


# === Instantiate RadioFreeDJ with on_response callback ===
gpt_dj = RadioFreeDJ(
    api_key=api_key,
    active_model=gpt_model,
    log_path=log_path,
    on_response=log_gpt,  # ← every ask() now auto‑logs into gpt_log_buffer
)

# === Other Components ===
spotify_controller = SpotifyController()
upnext = UpNextManager(gpt_dj, spotify_controller)
lyrics_manager = LyricsSyncManager(spotify_controller)

console = Console()
last_song = (None, None)

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


def parse_response(response):
    try:
        song_data = json.loads(response.replace("'", '"'))
        if (
            isinstance(song_data, dict)
            and "track_name" in song_data
            and "artist_name" in song_data
        ):
            return [f"{song_data['track_name']} by {song_data['artist_name']}"]
    except json.JSONDecodeError:
        pass

    pattern = r"\d+\.\s*(.+?)\s+by\s+(.+)"
    matches = re.findall(pattern, response, re.IGNORECASE)
    return [f"{title} by {artist}" for title, artist in matches] if matches else []


def render_progress_bar(progress_ms, duration_ms):
    percent = min(progress_ms / duration_ms, 1.0) if duration_ms else 0
    bar_length = 30
    filled = int(bar_length * percent)
    empty = bar_length - filled
    bar = f"[cyan][{'█' * filled}{'░' * empty}][/cyan]"
    return f"{bar} {int(percent * 100)}%"


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
        Layout(name="queue", ratio=1),
    )

    notif_text = Text()
    for note in notifications[-3:]:
        notif_text.append(note + "\n")

    track_info = spotify_controller.sp.current_playback()
    progress = track_info.get("progress_ms", 0) if track_info else 0
    duration = track_info.get("item", {}).get("duration_ms", 0) if track_info else 0
    elapsed = time.strftime("%M:%S", time.gmtime(progress // 1000))
    total = time.strftime("%M:%S", time.gmtime(duration // 1000))
    timecode = f"{elapsed} / {total}"
    progress_bar = render_progress_bar(progress, duration)
    lyrics_manager.sync(progress)  # ensure real-time display updates

    layout["header"].update(
        Panel(
            f"[bold green] Now Playing:[/bold green] [yellow]{song_name}[/yellow] by [cyan]{artist_name}[/cyan]  [dim]| {timecode}[/dim]",
            title=f"RadioFreeDJ {progress_bar}",
            subtitle=notif_text.plain if notif_text else "",
            subtitle_align="right",
        )
    )

    lyrics_panel = Panel(
        lyrics_manager.get_text()
        if show_lyrics
        else "[dim]Lyrics hidden (press [bold]l[/bold] to show)[/dim]",
        title=" Lyrics",
        border_style="cyan",
    )
    layout["lyrics"].update(lyrics_panel)

    layout["menu"].update(
        Panel(get_menu_text(), title="  Main Menu", border_style="green")
    )
    gpt_panel_text = Text()
    if show_gpt_log:
        for prompt, response in gpt_log_buffer[-5:]:
            parsed = parse_response(response)
            if parsed:
                gpt_panel_text.append(
                    f"[bold cyan]{prompt}[/bold cyan]\n", style="cyan"
                )
                for line in parsed:
                    gpt_panel_text.append(f"   {line}\n", style="green")
            else:
                gpt_panel_text.append(
                    f"[bold cyan]{prompt}[/bold cyan]\n{response}\n\n", style="cyan"
                )
    else:
        gpt_panel_text.append(
            "[dim]GPT log hidden (press [bold]g[/bold] to show)[/dim]"
        )

    layout["gpt"].update(
        Panel(gpt_panel_text, title=" GPT Log", border_style="magenta")
    )

    queue_status = Text.from_markup(
        f"[bold]Mode:[/bold] {upnext.mode}\n"
        f"[bold]Queued Songs:[/bold] {len(upnext.queue)}\n"
    )
    if upnext.queue:
        next_up = upnext.queue[0]
        queue_status.append(
            Text.from_markup(
                f"[bold]Next Up:[/bold] {next_up['track_name']} - {next_up['artist_name']}"
            )
        )
    else:
        queue_status.append(Text.from_markup("[dim]No songs queued.[/dim]"))

    layout["queue"].update(
        Panel(queue_status, title="  UpNext Queue", border_style="blue")
    )

    return layout


def get_menu_text():
    mode_label = "(Playlist)" if upnext.mode == "playlist" else "(Smart)"
    menu = [
        f"[bold]1.[/bold] Auto-play from UpNext queue {mode_label}",
        "[bold]2.[/bold] Queue 1 recommended song",
        "[bold]3.[/bold] Queue 10 recommendations",
        "[bold]4.[/bold] Queue 15-song playlist",
        "[bold]5.[/bold] Queue 10-song theme playlist",
        "[bold]6.[/bold] Get info on current song",
        "[bold]t.[/bold] Toggle playlist mode",
        "[bold]0.[/bold] Quit",
    ]
    if command_log_buffer:
        menu.append(f"\n[bold]Last:[/bold] {command_log_buffer[-1]}")
    return Text.from_markup("\n".join(menu))


# ─────────────────────────────────────────────────────────────
# GPT Actions
# ─────────────────────────────────────────────────────────────


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


def read_input():
    while True:
        choice = Prompt.ask("[bold green]  Select an option[/bold green]").strip()
        user_input_queue.put(choice)


input_thread = threading.Thread(target=read_input, daemon=True)
input_thread.start()


def main():
    global last_song, show_lyrics, show_gpt_log

    try:
        console.print("[green]🚀 Starting FreeRadioDJ...[/green]\n")

        # — Get the very first track
        song_name, artist_name = spotify_controller.get_current_song()
        while not song_name:
            console.print(
                "[yellow]⏳ Waiting for Spotify to start playback...[/yellow]"
            )
            time.sleep(3)
            song_name, artist_name = spotify_controller.get_current_song()

        # — Wait until Spotify reports a real duration_ms (>= 1 sec)
        while True:
            try:
                playback = spotify_controller.sp.current_playback()
                item = playback.get("item", {}) if playback else {}
                duration_ms = item.get("duration_ms", 0)
            except ReadTimeout:
                notify("⚠️ Spotify API timeout (startup), retrying...", style="red")
                time.sleep(1)
                continue
            except RequestException as e:
                notify(f"⚠️ Spotify API error (startup): {e}", style="red")
                time.sleep(1)
                continue

            if duration_ms >= 1000:
                break
            time.sleep(0.2)

        album_name = item.get("album", {}).get("name", "")
        last_song = (song_name, artist_name)
        lyrics_manager.start(song_name, artist_name, album_name, duration_ms)

        console.print(
            "[dim]Press [bold]l[/bold] to toggle lyrics, "
            "[bold]g[/bold] for GPT log, or enter menu option (0–6, t).[/dim]"
        )

        with Live(refresh_per_second=2, screen=True) as live:
            while True:
                # — Safely poll Spotify
                try:
                    playback = spotify_controller.sp.current_playback()
                except ReadTimeout:
                    notify("⚠️ Spotify API timeout, retrying...", style="red")
                    time.sleep(1)
                    continue
                except RequestException as e:
                    notify(f"⚠️ Spotify API error: {e}", style="red")
                    time.sleep(1)
                    continue

                if not playback or not playback.get("item"):
                    time.sleep(1)
                    continue

                item = playback["item"]
                current_song = item["name"]
                current_artist = item["artists"][0]["name"]
                progress_ms = playback.get("progress_ms", 0)

                # On track change: wait for valid duration_ms then restart lyrics
                if (current_song, current_artist) != last_song:
                    last_song = (current_song, current_artist)

                    # wait for a proper duration_ms
                    while True:
                        try:
                            play2 = spotify_controller.sp.current_playback()
                            item2 = play2.get("item", {}) if play2 else {}
                            duration_ms = item2.get("duration_ms", 0)
                        except ReadTimeout:
                            time.sleep(0.2)
                            continue
                        except RequestException:
                            time.sleep(0.2)
                            continue
                        if duration_ms >= 1000:
                            break
                        time.sleep(0.2)

                    album_name = item2.get("album", {}).get("name", "")

                    notify(
                        f"🔄 Track changed: {current_song} by {current_artist}",
                        style="cyan",
                    )
                    lyrics_manager.start(
                        current_song, current_artist, album_name, duration_ms
                    )

                # Sync lyrics and redraw
                lyrics_manager.sync(progress_ms)
                live.update(create_layout(current_song, current_artist))

                # Handle user input
                if not user_input_queue.empty():
                    choice = user_input_queue.get()
                    # ... your existing input-handling logic here ...

                time.sleep(0.5)

    except KeyboardInterrupt:
        console.print("\n[bold red]⏹ Exiting FreeRadioDJ... Goodbye![/bold red]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error in main loop: {e}[/red]")
        console.print("\n[bold red]⏹ Exiting FreeRadioDJ... Goodbye![/bold red]")


if __name__ == "__main__":
    main()
