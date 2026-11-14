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

def is_guardian_enabled():
    return not os.path.exists(os.path.join(BRAIN, ".guardian_disabled"))

def stop_guardian_now():
    flag = os.path.join(BRAIN, ".active_session.json")
    if os.path.exists(flag):
        os.remove(flag)
    subprocess.run(["schtasks", "/End", "/TN", "AILAB_Guardian"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["schtasks", "/Delete", "/TN", "AILAB_Guardian", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["taskkill", "/F", "/IM", "wscript.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def toggle_guardian(cmd=""):
    dis_flag = os.path.join(BRAIN, ".guardian_disabled")
    arg = cmd.strip().lower()
    if "off" in arg or (not arg and is_guardian_enabled()):
        open(dis_flag, "w").write("1")
        stop_guardian_now()
        print(f"{C_YELLOW}🛑 Guardián APAGADO (0 MB RAM). Ya puedes cerrar AI-LAB libremente.{C_RESET}")
    else:
        if os.path.exists(dis_flag):
            os.remove(dis_flag)
        print(f"{C_GREEN}🛡️ Guardián ACTIVADO. Protegerá tus bucles y agentes ante cierres.{C_RESET}")

def launch_guardian(pid):
    if not is_guardian_enabled():
        return False
    vbs = os.path.join(ROOT, "CORE", "ailab_guardian.vbs")
    subprocess.run(["schtasks", "/Create", "/TN", "AILAB_Guardian", "/TR", f'wscript.exe "{vbs}" {pid}', "/SC", "ONCE", "/ST", "00:00", "/F", "/IT"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["schtasks", "/Run", "/TN", "AILAB_Guardian"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True

def close_current_window():
    tk = r"C:\Windows\System32\taskkill.exe"
    subprocess.Popen([tk, "/F", "/IM", "WindowsTerminal.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def is_ipad_online():
    try:
        urllib.request.urlopen("http://127.0.0", timeout=0.6)
        return True
    except Exception:
        return False

def ensure_ipad_bridge():
    bridge = os.path.join(TASKS, "06_ipad_worker", "bridge_server.py")
    if os.path.exists(bridge) and not is_ipad_online():
        subprocess.Popen([sys.executable, bridge], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
        print(f"{C_CYAN}📱 Puente Wi-Fi iPad (puerto 8765) reconectado en segundo plano.{C_RESET}")

def check_crash_recovery():
    flag = os.path.join(BRAIN, ".active_session.json")
    if not os.path.exists(flag):
        return None
    try:
        info = json.loads(open(flag, encoding="utf-8").read())
        os.remove(flag)
        tdir = info.get("task_dir", "")
        mode = info.get("mode", "loop")
        ipad_active = info.get("ipad_active", False)
        is_test = info.get("is_test", False)
        t_cur = os.path.join(tdir, "target.py")
        t_good = os.path.join(tdir, ".tmp", "target.last_good.py")
        if os.path.exists(t_good):
            shutil.copy2(t_good, t_cur)
        lesson = "- [崩溃教训] 实验导致进程意外终止，已自动回滚并记录异常特征以防再次触发。\n"
        open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(lesson)
        open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), "a", encoding="utf-8").write(
            f"- [崩溃记录] Tarea {os.path.basename(tdir)} ({mode}) sufrió cierre inesperado y fue recuperada.\n"
        )
        print(f"\n{C_GREEN}🚑 [AUTO-POSTMORTEM EXITOSO] Se detectó cierre inesperado en '{os.path.basename(tdir)}'.{C_RESET}")
        print(f"{C_GREEN}🧠 Lección grabada en BRAIN/PRINCIPLES.md y código restaurado a versión sana.{C_RESET}\n")
        if is_test:
            print(f"{C_CYAN}✅ PRUEBA DE WATCHDOG + APRENDIZAJE COMPLETADA CON ÉXITO.{C_RESET}\n")
            time.sleep(1.5)
            return None
        if ipad_active:
            ensure_ipad_bridge()
        print(f"{C_CYAN}🔄 Reanudando '{os.path.basename(tdir)}' en modo [{mode.upper()}] en 3 segundos...{C_RESET}\n")
        time.sleep(3.0)
        return {"task_dir": tdir, "mode": mode}
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
    print(f"  {C_BOLD}Pruebas de Resiliencia y Aprendizaje:{C_RESET}")
    print(f"    [1] Simular cierre de proceso Python (reabre en esta ventana)")
    print(f"    [2] Simular cierre TOTAL de ventana (cierra ventana y abre nueva)")
    print(f"    [3] Ejecutar TODAS las pruebas en cadena (1 + 2)")
    print(f"    [4] Activar Guardi�n y esperar cierre MANUAL (X o Task Manager)")
    print(f"    [0] Volver al men�")
    ans = input(f"  {C_YELLOW}Elige prueba (0/1/2/3/4): {C_RESET}").strip()
    if ans == "4":
        tdir = os.path.join(TASKS, "09_win_ram_optimizer")
        flag = os.path.join(BRAIN, ".active_session.json")
        open(flag, "w", encoding="utf-8").write(json.dumps({"task_dir": tdir, "is_test": True}))
        launch_guardian(os.getpid())
        print(f"\n{C_GREEN}??? Guardi�n AILAB_Guardian ACTIVO vigilando PID={os.getpid()}.{C_RESET}")
        print(f"{C_YELLOW}?? Ahora cierra esta ventana con la X o m�tala desde el Administrador de Tareas...{C_RESET}")
        input(f"{C_DIM}(O pulsa Enter aqui para cancelar la prueba){C_RESET}")
        if os.path.exists(flag): os.remove(flag)
    elif ans in ("1", "2", "3"):
        tdir = os.path.join(TASKS, "09_win_ram_optimizer")
        flag = os.path.join(BRAIN, ".active_session.json")
        if ans == "1":
            open(flag, "w", encoding="utf-8").write(json.dumps({"task_dir": tdir, "is_test": True}))
            print(f"{C_RED}?? Matando proceso Python... Observa el Watchdog en 2s:{C_RESET}")
            time.sleep(0.8)
            os._exit(1)
        elif ans == "2":
            open(flag, "w", encoding="utf-8").write(json.dumps({"task_dir": tdir, "is_test": True}))
            launch_guardian(os.getpid())
            print(f"{C_RED}?? Cerrando ventana completa... El guardi�n abrir� una ventana nueva en 3.5s:{C_RESET}")
            time.sleep(1.0)
            close_current_window()
            time.sleep(0.5)
            os._exit(1)
        elif ans == "3":
            open(flag, "w", encoding="utf-8").write(json.dumps({"task_dir": tdir, "is_test": True, "chain_next": True}))
            print(f"{C_RED}?? [SUITE COMPLETA 1/2] Matando proceso Python... Luego cerrar� ventana:{C_RESET}")
            time.sleep(0.8)
            os._exit(1)

def run_guarded_session(tdir, mode="loop"):
    os.makedirs(os.path.join(tdir, ".tmp"), exist_ok=True)
    t_cur = os.path.join(tdir, "target.py")
    if os.path.exists(t_cur):
        shutil.copy2(t_cur, os.path.join(tdir, ".tmp", "target.last_good.py"))
    flag = os.path.join(BRAIN, ".active_session.json")
    ipad_was_on = is_ipad_online()
    if is_guardian_enabled():
        open(flag, "w", encoding="utf-8").write(json.dumps({
            "task_dir": tdir,
            "mode": mode,
            "ipad_active": ipad_was_on
        }))
        launch_guardian(os.getpid())
        print(f"{C_GREEN}🛡️ Guardián ACTIVO (PID={os.getpid()} | Modo={mode} | iPad={'ON' if ipad_was_on else 'OFF'}){C_RESET}")
    else:
        print(f"{C_DIM}⚪ Guardián desactivado (/guardian on para activar){C_RESET}")
    try:
        if mode == "agent":
            subprocess.run([sys.executable, os.path.join(ROOT, "CORE", "agent_tools.py"), tdir])
        else:
            subprocess.run(["bash", os.path.join(ROOT, "CORE", "engine.sh")], cwd=tdir)
    finally:
        if os.path.exists(flag):
            os.remove(flag)
