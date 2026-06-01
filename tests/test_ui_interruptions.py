from tests.isolated_test_case import IsolatedTestCase
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

class TestMeetingInterruption(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.cli = self.create_cli()
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

        # Calling check_meetings before the meeting starts should not chime
        self.cli.check_meetings()
        self.cli.play_chime.assert_not_called()

        # 3. Fast forward time to when meeting starts
        future_now = meeting_start + timedelta(seconds=1)

        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now
            # 4. Call check_meetings — should fire exactly one chime.
            # Without the last_chime_timestamp reset in check_meetings, the
            # reminder branch would also fire in this same call, producing 2.
            self.cli.check_meetings()

        # 5. Verify results: task STAYS on top (No Takeover), mode stays FOCUS,
        # initial chime fired exactly once (no double-chime)
        self.assertEqual(self.cli.mode, "FOCUS")
        self.assertEqual(self.cli.last_msg, "Meeting Starting: " + meeting_item.content)
        self.assertEqual(self.cli.triage_stack[0], task_item)
        self.assertEqual(self.cli.play_chime.call_count, 1)

        # 6. An immediate follow-up call should not re-chime — the 15s
        # reminder interval has not elapsed
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now + timedelta(seconds=5)
            self.cli.check_meetings()
        self.assertEqual(self.cli.play_chime.call_count, 1)

        # 7. Simulate the reminder interval elapsing by rewinding the
        # timer's last_chime_timestamp, then call again — should chime
        # NOTE: Task is still on top, meeting is due in timeline.
        self.cli.timers.chimer.last_chime_timestamp = 0
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_now + timedelta(seconds=20)
            self.cli.check_meetings()
        # Chime SHOULD happen because the meeting is due in the timeline
        self.assertEqual(self.cli.play_chime.call_count, 2)

    def test_no_reminder_when_meeting_focused(self):
        from focuscli import Meeting
        # 1. Setup a focused meeting
        now = datetime.now()
        meeting = Meeting.from_attributes("Focused Meeting", 0, ' ', start_time=now - timedelta(minutes=1), duration=30)
        meeting.promoted = True
        self.cli.triage_stack = [meeting]
        self.cli.mode = "FOCUS"

        # Mark as already chimed
        state_str = meeting.state if meeting.state.strip() else ''
        meeting_id = f"[{state_str}] {meeting.content}_{meeting.start_time}"
        self.cli.chimed_meetings.add(meeting_id)

        # Load chimer (simulating initial chime already happened)
        self.cli.timers.chimer.load(meeting.content)
        self.cli.play_chime.reset_mock()

        # 2. Fast forward and call check_meetings
        self.cli.timers.chimer.last_chime_timestamp = 0
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = now + timedelta(seconds=20)
            self.cli.check_meetings()

        # 3. Should NOT chime because it's focused
        self.cli.play_chime.assert_not_called()
        # The chimer is stopped by check_meetings for index 0
        self.assertFalse(self.cli.timers.chimer.is_active)

if __name__ == '__main__':
    unittest.main()
