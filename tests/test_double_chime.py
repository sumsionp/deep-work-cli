
from tests.isolated_test_case import IsolatedTestCase
from focuscli import Break
from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock
import time

class TestDoubleChime(IsolatedTestCase):
    def test_double_chime_on_break_start(self):
        cli = self.create_cli()
        cli.play_chime = MagicMock()

        # Setup an active break
        start_time = datetime.now() - timedelta(seconds=1)
        break_item = Break.from_attributes(
            content="Active Break",
            start_time=start_time,
            duration=5
        )

        cli.triage_stack.append(break_item)
        cli.mode = "FOCUS"
        cli.timers.last_chime_timestamp = 0

        # 1. check_chime()
        # If it's already considered BREAK mode by some other logic?
        # No, it's still FOCUS. check_chime does nothing for FOCUS unless exceeded.
        cli.check_chime()

        # 2. check_meetings()
        # It's active. It's not in chimed_meetings.
        # It calls play_session_chime() -> sets timers.last_chime_timestamp = now
        cli.check_meetings()

        # 3. check_chime() again (as in main loop)
        # Now mode is BREAK.
        # remaining is positive (active break).
        # So check_chime() does nothing.
        cli.check_chime()

        self.assertEqual(cli.play_chime.call_count, 1)

    def test_double_chime_on_expired_break_start(self):
        cli = self.create_cli()
        cli.play_chime = MagicMock()
        cli.timers.last_chime_timestamp = 0

        # Setup an EXPIRED break
        start_time = datetime.now() - timedelta(minutes=10)
        break_item = Break.from_attributes(
            content="Expired Break",
            start_time=start_time,
            duration=5
        )

        cli.triage_stack.append(break_item)
        cli.mode = "FOCUS"

        # 1. check_chime()
        # mode is FOCUS. Not exceeded. Does nothing.
        cli.check_chime()

        # 2. check_meetings()
        # is active. not in chimed_meetings.
        # calls play_session_chime() -> play_chime(), last_chime_timestamp = now.
        # sets mode = BREAK.
        cli.check_meetings()

        # 3. check_chime()
        # mode is BREAK. remaining is -5 mins.
        # It checks if timers.should_chime(60).
        # Since last_chime_timestamp was JUST set to now, should_chime(60) is FALSE.
        # SO IT DOES NOT CHIME AGAIN.
        cli.check_chime()

        self.assertEqual(cli.play_chime.call_count, 1)

if __name__ == "__main__":
    unittest.main()
