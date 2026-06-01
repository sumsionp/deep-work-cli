from tests.isolated_test_case import IsolatedTestCase
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI, Break, Task

class TestBreakPreemption(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.cli = self.create_cli()
        # Mock dependencies
        self.cli.play_chime = MagicMock()
        self.cli.commit_to_ledger = MagicMock()
        self.cli._run_with_vi = MagicMock()

    def test_scheduled_break_does_not_preempt(self):
        """A scheduled [B] break should chime but NOT take over focus."""
        now = datetime.now()
        # Break starts in 1 minute
        break_start = now + timedelta(minutes=1)
        break_item = Break.from_attributes("Scheduled Break", start_time=break_start, duration=15)

        # Regular task is focused
        task_item = Task.from_line("[] Focused Task")

        self.cli.triage_stack.populate([task_item, break_item])
        self.cli.mode = "FOCUS"

        # Verify initial state
        self.assertEqual(self.cli.triage_stack[0], task_item)
        self.assertIn(break_item, self.cli.triage_stack.meeting_timeline)

        # Fast forward to when break starts
        future_now = break_start + timedelta(seconds=1)

        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now
            self.cli.check_meetings()

        # Verify result: Task stays on top
        self.assertEqual(self.cli.triage_stack[0], task_item)
        self.assertEqual(self.cli.mode, "FOCUS")

        # Verify chime was triggered
        self.cli.play_chime.assert_called()
        # last_msg will include the time block because it's part of the item's content
        self.assertIn("Meeting Starting: Scheduled Break", self.cli.last_msg)

    def test_scheduled_break_reminders(self):
        """A due [B] break should trigger recurring reminders while in the timeline."""
        now = datetime.now()
        break_start = now - timedelta(minutes=1) # Already due
        break_item = Break.from_attributes("Due Break", start_time=break_start, duration=15)

        task_item = Task.from_line("[] Focused Task")
        self.cli.triage_stack.populate([task_item, break_item])
        self.cli.mode = "FOCUS"

        # Mark as already chimed once to test reminder branch
        meeting_id = f"[B] Due Break_{break_item.start_time}"
        self.cli.chimed_meetings.add(meeting_id)

        # Trigger reminder
        self.cli.timers.chimer.last_chime_timestamp = 0 # Force chime

        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            self.cli.check_meetings()

        # Chime should be called again for the reminder
        self.cli.play_chime.assert_called()

if __name__ == '__main__':
    unittest.main()
