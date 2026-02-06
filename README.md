Project Brief: A Python-based modal CLI tool (TUI) to capture and organize thoughts into trackable tasks and then present those tasks in a way to promote focused completion.

Core Mechanics:

File-Based: It parses a markdown-style .txt file where notes are taken and tasks are stored.

Tasks: Tasks start with [], [ ], [x], [-], or [>]. [] or [ ] means Pending. [x] means Done. [-] means Cancelled. [>] means Deferred (to another day / txt file)

Subtasks: Indented lines starting with a task marker [] or [x] are toggleable sub-actions.

Notes: Any line that isn't a task as defined above, is considered a note. Notes can be standalone. They can also belong to a task by being indented below a task.

Ledger Strategy: The program primarily appends to the file, preserving a chronological history of thoughts and actions rather than editing in place.

Markers:
  - ------- Triage Session "%D %r" -------
  - ------- Free Write Session "%D %r" -------
  - ------- Work Session "%D %r" -------
  - ------- Completed "%D %r" -------
  - ------- Deferred "%D %r" -------
  - ------- Interrupted "%D %r" -------

Modal Workflow: The program has three modes: Free Write, Triage, and Work
  - Free Write mode is in vi. This is where notes and tasks are entered freely and in any order. The focus here is getting everything moving and out.
  - Triage mode is where things start to get organized. It is entered by pressing F5 from an open file in vi. This mode is primarily for sorting tasks and notes.
  - Work mode is for focused task completion. It shows the triaged tasks one at a time in the triaged order with any associated tasks and notes.

Free Write Mode:
  - Enter by opening a file in vi
  - Exit into Triage Mode by typing F5

Triage Mode:
  - Picks up any notes and pending tasks from the end of the file after the last marker
  - Enter by typing F5 from any open vi file
  - Displays a list of notes and tasks from Free Write Mode
  - Displays a footer listing the possible commands
  - Select note or task by moving the selector down or up by typing 'j' or 'k' respectively
  - Ignore a note by selecting it and typing 'i'.
  - An ignored note is removed from the triaged list of notes and tasks.
  - Move a task or note by selecting it, holding down CTRL, and moving it left, down, up, or right with 'h', 'j', 'k', or 'l' respectively
  - Move a task and it's associated notes and subtasks to the top of the list by selecting it and typing 'p' (for prioritize)
  - Exit back to Free Write Mode by typing 'q'
  - Exit to Work Mode by typing 'w'

Work Mode:
  - Enter by typing 'w' from Triage Mode
  - Displays the top task from Triage Mode along with any associated notes or subtasks
  - Displays a footer listing the possible commands
  - Select a subtask by moving the selector down or up by typing 'j' or 'k' respectively
  - Complete the task and all its associated subtasks by typing 'x'
  - Complete a subtask by selecting it and typing 'x'
  - A completed task is marked with [x] and appended to the end of the file after a Completed marker.
  - Add a task by typing 'n', entering a line of text, and pressing Enter.
  - New tasks are appended to the list of tasks
  - Add a prioritized task by typing 'N', entering a line of text, and pressing Enter.
  - The prioritized task is displayed as the current focused task
  - Add a new note or subtask to the current focused task by typing 'n', entering a line of text beginning with '  ' (2 spaces), and pressing Enter.
  - New notes or subtasks added to the current focused task are shown under that task after any already associated notes or subtasks
  - Defer a task and all its subtasks by typing '>'
  - Defer a subtask by selecting it and typing '>'
  - A deferred task is marked with [>] appended to another .txt file after a Deferred marker. By default, that file will be called yyyymmdd-plan.txt, but it should be able to be changed.
  - Cancel a task or subtask by selecting it and typing '-'.
  - A cancelled task is marked with [-] and appended to the bottom of the file after a Cancelled marker.
  - Exit back to Free Write Mode by typing 'q'
  - Exit back to Triage Mode by typing 't'
  - Exiting Work Mode in any way, SIGINT, 'q', 't', appends any pending tasks and notes to the end of the file after an Interrupted marker
  - Exiting Work Mode the CLI displays a Daily Scorecard which is a summary of tasks Finished, Cancelled, and Deferred during that Work Session

Break Mode:
  - Take a measured break by typing 'b' in Work Mode
  - Restart the Work Session after a break by typing 'w'
