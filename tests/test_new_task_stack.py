import unittest
from datetime import datetime, timedelta
import os
import sys

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import TaskStack, Task, Meeting, Note

class TestNewTaskStack(unittest.TestCase):
    def test_stack_partitioning(self):
        now = datetime.now()
        task = Task("Normal Task")
        active_meeting = Meeting("Active Meeting", start_time=now - timedelta(minutes=5), end_time=now + timedelta(minutes=5))
        future_meeting = Meeting("Future Meeting", start_time=now + timedelta(minutes=10), end_time=now + timedelta(minutes=20))

        stack = TaskStack()
        stack.populate([task, active_meeting, future_meeting])

        self.assertEqual(len(stack.focus_queue), 2)
        self.assertEqual(len(stack.meeting_timeline), 1)
        self.assertIn(active_meeting, stack.focus_queue)
        self.assertIn(future_meeting, stack.meeting_timeline)

    def test_due_meeting_logic(self):
        now = datetime.now()
        task = Task("Focused")
        due_meeting = Meeting("Starting", start_time=now - timedelta(seconds=1), end_time=now + timedelta(minutes=10))

        stack = TaskStack()
        stack.focus_queue = [task]
        stack.meeting_timeline = [due_meeting]

        from unittest.mock import patch
        with patch('focuscli.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            due = stack.check_for_due_meetings()
            self.assertEqual(due.content, due_meeting.content)
            self.assertEqual(len(stack.focus_queue), 1)
            self.assertEqual(stack.focus_queue[0].content, "Focused")

            # Now promote it
            promoted = stack.promote_due_meetings()
            self.assertEqual(promoted.content, due_meeting.content)
            self.assertEqual(len(stack.focus_queue), 2)
            self.assertEqual(stack.focus_queue[0].content, due_meeting.content)

if __name__ == '__main__':
    unittest.main()

    def test_compatibility(self):
        stack = TaskStack()
        task1 = Task("T1")
        stack.append(task1)
        self.assertEqual(len(stack), 1)
        self.assertEqual(stack[0].content, "T1")

        task2 = Task("T2")
        stack.insert(0, task2)
        self.assertEqual(stack[0].content, "T2")
        self.assertEqual(stack[1].content, "T1")

        popped = stack.pop(0)
        self.assertEqual(popped.content, "T2")
        self.assertEqual(len(stack), 1)
