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
- If the currently focused task is a Meeting or a Break and only `>` or `>#` is specified, the item should be changed to a regular task and placed at the specified place in the focus_queue.
  ie: `>` moves it to the end of the focus_queue and `>#` moves it to the specified index.
  Any time block that is part of the Meeting or Break content is stripped out so that it will be parsed as a regular Task.
  Since the content is changed, the old version of the Meeting or Break is written to the ledger with [e] status just as if it had been edited.
