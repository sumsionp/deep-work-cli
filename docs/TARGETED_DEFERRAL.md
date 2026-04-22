### Targeted Deferral

## Summary

Tasks can be deferred to a specific point in the focus_queue.
This is most often used to put off the current task to the next task.
The same thing could be done by switching to TRIAGE mode.
The feature described in this document is essentially a shortcut to entering TRIAGE mode and reordering the tasks.

## Command Syntax

The command `>1` defers the current task to focus_queue[1], moving the next task into focus at [0].
In this way, tasks can be moved to any index in the focus_queue.
If a positive out of bounds index is given, the task is placed at the end of the focus_queue.
If a negative index is specified, the task is deferred to the earliest possible index for it to still be a deferral, ie: [1].
Thus, `>-1` is identical `>1`.

## Meeting and Break Deferral

If the focused task is a Meeting or a Break, there are two options:

- A new timestamp can be specified such as `> 2 PM`
  This changes the start time of the Meeting or Break to 2 PM and keeps the duration the same.
  The duration can also be changed by specifying either an end time or a duration such as `> 2-3 PM` or `> 2 PM 30m`
- If the currently focused task is a Meeting or a Break and only `>` or `>#` is specified, the start time of the deferred item is changed to the end time of the currently focused Meeting or Break.
  The duration stays the same and the old end time is thrown away.

## Blocking Functionality

There are some things that need to be taken care of before this feature will be truly helpful.

- Deferral of meetings and breaks needs to be handled by properly changing the timestamp of the meeting or break.
  This may take some extensive work since the user will need to specify the new timestamp, essentially rescheduling the meeting or break.
- This feature will make at least the third command that can take a number as a parameter.
  The parsing functionality should be shared between these commands.
- The current functionality of moving the next pending meeting to focus_queue[1] may need to change.
  This becomes problematic when we start adding meetings or reordering meetings  with functionality like `>`.
  I don't want to handle complex ordering functionality in this command.
  I want all that logic to stay in check_for_due_meetings.
  One way to handle this is to call check_for_due_meetings when resolving any task.
  If an due meeting is found, it becomes the focused task.
  Thus, all added or reordered Meetings and Breaks could simply be put in meeting_timeline.
  This actually makes the code cleaner since focus_queue would only ever hold a Meeting or Break object at [0].
