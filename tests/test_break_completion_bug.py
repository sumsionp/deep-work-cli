
from tests.isolated_test_case import IsolatedTestCase
from focuscli import Break
from datetime import datetime, timedelta
import unittest

class TestBreakCompletionBug(IsolatedTestCase):
    def test_complete_break_with_x(self):
        cli = self.create_cli()
        # Setup a break
        cli.mode = "BREAK"
        break_item = Break.from_attributes(
            content="Test Break",
            start_time=datetime.now() - timedelta(minutes=10),
            duration=5
        )
        cli.triage_stack.append(break_item)
        cli.triage_stack.append(cli._process_multi_line_input(["[ ] Next Task"])[0])

        # Verify initial state
        self.assertEqual(cli.mode, "BREAK")
        self.assertEqual(len(cli.triage_stack), 2)
        self.assertIsInstance(cli.triage_stack[0], Break)

        # Execute 'x' command
        cli.handle_command("x")

        # Verify it transitioned to FOCUS
        self.assertEqual(cli.mode, "FOCUS", "Should transition to FOCUS after completing break with 'x'")
        self.assertEqual(len(cli.triage_stack), 1)
        self.assertEqual(cli.triage_stack[0].content, "Next Task")

    def test_ignore_break_with_i(self):
        cli = self.create_cli()
        # Setup a break
        cli.mode = "BREAK"
        break_item = Break.from_attributes(
            content="Test Break",
            start_time=datetime.now() - timedelta(minutes=10),
            duration=5
        )
        cli.triage_stack.append(break_item)

        # Execute 'i' command - this should not crash and should complete/ignore the break
        # It currently should have "Error: name 'ResolutionCommand' is not defined" in last_msg
        cli.handle_command("i")

        self.assertNotIn("Error: name 'ResolutionCommand' is not defined", cli.last_msg)

        # If it was the only task, it should go to EXIT mode (via transition to FOCUS first)
        self.assertIn(cli.mode, ["EXIT", "TRIAGE", "FOCUS"])

    def test_cancel_break_with_minus(self):
        cli = self.create_cli()
        # Setup a break
        cli.mode = "BREAK"
        break_item = Break.from_attributes(
            content="Test Break",
            start_time=datetime.now() - timedelta(minutes=10),
            duration=5
        )
        cli.triage_stack.append(break_item)
        cli.triage_stack.append(cli._process_multi_line_input(["[ ] Next Task"])[0])

        # Execute '-' command
        cli.handle_command("-")

        # Verify it transitioned to FOCUS
        self.assertEqual(cli.mode, "FOCUS", "Should transition to FOCUS after cancelling break with '-'")

if __name__ == "__main__":
    unittest.main()
