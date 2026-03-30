import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import datetime as dt
import time

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI, Item, Task, Meeting, Break

class TestBreak(unittest.TestCase):

    def setUp(self):
        # Mock FILENAME to avoid creating real files during tests
        with patch('focuscli.FILENAME', 'test-plan.txt'):
            self.cli = FocusCLI()

        # Mock dependencies to avoid side effects
        self.cli.play_chime = MagicMock()
        self.cli.commit_to_ledger = MagicMock()
        self.cli._run_with_vi = MagicMock()

    def test_random_quote(self):
        """Break.random_quote returns a random inspirational quote"""
        self.assertIn(Break.random_quote(), Break.BREAK_QUOTES)

    def test_datetime_knowledge(self):
        now = dt.time(2,3)

        self.assertEqual(now.strftime('%I:%M %p'), '02:03 AM')

        with patch('time.time', return_value=50000.0):
            time_now = time.time()

        time_now_plus_five_minutes = time_now + (5 * 60)

        self.assertEqual(time_now_plus_five_minutes, 50300.0)

    def test_break_attributes(self):
        """Break objects have attributes"""
        b1 = Break.from_line("[B] Run errand 3-4 PM")

        self.assertEqual(b1.duration, 60)
        self.assertEqual(b1.start_time.strftime('%I:%M %p'), '03:00 PM')
        self.assertEqual(b1.end_time.strftime('%I:%M %p'), '04:00 PM')

        content = "Be Inspired!"
        start = dt.datetime.combine(dt.date.today(), dt.time(3,55))
        end = dt.datetime.combine(dt.date.today(), dt.time(4,00))
        duration = 5

        # All attributes
        b2 = Break.from_attributes(content, start_time=start, end_time=end, duration=duration)

        self.assertEqual(b2.duration, 5)
        self.assertEqual(b2.start_time.strftime('%I:%M %p'), '03:55 AM')
        self.assertEqual(b2.end_time.strftime('%I:%M %p'), '04:00 AM')

        # Only start and end
        b3 = Break.from_attributes(content, start_time=start, end_time=end, duration=None)

        self.assertEqual(b3.duration, 5)
        self.assertEqual(b3.start_time.strftime('%I:%M %p'), '03:55 AM')
        self.assertEqual(b3.end_time.strftime('%I:%M %p'), '04:00 AM')
 
        # Only start and duration
        b4 = Break.from_attributes(content, start_time=start, end_time=None, duration=duration)

        self.assertEqual(b4.duration, 5)
        self.assertEqual(b4.start_time.strftime('%I:%M %p'), '03:55 AM')
        self.assertEqual(b4.end_time.strftime('%I:%M %p'), '04:00 AM')

        # Only end and duration
        b5 = Break.from_attributes(content, start_time=None, end_time=end, duration=duration)

        self.assertEqual(b5.duration, 5)
        self.assertEqual(b5.start_time.strftime('%I:%M %p'), '03:55 AM')
        self.assertEqual(b5.end_time.strftime('%I:%M %p'), '04:00 AM')

    def test_to_ledger(self):
        """to_ledger should return a string suitable to write this break to the ledger"""
        break_line = "[B] Scheduled Break 11:15-12:30 PM"

        b1 = Break.from_line(break_line)

        self.assertEqual(b1.to_ledger(), break_line)

        content = "Be Inspired!"
        start = dt.datetime.combine(dt.date.today(), dt.time(3,55))
        end = dt.datetime.combine(dt.date.today(), dt.time(4,00))
        duration = 5

        b2 = Break.from_attributes(content, start, end, duration)

        self.assertEqual(b2.to_ledger(), f"[B] {content} 03:55-04:00 AM")

    def test_auto_adds_b_marker(self):
        """Break.from_attributes should automatically add [B] marker"""
        start = dt.datetime.combine(dt.date.today(), dt.time(3,55))
        end = dt.datetime.combine(dt.date.today(), dt.time(4,00))

        b1 = Break.from_attributes("Be Inspired!", start, end, None)

        self.assertEqual(b1.to_ledger(), "[B] Be Inspired! 03:55-04:00 AM")

    def test_break_detection(self):
        """Break.from_line should identify break pattern"""

        break_line = "[B] Lunch 12-1 PM"

        # Valid breaks
        b1 = Break.from_line(break_line)
        self.assertIsInstance(b1, Break)
        self.assertEqual(b1.content, "Lunch 12-1 PM")

        # [B] can't be a Meeting or a Task
        t1 = Task.from_line(break_line)
        self.assertIsNone(t1)

        m1 = Meeting.from_line(break_line)
        self.assertIsNone(m1)

    def test_specialized_is_pending(self):
        """Test that is_pending recognizes [B] status"""
        b1 = Break.from_attributes("A Break", start_time=dt.datetime.now(), end_time=None, duration=5)
        self.assertTrue(b1.is_pending)

        b2 = Break.from_attributes("A Break", start_time=dt.datetime.now(), end_time=None, duration=5)
        self.assertTrue(b2.is_pending)

    def test_transition_from_break_to_focus(self):
        """Test the transition logic from break back to Focus session."""
        now_dt = dt.datetime.now()
        start_dt = now_dt - dt.timedelta(minutes=5)
        break_item = Break.from_attributes("Test Break", start_time=start_dt, duration=5)

        self.cli.mode = "BREAK"
        # task_start_time was 10 mins before the break started
        # which is now_dt - 15 mins
        task_start_time_float = (start_dt - dt.timedelta(minutes=10)).timestamp()
        self.cli.task_start_time = task_start_time_float
        self.cli.break_meeting_interrupted = True

        now_float = now_dt.timestamp()
        with patch('time.time', return_value=now_float), \
             patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = now_dt
            self.cli._transition_from_break_to_focus(break_item=break_item)

        self.assertEqual(self.cli.mode, "FOCUS")
        self.assertFalse(self.cli.break_meeting_interrupted)
        # task_start_time should have advanced by the break duration (5 mins = 300s)
        expected_task_start = task_start_time_float + 300
        self.assertAlmostEqual(self.cli.task_start_time, expected_task_start)

    def test_transition_from_focus_to_break(self):
        self.cli.mode = "FOCUS"

        self.cli._transition_from_focus_to_break("b7")

        self.assertEqual(self.cli.mode, "BREAK")
        self.assertEqual(self.cli.triage_stack[0].duration, 7)

if __name__ == '__main__':
    unittest.main()
