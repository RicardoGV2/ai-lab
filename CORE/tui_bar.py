import os, sys, re, time, shutil, ctypes, threading
from collections import deque

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

C_CYAN, C_GREEN, C_YELLOW, C_RED, C_MAG, C_BOLD, C_DIM, C_RESET = (
    "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[95m", "\033[1m", "\033[2m", "\033[0m"
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_ram_str():
    try:
        st = MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        tot = st.ullTotalPhys / (1024**3)
        used = (st.ullTotalPhys - st.ullAvailPhys) / (1024**3)
        return f"RAM:{used:.1f}/{tot:.1f}GB"
    except Exception:
        return "RAM:?/7.8GB"

class BottomBarTUI:
    def __init__(self, read_cfg_fn, write_cfg_fn, modes, load_hist_fn, save_hist_fn):
        self.read_cfg = read_cfg_fn
        self.write_cfg = write_cfg_fn
        self.modes = modes
        self.load_hist = load_hist_fn
        self.save_hist = save_hist_fn
        self.lock = threading.RLock()
        self.buf = []
        self.queue = deque()
        self.busy = False
        self.status_note = ""
        self.cancel_flag = False
        self.running = False
        self.scroll_col = 0
        self.last_h = 0

    def _dims(self):
        sz = shutil.get_terminal_size((80, 24))
        return max(50, sz.columns), max(12, sz.lines)

    def _setup_region(self, h):
        if h != self.last_h:
            sys.stdout.write(f"\033[1;{h - 5}r")
            self.last_h = h

    def _draw_dock(self, w, h):
        cfg = self.read_cfg()
        model = cfg.get("MODEL", "qwen3.5-pi")
        mode = cfg.get("AGENT_MODE", "chat").upper()
        eff = cfg.get("EFFORT", "low").upper()
        m_col = C_GREEN if mode == "CHAT" else (C_YELLOW if mode == "PLAN" else (C_RED if mode == "FREE" else (C_MAG if mode == "INFINITE" else C_CYAN)))
        loop_st = f"{C_YELLOW}● BUSY{C_RESET}" if self.busy else f"{C_DIM}○ IDLE{C_RESET}"
        q_st = f" | {C_CYAN}Q:{len(self.queue)}{C_RESET}" if self.queue else ""
        now = time.strftime("%H:%M:%S")
        sep = f"{C_DIM}{'-' * (w - 1)}{C_RESET}"

        act_raw = f"* {self.status_note} (esc to interrupt)" if self.status_note else ""
        act_line = f"{C_YELLOW}{act_raw[:w-1]}{C_RESET}" if act_raw else ""

        typed = "".join(self.buf)
        max_in = max(10, w - 5)
        vis_typed = typed[-max_in:]
        prompt_line = f"{C_BOLD}{C_CYAN}> {C_RESET}{vis_typed}"

        status_line = (
            f"[{C_BOLD}{model}{C_RESET}] {C_GREEN}UCRT64/Win{C_RESET} | {C_MAG}{get_ram_str()}{C_RESET} | "
            f"{loop_st} | {m_col}[{mode}|{eff}]{C_RESET} | {now} | v4.3{q_st}"
        ) if w >= 86 else (
            f"[{C_BOLD}{model}{C_RESET}] {C_MAG}{get_ram_str()}{C_RESET} | {loop_st} | {m_col}[{mode}|{eff}]{C_RESET} | {now} | v4.3{q_st}"
        )

        sys.stdout.write(
            f"\033[{h-4};1H\033[2K{act_line}"
            f"\033[{h-3};1H\033[2K{sep}"
            f"\033[{h-2};1H\033[2K{prompt_line}"
            f"\033[{h-1};1H\033[2K{sep}"
            f"\033[{h};1H\033[2K{status_line}"
            f"\033[{h-2};{3 + len(vis_typed)}H"
        )
        sys.stdout.flush()

    def write(self, text):
        with self.lock:
            w, h = self._dims()
            self._setup_region(h)
            top_bot = h - 5
            sys.stdout.write(f"\033[{top_bot};{self.scroll_col + 1}H")
            parts = re.split(r"(\x1b\[[0-9;]*[A-Za-z]|\n|\r)", str(text))
            for p in parts:
                if not p:
                    continue
                if p == "\r":
                    sys.stdout.write("\r")
                    self.scroll_col = 0
                elif p == "\n":
                    sys.stdout.write("\n")
                    self.scroll_col = 0
                elif ANSI_RE.match(p):
                    sys.stdout.write(p)
                else:
                    for ch in p:
                        if self.scroll_col >= w - 2:
                            sys.stdout.write("\n")
                            self.scroll_col = 0
                        sys.stdout.write(ch)
                        self.scroll_col += 1
            self._draw_dock(w, h)

    def refresh(self):
        with self.lock:
            w, h = self._dims()
            self._setup_region(h)
            self._draw_dock(w, h)

    def start(self):
        self.running = True
        w, h = self._dims()
        sys.stdout.write(f"\033[2J\033[1;{h - 5}r\033[1;1H")
        self.refresh()
        threading.Thread(target=self._key_loop, daemon=True).start()
        threading.Thread(target=self._clock_loop, daemon=True).start()

    def stop(self):
        self.running = False
        w, h = self._dims()
        sys.stdout.write(f"\033[r\033[{h};1H\n")
        sys.stdout.flush()

    def _clock_loop(self):
        while self.running:
            time.sleep(1.0)
            if self.running:
                self.refresh()

    def _key_loop(self):
        import msvcrt
        hist = self.load_hist()
        h_idx = len(hist)
        draft = ""
        while self.running:
            if not msvcrt.kbhit():
                time.sleep(0.02)
                continue
            ch = msvcrt.getwch()
            with self.lock:
                if ch in ("\r", "\n"):
                    msg = "".join(self.buf).strip()
                    self.buf.clear()
                    if msg:
                        self.save_hist(msg)
                        hist = self.load_hist()
                        h_idx = len(hist)
                        self.queue.append(msg)
                    self.refresh()
                elif ch == "\x03":
                    self.cancel_flag = True
                    self.queue.append("exit")
                elif ch in ("\x08", "\x7f"):
                    if self.buf:
                        self.buf.pop()
                        self.refresh()
                elif ch == "\x1b":
                    if msvcrt.kbhit():
                        n1 = msvcrt.getwch()
                        if n1 == "[" and msvcrt.kbhit():
                            n2 = msvcrt.getwch()
                            if n2 == "A" and hist:
                                if h_idx == len(hist): draft = "".join(self.buf)
                                if h_idx > 0:
                                    h_idx -= 1
                                    self.buf = list(hist[h_idx])
                            elif n2 == "B" and hist:
                                if h_idx < len(hist):
                                    h_idx += 1
                                    self.buf = list(hist[h_idx]) if h_idx < len(hist) else list(draft)
                            self.refresh()
                            continue
                    if self.busy:
                        self.cancel_flag = True
                    elif self.buf:
                        self.buf.clear()
                    else:
                        self.queue.append("exit")
                    self.refresh()
                elif ch in ("\x00", "\xe0"):
                    ext = msvcrt.getwch()
                    if ext == "\x0f":
                        cur = self.read_cfg().get("AGENT_MODE", "chat")
                        self.write_cfg({"AGENT_MODE": self.modes[(self.modes.index(cur) + 1) % len(self.modes)] if cur in self.modes else "chat"})
                    elif ext == "H" and hist:
                        if h_idx == len(hist): draft = "".join(self.buf)
                        if h_idx > 0:
                            h_idx -= 1
                            self.buf = list(hist[h_idx])
                    elif ext == "P" and hist:
                        if h_idx < len(hist):
                            h_idx += 1
                            self.buf = list(hist[h_idx]) if h_idx < len(hist) else list(draft)
                    self.refresh()
                elif ch == "\t" and not self.buf:
                    cur = self.read_cfg().get("AGENT_MODE", "chat")
                    self.write_cfg({"AGENT_MODE": self.modes[(self.modes.index(cur) + 1) % len(self.modes)] if cur in self.modes else "chat"})
                    self.refresh()
                elif ch.isprintable():
                    self.buf.append(ch)
                    self.refresh()
