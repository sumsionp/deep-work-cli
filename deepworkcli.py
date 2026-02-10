import os
import sys
import re
import time
import logging
import copy
import random
import select
import termios
import tty
from datetime import datetime, timedelta

# --- CONFIG ---
DATE_FORMAT = '%Y%m%d'
FILENAME = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime(f'{DATE_FORMAT}-notes.txt')
LOG_FILE = "deepwork_activity.log"
ALERT_THRESHOLD = 90 * 60 

BREAK_QUOTES = [
    "The time to relax is when you don't have time for it. – Sydney J. Harris",
    "Taking a break can lead to breakthroughs. – Unknown",
    "Rest is not idleness, and to lie sometimes on the grass under trees... is by no means a waste of time. – John Lubbock",
    "Sometimes the most productive thing you can do is relax. – Mark Black",
    "Almost everything will work again if you unplug it for a few minutes, including you. – Anne Lamott",
    "A break from everything is much needed once in a while. – Unknown",
    "Reflection is one of the most underused yet powerful tools for success. – Richard Carlson",
    "Disconnect to reconnect. – Unknown",
    "Your mind will answer most questions if you learn to relax and wait for the answer. – William S. Burroughs",
    "Pause. Breathe. Rest. Start again. – Unknown"
]

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

def get_timestamp():
    return datetime.now().strftime('%I:%M %p')

def get_tomorrow_file():
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime(f'{DATE_FORMAT}-plan.txt')

class DeepWorkCLI:
    def __init__(self):
        self.mode = "TRIAGE"
        self.triage_stack = []
        self.initial_stack = []
        self.last_msg = "DeepWorkCLI Ready."
        self.task_start_time = None
        self.break_start_time = None
        self.break_duration = 0
        self.break_quote = ""
        self.last_chime_timestamp = 0

    def get_daily_summary(self):
        counts = {'[x]': 0, '[-]': 0, '[>]': 0}
        if not os.path.exists(FILENAME): return counts

        seen_tasks = set()
        with open(FILENAME, 'r') as f:
            lines = f.readlines()
            for line in reversed(lines):
                clean = line.strip()
                if not clean or "-------" in clean or line.startswith('  '):
                    continue

                marker_match = re.match(r'^\[([x\->\s]?)\]', clean)
                if marker_match:
                    state = marker_match.group(1)
                    content = clean[marker_match.end():].strip()
                    if content not in seen_tasks:
                        if state in ['x', '-', '>']:
                            counts[f'[{state}]'] += 1
                        seen_tasks.add(content)
        return counts

    def load_context(self):
        """Whole-file aware parser with resolution logic."""
        if not os.path.exists(FILENAME):
            with open(FILENAME, 'w') as f: f.write(f"Session Start - {get_timestamp()}\n")
            self.triage_stack = []
            return
        
        with open(FILENAME, 'r') as f:
            lines = [l.rstrip() for l in f.readlines()]

        active_entries = {} # content -> {notes, is_task}
        entry_order = [] # list of contents
        last_entry_content = None
        
        for line in lines:
            if "------- Triage" in line:
                new_entry_order = []
                for content in entry_order:
                    if active_entries[content]['is_task']:
                        new_entry_order.append(content)
                    else:
                        del active_entries[content]
                entry_order = new_entry_order
                last_entry_content = None
                continue

            if not line.strip() or "-------" in line:
                continue
            
            if not line.startswith('  '):
                clean = line.strip()
                marker_match = re.match(r'^\[([x\->\s]?)\]\s*', clean)
                if marker_match:
                    state = marker_match.group(1).strip()
                    content = clean[marker_match.end():].strip()

                    if not state:
                        # Pending task
                        notes = active_entries.pop(content, {}).get('notes', [])
                        active_entries[content] = {'notes': notes, 'is_task': True}
                        if content in entry_order: entry_order.remove(content)
                        entry_order.append(content)
                    else:
                        # Resolution
                        active_entries.pop(content, None)
                        if content in entry_order: entry_order.remove(content)
                    last_entry_content = content
                else:
                    # Non-task entry
                    content = clean
                    notes = active_entries.pop(content, {}).get('notes', [])
                    active_entries[content] = {'notes': notes, 'is_task': False}
                    if content in entry_order: entry_order.remove(content)
                    entry_order.append(content)
                    last_entry_content = content
            else:
                # Indented line
                if last_entry_content and last_entry_content in active_entries:
                    note = line.strip()
                    notes_list = active_entries[last_entry_content]['notes']

                    # Subtask/Note resolution logic
                    sub_marker_match = re.match(r'^\[([x\->\s]?)\]\s*', note)
                    if sub_marker_match:
                        sub_content = note[sub_marker_match.end():].strip()
                        # Remove any existing instance of this subtask content
                        new_notes = []
                        for n in notes_list:
                            m = re.match(r'^\[[x\->\s]?\]\s*', n)
                            if m and n[m.end():].strip() == sub_content:
                                continue
                            new_notes.append(n)
                        notes_list = new_notes
                        notes_list.append(note)
                    else:
                        if note in notes_list: notes_list.remove(note)
                        notes_list.append(note)
                    active_entries[last_entry_content]['notes'] = notes_list

        self.triage_stack = []
        for content in entry_order:
            entry = active_entries[content]
            self.triage_stack.append({
                'line': f"[] {content}" if entry['is_task'] else content,
                'notes': entry['notes']
            })

    def commit_to_ledger(self, mode_label, items, target_file=None):
        dest = target_file if target_file else FILENAME
        with open(dest, 'a') as f:
            f.write(f"\n------- {mode_label} {get_timestamp()} -------\n")
            if items:
                for t in items:
                    f.write(f"{t['line']}\n")
                    for n in t['notes']:
                        f.write(f"  {n}\n")

    def check_chime(self):
        if self.mode != "BREAK": return

        now = time.time()
        elapsed_break = now - self.break_start_time
        remaining = self.break_duration * 60 - elapsed_break

        if remaining <= 0:
            if now - self.last_chime_timestamp >= 60:
                sys.stdout.write('\a')
                sys.stdout.flush()
                self.last_chime_timestamp = now

    def render_break(self):
        elapsed_break = time.time() - self.break_start_time
        remaining = int(self.break_duration * 60 - elapsed_break)

        sign = ""
        if remaining < 0:
            sign = "-"
            abs_rem = abs(remaining)
        else:
            abs_rem = remaining

        m, s = divmod(abs_rem, 60)
        time_str = f"{sign}{m:02d}:{s:02d}"

        color = "\033[1;34m"
        header = " BREAK SESSION "

        print(color + "="*65 + "\033[0m")
        print(f"{color}{header}\033[0m | Remaining: {time_str}")
        print(color + "="*65 + "\033[0m")

        print(f"\n\033[1;32mFOCUS >> \033[0m{self.break_quote}")

        print("\n" + color + "-"*65 + "\033[0m")
        print("Cmds: [n] add, [t] triage, [w] work, [q] quit")

    def run(self):
        self.load_context()
        self.initial_stack = copy.deepcopy(self.triage_stack)

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            buffer = ""
            while True:
                os.system('clear')
                if self.mode == "TRIAGE":
                    self.render_triage()
                elif self.mode == "WORK":
                    self.render_work()
                elif self.mode == "BREAK":
                    self.render_break()

                print(f"\n\033[90mStatus: {self.last_msg}\033[0m")
                sys.stdout.write(f"\033[1;37m>> \033[0m{buffer}")
                sys.stdout.flush()

                if self.mode == "BREAK":
                    self.check_chime()

                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    char = sys.stdin.read(1)
                    if char == '\n' or char == '\r':
                        cmd = buffer.strip().lower()
                        buffer = ""
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        print()
                        result = self.handle_command(cmd)
                        if result == "QUIT":
                            summary = self.get_daily_summary()
                            print("\n" + "="*35)
                            print(f"\033[1;32mDAILY SCORECARD ({os.path.basename(FILENAME)})\033[0m")
                            print(f"  Finished  [x]: {summary['[x]']}")
                            print(f"  Cancelled [-]: {summary['[-]']}")
                            print(f"  Deferred  [>]: {summary['[>]']}")
                            print("="*35)
                            input("\nTake a break. Press Enter to return to Free Write...")
                            break
                        tty.setcbreak(fd)
                    elif char in ['\x7f', '\x08']:
                        buffer = buffer[:-1]
                    elif ord(char) == 3: # Ctrl+C
                        raise KeyboardInterrupt
                    else:
                        buffer += char
        except KeyboardInterrupt:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def render_triage(self):
        print(f"--- TRIAGE: {os.path.basename(FILENAME)} ---")
        visible_count = 0
        for i, t in enumerate(self.triage_stack):
            color = "\033[1;36m" if '[]' in t['line'] else ""
            print(f"{i}: {color}{t['line']}\033[0m")
            for j, n in enumerate(t['notes']):
                n_color = "\033[1;36m" if '[]' in n else ""
                print(f"   {i}.{j}: {n_color}{n}\033[0m")
            visible_count += 1
        
        if visible_count == 0:
            print("\n\033[1;36m[FREE WRITE MODE]\033[0m Everything triaged or finished.")
        else:
            print("\nCmds: [p# #] reorder, [a# #] assign, [i#] ignore, [w] work, [q] quit")

    def render_work(self):
        if not self.triage_stack:
            print("\n\033[1;32m[FLOW COMPLETE]\033[0m Press 'q' to return to vi.")
            return
        
        if self.task_start_time is None: self.task_start_time = time.time()
        elapsed = int(time.time() - self.task_start_time)
        m, s = divmod(elapsed, 60)
        
        color = "\033[1;34m"
        header = " DEEP WORK SESSION "
        if elapsed > ALERT_THRESHOLD:
            color = "\033[1;31;7m"
            header = " !!! FOCUS LIMIT EXCEEDED !!! "

        t = self.triage_stack[0]
        is_task = t['line'].startswith('[]')
        print(color + "="*65 + "\033[0m")
        print(f"{color}{header}\033[0m | Time: {m:02d}:{s:02d}")
        print(color + "="*65 + "\033[0m")
        
        display_line = re.sub(r'^\[\s?\]\s*', '', t['line'])
        if is_task:
            print(f"\n\033[1;32mFOCUS >> {display_line}\033[0m")
        else:
            print(f"\n\033[1;32mFOCUS >> \033[0m{display_line}")
        for i, n in enumerate(t['notes']):
            n_color = "\033[1;36m" if '[]' in n else ""
            print(f"  {i}: {n_color}{n}\033[0m")
        print("\n" + color + "-"*65 + "\033[0m")
        print("Cmds: [x] done, [x#] subtask, [-] cancel, [>] defer, [n] add, [i] ignore, [t] triage, [q] quit")

    def handle_command(self, cmd):
        try:
            cmd_clean = re.sub(r'^([a-z])(\d)', r'\1 \2', cmd) 
            parts = cmd_clean.split()
            if not parts: return
            base_cmd = parts[0]
            
            if base_cmd == 'q':
                active = self.triage_stack
                if active:
                    print(f"\n\033[1;33m[!] Session Interrupted.\033[0m")
                    if input("Rescue remaining tasks to Free Write? (y/n): ").lower() == 'y':
                        self.commit_to_ledger("Interrupted", active)
                    else:
                        self.commit_to_ledger("Interrupted", [])
                else:
                    if self.mode in ["WORK", "BREAK"]:
                        print(f"\n\033[1;32m[+] Work Session Complete.\033[0m")
                        self.commit_to_ledger("Work Session Complete", [])
                    else:
                        self.commit_to_ledger("Triage", [])
                return "QUIT"

            if base_cmd == 't': 
                self.mode = "TRIAGE"; self.task_start_time = None
                self.break_start_time = None
                return

            if self.mode == "BREAK":
                if base_cmd == 'w':
                    break_total_time = time.time() - self.break_start_time
                    if self.task_start_time:
                        self.task_start_time += break_total_time
                    self.mode = "WORK"
                    self.commit_to_ledger("Work Session Re-started at", [])
                    self.last_msg = "Work Resumed"
                    return
                elif base_cmd == 'b':
                    self.last_msg = "Break time overload! Doing nothing."
                    self.break_quote = random.choice(BREAK_QUOTES)
                    return
                elif base_cmd == 'n':
                    pass # Handled by shared WORK/BREAK logic
                elif base_cmd in ['t', 'q']:
                    pass # Handled by common logic
                else:
                    self.last_msg = "Command disabled during break."
                    return

            if self.mode == "TRIAGE":
                if base_cmd == 'w':
                    active = self.triage_stack
                    items_to_write = active if active != self.initial_stack else []
                    self.commit_to_ledger("Triage", items_to_write)
                    self.triage_stack = active
                    self.mode = "WORK"; self.last_msg = ""
                    self.initial_stack = copy.deepcopy(self.triage_stack)
                elif base_cmd == 'i':
                    if len(parts) > 1:
                        idx = int(parts[1])
                    elif len(self.triage_stack) == 1:
                        idx = 0
                    else:
                        # Fallback to existing behavior if multiple items but no index
                        idx = int(parts[1])

                    item = self.triage_stack.pop(idx)
                    if item['line'].startswith('[]'):
                        # It's a task, mark as cancelled
                        task_content = re.sub(r'^\[\s?\]\s*', '', item['line'])
                        item['line'] = f"[-] {task_content}"
                        new_notes = []
                        for n in item['notes']:
                            if re.match(r'^\[[x>]\]', n):
                                new_notes.append(n)
                            else:
                                clean_note = re.sub(r'^\[[\s\-]?\]\s*', '', n)
                                new_notes.append(f"[-] {clean_note}")
                        item['notes'] = new_notes
                        self.commit_to_ledger("Cancelled", [item])
                elif base_cmd == 'p':
                    src, dest = int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
                    self.triage_stack.insert(dest, self.triage_stack.pop(src))
                elif base_cmd == 'a':
                    src_str, dest_idx = parts[1], int(parts[2])
                    item = self.triage_stack[int(src_str.split('.')[0])]['notes'].pop(int(src_str.split('.')[1])) if '.' in src_str else self.triage_stack.pop(int(src_str))['line']
                    self.triage_stack[dest_idx]['notes'].append(item)

            elif self.mode in ["WORK", "BREAK"]:
                if not self.triage_stack:
                    if base_cmd == 'n' or base_cmd == 'q':
                        return "QUIT"
                    return

                task = self.triage_stack[0]
                is_note = not task['line'].startswith('[]')

                if base_cmd == 'b' and self.mode == "WORK":
                    duration = 5
                    if len(parts) > 1:
                        try:
                            duration = int(parts[1])
                        except ValueError:
                            self.last_msg = f"Invalid break duration: {parts[1]}"
                            return

                    if duration <= 0:
                        self.last_msg = "Seriously? Take a real break! 0 minutes is too short."
                        return

                    self.mode = "BREAK"
                    self.break_duration = duration
                    self.break_start_time = time.time()
                    self.break_quote = random.choice(BREAK_QUOTES)
                    self.last_chime_timestamp = 0
                    self.commit_to_ledger(f"Break for {duration} at", [])
                    return

                if base_cmd == 'n':
                    line = input("Enter note or task: ")
                    if not line.strip(): return

                    if line.startswith(' '):
                        # Sub-item
                        content = line.strip()
                        is_subtask = bool(re.match(r'^\[\s?\]', content))
                        task['notes'].append(content)
                        self.commit_to_ledger("New Entry", [task])
                        self.last_msg = "Subtask Added" if is_subtask else "Subnote Added"
                    else:
                        # Top-level
                        clean = line.strip()
                        marker_match = re.match(r'^\[([x\->\s]?)\]\s*', clean)
                        is_new_task = False
                        if marker_match:
                            state = marker_match.group(1).strip()
                            if not state:
                                is_new_task = True
                                content = clean[marker_match.end():].strip()

                        if is_new_task:
                            item = {'line': f"[] {content}", 'notes': []}
                            self.last_msg = "Task Added"
                        else:
                            item = {'line': clean, 'notes': []}
                            self.last_msg = "Note Added"

                        self.commit_to_ledger("New Entry", [item])
                        self.triage_stack.append(item)
                    return

                match_x = re.match(r'^x(\d+)', cmd)
                if match_x:
                    if self.mode == "BREAK":
                        self.last_msg = "Command disabled during break."
                        return
                    idx = int(match_x.group(1))
                    task['notes'][idx] = re.sub(r'^\[\s?\]', '[x]', task['notes'][idx])
                    return

                if is_note and base_cmd in ['x', '-', 'i']:
                    if self.mode == "BREAK":
                        self.last_msg = "Command disabled during break."
                        return
                    self.triage_stack.pop(0)
                    self.task_start_time = None
                    self.initial_stack = copy.deepcopy(self.triage_stack)
                    return

                if base_cmd in ['x', '-', '>', 'i']:
                    if self.mode == "BREAK":
                        self.last_msg = "Command disabled during break."
                        return
                    effective_cmd = '-' if base_cmd == 'i' else base_cmd
                    marker = {'x': '[x]', '-': '[-]', '>': '[>]'}[effective_cmd]
                    task_content = re.sub(r'^\[[x\->\s]?\]\s*', '', task['line'])

                    if effective_cmd == '>':
                        tomorrow = get_tomorrow_file()
                        clean_task = copy.deepcopy(task)
                        clean_task['line'] = f"[] {task_content}"
                        clean_task['notes'] = [re.sub(r'^\[[x\->\s]?\]\s*', '', n) for n in clean_task['notes']]
                        self.commit_to_ledger("Deferred from last session", [clean_task], target_file=tomorrow)
                    
                    task['line'] = f"{marker} {task_content}"
                    task['notes'] = [f"{marker} " + re.sub(r'^\[[x\->\s]?\]\s*', '', n) for n in task['notes']]
                    
                    self.commit_to_ledger("Work", [self.triage_stack.pop(0)])
                    self.task_start_time = None
                    self.initial_stack = copy.deepcopy(self.triage_stack)

        except Exception as e:
            self.last_msg = f"Error: {e}"
        return None

if __name__ == "__main__":
    DeepWorkCLI().run()
