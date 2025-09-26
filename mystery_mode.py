"""Mystery recommendation mode for surfacing five secret song options.

This module defines :class:`MysteryModeManager`, a coordinator that queries
GPT for five similar tracks whenever the currently playing song changes. The
manager keeps GPT's chosen follow-up track hidden from the listener while still
queuing it on Spotify, and exposes helpers for rendering a neutral list of
options as well as locking in a listener's manual choice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(slots=True)
class MysteryTrack:
    """Container describing a mystery mode recommendation."""

    track_name: str
    artist_name: str
    uri: str | None


class MysteryModeManager:
    """Coordinate GPT-powered mystery recommendations for the next track."""

    def __init__(
        self,
        gpt_dj: Any,
        spotify_controller: Any,
        prompt_template: str,
    ) -> None:
        """Initialize the manager with GPT and Spotify helpers."""

        self.dj = gpt_dj
        self.sp = spotify_controller
        self.prompt_template = prompt_template
        self.enabled: bool = False
        self._awaiting_choice: bool = False
        self._choices: list[MysteryTrack] = []
        self._selected_index: int | None = None

    @property
    def awaiting_choice(self) -> bool:
        """Return ``True`` when the UI should capture numeric selections."""

        return self._awaiting_choice

    @property
    def choice_count(self) -> int:
        """Return the number of active options in the current mystery round."""

        return len(self._choices)

    def clear_choices(self) -> None:
        """Reset any outstanding GPT choices so regular keybinds resume."""

        self._choices.clear()
        self._selected_index = None
        self._awaiting_choice = False

    def toggle(self) -> bool:
        """Toggle mystery mode on/off, clearing pending choices if disabled."""

        self.enabled = not self.enabled
        if not self.enabled:
            self.clear_choices()
        return self.enabled

    def activate_round(
        self,
        song_name: str,
        artist_name: str,
        cancel_event: Any | None = None,
    ) -> str | None:
        """Fetch five follow-up tracks for ``song_name``/``artist_name``.

        Returns a sanitized Rich markup string safe for user display or ``None``
        if the GPT call failed or produced no valid options.
        """

        if not self.enabled or not self.prompt_template:
            return None

        prompt = self.prompt_template.format(
            song_name=song_name,
            artist_name=artist_name,
        )
        if cancel_event is not None:
            cancel_event.clear()
        response = self.dj.ask(prompt, cancel_event=cancel_event)
        if not response:
            self.dj.logger.warning("Mystery mode: no response from GPT")
            self.clear_choices()
            return None

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            self.dj.logger.error("Mystery mode JSON parse error: %s", exc)
            self.clear_choices()
            return None

        options = self._extract_options(parsed)
        selected_index = self._extract_selected_index(parsed)
        if not options:
            self.dj.logger.warning("Mystery mode: GPT returned no options")
            self.clear_choices()
            return None

        self._choices = []
        for option in options[:5]:
            name = option.get("track_name")
            artist = option.get("artist_name")
            if not name or not artist:
                continue
            uri = self.sp.search_track(name, artist)
            self._choices.append(MysteryTrack(name, artist, uri))

        if not self._choices:
            self.dj.logger.warning("Mystery mode: no playable Spotify tracks")
            self.clear_choices()
            return None

        self._selected_index = (
            selected_index if selected_index is not None else None
        )
        if (
            self._selected_index is not None
            and 0 <= self._selected_index < len(self._choices)
        ):
            uri = self._choices[self._selected_index].uri
            if uri:
                self.sp.add_to_queue(uri)
            else:
                self.dj.logger.warning(
                    "Mystery mode: GPT-selected track missing Spotify URI"
                )

        self._awaiting_choice = True
        return self._build_display_text()

    def play_choice(self, selection_index: int) -> tuple[bool, str]:
        """Play the listener's chosen track immediately."""

        if not self._awaiting_choice:
            return False, "No mystery selection pending."

        zero_index = selection_index - 1
        if zero_index < 0 or zero_index >= len(self._choices):
            return False, "Invalid selection."

        choice = self._choices[zero_index]
        if not choice.uri:
            return False, "Selected track is unavailable on Spotify."

        self.sp.play_track(choice.uri)
        self.clear_choices()
        return True, f"Now playing {choice.track_name} by {choice.artist_name}."

    def _extract_options(self, parsed: Any) -> Iterable[dict[str, Any]]:
        """Return the list of options from an arbitrary GPT response."""

        if isinstance(parsed, dict):
            options = parsed.get("options")
            if isinstance(options, list):
                return options
        if isinstance(parsed, list):
            return parsed
        return []

    def _extract_selected_index(self, parsed: Any) -> int | None:
        """Return the zero-based index GPT marked as its secret choice."""

        if isinstance(parsed, dict):
            raw_index = parsed.get("selected_index")
            if isinstance(raw_index, int):
                # ``selected_index`` is expected to be 1-based for readability.
                return raw_index - 1 if raw_index > 0 else raw_index
        return None

    def _build_display_text(self) -> str:
        """Return Rich markup summarising GPT's options without spoilers."""

        lines = ["[bold]Mystery Crate Picks[/bold]"]
        for idx, track in enumerate(self._choices, start=1):
            availability = "" if track.uri else " [dim](unavailable)[/dim]"
            lines.append(
                f"{idx}. {track.track_name} — {track.artist_name}{availability}"
            )
        lines.append("")
        lines.append("[dim]Press 1-5 to choose the next track.[/dim]")
        return "\n".join(lines)

