import shutil
import os, ctypes, re
from datetime import datetime

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
TASKS = os.path.join(ROOT, "TASKS")

C_CYAN, C_GREEN, C_YELLOW, C_MAGENTA, C_DIM, C_BOLD, C_RESET = (
    "\033[96m", "\033[92m", "\033[93m", "\033[95m", "\033[90m", "\033[1m", "\033[0m"
)

def get_ram_compact():
    try:
        class MEMSTAT(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = MEMSTAT()
        s.dwLength = ctypes.sizeof(MEMSTAT)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        used = (s.ullTotalPhys - s.ullAvailPhys) / (1024**3)
        tot = s.ullTotalPhys / (1024**3)
        return f"{used:.1f}/{tot:.1f}GB"
    except Exception:
        return "N/A"

def get_model_name():
    p = os.path.join(BRAIN, "CONFIG.env")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if l.startswith("MODEL_NAME="):
                return l.split("=", 1)[1].strip().strip('"').strip("'")
    return "qwen3.5-pi"

def get_loop_badge(active_proc, active_task):
    if active_proc and active_proc.poll() is None:
        tname = os.path.basename(active_task)
        rep = os.path.join(active_task, "REPORT.md")
        last_info = "starting..."
        if os.path.exists(rep):
            rows = [r for r in open(rep, encoding="utf-8") if r.startswith("| #")]
            if rows:
                parts = [c.strip() for c in rows[-1].strip().strip("|").split("|")]
                if len(parts) >= 7:
                    last_info = f"{parts[0]} {parts[5]} ({parts[6]})"
        return f"{C_GREEN}● LOOP:{tname} [{last_info}]{C_RESET}"
    return f"{C_DIM}○ LOOP:IDLE{C_RESET}"

def render_prompt_bar(mode_label, active_proc=None, active_task=None):
    model = get_model_name()
    ram = get_ram_compact()
    now = datetime.now().strftime("%H:%M:%S")
    loop_str = get_loop_badge(active_proc, active_task)
    w = max(50, shutil.get_terminal_size((76, 24)).columns - 1)
    print(f"{C_DIM}{'─'*w}{C_RESET}")
    print(f"{C_CYAN}❯ [{mode_label}]{C_RESET} Type {C_YELLOW}/help{C_RESET}, {C_YELLOW}/clip{C_RESET}, {C_YELLOW}/dash{C_RESET}, {C_YELLOW}/brain{C_RESET}, {C_YELLOW}/paste{C_RESET} or any {C_GREEN}UCRT64{C_RESET} cmd")
    w = max(50, shutil.get_terminal_size((76, 24)).columns - 1)
    print(f"{C_DIM}{'─'*w}{C_RESET}")
    print(f"{C_BOLD}[{model}]{C_RESET} {C_GREEN}UCRT64/Win{C_RESET} | {C_MAGENTA}RAM:{ram}{C_RESET} | {loop_str} | {now} | v4.3")

if __name__ == "__main__":
    import sys
    lbl = sys.argv[1] if len(sys.argv) > 1 else "EVOLVING"
    render_prompt_bar(lbl)
