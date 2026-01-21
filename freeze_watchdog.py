"""Freeze watchdog utilities for diagnosing TUI hangs.

This module is intentionally dependency-free and safe to import from the TUI.
When enabled, it can emit periodic thread stack traces if the main loop stops
making forward progress (useful for diagnosing "frozen" UIs).
"""

from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _default_dump_path() -> str:
    return os.path.join(os.path.dirname(__file__), "logs", "freeze_watchdog.log")


@dataclass
class Heartbeat:
    """Stores a monotonic timestamp that indicates forward progress."""

    last_beat: float = field(default_factory=time.monotonic)
    last_note: str = "init"

    def beat(self, note: str = "") -> None:
        self.last_beat = time.monotonic()
        if note:
            self.last_note = note


def format_all_thread_traces() -> str:
    """Collect and format stack traces for all live threads."""

    frames = sys._current_frames()
    threads_by_id = {t.ident: t for t in threading.enumerate() if t.ident is not None}
    blocks: list[str] = []

    for thread_id, frame in frames.items():
        thread = threads_by_id.get(thread_id)
        name = thread.name if thread else "UnknownThread"
        daemon = thread.daemon if thread else "?"
        header = f"--- Thread {name} (id={thread_id}, daemon={daemon}) ---"
        blocks.append(header + "\n" + "".join(traceback.format_stack(frame)).rstrip())

    return "\n\n".join(blocks)


@contextmanager
def log_if_slow(logger, label: str, threshold_ms: float) -> Iterator[None]:
    """Log a warning when the wrapped block exceeds ``threshold_ms``."""

    start = time.monotonic()
    try:
        yield
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000.0
        if elapsed_ms >= threshold_ms:
            logger.warning("SLOW: %s took %.1fms", label, elapsed_ms)


def start_freeze_watchdog(
    logger,
    heartbeat: Heartbeat,
    *,
    enabled: Optional[bool] = None,
    threshold_s: Optional[float] = None,
    cooldown_s: Optional[float] = None,
    dump_path: Optional[str] = None,
) -> Optional[threading.Thread]:
    """Start a daemon thread that dumps stacks when the heartbeat stalls.

    Environment variables (defaults shown):
      - ``RADIOFREE_FREEZE_WATCHDOG``: 0/1 (default: 0)
      - ``RADIOFREE_FREEZE_WATCHDOG_THRESHOLD_S``: seconds (default: 8)
      - ``RADIOFREE_FREEZE_WATCHDOG_COOLDOWN_S``: seconds (default: 60)
      - ``RADIOFREE_FREEZE_WATCHDOG_DUMP_PATH``: path (default: logs/freeze_watchdog.log)
    """

    if enabled is None:
        enabled = _env_bool("RADIOFREE_FREEZE_WATCHDOG", default=False)
    if not enabled:
        return None

    threshold_s = threshold_s if threshold_s is not None else _env_float(
        "RADIOFREE_FREEZE_WATCHDOG_THRESHOLD_S", default=8.0
    )
    cooldown_s = cooldown_s if cooldown_s is not None else _env_float(
        "RADIOFREE_FREEZE_WATCHDOG_COOLDOWN_S", default=60.0
    )
    dump_path = dump_path or os.getenv("RADIOFREE_FREEZE_WATCHDOG_DUMP_PATH") or _default_dump_path()

    os.makedirs(os.path.dirname(dump_path), exist_ok=True)

    def _worker() -> None:
        last_dump = 0.0
        poll_s = min(1.0, max(0.2, threshold_s / 10.0))
        logger.info(
            "Freeze watchdog enabled (threshold=%.1fs cooldown=%.1fs dump_path=%s)",
            threshold_s,
            cooldown_s,
            dump_path,
        )
        while True:
            time.sleep(poll_s)
            now = time.monotonic()
            age = now - heartbeat.last_beat
            if age < threshold_s:
                continue
            if now - last_dump < cooldown_s:
                continue

            last_dump = now
            traces = format_all_thread_traces()
            message = (
                f"FREEZE WATCHDOG: no heartbeat for {age:.1f}s "
                f"(last_note={heartbeat.last_note!r})\n{traces}"
            )
            logger.error(message)
            try:
                with open(dump_path, "a", encoding="utf-8") as handle:
                    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    handle.write(f"\n[{ts}] {message}\n")
            except Exception as exc:
                logger.warning("Freeze watchdog failed to write dump file: %s", exc)

    thread = threading.Thread(target=_worker, name="freeze-watchdog", daemon=True)
    thread.start()
    return thread

