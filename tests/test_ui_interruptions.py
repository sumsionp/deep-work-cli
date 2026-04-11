import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import time
import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock FILENAME before importing FocusCLI
os.environ['FOCUS_FILENAME'] = 'test-plan.txt'

from focuscli import FocusCLI, ItemFactory

class TestMeetingInterruption(unittest.TestCase):
    def setUp(self):
        self.cli = FocusCLI()
        # Mock dependencies to avoid side effects
        self.cli.play_chime = MagicMock()
        self.cli.commit_to_ledger = MagicMock()
        self.cli._run_with_vi = MagicMock()

    def test_new_meeting_visually_interrupts_break(self):
        from focuscli import Break
        # 1. Setup a meeting
        now = datetime.now()
        meeting_start = now + timedelta(minutes=1)
        meeting_end = meeting_start + timedelta(minutes=5)

        meeting_text = f"[] Meeting at {meeting_start.strftime('%I:%M %p')} 5m"
        meeting_item = ItemFactory.from_line(meeting_text)

        # 2. Start a break
        break_item = Break.from_attributes("Quick Break", start_time=now, duration=5)
        self.cli.triage_stack = [break_item, meeting_item]
        self.cli.mode = "BREAK"
        self.cli.break_meeting_interrupted = False

        # 3. Fast forward time to when meeting starts
        future_now = meeting_start + timedelta(seconds=1)

        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now
            # 4. Call check_meetings
            self.cli.check_meetings()

        # 5. Verify results
        self.assertEqual(self.cli.mode, "BREAK") # Should stay in BREAK
        self.assertTrue(self.cli.break_meeting_interrupted) # But be interrupted
        self.assertEqual(self.cli.last_msg, "Meeting Starting: Meeting at " + meeting_start.strftime('%I:%M %p') + " 5m")

        # 6. Verify chime triggers in BREAK mode when interrupted
        self.cli.check_chime()
        self.cli.play_chime.assert_called()

    def test_break_during_ongoing_meeting_not_visually_interrupted(self):
        from focuscli import Break
        # 1. Setup an ongoing meeting that has already chimed
        now = datetime.now()
        meeting_start = now - timedelta(minutes=2)
        meeting_end = now + timedelta(minutes=5)

        meeting_text = f"[] Meeting at {meeting_start.strftime('%I:%M %p')} 10m"
        meeting_item = ItemFactory.from_line(meeting_text)

        # Mark as already chimed
        meeting_id = f"[] {meeting_item.content}_{meeting_item.start_time}"
        self.cli.chimed_meetings.add(meeting_id)

        # 2. Start a break
        break_item = Break.from_attributes("Quick Break", start_time=now, duration=5)
        self.cli.triage_stack = [break_item, meeting_item]
        self.cli.mode = "BREAK"
        self.cli.break_meeting_interrupted = False

        # 3. Call check_meetings
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            self.cli.check_meetings()

        # 4. Verify results
        self.assertEqual(self.cli.mode, "BREAK")
        self.assertFalse(self.cli.break_meeting_interrupted)

    def test_meeting_only_interrupts_current_task_visually(self):
        from focuscli import Task
        # 1. Setup a meeting
        now = datetime.now()
        meeting_start = now + timedelta(minutes=1)
        meeting_end = meeting_start + timedelta(minutes=5)

        meeting_text = f"[] Meeting at {meeting_start.strftime('%I:%M %p')} 5m"
        meeting_item = ItemFactory.from_line(meeting_text)

        # 2. Start with a task on top of the meeting
        task_item = Task.from_line("[] Do Task")
        self.cli.triage_stack = [task_item, meeting_item]
        self.cli.mode = "FOCUS"

        # Mock the reminder-interval check so we control exactly when the
        # second chime fires. (should_chime uses time.time(), so patching
        # focuscli.datetime does NOT control it.)
        self.cli.timers.should_chime = MagicMock(return_value=False)

        # Calling check_meetings before the meeting starts should not chime
        self.cli.check_meetings()
        self.cli.play_chime.assert_not_called()

        # 3. Fast forward time to when meeting starts
        future_now = meeting_start + timedelta(seconds=1)

        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now
            # 4. Call check_meetings — should fire the initial chime
            self.cli.check_meetings()

        # 5. Verify results: task stays on top, mode stays FOCUS,
        # initial chime fired exactly once
        self.assertEqual(self.cli.mode, "FOCUS")
        self.assertEqual(self.cli.last_msg, "Meeting Starting: " + meeting_item.content)
        self.assertEqual(self.cli.triage_stack[0], task_item)
        self.assertEqual(self.cli.play_chime.call_count, 1)

        # 6. Without the reminder interval elapsing, another call should NOT chime
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now + timedelta(seconds=5)
            self.cli.check_meetings()
        self.assertEqual(self.cli.play_chime.call_count, 1)

        # 7. When the reminder interval elapses, the next call SHOULD chime again
        self.cli.timers.should_chime.return_value = True
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now + timedelta(seconds=15)
            self.cli.check_meetings()
        self.assertEqual(self.cli.play_chime.call_count, 2)

if __name__ == '__main__':
    unittest.main()
