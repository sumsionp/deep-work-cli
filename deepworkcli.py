import os
import sys
import re
import time
import logging
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
        self.ignored_indices = set()
        self.last_msg = "DeepWorkCLI Ready."
        self.task_start_time = None

    def get_daily_summary(self):
        counts = {'[x]': 0, '[-]': 0, '[>]': 0}
        if not os.path.exists(FILENAME): return counts
        with open(FILENAME, 'r') as f:
            for line in f:
                # Count top-level markers for the scorecard
                if not line.startswith('  '):
                    for marker in counts:
                        if line.strip().startswith(marker):
                            counts[marker] += 1
        return counts

    def load_context(self):
        """Hierarchy-aware parser that strictly ignores any marked [x], [-], or [>]."""
        if not os.path.exists(FILENAME):
            with open(FILENAME, 'w') as f: f.write(f"Session Start - {get_timestamp()}\n")
        
        with open(FILENAME, 'r') as f:
            lines = [l.rstrip() for l in f.readlines()]

        last_marker_idx = -1
        for i, line in enumerate(lines):
            if "-------" in line: last_marker_idx = i
        
        dump = lines[last_marker_idx+1:]
        self.triage_stack = []
        
        for line in dump:
            clean = line.strip()
            if not clean or clean.startswith('-------'): continue
            
            # CRITICAL FIX: Ignore ANY line (indented or not) starting with a status marker
            if re.match(r'^\[[x\->]\]', clean): continue 
            
            if line.startswith('  ') and self.triage_stack:
                self.triage_stack[-1]['notes'].append(line.strip())
            else:
                self.triage_stack.append({'line': line.strip(), 'notes': []})
        self.ignored_indices = set()

    def commit_to_ledger(self, mode_label, items, target_file=None):
        if not items: return
        dest = target_file if target_file else FILENAME
        
        exists = os.path.exists(dest)
        has_marker = False
        if exists:
            with open(dest, 'r') as f:
                if mode_label in f.read():
                    has_marker = True

        with open(dest, 'a') as f:
            if not has_marker:
                f.write(f"\n------- {mode_label} {get_timestamp()} -------\n")
            for t in items:
                f.write(f"{t['line']}\n")
                for n in t['notes']:
                    f.write(f"  {n}\n")

    def run(self):
        self.load_context()
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
                if self.mode == "WORK" and self.triage_stack:
                    print(f"\n\033[1;33m[!] Session Interrupted.\033[0m")
                    if input("Rescue remaining tasks to Free Write? (y/n): ").lower() == 'y':
                        self.commit_to_ledger("Interrupted", self.triage_stack)
                return "QUIT"

            if base_cmd == 't': 
                self.mode = "TRIAGE"; self.task_start_time = None
                return

            if self.mode == "TRIAGE":
                if base_cmd == 'w':
                    active = [t for i, t in enumerate(self.triage_stack) if i not in self.ignored_indices]
                    self.commit_to_ledger("Triage", active)
                    self.triage_stack = active
                    self.mode = "WORK"; self.last_msg = ""
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
                    task['notes'][idx] = re.sub(r'^\[\s?\]', '[x]', task['notes'][idx])
                    return

                if base_cmd in ['x', '-', '>']:
                    if base_cmd == '>':
                        tomorrow = get_tomorrow_file()
                        # Defer a clean copy (pending states) to tomorrow
                        self.commit_to_ledger("Deferred from last session", [task], target_file=tomorrow)
                    
                    marker = {'x': '[x]', '-': '[-]', '>': '[>]'}[base_cmd]
                    task['line'] = f"{marker} " + re.sub(r'^\[\s?\]\s*', '', task['line'])
                    
                    # Force the marker on ALL sub-notes/tasks in today's file to kill orphans
                    task['notes'] = [f"{marker} " + re.sub(r'^\[[x\->\s]?\]\s*', '', n) for n in task['notes']]
                    
                    self.commit_to_ledger("Work", [self.triage_stack.pop(0)])
                    self.task_start_time = None

        except Exception as e:
            self.last_msg = f"Error: {e}"
        return None

if __name__ == "__main__":
    DeepWorkCLI().run()
