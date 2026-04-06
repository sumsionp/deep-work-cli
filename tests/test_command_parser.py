import unittest
import os
import sys

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import CommandParser, QuitCommand, AddCommand, ResolveCommand

class TestCommandParser(unittest.TestCase):
    def setUp(self):
        from focuscli import FocusCLI
        self.cli = FocusCLI()

    def test_basic_parsing(self):
        cmd = CommandParser.parse(self.cli, "q", "TRIAGE")
        self.assertIsInstance(cmd, QuitCommand)

        cmd = CommandParser.parse(self.cli, "n task", "FOCUS")
        self.assertIsInstance(cmd, AddCommand)
        self.assertEqual(cmd.parts, ["n", "task"])

    def test_resolution_parsing(self):
        cmd = CommandParser.parse(self.cli, "x", "FOCUS")
        self.assertIsInstance(cmd, ResolveCommand)

        cmd1 = CommandParser.parse(self.cli, "x1", "TRIAGE")
        self.assertIsInstance(cmd, ResolveCommand)

    def test_mode_aware_parsing(self):
        # In EXIT mode, only q and w are allowed
        cmd = CommandParser.parse(self.cli, "f", "EXIT")
        self.assertIsNone(cmd)

        cmd = CommandParser.parse(self.cli, "q", "EXIT")
        self.assertIsInstance(cmd, QuitCommand)

if __name__ == '__main__':
    unittest.main()
