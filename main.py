import threading
import time
import os
import json
import re
from dotenv import load_dotenv
from datetime import datetime
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

# === Load Environment Variables ===
load_dotenv()

# === Load Prompt Templates ===
prompts_path = os.path.join(os.path.dirname(__file__), "prompts.json")
with open(prompts_path, "r", encoding="utf-8") as f:
    prompt_templates = json.load(f)


# --- Command logging setup ---
COMMAND_LABELS = {
    "1": "Auto-DJ",
    "2": "Queue One Song",
    "3": "Queue Ten Songs",
    "4": "Queue Playlist",
    "5": "Queue Theme Playlist",
    "6": "Song Insight",
    "t": "Toggle Mode",
    "0": "Quit",
    "l": "Toggle Lyrics View",
    "g": "Toggle GPT Log",
    "j": "Cursor Down",
    "k": "Cursor Up",
}
COMMAND_LOG_FILE = os.path.join(os.path.dirname(__file__), "commands.log")


def log_command(choice: str):
    """
    Append a timestamped command entry to COMMAND_LOG_FILE.
    """
    label = COMMAND_LABELS.get(choice, "Unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} - {choice} → {label}\n"
    try:
        with open(COMMAND_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    return label


# === Initialize UI State ===
show_lyrics = True
lyrics_view_mode = "chunk"
lyrics_cursor = 0

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


# === Instantiate RadioFreeDJ ===
gpt_dj = RadioFreeDJ(
    api_key=api_key,
    active_model=gpt_model,
    log_path=log_path,
    on_response=log_gpt,
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
# Rich UI Layout & Helpers
# ─────────────────────────────────────────────────────────────
def render_queue_status() -> Text:
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
    return queue_status


def parse_response(response):
    try:
        song_data = json.loads(response.replace("'", '"'))
        if isinstance(song_data, dict) and "track_name" in song_data:
            return [f"{song_data['track_name']} by {song_data['artist_name']}"]
    except json.JSONDecodeError:
        pass
    pattern = r"\d+\.\s*(.+?)\s+by\s+(.+)"
    matches = re.findall(pattern, response, re.IGNORECASE)
    return [f"{t} by {a}" for t, a in matches] if matches else []


def render_progress_bar(progress_ms, duration_ms):
    percent = min(progress_ms / duration_ms, 1.0) if duration_ms else 0
    bar_length = 30
    filled = int(bar_length * percent)
    empty = bar_length - filled
    bar = f"[cyan][{'█' * filled}{'░' * empty}][/cyan]"
    return f"{bar} {int(percent * 100)}%"


def render_gpt_log() -> Text:
    panel_text = Text()
    if show_gpt_log and gpt_log_buffer:
        _, latest = gpt_log_buffer[-1]
        panel_text.append(latest, style="cyan")
    else:
        panel_text.append("[dim]GPT log hidden (press [bold]g[/bold] to show)[/dim]")
    return panel_text


def get_menu_text():
    mode_label = "Playlist" if upnext.mode == "playlist" else "Smart"
    menu = [
        "[bold]1.[/bold] 󰼛 Tune in to RadioFree󰲿 with DJ gpt-4o-mini 󱚣 ",
        "[bold]2.[/bold] Queue 1 recommended song",
        "[bold]3.[/bold] Queue 10 recommendations",
        "[bold]4.[/bold] Queue 15-song playlist",
        "[bold]5.[/bold] Queue 10-song theme playlist",
        "[bold]6.[/bold] Get info on current song",
        f"[bold]t.[/bold] Toggle playback mode ({mode_label} Mode)",
        "[bold]0.[/bold] Quit",
    ]
    if command_log_buffer:
        menu.append(f"\n[bold]Last:[/bold] {command_log_buffer[-1]}")
    return Text.from_markup("\n".join(menu))


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

    # Queue panel
    layout["queue"].update(
        Panel(render_queue_status(), title="  Coming Up Next", border_style="blue")
    )

    # Header panel
    playback = spotify_controller.sp.current_playback() or {}
    progress = playback.get("progress_ms", 0)
    duration = playback.get("item", {}).get("duration_ms", 0)
    elapsed = time.strftime("%M:%S", time.gmtime(progress // 1000))
    total = time.strftime("%M:%S", time.gmtime(duration // 1000))
    progress_bar = render_progress_bar(progress, duration)
    subtitle = "\n".join(n.plain for n in notifications[-3:])
    layout["header"].update(
        Panel(
            f"[bold green]  Now Playing:[/bold green] [yellow]{song_name}[/yellow] by [cyan]{artist_name}[/cyan]  [dim]| {elapsed} / {total}[/dim]",
            title=f"RadioFreeDJ {progress_bar}",
            subtitle=subtitle,
            subtitle_align="right",
        )
    )

    # Lyrics panel
    lyrics_manager.sync(progress)
    panel_text = Text()
    lines, idx = lyrics_manager.lines, lyrics_manager.current_index
    if lyrics_view_mode == "chunk":
        start = max(0, idx - 3)
        for i, line in enumerate(lines[start : start + 8], start):
            prefix, style = ("", "bold italic yellow") if i == idx else ("-", None)
            panel_text.append(f"{prefix} {line}\n", style=style)
    else:
        for i, line in enumerate(lines):
            style = "bold italic yellow" if i == lyrics_cursor else None
            panel_text.append(f"  {line}\n", style=style)
    layout["lyrics"].update(Panel(panel_text, title="󰎆 Lyrics", border_style="cyan"))

    # Menu & GPT panels
    layout["menu"].update(
        Panel(get_menu_text(), title="󰮫 Main Menu", border_style="green")
    )
    layout["gpt"].update(
        Panel(render_gpt_log(), title=" RadioFree󰲿", border_style="magenta")
    )

    return layout


# ─────────────────────────────────────────────────────────────
# GPT Actions (using prompt_templates)
# ─────────────────────────────────────────────────────────────
def recommend_next_song(song_name, artist_name):
    tpl = prompt_templates["recommend_next_song"]
    prompt = tpl.format(song_name=song_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    if resp:
        console.print(
            Panel(resp, title="  RadioFree󰲿 Recommended", border_style="magenta")
        )
    return resp


def recommend_next_ten_songs(song_name, artist_name):
    tpl = prompt_templates["recommend_next_ten_songs"]
    prompt = tpl.format(song_name=song_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    if resp:
        console.print(
            Panel(
                resp, title="  Top 10 - RadioFree󰲿 Recommended", border_style="magenta"
            )
        )


def create_playlist(song_name, artist_name):
    tpl = prompt_templates["create_playlist"]
    prompt = tpl.format(song_name=song_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    if resp:
        console.print(Panel(resp, title="󰐑 FreeRadio Playlist", border_style="magenta"))


def theme_based_playlist():
    theme = Prompt.ask("Enter a theme").strip()
    tpl = prompt_templates["theme_based_playlist"]
    prompt = tpl.format(theme=theme)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    if resp:
        console.print(
            Panel(resp, title=f"󰐑 Themed Playlist: {theme}", border_style="magenta")
        )


def generate_radio_intro(track_name, artist_name):
    tpl = prompt_templates["generate_radio_intro"]
    prompt = tpl.format(track_name=track_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    return resp or "󱚢 [DJ dead air] No intro available."


def song_insights(song_name, artist_name):
    tpl = prompt_templates["song_insights"]
    prompt = tpl.format(song_name=song_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    if resp:
        console.print(
            Panel(resp, title=" RadioFree DJ - gpt-4o-mini", border_style="cyan")
        )


# ─────────────────────────────────────────────────────────────
# User Interaction Loop
# ─────────────────────────────────────────────────────────────


def read_input():
    """
    Background thread: prompt user, enqueue choice, log immediately.
    """
    while True:
        choice = Prompt.ask("[bold green]  Select an option[/bold green]").strip()
        user_input_queue.put(choice)
        log_command(choice)


# Start the input thread exactly once
input_thread = threading.Thread(target=read_input, daemon=True)
input_thread.start()


def process_user_input(choice: str, current_song: str, current_artist: str):
    """
    Handle a single user choice: update in-UI buffer, notify, dispatch actions.
    """
    label = log_command(choice)
    # In-UI buffer
    command_log_buffer.append(f"{choice} → {label}")
    if len(command_log_buffer) > 50:
        command_log_buffer.pop(0)
    # Notification
    notify(f"Command: {label}", style="green")

    # Dispatch
    global lyrics_view_mode, lyrics_cursor, show_gpt_log
    if choice == "l":
        if lyrics_view_mode == "chunk":
            lyrics_view_mode = "full"
            lyrics_cursor = lyrics_manager.current_index
        else:
            lyrics_view_mode = "chunk"

    elif choice == "g":
        show_gpt_log = not show_gpt_log

    elif lyrics_view_mode == "full" and choice == "j":
        lyrics_cursor = min(lyrics_cursor + 1, len(lyrics_manager.lines) - 1)

    elif lyrics_view_mode == "full" and choice == "k":
        lyrics_cursor = max(lyrics_cursor - 1, 0)

    elif choice == "0":
        raise KeyboardInterrupt

    elif choice == "1":
        upnext.auto_dj_transition(current_song, current_artist)
    elif choice == "2":
        upnext.queue_one_song(current_song, current_artist)
    elif choice == "3":
        upnext.queue_ten_songs(current_song, current_artist)
    elif choice == "4":
        upnext.queue_playlist(current_song, current_artist)
    elif choice == "5":
        upnext.queue_theme_playlist()
    elif choice == "6":
        upnext.song_insight(current_song, current_artist)
    elif choice == "t":
        upnext.toggle_playlist_mode()
        notify(
            f"Queue mode: {'Playlist' if upnext.mode == 'playlist' else 'Smart'}",
            style="magenta",
        )
    else:
        notify("❌ Invalid menu option.", style="red")


def main():
    global last_song, show_lyrics, show_gpt_log, lyrics_view_mode, lyrics_cursor

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

        # — Wait for a real duration_ms (>=1 sec)
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

                # On track change
                if (current_song, current_artist) != last_song:
                    last_song = (current_song, current_artist)
                    while True:
                        try:
                            play2 = spotify_controller.sp.current_playback()
                            item2 = play2.get("item", {}) if play2 else {}
                            duration_ms = item2.get("duration_ms", 0)
                        except (ReadTimeout, RequestException):
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

                # Sync and redraw
                lyrics_manager.sync(progress_ms)
                live.update(create_layout(current_song, current_artist))

                # Handle user input
                if not user_input_queue.empty():
                    choice = user_input_queue.get()
                    process_user_input(choice, current_song, current_artist)

                time.sleep(0.5)

    except KeyboardInterrupt:
        console.print("\n[bold red]⏹ Exiting FreeRadioDJ... Goodbye![/bold red]")
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error in main loop: {e}[/red]")
        console.print("\n[bold red]⏹ Exiting FreeRadioDJ... Goodbye![/bold red]")


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
