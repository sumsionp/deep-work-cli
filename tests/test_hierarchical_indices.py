import unittest
from unittest.mock import MagicMock, patch
import copy
from focuscli import FocusCLI, Task, Note, CommandParser
from tests.isolated_test_case import IsolatedTestCase

class TestHierarchicalIndices(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.cli = self.create_cli()

        # Setup a complex stack
        # Task 0
        #   Subtask 0.0 (Task)
        #     Sub-subtask 0.0.0 (Task)
        #   Subtask 0.1 (Note)
        # Task 1

        t0 = Task("Task 0")
        s0_0 = Task("Subtask 0.0")
        s0_0_0 = Task("Sub-subtask 0.0.0")
        s0_1 = Note("Subtask 0.1")

        s0_0.children.append(s0_0_0)
        t0.children.extend([s0_0, s0_1])

        t1 = Task("Task 1")

        self.cli.triage_stack.extend([t0, t1])
        self.cli.commit_to_ledger = MagicMock()
        self.cli._edit_item_obj = MagicMock(side_effect=lambda x: x)

    def test_resolve_hierarchical_subtask(self):
        self.cli.mode = "FOCUS"
        # Resolve Sub-subtask 0.0.0 via index 0.0.0
        cmd = CommandParser.parse(self.cli, "x0.0.0", "FOCUS")
        cmd.execute(self.cli)

        # Verify it was resolved in the stack
        t0 = self.cli.triage_stack[0]
        s0_0 = t0.children[0]
        s0_0_0 = s0_0.children[0]
        self.assertEqual(s0_0_0.state, 'x')

        # Check ledger call - ResolveCommand calls commit_to_ledger with hierarchical_context
        # which is the top-level item pruned to the path of the resolved item.
        args, kwargs = self.cli.commit_to_ledger.call_args_list[0]
        self.assertEqual(args[0], 'Task Completed')
        # hierarchical_context should have state ' ' for top level Task 0
        self.assertEqual(args[1][0].content, "Task 0")
        self.assertEqual(args[1][0].state, " ")
        # And Subtask 0.0 should have state ' '
        self.assertEqual(args[1][0].children[0].content, "Subtask 0.0")
        self.assertEqual(args[1][0].children[0].state, " ")
        # And Sub-subtask 0.0.0 should have state 'x'
        self.assertEqual(args[1][0].children[0].children[0].content, "Sub-subtask 0.0.0")
        self.assertEqual(args[1][0].children[0].children[0].state, "x")

    def test_resolve_note_error(self):
        self.cli.mode = "FOCUS"
        # Try to resolve Subtask 0.1 (Note)
        cmd = CommandParser.parse(self.cli, "x0.1", "FOCUS")
        cmd.execute(self.cli)

        self.assertEqual(self.cli.last_msg, "Invalid action for a note.")

        # Verify it's still a Note and unchanged
        self.assertIsInstance(self.cli.triage_stack[0].children[1], Note)

    def test_cancel_top_level_index_1(self):
        self.cli.mode = "FOCUS"
        # Cancel Task 1 (index 1) while focused on Task 0
        cmd = CommandParser.parse(self.cli, "-1", "FOCUS")
        cmd.execute(self.cli)

        # Task 1 should be gone from stack
        self.assertEqual(len(self.cli.triage_stack), 1)
        self.assertEqual(self.cli.triage_stack[0].content, "Task 0")

        # Check ledger call
        args, kwargs = self.cli.commit_to_ledger.call_args_list[0]
        self.assertEqual(args[0], 'Task Cancelled')
        self.assertEqual(args[1][0].content, "Task 1")
        self.assertEqual(args[1][0].state, "-")

    def test_edit_hierarchical_subtask(self):
        self.cli.mode = "FOCUS"
        # Edit Sub-subtask 0.0.0
        edited_item = Task("Edited Sub-subtask")
        self.cli._edit_item_obj = MagicMock(return_value=edited_item)

        cmd = CommandParser.parse(self.cli, "e0.0.0", "FOCUS")
        cmd.execute(self.cli)

        # Verify it was updated
        self.assertEqual(self.cli.triage_stack[0].children[0].children[0].content, "Edited Sub-subtask")

    def test_invalid_index(self):
        self.cli.mode = "FOCUS"
        cmd = CommandParser.parse(self.cli, "x0.5", "FOCUS")
        cmd.execute(self.cli)
        self.assertIn("Error: Invalid sub-index 5", self.cli.last_msg)

    def test_resolve_focus_no_index(self):
        self.cli.mode = "FOCUS"
        # Without index, should resolve the deepest pending task (Sub-subtask 0.0.0)
        cmd = CommandParser.parse(self.cli, "x", "FOCUS")
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].children[0].children[0].state, 'x')

    def test_resolve_triage_no_index(self):
        self.cli.mode = "TRIAGE"
        # In TRIAGE, 'x' should resolve Task 0 (top-level)
        cmd = CommandParser.parse(self.cli, "x", "TRIAGE")
        cmd.execute(self.cli)

        # Task 0 should be gone
        self.assertEqual(len(self.cli.triage_stack), 1)
        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")

if __name__ == "__main__":
    unittest.main()
