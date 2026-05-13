import unittest
import os
import sys
import shutil
import tempfile
from unittest.mock import patch, MagicMock

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI, Task, TaskStack, AddCommand

class TestTemplates(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.cli = FocusCLI()
        # Mock _run_with_vi to avoid opening actual vi
        self.vi_patcher = patch.object(FocusCLI, '_run_with_vi')
        self.mock_vi = self.vi_patcher.start()

    def tearDown(self):
        self.vi_patcher.stop()
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

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
        self.assertEqual(content, "[] Task 1\n[] Task 2")

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

        # Verify _get_multi_line_input was called with existing content
        mock_input.assert_called_once_with(initial_content="[] Existing Task")

        # Verify template was updated
        with open(template_path, 'r') as f:
            content = f.read()
        self.assertEqual(content, "[] Existing Task\n[] New Task")

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

if __name__ == '__main__':
    unittest.main()
