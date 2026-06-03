
from tests.isolated_test_case import IsolatedTestCase
from focuscli import Break
from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock

class TestBreakChimeV2(IsolatedTestCase):
    def test_no_start_chime_for_auto_break(self):
        cli = self.create_cli()
        cli.play_chime = MagicMock()

        # 1. Setup a break without a schedule (uninitialized)
        break_item = Break.from_line("[B] Unscheduled Break")
        cli.triage_stack.append(break_item)
        cli.mode = "FOCUS"

        # 2. Transition from FOCUS to BREAK via check_meetings
        # When check_meetings is called, it initializes the break
        # and SHOULD NOT chime since it's an auto-started unscheduled break.
        cli.check_meetings()

        # It currently chimes because it initializes it then sees it's active.
        self.assertEqual(cli.play_chime.call_count, 0, "Should not chime for auto-started unscheduled break")
        self.assertEqual(cli.mode, "BREAK")
        self.assertIsNotNone(break_item.end_time)

    def test_start_chime_for_scheduled_meeting(self):
        cli = self.create_cli()
        cli.mode = "FOCUS"
        cli.play_chime = MagicMock()

        # A scheduled meeting starting NOW should chime
        now = datetime.now()
        m = cli._process_multi_line_input([f"[] Meeting at {now.strftime('%I:%M %p')} 10m"])[0]
        cli.triage_stack.append(m)

        cli.check_meetings()
        self.assertEqual(cli.play_chime.call_count, 1)

if __name__ == "__main__":
    unittest.main()
