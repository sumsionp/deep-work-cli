from tests.isolated_test_case import IsolatedTestCase
import unittest
import os
import sys
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI, Task, TaskStack, AddCommand

class TestTemplates(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.cli = self.create_cli()
        # Mock _run_with_vi to avoid opening actual vi
        self.vi_patcher = patch('focuscli.FocusCLI._run_with_vi')
        self.mock_vi = self.vi_patcher.start()

    def tearDown(self):
        self.vi_patcher.stop()
        super().tearDown()

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_add_new_template(self, mock_input):
        # Setup: n daily (where daily doesn't exist)
        mock_input.return_value = ["[] Task 1", "[] Task 2"]

        cmd = AddCommand(['n', 'daily'])
        cmd.execute(self.cli)

        # Verify template was created
        template_path = os.path.join("templates", "daily.txt")
        self.assertTrue(os.path.exists(template_path))
        with open(template_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "[] Task 1\n[] Task 2\n")

        # Verify tasks were added to triage stack
        self.assertEqual(len(self.cli.triage_stack), 2)
        self.assertEqual(self.cli.triage_stack[0].content, "Task 1")
        self.assertEqual(self.cli.triage_stack[1].content, "Task 2")

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_use_existing_template(self, mock_input):
        # Setup: Create template first
        template_dir = "templates"
        os.makedirs(template_dir)
        template_path = os.path.join(template_dir, "daily.txt")
        with open(template_path, 'w') as f:
            f.write("[] Existing Task")

        mock_input.return_value = ["[] Existing Task", "[] New Task"]

        cmd = AddCommand(['n', 'daily'])
        cmd.execute(self.cli)

        # Verify _get_multi_line_input was called with existing content and proper flags
        mock_input.assert_called_once_with(
            initial_content="[] Existing Task",
            start_insert=False,
            add_open_line=False
        )

        # Verify template was updated
        with open(template_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "[] Existing Task\n[] New Task\n")

        # Verify tasks added
        self.assertEqual(len(self.cli.triage_stack), 2)

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_multi_word_not_template(self, mock_input):
        # Setup: n "[] my new task"
        cmd = AddCommand(['n', '[]', 'my', 'new', 'task'])
        cmd.execute(self.cli)

        # Verify _get_multi_line_input was NOT called
        mock_input.assert_not_called()

        # Verify task was added directly
        self.assertEqual(len(self.cli.triage_stack), 1)
        self.assertEqual(self.cli.triage_stack[0].content, "my new task")

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_prioritize_template(self, mock_input):
        # Setup: Existing task in stack
        self.cli.triage_stack.append(Task("Existing"))

        mock_input.return_value = ["[] Priority Task"]

        cmd = AddCommand(['N', 'urgent'])
        cmd.execute(self.cli)

        # Verify prioritized (inserted at 0)
        self.assertEqual(self.cli.triage_stack[0].content, "Priority Task")
        self.assertEqual(self.cli.triage_stack[1].content, "Existing")

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_target_index_template(self, mock_input):
        # Setup: Multiple existing tasks
        self.cli.triage_stack.append(Task("Task 0"))
        self.cli.triage_stack.append(Task("Task 1"))

        mock_input.return_value = ["[] Inserted Task"]

        # n1 daily -> insert after index 0
        cmd = AddCommand(['n', '1', 'daily'])
        cmd.execute(self.cli)

        self.assertEqual(self.cli.triage_stack[0].content, "Task 0")
        self.assertEqual(self.cli.triage_stack[1].content, "Inserted Task")
        self.assertEqual(self.cli.triage_stack[2].content, "Task 1")

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_sanitize_template_name(self, mock_input):
        # Setup: n ../dangerous
        mock_input.return_value = ["[] Safe Task"]

        cmd = AddCommand(['n', '../dangerous'])
        cmd.execute(self.cli)

        # Verify template was created in the templates directory, NOT the parent
        self.assertFalse(os.path.exists("../dangerous.txt"))
        self.assertTrue(os.path.exists(os.path.join("templates", "dangerous.txt")))

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_discard_empty_template(self, mock_input):
        # Case 1: New template with only blank lines
        mock_input.return_value = ["", "  ", "\n"]
        cmd = AddCommand(['n', 'fatfinger'])
        cmd.execute(self.cli)

        template_path = os.path.join("templates", "fatfinger.txt")
        self.assertFalse(os.path.exists(template_path))
        self.assertEqual(self.cli.last_msg, "Empty template discarded.")

        # Case 2: Clearing an existing template
        os.makedirs("templates", exist_ok=True)
        with open(os.path.join("templates", "exists.txt"), 'w') as f:
            f.write("Some content")

        mock_input.return_value = []
        cmd = AddCommand(['n', 'exists'])
        cmd.execute(self.cli)

        self.assertFalse(os.path.exists(os.path.join("templates", "exists.txt")))
        self.assertEqual(self.cli.last_msg, "Empty template discarded.")

    @patch('focuscli.FocusCLI._get_multi_line_input')
    def test_no_newline_accumulation(self, mock_input):
        template_path = os.path.join("templates", "clean.txt")

        # Cycle 1: Create template
        # Mock returns stripped lines because _get_multi_line_input now strips them
        mock_input.return_value = ["[] Task"]
        AddCommand(['n', 'clean']).execute(self.cli)

        with open(template_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "[] Task\n")

        # Cycle 2: Edit template
        mock_input.return_value = ["[] Task", "[] Task 2"]
        AddCommand(['n', 'clean']).execute(self.cli)

        with open(template_path, 'r') as f:
            content = f.read()
        # Should still be clean: exactly one trailing newline added
        self.assertEqual(content, "[] Task\n[] Task 2\n")

    def test_get_multi_line_input_stripping(self):
        # We need to mock the file reading part or the vi part to test this
        # Let's mock _run_with_vi to write some messy content to the temp file
        def side_effect(args):
            temp_path = args[-1]
            with open(temp_path, 'w') as f:
                f.write("\n\n[] Task 1\n\n[] Task 2\n\n# Comment\n\n")

        self.mock_vi.side_effect = side_effect

        lines = self.cli._get_multi_line_input()

        # Should be stripped of leading/trailing blank lines and comments
        self.assertEqual(lines, ["[] Task 1", "", "[] Task 2"])

if __name__ == '__main__':
    unittest.main()
