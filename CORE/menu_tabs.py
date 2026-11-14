import os, sys, shutil
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
CFG_FILE = os.path.join(BRAIN, "CONFIG.env")

C_CYAN, C_GREEN, C_YELLOW, C_RED, C_MAG, C_BOLD, C_DIM, C_REV, C_RESET = (
    "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[95m", "\033[1m", "\033[2m", "\033[7m", "\033[0m"
)
ACTIVE_TAB = 0

def _read_cfg():
    cfg = {"AGENT_MODE": "chat", "EFFORT": "low"}
    if os.path.exists(CFG_FILE):
        for l in open(CFG_FILE, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def _brain_stats():
    def cnt(fn):
        p = os.path.join(BRAIN, fn)
        return sum(1 for l in open(p, encoding="utf-8") if l.strip().startswith("-")) if os.path.exists(p) else 0
    return f"{cnt('PRINCIPLES.md')}+{cnt('TOOLS_MEMORY.md')} rules | {cnt('CANDIDATE_LESSONS.md')} staged"

TABS = [
    ("1. Agents & Run", [
        ("(1)", "Evolution Loop", "Autonomous metric-driven code evolution"),
        ("(2)", "Orchestrator Agent", "Split-screen + Subagents + 5-frame Vision"),
        ("(3)", "Run Best Script", "Execute current optimized target.py"),
        ("(8)", "New Task", "Create a new experimental task folder"),
    ]),
    ("2. Brain & Science", [
        ("(b)", "View Brain (/brain)", "Inspect active principles & tool memory"),
        ("(4)", "Search arXiv", "Query papers and extract algorithms"),
        ("(c)", "Compact (/compact)", "Compress session into Chinese knowledge map"),
        ("(5)", "Dashboard (/dash)", "Evolution charts & performance metrics"),
        ("(6)", "Copy Report (/clip)", "Export metrics & logs to clipboard"),
    ]),
    ("3. System & /undo", [
        ("(s)", "Settings (/settings)", "Mode, Effort, Verbose & Guardian toggle"),
        ("(u)", "Time Machine (/undo)", "Revert safely to any saved checkpoint"),
        ("(v)", "Save Checkpoint (/save)", "Commit local + CHANGELOG backup"),
        ("(9)", "Sync GitHub (/sync)", "Push checkpoints to remote repository"),
        ("(7)", "Switch Model (/model)", "Select active local Ollama model"),
        ("(i)", "Connect iPad (/ipad)", "Link secondary network worker"),
        ("(t)", "Test Systems (/test)", "Run health & immortality diagnostics"),
    ]),
]

def render_menu(tab_idx, statusbar, bg_proc, bg_task):
    cfg = _read_cfg()
    amode = cfg.get("AGENT_MODE", "chat").upper()
    g_on = not os.path.exists(os.path.join(BRAIN, ".guardian_disabled"))
    g_badge = f"{C_GREEN}Guardian:ON{C_RESET}" if g_on else f"{C_DIM}Guardian:OFF{C_RESET}"
    cols = shutil.get_terminal_size((80, 24)).columns
    w = min(74, max(60, cols - 4))

    sys.stdout.write("\033[2J\033[H")
    print(f"{C_CYAN}{C_BOLD}\u256d{'\u2500'*w}\u256e{C_RESET}")
    print(f"{C_CYAN}\u2502{C_RESET} {C_GREEN}* {C_BOLD}AI-LAB v4.3{C_RESET} | Brain ({_brain_stats()}) | {g_badge} | {C_YELLOW}{amode}{C_RESET}")
    print(f"{C_CYAN}\u251c{'\u2500'*w}\u2524{C_RESET}")

    tab_bar = []
    for idx, (title, _) in enumerate(TABS):
        tab_bar.append(f"{C_REV}{C_CYAN}{C_BOLD} {title} {C_RESET}" if idx == tab_idx else f"{C_DIM} {title} {C_RESET}")
    print(f"{C_CYAN}\u2502{C_RESET} " + " | ".join(tab_bar))
    print(f"{C_CYAN}\u251c{'\u2500'*w}\u2524{C_RESET}")

    _, items = TABS[tab_idx]
    for key, label, desc in items:
        d_trim = desc[:max(15, w - 34)]
        print(f"{C_CYAN}\u2502{C_RESET}  {C_GREEN}{C_BOLD}{key:<4}{C_RESET} {C_BOLD}{label:<23}{C_RESET} {C_DIM}{d_trim}{C_RESET}")
    for _ in range(max(0, 7 - len(items))):
        print(f"{C_CYAN}\u2502{C_RESET}")

    print(f"{C_CYAN}\u251c{'\u2500'*w}\u2524{C_RESET}")
    print(f"{C_CYAN}\u2502{C_RESET}  {C_DIM}Tab / Left-Right: Switch Tab  |  All shortcuts active  |  {C_RED}(0) Exit{C_RESET}")
    print(f"{C_CYAN}\u2570{'\u2500'*w}\u256f{C_RESET}\n")
    statusbar.render_prompt_bar(f"TAB {tab_idx+1}/3", bg_proc, bg_task)

def prompt_with_tabs(statusbar, bg_proc, bg_task):
    global ACTIVE_TAB
    render_menu(ACTIVE_TAB, statusbar, bg_proc, bg_task)
    if os.name != "nt":
        return input(f"{C_CYAN}> {C_RESET}").strip()
    import msvcrt
    buf = []
    sys.stdout.write(f"{C_CYAN}> {C_RESET}")
    sys.stdout.flush()
    while True:
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            return "".join(buf).strip()
        elif ch == "\x03":
            raise KeyboardInterrupt
        elif ch in ("\x08", "\x7f"):
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
        elif ch == "\t" and not buf:
            ACTIVE_TAB = (ACTIVE_TAB + 1) % len(TABS)
            render_menu(ACTIVE_TAB, statusbar, bg_proc, bg_task)
            sys.stdout.write(f"{C_CYAN}> {C_RESET}")
            sys.stdout.flush()
        elif ch in ("\x00", "\xe0"):
            ext = msvcrt.getwch()
            if not buf and ext in ("M", "K"):
                ACTIVE_TAB = (ACTIVE_TAB + (1 if ext == "M" else -1)) % len(TABS)
                render_menu(ACTIVE_TAB, statusbar, bg_proc, bg_task)
                sys.stdout.write(f"{C_CYAN}> {C_RESET}")
                sys.stdout.flush()
        elif ch == "\x1b" and msvcrt.kbhit():
            if msvcrt.getwch() == "[" and msvcrt.kbhit():
                d = msvcrt.getwch()
                if not buf and d in ("C", "D"):
                    ACTIVE_TAB = (ACTIVE_TAB + (1 if d == "C" else -1)) % len(TABS)
                    render_menu(ACTIVE_TAB, statusbar, bg_proc, bg_task)
                    sys.stdout.write(f"{C_CYAN}> {C_RESET}")
                    sys.stdout.flush()
        elif ch.isprintable():
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
