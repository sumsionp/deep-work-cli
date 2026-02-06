import os
import sys
import re
import time
import logging
import copy
from datetime import datetime, timedelta

# --- CONFIG ---
DATE_FORMAT = '%Y%m%d'
FILENAME = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime(f'{DATE_FORMAT}-notes.txt')
LOG_FILE = "deepwork_activity.log"
ALERT_THRESHOLD = 90 * 60 

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
        self.ignored_indices = set()
        self.last_msg = "DeepWorkCLI Ready."
        self.task_start_time = None

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

                marker_match = re.match(r'^\[([x\->])\]', clean)
                if marker_match:
                    state = marker_match.group(1)
                    content = clean[marker_match.end():].strip()
                    if content not in seen_tasks:
                        counts[f'[{state}]'] += 1
                        seen_tasks.add(content)
        return counts

    def update_task_in_file(self, task_line_content, new_marker, target_file=None):
        dest = target_file if target_file else FILENAME
        if not os.path.exists(dest): return

        with open(dest, 'r') as f:
            lines = f.readlines()

        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip() or "-------" in line:
                new_lines.append(line)
                i += 1
                continue

            clean_line = re.sub(r'^\[[x\->\s]?\]\s*', '', line.strip())
            if clean_line == task_line_content:
                leading_spaces = line[:line.find(line.strip())]
                new_lines.append(f"{leading_spaces}{new_marker} {task_line_content}\n")

                i += 1
                while i < len(lines) and (lines[i].startswith('  ') or not lines[i].strip()):
                    if lines[i].strip():
                        note_content = re.sub(r'^\[[x\->\s]?\]\s*', '', lines[i].strip())
                        leading_note_spaces = lines[i][:lines[i].find(lines[i].strip())]
                        new_lines.append(f"{leading_note_spaces}{new_marker} {note_content}\n")
                    else:
                        new_lines.append(lines[i])
                    i += 1
                continue
            else:
                new_lines.append(line)
            i += 1

        with open(dest, 'w') as f:
            f.writelines(new_lines)

    def load_context(self):
        """Whole-file aware parser. Authoritative version is the latest one."""
        if not os.path.exists(FILENAME):
            with open(FILENAME, 'w') as f: f.write(f"Session Start - {get_timestamp()}\n")
            self.triage_stack = []
            return
        
        with open(FILENAME, 'r') as f:
            lines = [l.rstrip() for l in f.readlines()]

        all_entries = {} # content_key -> {line, notes, is_task, state, order}
        order_counter = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip() or "-------" in line:
                i += 1
                continue
            
            if not line.startswith('  '):
                clean = line.strip()
                marker_match = re.match(r'^\[([x\->\s]?)\]\s*', clean)
                if marker_match:
                    state = marker_match.group(1)
                    content = clean[marker_match.end():]
                else:
                    state = ""
                    content = clean

                notes = []
                i += 1
                while i < len(lines) and (lines[i].startswith('  ') or not lines[i].strip()):
                    if lines[i].strip():
                        notes.append(lines[i].strip())
                    i += 1

                if content in all_entries:
                    # Append new notes if not already there
                    existing_notes = all_entries[content]['notes']
                    for n in notes:
                        if n not in existing_notes:
                            existing_notes.append(n)
                    # Latest state and order wins
                    all_entries[content]['state'] = state
                    all_entries[content]['order'] = order_counter
                    if marker_match:
                        all_entries[content]['is_task'] = True
                        all_entries[content]['line'] = f"[] {content}"
                else:
                    all_entries[content] = {
                        'line': f"[] {content}" if marker_match else content,
                        'notes': notes,
                        'is_task': bool(marker_match),
                        'state': state,
                        'order': order_counter
                    }
                order_counter += 1
            else:
                i += 1

        sorted_entries = sorted(all_entries.values(), key=lambda x: x['order'])
        self.triage_stack = []
        for e in sorted_entries:
            if not e['is_task'] or e['state'] in ['', ' ']:
                self.triage_stack.append({'line': e['line'], 'notes': e['notes']})

        self.ignored_indices = set()

    def commit_to_ledger(self, mode_label, items, target_file=None):
        dest = target_file if target_file else FILENAME
        with open(dest, 'a') as f:
            f.write(f"\n------- {mode_label} {get_timestamp()} -------\n")
            if items:
                for t in items:
                    f.write(f"{t['line']}\n")
                    for n in t['notes']:
                        f.write(f"  {n}\n")

    def run(self):
        self.load_context()
        self.initial_stack = copy.deepcopy(self.triage_stack)
        while True:
            os.system('clear')
            if self.mode == "TRIAGE":
                self.render_triage()
            else:
                self.render_work()

            print(f"\n\033[90mStatus: {self.last_msg}\033[0m")
            cmd = input("\033[1;37m>> \033[0m").strip().lower()
            
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

    def render_triage(self):
        print(f"--- TRIAGE: {os.path.basename(FILENAME)} ---")
        visible_count = 0
        for i, t in enumerate(self.triage_stack):
            if i in self.ignored_indices: continue
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
        print(color + "="*65 + "\033[0m")
        print(f"{color}{header}\033[0m | Time: {m:02d}:{s:02d}")
        print(color + "="*65 + "\033[0m")
        
        display_line = re.sub(r'^\[\s?\]\s*', '', t['line'])
        print(f"\n\033[1;32mFOCUS >> {display_line}\033[0m")
        for i, n in enumerate(t['notes']):
            n_color = "\033[1;36m" if '[]' in n else ""
            print(f"  {i}: {n_color}{n}\033[0m")
        print("\n" + color + "-"*65 + "\033[0m")
        print("Cmds: [x] done, [x#] subtask, [-] cancel, [>] defer, [t] triage, [q] quit")

    def handle_command(self, cmd):
        try:
            cmd_clean = re.sub(r'^([a-z])(\d)', r'\1 \2', cmd) 
            parts = cmd_clean.split()
            if not parts: return
            base_cmd = parts[0]
            
            if base_cmd == 'q':
                if self.triage_stack:
                    print(f"\n\033[1;33m[!] Session Interrupted.\033[0m")
                    if input("Rescue remaining tasks to Free Write? (y/n): ").lower() == 'y':
                        self.commit_to_ledger("Interrupted", self.triage_stack)
                    else:
                        self.commit_to_ledger("Interrupted", [])
                else:
                    self.commit_to_ledger("Interrupted", [])
                return "QUIT"

            if base_cmd == 't': 
                self.mode = "TRIAGE"; self.task_start_time = None
                return

            if self.mode == "TRIAGE":
                if base_cmd == 'w':
                    active = [t for i, t in enumerate(self.triage_stack) if i not in self.ignored_indices]
                    items_to_write = active if active != self.initial_stack else []
                    self.commit_to_ledger("Triage", items_to_write)
                    self.triage_stack = active
                    self.mode = "WORK"; self.last_msg = ""
                    self.initial_stack = copy.deepcopy(self.triage_stack)
                elif base_cmd == 'i':
                    self.ignored_indices.add(int(parts[1]))
                elif base_cmd == 'p':
                    src, dest = int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
                    self.triage_stack.insert(dest, self.triage_stack.pop(src))
                elif base_cmd == 'a':
                    src_str, dest_idx = parts[1], int(parts[2])
                    item = self.triage_stack[int(src_str.split('.')[0])]['notes'].pop(int(src_str.split('.')[1])) if '.' in src_str else self.triage_stack.pop(int(src_str))['line']
                    self.triage_stack[dest_idx]['notes'].append(item)

            elif self.mode == "WORK":
                task = self.triage_stack[0]
                match_x = re.match(r'^x(\d+)', cmd)
                if match_x:
                    idx = int(match_x.group(1))
                    subtask_content = re.sub(r'^\[[x\->\s]?\]\s*', '', task['notes'][idx])
                    task['notes'][idx] = re.sub(r'^\[\s?\]', '[x]', task['notes'][idx])
                    self.update_task_in_file(subtask_content, "[x]")
                    return

                if base_cmd in ['x', '-', '>']:
                    marker = {'x': '[x]', '-': '[-]', '>': '[>]'}[base_cmd]
                    task_content = re.sub(r'^\[[x\->\s]?\]\s*', '', task['line'])

                    self.update_task_in_file(task_content, marker)
                    for n in task['notes']:
                        n_content = re.sub(r'^\[[x\->\s]?\]\s*', '', n)
                        self.update_task_in_file(n_content, marker)

                    if base_cmd == '>':
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
