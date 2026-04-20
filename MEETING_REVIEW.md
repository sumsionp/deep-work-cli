# Meeting Handling Code Review

This document provides a detailed technical analysis of the current meeting handling implementation in `focuscli.py` and compares it with the proposed future state.

## 1. Current Technical Implementation

### A. Stack Management (`sort_triage_stack`)
The current logic (lines 941–965) prioritizes active meetings above all else:
- **Identification**: It iterates through the `triage_stack` and uses `item.is_active()` to find meetings whose start time has passed but end time has not.
- **Reordering**: It reconstructs the stack in this order: `[Active Meetings] + [Regular Tasks] + [Sorted Inactive Meetings]`.
- **Result**: This forces any meeting that starts to the `triage_stack[0]` position, immediately taking focus.

### B. Alerting Logic (`check_meetings`)
The alerting system (lines 1608–1658) runs on every heartbeat of the main loop:
- **Initial Alert**: When a meeting first becomes active, it plays a chime and adds a `meeting_id` to `self.chimed_meetings`. This prevents the "starting" chime from repeating.
- **Periodic Reminders**:
    - It searches the stack for an active meeting that is *not* at index 0.
    - If found, it triggers a chime every 15 seconds using `self.timers.should_chime(interval_seconds=15)`.
- **State Coupling**: The logic for transitioning to `BREAK` mode is intertwined with the alerting logic, making it difficult to modify one without affecting the other.

---

## 2. Comparison: Current vs. Proposed Vision

| Feature | Current State | Proposed Vision |
| :--- | :--- | :--- |
| **Meeting Placement** | Forced to `triage_stack[0]` (Focus). | Placed at `triage_stack[1]` (Next). |
| **Notification System** | Procedural loop in `check_meetings`. | Dedicated `Chimer` timer object. |
| **Notification Scope** | Alerts for any non-focused active meeting. | Only the "next" starting meeting alerts. |
| **Persistence** | `chimed_meetings` set (in-memory). | Potential for `pending_meeting_stack`. |
| **Command set** | Regex patterns in `n` / `N` commands. | Explicit `s` (Schedule) command. |

---

## 3. Architectural Analysis of Suggestions

### The `TaskStack` & `pending_meeting_stack`
The current `FocusCLI` class is over-encapsulated, managing both the UI and the data structure logic.
- **Problem**: Filtering the entire `triage_stack` for meetings every 0.1 seconds is inefficient and litters the codebase with `isinstance(item, Meeting)` checks.
- **Solution**: A `TaskStack` class could maintain two distinct lists:
    1. `work_queue`: The sequential list of tasks the user is working through.
    2. `meeting_timeline`: A sorted list of `Meeting` objects.
- **Impact**: `check_meetings` would simply check `meeting_timeline[0].start_time`. If due, it moves the meeting to `work_queue[1]`.

### The `Chimer` Object: Centralized vs. Per-Meeting
A key architectural question is whether the alert timer should live inside every `Meeting` object or in a centralized "Chimer" slot.

- **Per-Meeting Timers**:
    - Each `Meeting` would have its own `CountdownTimer`.
    - *Benefit*: Encapsulation of alert state.
    - *Drawback*: Requires complex coordination to ensure only the "next" meeting is actively ticking/chiming to avoid auditory chaos.
- **Centralized Chimer (Recommended)**:
    - A single `Chimer` object (subclass of `CountdownTimer`) resides in `TimerManager`.
    - *Benefit*: Naturally enforces the "only one alert at a time" rule. The `TaskStack` simply "loads" the highest-priority starting meeting into this slot.
    - *Impact*: Decouples the *existence* of a meeting from the *activity* of an alert.

### The `s` (Schedule) Command
- **Current**: To "schedule" a task, you must edit its text to match a time regex.
- **Proposed**: An `s` command would allow the user to type `s1 10:00AM 30m` to convert a task at index 1 into a meeting.
- **Impact**: Improves the "Object-Oriented" nature of the system by using a dedicated `ScheduleCommand` instead of relying on side effects of string parsing.

---

## 4. Conclusion
The current implementation is functional but "greedy" (it takes focus immediately) and "procedural" (logic is scattered). Moving to a dedicated `TaskStack` and `Chimer` model would make the code more predictable and easier to maintain.
