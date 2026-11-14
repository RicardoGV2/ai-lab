import os, ctypes, ctypes.wintypes as wt, subprocess, gc, json

ROOT = os.path.expanduser("~/ai-lab")
PROT_FILE = os.path.join(ROOT, "BRAIN", "PROTECTED_APPS.txt")
LAST_ACTION_FILE = os.path.join(ROOT, "TASKS", "09_win_ram_optimizer", ".tmp", "last_actions.json")

CANDIDATE_BLOAT = {
    "widgets.exe", "widgetservice.exe", "phoneexperiencehost.exe", "yourphone.exe",
    "gamebar.exe", "gamebarftserver.exe", "xboxpcapp.exe", "microsoftedgeupdate.exe",
    "onedrive.exe", "teams.exe", "ms-teams.exe", "skype.exe", "cortana.exe",
    "searchapp.exe", "searchhost.exe", "mousocoreworker.exe", "compattelrunner.exe",
    "runtimebroker.exe", "backgroundtaskhost.exe", "startmenuexperiencehost.exe"
}

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
        ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
        ("sullAvailExtendedVirtual", ctypes.c_uint64),
    ]

def load_protected():
    prot = {
        "python.exe", "cmd.exe", "bash.exe", "mintty.exe", "windowsterminal.exe",
        "conhost.exe", "ollama.exe", "ollama_llama_server.exe", "chrome.exe",
        "msedge.exe", "firefox.exe", "brave.exe", "explorer.exe", "dwm.exe",
        "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "svchost.exe"
    }
    if os.path.exists(PROT_FILE):
        for l in open(PROT_FILE, encoding="utf-8"):
            s = l.strip().lower()
            if s and not s.startswith("#"):
                prot.add(s)
    return prot

def get_avail_mb():
    st = MEMORYSTATUSEX(dwLength=ctypes.sizeof(MEMORYSTATUSEX))
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    return st.ullAvailPhys // (1024 * 1024)

def run():
    before_mb = get_avail_mb()
    gc.collect()
    protected = load_protected()
    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_SET_QUOTA = 0x0100
    PROCESS_SET_INFORMATION = 0x0200
    PROCESS_TERMINATE = 0x0001
    BELOW_NORMAL_PRIORITY_CLASS = 0x00004000

    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    trimmed, closed_apps = [], []
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) < 2:
            continue
        raw_name, pid_str, *_ = parts
        name = raw_name.lower()
        if name in protected or not pid_str.isdigit():
            continue
        pid = int(pid_str)
        if name in CANDIDATE_BLOAT:
            h_kill = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if h_kill:
                if kernel32.TerminateProcess(h_kill, 0):
                    closed_apps.append(name)
                kernel32.CloseHandle(h_kill)
                continue
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SET_QUOTA | PROCESS_SET_INFORMATION, False, pid)
        if h:
            kernel32.SetPriorityClass(h, BELOW_NORMAL_PRIORITY_CLASS)
            if psapi.EmptyWorkingSet(h):
                trimmed.append(name)
            kernel32.CloseHandle(h)

    os.makedirs(os.path.dirname(LAST_ACTION_FILE), exist_ok=True)
    open(LAST_ACTION_FILE, "w", encoding="utf-8").write(json.dumps({
        "closed": sorted(set(closed_apps)),
        "trimmed_count": len(trimmed)
    }, indent=2))

    after_mb = get_avail_mb()
    return {
        "before_mb": before_mb,
        "after_mb": after_mb,
        "freed_mb": max(0, after_mb - before_mb),
        "trimmed": len(trimmed),
        "closed": sorted(set(closed_apps))
    }

if __name__ == "__main__":
    print(run())
