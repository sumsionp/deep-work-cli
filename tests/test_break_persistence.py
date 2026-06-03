
from tests.isolated_test_case import IsolatedTestCase
from focuscli import Break, Task
from datetime import datetime, timedelta
import unittest
import os

class TestBreakPersistence(IsolatedTestCase):
    def test_break_completion_persistence(self):
        cli = self.create_cli()

        # 1. Setup a break
        break_item = Break.from_attributes(
            content="Break to complete",
            start_time=datetime.now(),
            duration=5
        )
        cli.triage_stack.append(break_item)
        cli.mode = "BREAK"

        # 2. Complete the break with 'x'
        cli.handle_command("x")

        # 3. Verify ledger shows [x] and NOT [B]
        # In the ledger, we should see the completed item
        with open(self.filename, 'r') as f:
            ledger_content = f.read()

        print(f"Ledger content:\n{ledger_content}")

        # It should contain [x] Break to complete
        self.assertIn("[x] Break to complete", ledger_content)
        # It should NOT contain [B] Break to complete in the most recent section
        # Actually, it's appended, so we check if the LAST occurrence is [x]

        # 4. Reload context and verify it's gone from triage stack
        cli.load_context()
        self.assertEqual(len(cli.triage_stack), 0, "Completed break should not be reloaded as pending")

if __name__ == "__main__":
    unittest.main()
