from tests.isolated_test_case import IsolatedTestCase
import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI, TriageCommand, AddCommand, Task, Note

class TestCommandsExecution(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        super().setUp()
        if True: # Patched FILENAME removed
            self.cli = self.create_cli()
        self.cli.commit_to_ledger = MagicMock()
        self.cli._process_multi_line_input = MagicMock()
        self.cli._get_multi_line_input = MagicMock(return_value=[])

    def test_triage_command_execution(self):
        cmd = TriageCommand(["t"])
        self.cli.mode = "FOCUS"
        cmd.execute(self.cli)
        self.assertEqual(self.cli.mode, "TRIAGE")
        self.cli.commit_to_ledger.assert_called_with("Triage Session Started at", [])

    def test_add_command_execution(self):
        # Mocking the item creation because it normally uses regex and class methods
        # and I want to verify if the list is updated correctly
        new_task = Task("New Task")
        self.cli._process_multi_line_input.return_value = [new_task]

        cmd = AddCommand(["n", "New Task"])
        self.cli.mode = "TRIAGE"
        cmd.execute(self.cli)

        self.assertEqual(len(self.cli.triage_stack), 1)
        self.assertEqual(self.cli.triage_stack[0].content, "New Task")

if __name__ == '__main__':
    unittest.main()
