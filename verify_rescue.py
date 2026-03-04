
import os
import signal
import time
import subprocess
from datetime import datetime

# Setup a test file
FILENAME = "test_rescue.txt"
if os.path.exists(FILENAME): os.remove(FILENAME)

# We will run a small script that initializes the CLI and then we'll send it a signal
script_content = f"""
import os
import signal
import sys
import time
from deepworkcli import DeepWorkCLI

FILENAME = "{FILENAME}"
cli = DeepWorkCLI()
import deepworkcli
deepworkcli.FILENAME = FILENAME

# Setup a stack
cli.triage_stack = [{{'line': '[] Task 1', 'notes': []}}, {{'line': '[] Task 2', 'notes': []}}]

# Define a way to trigger the rescue manually for testing or just wait for signal
# Since we updated run() to have signal handlers, we just need run() to start.
# But run() starts Free Write. Let's mock enter_free_write to do nothing.
cli.enter_free_write = lambda: None

try:
    cli.run()
except SystemExit:
    pass
"""

with open("temp_test_rescue.py", "w") as f:
    f.write(script_content)

# Start the process
proc = subprocess.Popen(["python3", "temp_test_rescue.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Wait a bit for it to initialize
time.sleep(2)

# Send SIGINT (Ctrl-C)
proc.send_signal(signal.SIGINT)

# Wait for it to finish
proc.wait()

print("\n--- After Interruption ---")
if os.path.exists(FILENAME):
    with open(FILENAME, 'r') as f:
        content = f.read()
        print("\n--- File Content ---")
        print(content)

        if "------- Interrupted" in content and "[] Task 1" in content and "[] Task 2" in content:
            print("\nSUCCESS: Tasks rescued on CTRL-C.")
        else:
            print("\nFAILURE: Tasks not correctly rescued.")
else:
    print("\nFAILURE: Ledger file not created.")

# Cleanup
if os.path.exists(FILENAME): os.remove(FILENAME)
if os.path.exists("temp_test_rescue.py"): os.remove("temp_test_rescue.py")
