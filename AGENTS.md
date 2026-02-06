# DeepWorkCLI Agent Instructions (v3.4)

## Core Philosophy: The Ledger
This program is a "lens" for a chronological journal. 
- **Rule 1:** Append, don't edit. We preserve history. (Exception: When a task is completed, cancelled, or deferred, all previous instances of that task's marker in the file should be updated to match the new state).
- **Rule 2:** Use Markers (e.g., `------- Triage Session -------`) to denote blocks of time.
- **Rule 3:** The "Free Write" is always the section after the very last marker in the file.

## Syntax & Hierarchy
- **Tasks:** Lines starting with `[]`, `[ ]`, `[x]`, `[-]`, or `[>]`.
- **Hierarchy:** Two leading spaces indicate a child relationship (subtask or note) to the task above.
- **Notes:** Anything not matching a task marker.

## Modal State Machine
- **Free Write (via vi):** User enters data. 
- **Triage (F5):** Parsed from Free Write. Commands: `j/k` (nav), `i` (ignore), `CTRL+hjkl` (move/indent), `p` (prioritize).
- **Work (w):** Focused UI. Commands: `x` (complete), `n/N` (add task/note), `-` (cancel), `>` (defer), `b` (break).
- **Exit Logic:** ANY exit from Work/Triage (q, SIGINT, etc.) must trigger a "Rescue Append" of pending items under an `------- Interrupted -------` marker.

## Critical Bugs to Fix
1. **Duplication on Interrupt:** Unfinished tasks are duplicating during 'q' exits.
2. **Ignored Note Leakage:** 'i' ignored notes are reappearing in Work mode.
3. **Missing Markers:** Markers are failing to write on certain 'q' exit paths.
