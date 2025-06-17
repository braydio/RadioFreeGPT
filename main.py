"""Interactive TUI for controlling Spotify playback with GPT prompts."""

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
from lastfm_utils import update_now_playing, scrobble
from requests.exceptions import ReadTimeout, RequestException

from queue import Queue
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt
from rich.text import Text

from logger_utils import setup_logger

# === Load Environment Variables ===
load_dotenv()

# === Load Prompt Templates ===
prompts_path = os.path.join(os.path.dirname(__file__), "prompts.json")
with open(prompts_path, "r", encoding="utf-8") as f:
    prompt_templates = json.load(f)

# === Setup Logging ===
log_path = os.path.join(os.path.dirname(__file__), "requests.log")
logger = setup_logger("FreeRadioMain", log_path)

# --- Command Logging Setup ---
COMMAND_LABELS = {
    "1": "Auto-DJ",
    "s": "Save Song",
    "d": "Dislike Song",
    "right": "Next Track",
    "left": "Previous Track",
    "2": "Queue One Song",
    "3": "Queue Ten Songs",
    "4": "Queue Playlist",
    "5": "Queue Theme Playlist",
    "6": "Song Insight",
    "7": "Lyric Breakdown",
    "t": "Toggle Mode",
    "0": "Quit",
    "l": "Toggle Lyrics View",
    "g": "Toggle GPT Log",
    "j": "Cursor Down",
    "k": "Cursor Up",
}
COMMAND_LOG_FILE = os.path.join(os.path.dirname(__file__), "commands.log")


def log_command(choice: str):
    label = COMMAND_LABELS.get(choice, "Unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} - {choice} → {label}\n"
    try:
        with open(COMMAND_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        logger.warning(f"Could not write command log: {e}")
    return label


# === Initialize UI State ===
show_lyrics = True
lyrics_view_mode = "chunk"
lyrics_cursor = 0

show_gpt_log = True
command_log_buffer = []
notifications = []
user_input_queue = Queue()

gpt_log_buffer = []


GPT_LOG_FILE = os.path.expanduser("~/RadioFree/logs/gpt_log.jsonl")


def log_gpt(prompt: str, response: str):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt.strip(),
        "response": (response or "[No response]").strip(),
    }
    gpt_log_buffer.append((entry["prompt"], entry["response"]))
    if len(gpt_log_buffer) > 50:
        gpt_log_buffer.pop(0)

    try:
        os.makedirs(os.path.dirname(GPT_LOG_FILE), exist_ok=True)
        with open(GPT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write GPT log: {e}")


# === instantiate radiofreedj ===
api_key = os.getenv("OPENAI_API_KEY")
gpt_model = os.getenv("GPT_MODEL", "gpt-4o-mini")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in .env!")

gpt_dj = RadioFreeDJ(
    api_key=api_key,
    active_model=gpt_model,
    log_path=log_path,
    on_response=log_gpt,
)

# === other components ===
spotify_controller = SpotifyController()
upnext = UpNextManager(gpt_dj, spotify_controller, prompt_templates)
lyrics_manager = LyricsSyncManager(spotify_controller)
console = Console()
last_song = {"name": None, "artist": None, "started": 0}
auto_dj_counter = 0

# ─────────────────────────────────────────────────────────────
# Event Notifications
# ─────────────────────────────────────────────────────────────


def notify(message: str, style="bold yellow"):
    notifications.append(Text(message, style=style))
    if len(notifications) > 3:
        notifications.pop(0)


def log_song_history(
    song_name, artist_name, queued_by="unknown", liked=False, skipped=False
):
    history_dir = os.path.expanduser("~/RadioFree/logs")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "song_history.jsonl")

    entry = {
        "track_name": song_name,
        "artist_name": artist_name,
        "timestamp": datetime.now().isoformat(),
        "queued_by": queued_by,
        "liked": liked,
        "skipped": skipped,
        "played_count": 1,
        "recommended_count": 1 if queued_by == "gpt" else 0,
    }

    with open(history_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ─────────────────────────────────────────────────────────────
# Rich UI Layout & Helpers
# ─────────────────────────────────────────────────────────────


def render_queue_status() -> Text:
    queue_status = Text.from_markup(
        f"[bold]Mode:[/bold] {upnext.mode}\n"
        f"[bold]Queued Songs:[/bold] {len(upnext.queue)}\n"
    )
    if upnext.queue:
        for i, track in enumerate(upnext.queue[:5], start=1):
            t_name = track.get("track_name", "Unknown")
            a_name = track.get("artist_name", "Unknown")
            queue_status.append(Text.from_markup(f"{i}. {t_name} - {a_name}\n"))
    else:
        queue_status.append(Text.from_markup("[dim]No songs queued.[/dim]"))
    return queue_status


def render_progress_bar(progress_ms, duration_ms):
    percent = min(progress_ms / duration_ms, 1.0) if duration_ms else 0
    bar_length = 30
    filled = int(bar_length * percent)
    empty = bar_length - filled
    bar = f"[cyan][{'█' * filled}{'░' * empty}][/cyan]"
    return f"{bar} {int(percent * 100)}%"


def render_gpt_log() -> Text:
    """Return the latest GPT response formatted with Rich markup."""

    panel_text = Text()
    if show_gpt_log and gpt_log_buffer:
        _, latest = gpt_log_buffer[-1]
        # Parse markup tags in the GPT response so styling is applied
        panel_text = Text.from_markup(latest, style="cyan")
    else:
        panel_text.append("[dim]GPT log hidden (press [bold]g[/bold] to show)[/dim]")
    return panel_text


def get_menu_text():
    mode_label = "Playlist" if upnext.mode == "playlist" else "Smart"
    menu = [
        "[bold]1.[/bold] 󰼛 Tune in to RadioFree󰲿 with DJ gpt-4o-mini 󱚣 ",
        "[bold]2.[/bold] Queue 1 recommended song",
        "[bold]3.[/bold] Queue 10 recommendations",
        "[bold]s.[/bold] Save song to favorites",
        "[bold]d.[/bold] Dislike current song",
        "[bold]4.[/bold] Queue 15-song playlist",
        "[bold]5.[/bold] Queue 10-song theme playlist",
        "[bold]6.[/bold] Get info on current song",
        "[bold]7.[/bold] Explain current song lyrics",
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
    if not lyrics_manager.ready:
        panel_text.append("[dim]Loading lyrics...[/dim]")
    else:
        lines, idx = lyrics_manager.lines, lyrics_manager.current_index
        if lyrics_view_mode == "chunk":
            start = max(0, idx - 3)
            for i, line in enumerate(lines[start : start + 8], start):
                prefix, style = (
                    (
                        "",
                        "bold italic yellow",
                    )
                    if i == idx
                    else ("-", None)
                )
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


def create_playlist(song_name, artist_name):
    tpl = prompt_templates["create_playlist"]
    prompt = tpl.format(song_name=song_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    logger.info(f"[create_playlist] Prompt:\n{prompt}")
    logger.info(f"[create_playlist] Response:\n{resp}")
    if resp:
        console.print(Panel(resp, title="󰐑 FreeRadio Playlist", border_style="magenta"))


def theme_based_playlist():
    theme = Prompt.ask("Enter a theme").strip()
    tpl = prompt_templates["theme_based_playlist"]
    prompt = tpl.format(theme=theme)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    logger.info(f"[theme_based_playlist] Prompt:\n{prompt}")
    logger.info(f"[theme_based_playlist] Response:\n{resp}")
    if resp:
        console.print(
            Panel(resp, title=f"󰐑 Themed Playlist: {theme}", border_style="magenta")
        )


def generate_radio_intro(track_name, artist_name):
    tpl = prompt_templates["generate_radio_intro"]
    prompt = tpl.format(track_name=track_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    logger.info(f"[generate_radio_intro] Prompt:\n{prompt}")
    logger.info(f"[generate_radio_intro] Response:\n{resp}")
    return resp or "󱚢 [DJ dead air] No intro available."


def song_insights(song_name, artist_name):
    tpl = prompt_templates["song_insights"]
    prompt = tpl.format(song_name=song_name, artist_name=artist_name)
    resp = gpt_dj.ask(prompt)
    log_gpt(prompt, resp)
    logger.info(f"[song_insights] Prompt:\n{prompt}")
    logger.info(f"[song_insights] Response:\n{resp}")
    if resp:
        console.print(
            Panel(resp, title=" RadioFree DJ - gpt-4o-mini", border_style="cyan")
        )


# ─────────────────────────────────────────────────────────────
# User Interaction Loop
# ─────────────────────────────────────────────────────────────
def read_input():
    try:
        while True:
            choice = Prompt.ask("[bold green]   Select an option[/bold green]")
            user_input_queue.put(choice)
            log_command(choice)
    except KeyboardInterrupt:
        pass


def process_user_input(choice: str, current_song: str, current_artist: str):
    label = log_command(choice)
    command_log_buffer.append(f"{choice} → {label}")
    if len(command_log_buffer) > 50:
        command_log_buffer.pop(0)
    notify(f"Command: {label}", style="green")

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
        upnext.auto_dj_enabled = not upnext.auto_dj_enabled
        state = "enabled" if upnext.auto_dj_enabled else "disabled"
        notify(f"Auto-DJ {state}", style="cyan")
        if upnext.auto_dj_enabled:
            upnext.maintain_queue(current_song, current_artist)
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
    elif choice == "7":
        upnext.explain_lyrics(current_song, current_artist)
    elif choice == "t":
        upnext.toggle_playlist_mode()
        notify(
            f"Queue mode: {'Playlist' if upnext.mode == 'playlist' else 'Smart'}",
            style="magenta",
        )
    elif choice == "toggle_play":
        playback = spotify_controller.sp.current_playback()
        if playback and playback.get("is_playing"):
            spotify_controller.pause()
            notify("⏸ Paused playback", style="yellow")
        else:
            spotify_controller.resume()
            notify("▶️ Resumed playback", style="yellow")
    elif choice == "next":
        spotify_controller.next()
        notify("⏭ Skipped to next track.", style="yellow")
    elif choice == "prev":
        spotify_controller.previous()
        notify("⏮ Went back to previous track.", style="yellow")
    elif choice == "vol_up":
        spotify_controller.change_volume(+10)
    elif choice == "vol_down":
        spotify_controller.change_volume(-10)
    elif choice == "s":
        saved_path = os.path.expanduser("~/.radiofreedj/saved_songs.json")
        os.makedirs(os.path.dirname(saved_path), exist_ok=True)
        song_data = {
            "track_name": current_song,
            "artist_name": current_artist,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            if os.path.exists(saved_path):
                with open(saved_path, "r") as f:
                    data = json.load(f)
            else:
                data = []
            data.append(song_data)
            with open(saved_path, "w") as f:
                json.dump(data, f, indent=2)
            notify(f"💾 Saved: {current_song} by {current_artist}", style="green")
        except Exception as e:
            notify(f"Error saving song: {e}", style="red")
    elif choice == "d":
        log_song_history(current_song, current_artist, queued_by="user", skipped=True)
        notify(f"👎 Marked as disliked: {current_song}", style="red")
    else:
        notify("❌ Invalid menu option.", style="red")


def sync_with_lastfm(song_name, artist_name):
    update_now_playing(song_name, artist_name)


def fetch_playback_item(max_retries: int = 10, delay: float = 0.2) -> dict:
    """Return the current playback item with limited retries.

    Parameters
    ----------
    max_retries:
        Number of attempts before giving up.
    delay:
        Seconds to wait between retries.

    Returns
    -------
    dict
        Playback item dictionary (may be empty if unavailable).
    """
    item: dict = {}
    for _ in range(max_retries):
        try:
            playback = spotify_controller.sp.current_playback()
            item = playback.get("item", {}) if playback else {}
            if item.get("duration_ms", 0) >= 1000:
                return item
        except (ReadTimeout, RequestException) as e:
            logger.warning(f"Spotify API error: {e}")
        time.sleep(delay)
    logger.warning(
        f"Playback details unavailable after {max_retries} attempts"
    )
    return item


def main():
    global last_song, show_lyrics, show_gpt_log, lyrics_view_mode, lyrics_cursor
    try:
        threading.Thread(target=read_input, daemon=True).start()
        console.print("[green]🚀 Starting FreeRadioDJ...[/green]\n")
        song_name, artist_name = spotify_controller.get_current_song()
        while not song_name:
            console.print(
                "[yellow]⏳ Waiting for Spotify to start playback...[/yellow]"
            )
            time.sleep(3)
            song_name, artist_name = spotify_controller.get_current_song()
        item = fetch_playback_item()
        duration_ms = item.get("duration_ms", 0)
        album_name = item.get("album", {}).get("name", "")
        last_song = {
            "name": song_name,
            "artist": artist_name,
            "started": int(time.time()),
        }
        lyrics_manager.start(song_name, artist_name, album_name, duration_ms)
        update_now_playing(song_name, artist_name)
        console.print(
            "[dim]Press [bold]l[/bold] to toggle lyrics, [bold]g[/bold] for GPT log, or press keys (1–6, t, arrows, space, +, -).[/dim]"
        )
        # Increase refresh rate to improve UI responsiveness
        # CPU overhead measured <0.1s over 3 seconds at 10 FPS (see docs).
        with Live(refresh_per_second=10, screen=True) as live:
            while True:
                try:
                    playback = spotify_controller.sp.current_playback()
                except (ReadTimeout, RequestException) as e:
                    notify(f"Spotify API error: {e}", style="red")
                    continue
                if not playback or not playback.get("item"):
                    time.sleep(1)
                    continue
                item = playback["item"]
                current_song = item["name"]
                current_artist = item["artists"][0]["name"]
                progress_ms = playback.get("progress_ms", 0)
                if (current_song, current_artist) != (
                    last_song["name"],
                    last_song["artist"],
                ):
                    if last_song["name"] and last_song["artist"]:
                        scrobble(
                            last_song["name"], last_song["artist"], last_song["started"]
                        )
                    last_song = {
                        "name": current_song,
                        "artist": current_artist,
                        "started": int(time.time()),
                    }
                    item2 = fetch_playback_item()
                    duration_ms = item2.get("duration_ms", 0)
                    album_name = item2.get("album", {}).get("name", "")
                    notify(
                        f"🔄 Track changed: {current_song} by {current_artist}",
                        style="cyan",
                    )
                    lyrics_manager.start(
                        current_song, current_artist, album_name, duration_ms
                    )
                    sync_with_lastfm(current_song, current_artist)
                    global auto_dj_counter
                    auto_dj_counter += 1
                    if upnext.auto_dj_enabled:
                        upnext.maintain_queue(current_song, current_artist)
                        if auto_dj_counter % 3 == 0 and upnext.queue:
                            upnext.dj_commentary(
                                (last_song["name"], last_song["artist"]),
                                (
                                    upnext.queue[0]["track_name"],
                                    upnext.queue[0]["artist_name"],
                                ),
                            )
                lyrics_manager.sync(progress_ms)
                if upnext.auto_dj_enabled:
                    upnext.maintain_queue(current_song, current_artist)
                live.update(create_layout(current_song, current_artist))
                if not user_input_queue.empty():
                    choice = user_input_queue.get()
                    process_user_input(choice, current_song, current_artist)
                time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[bold red]⏹ Exiting FreeRadioDJ... Goodbye![/bold red]")
    except Exception as e:
        logger.exception("Unexpected error in main loop")
        console.print(f"\n[red]❌ Unexpected error in main loop: {e}[/red]")
        console.print("\n[bold red]⏹ Exiting FreeRadioDJ... Goodbye![/bold red]")


if __name__ == "__main__":
    main()
