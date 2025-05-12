#!/usr/bin/env python3

import json
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table

HISTORY_FILE = os.path.expanduser("~/RadioFree/logs/song_history.jsonl")

def load_history():
    """Load song history entries from the JSONL file."""
    if not os.path.exists(HISTORY_FILE):
        print("No song history found.")
        return []

    with open(HISTORY_FILE, "r") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]

def display_history(entries, limit=25):
    """Render a table view of recent song history."""
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Time", style="dim", width=19)
    table.add_column("Track")
    table.add_column("Artist")
    table.add_column("Queued By", justify="center")
    table.add_column("Liked", justify="center")
    table.add_column("Skipped", justify="center")

    for entry in entries[-limit:]:
        table.add_row(
            datetime.fromisoformat(entry["timestamp"]).strftime("%m-%d %H:%M"),
            entry.get("track_name", "Unknown"),
            entry.get("artist_name", "Unknown"),
            entry.get("queued_by", "?"),
            "✔" if entry.get("liked") else "",
            "✘" if entry.get("skipped") else ""
        )

    console.print(table)

if __name__ == "__main__":
    history = load_history()
    display_history(history)

    print("\n[placeholder] 🚧 Last.fm sync integration coming soon.")
