import os
import sys
import tempfile
import time
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from freeze_watchdog import Heartbeat, format_all_thread_traces, start_freeze_watchdog


class FreezeWatchdogTest(unittest.TestCase):
    def test_heartbeat_updates_note(self):
        hb = Heartbeat()
        hb.beat("step-a")
        self.assertEqual(hb.last_note, "step-a")

    def test_format_all_thread_traces_includes_mainthread(self):
        traces = format_all_thread_traces()
        self.assertIn("Thread MainThread", traces)

    def test_watchdog_disabled_returns_none(self):
        hb = Heartbeat()
        thread = start_freeze_watchdog(None, hb, enabled=False)  # type: ignore[arg-type]
        self.assertIsNone(thread)

    def test_watchdog_writes_dump_file_when_stalled(self):
        hb = Heartbeat()
        hb.last_beat -= 10.0

        with tempfile.TemporaryDirectory() as tmpdir:
            dump_path = os.path.join(tmpdir, "freeze.log")

            class DummyLogger:
                def info(self, *args, **kwargs):
                    pass

                def error(self, *args, **kwargs):
                    pass

                def warning(self, *args, **kwargs):
                    pass

            start_freeze_watchdog(
                DummyLogger(),
                hb,
                enabled=True,
                threshold_s=0.1,
                cooldown_s=0.0,
                dump_path=dump_path,
            )
            time.sleep(0.4)

            with open(dump_path, "r", encoding="utf-8") as handle:
                contents = handle.read()
            self.assertIn("FREEZE WATCHDOG", contents)


if __name__ == "__main__":
    unittest.main()

