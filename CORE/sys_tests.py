import os, sys, json, time, shutil, subprocess, urllib.request, http.client

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
TASKS = os.path.join(ROOT, "TASKS")

C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def check_crash_recovery():
    flag = os.path.join(BRAIN, ".active_session.json")
    if not os.path.exists(flag):
        return None
    try:
        info = json.loads(open(flag, encoding="utf-8").read())
        os.remove(flag)
        tdir = info.get("task_dir", "")
        is_test = info.get("is_test", False)
        t_cur = os.path.join(tdir, "target.py")
        t_good = os.path.join(tdir, ".tmp", "target.last_good.py")
        if os.path.exists(t_good):
            shutil.copy2(t_good, t_cur)
        lesson = "- [????] ??????????,???????????????????\n"
        open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(lesson)
        open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), "a", encoding="utf-8").write(
            f"- [????] Tarea {os.path.basename(tdir)} sufri� cierre inesperado y fue recuperada.\n"
        )
        print(f"\n{C_GREEN}?? [AUTO-POSTMORTEM EXITOSO] Se detect� cierre inesperado en '{os.path.basename(tdir)}'.{C_RESET}")
        print(f"{C_GREEN}?? Lecci�n grabada en BRAIN/PRINCIPLES.md y c�digo restaurado a versi�n sana.{C_RESET}\n")
        if is_test:
            print(f"{C_CYAN}? PRUEBA DE WATCHDOG + APRENDIZAJE COMPLETADA CON �XITO.{C_RESET}\n")
            time.sleep(1.5)
            return None
        print(f"{C_CYAN}?? Reanudando bucle evolutivo en 3 segundos...{C_RESET}\n")
        time.sleep(3.0)
        return tdir
    except Exception:
        if os.path.exists(flag):
            os.remove(flag)
        return None

def run_system_tests():
    print(f"\n{C_BOLD}{C_CYAN}?? AI-LAB SYSTEM DIAGNOSTICS & SELF-TESTS{C_RESET}")
    print(f"{C_DIM}{'�'*56}{C_RESET}")
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=3)
        conn.request("GET", "/api/tags")
        st = conn.getresponse().status
        conn.close()
        print(f"  Ollama Local Engine:     {C_GREEN}? ONLINE (HTTP {st}){C_RESET}")
    except Exception as e:
        print(f"  Ollama Local Engine:     {C_RED}? OFFLINE ({e}){C_RESET}")
    try:
        urllib.request.urlopen("http://127.0.0", timeout=1)
        print(f"  iPad Wi-Fi Co-Processor: {C_GREEN}? ONLINE (Puerto 8765){C_RESET}")
    except Exception:
        print(f"  iPad Wi-Fi Co-Processor: {C_YELLOW}? STANDBY (Pulsa 'i' para activar){C_RESET}")
    r_opt = os.path.join(TASKS, "09_win_ram_optimizer", "verify.py")
    if os.path.exists(r_opt):
        res = subprocess.run([sys.executable, r_opt], capture_output=True, text=True)
        out = res.stdout.strip() or res.stderr.strip()
        print(f"  Win32 RAM Optimizer:     {C_GREEN}? {out}{C_RESET}")
    print(f"{C_DIM}{'�'*56}{C_RESET}")
    ans = input(f"  {C_YELLOW}�Ejecutar Prueba real de Cierre + Auto-Reapertura + Aprendizaje? (s/N): {C_RESET}").strip().lower()
    if ans == "s":
        tdir = os.path.join(TASKS, "09_win_ram_optimizer")
        flag = os.path.join(BRAIN, ".active_session.json")
        open(flag, "w", encoding="utf-8").write(json.dumps({"task_dir": tdir, "is_test": True}))
        subprocess.Popen(["wscript.exe", os.path.join(ROOT, "CORE", "ailab_guardian.vbs"), str(os.getpid())])
        print(f"{C_RED}?? Simulando cierre abrupto del proceso (exit code 1)... Observa el Watchdog:{C_RESET}")
        time.sleep(1.0)
        os._exit(1)
