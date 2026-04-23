import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import os
import sys

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI, DeferCommand, Task, Meeting, Break

class TestTargetedDeferral(unittest.TestCase):
    def setUp(self):
        with patch('focuscli.FILENAME', 'test-plan.txt'):
            self.cli = FocusCLI()
        self.cli.commit_to_ledger = MagicMock()

    def test_defer_task_to_index(self):
        t0 = Task("Task 0")
        t1 = Task("Task 1")
        t2 = Task("Task 2")
        self.cli.triage_stack.populate([t0, t1, t2])

        cmd = DeferCommand([">", "1"])
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")
        self.assertEqual(self.cli.triage_stack[1].content, "Task 0")
        self.assertEqual(self.cli.triage_stack[2].content, "Task 2")

    def test_defer_task_to_end(self):
        t0 = Task("Task 0")
        t1 = Task("Task 1")
        t2 = Task("Task 2")
        self.cli.triage_stack.populate([t0, t1, t2])

        cmd = DeferCommand([">"])
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")
        self.assertEqual(self.cli.triage_stack[1].content, "Task 2")
        self.assertEqual(self.cli.triage_stack[2].content, "Task 0")

    def test_defer_task_out_of_bounds(self):
        t0 = Task("Task 0")
        t1 = Task("Task 1")
        self.cli.triage_stack.populate([t0, t1])

        cmd = DeferCommand([">", "5"])
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")
        self.assertEqual(self.cli.triage_stack[1].content, "Task 0")

    def test_defer_meeting_no_args_converts_to_task(self):
        m0 = Meeting("Meeting 0 10:00 AM-11:00 AM")
        t1 = Task("Task 1")
        self.cli.triage_stack.populate([m0, t1])

        cmd = DeferCommand([">"])
        cmd.execute(self.cli)

        self.assertEqual(len(self.cli.triage_stack), 2)
        self.assertIsInstance(self.cli.triage_stack[1], Task)
        self.assertNotIsInstance(self.cli.triage_stack[1], Meeting)
        self.assertEqual(self.cli.triage_stack[1].content, "Meeting 0")
        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")

    def test_defer_meeting_with_index_converts_to_task(self):
        m0 = Meeting("Meeting 0 10:00 AM-11:00 AM")
        t1 = Task("Task 1")
        t2 = Task("Task 2")
        self.cli.triage_stack.populate([m0, t1, t2])

        cmd = DeferCommand([">", "1"])
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")
        self.assertIsInstance(self.cli.triage_stack[1], Task)
        self.assertEqual(self.cli.triage_stack[1].content, "Meeting 0")

    def test_reschedule_meeting(self):
        now = datetime.now().replace(hour=10, minute=0)
        m0 = Meeting("Meeting 0 10:00 AM-11:00 AM", start_time=now, duration=60)
        self.cli.triage_stack.populate([m0])

        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.strptime = datetime.strptime
            cmd = DeferCommand([">", "2", "PM"])
            cmd.execute(self.cli)

        self.assertIsInstance(self.cli.triage_stack[0], Meeting)
        self.assertEqual(self.cli.triage_stack[0].start_time.hour, 14)
        self.assertEqual(self.cli.triage_stack[0].duration, 60)

    def test_defer_negative_index(self):
        t0 = Task("Task 0")
        t1 = Task("Task 1")
        t2 = Task("Task 2")
        self.cli.triage_stack.populate([t0, t1, t2])

        cmd = DeferCommand([">", "-1"])
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")
        self.assertEqual(self.cli.triage_stack[1].content, "Task 0")

if __name__ == '__main__':
    unittest.main()
