import unittest
import os
import sys
import tempfile
import shutil

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from focuscli import FocusCLI

class IsolatedTestCase(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.filename = os.path.join(self.test_dir, "test_ledger.txt")
        self.log_file = os.path.join(self.test_dir, "test_focus_activity.log")
        self.templates_dir = os.path.join(self.test_dir, "templates")

        # Original sys.argv and working directory
        self.original_argv = sys.argv[:]
        self.original_cwd = os.getcwd()

        # Set sys.argv to something predictable
        sys.argv = [sys.argv[0], self.filename]

        # Change to temp directory so relative paths in app work as expected
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        sys.argv = self.original_argv

    def create_cli(self, **kwargs):
        params = {
            'filename': self.filename,
            'log_file': self.log_file,
            'templates_dir': self.templates_dir
        }
        params.update(kwargs)
        return FocusCLI(**params)
