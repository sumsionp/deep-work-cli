# DeepWorkCLI: Agent Instructions

## Core Philosophy
- **Ledger Only:** We prioritize appending to the journal file over in-place editing.
- **Modal Separation:** Strictly maintain the boundaries between Free Write, Triage, and Work modes.
- **Hierarchy Matters:** Indentation (2 spaces) defines subtasks. Do not flatten this structure during parsing.

## Critical Guardrails for Jules
1. **The Rescue Append:** When the program exits (SIGINT or 'q'), unfinished tasks must be moved to the bottom of the file. 
   - *Bug Alert:* Ensure we do not duplicate tasks that are already present in the Free Write section.
2. **Visual Integrity:** Do not change the user's prose. Only lines starting with `[]`, `[ ]`, `[x]`, `[-]`, or `[>]` (and their indented children) are "tasks." Everything else is a "note" and should be preserved as-is.
3. **Timer Logic:** The 90-minute focus guard is a visual-only inverted color alert. Do not automatically kill the process.
