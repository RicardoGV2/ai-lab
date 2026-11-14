import os; os.environ["PATH"] = r"C:\Program Files\Git\bin;C:\Program Files\Git\usr\bin;" + os.environ.get("PATH","")
import os; os.environ["PATH"] = r"C:\msys64\ucrt64\bin;C:\msys64\usr\bin;" + os.environ.get("PATH","")
import os, sys, subprocess, http.client, json, time, re, shutil
if os.name == "nt":
    import msvcrt

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
CORE = os.path.join(ROOT, "CORE")
TASKS = os.path.join(ROOT, "TASKS")
sys.path.insert(0, CORE)
import statusbar

C_CYAN, C_GREEN, C_YELLOW, C_RED, C_MAGENTA, C_DIM, C_BOLD, C_RESET = (
    "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[95m", "\033[90m", "\033[1m", "\033[0m"
)
BG_PROC, BG_TASK = None, None

def load_cfg():
    cfg = {"MODEL_NAME": "qwen3.5-pi", "OLLAMA_HOST": "127.0.0.1", "OLLAMA_PORT": "11434", "NUM_PREDICT": "900"}
    p = os.path.join(BRAIN, "CONFIG.env")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def copy_report(n=10):
    rfiles = [os.path.join(TASKS, d, "REPORT.md") for d in os.listdir(TASKS) if os.path.exists(os.path.join(TASKS, d, "REPORT.md"))]
    latest_rep = ""
    if rfiles:
        newest = max(rfiles, key=os.path.getmtime)
        lines = [l for l in open(newest, encoding="utf-8") if l.strip()]
        header = lines[:4]
        body = lines[4:]
        latest_rep = "".join(header + body[-n:]) if len(body) > n else "".join(lines)
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read()
    tmem = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read()
    payload = f"## ?? OBJETIVO\nCerebro evolutivo port�til y agn�stico.\n\n{latest_rep}\n\n{prin}\n\n## ?? TOOLS_MEMORY\n{tmem}"
    subprocess.run(["clip"], input=payload.encode("utf-8"))
    print(f"{C_GREEN}? Ultimos {n} registros + cerebro copiados al portapapeles.{C_RESET}")

def run_ucrt(first_line):
    if first_line.strip() == "/paste":
        res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"], capture_output=True)
        script = (res.stdout.decode("utf-8", errors="replace") if res.stdout else "").replace("\r\n", "\n").replace("\xa0", " ")
        print(f"{C_YELLOW}📋 [Ejecutando {len(script)} chars desde portapapeles]:{C_RESET}")
    else:
        lines = [first_line]
        if "<<" in first_line or first_line.count('"') % 2 == 1 or first_line.count("'") % 2 == 1:
            m = re.search(r"<<\s*['\"]?(\w+)['\"]?", first_line)
            end_m = m.group(1) if m else None
            while True:
                nxt = sys.stdin.readline()
                if not nxt: break
                nxt = nxt.rstrip("\r\n")
                lines.append(nxt)
                if end_m and nxt.strip() == end_m: break
                if not end_m and nxt.strip() == "": break
        script = "\n".join(lines)
        print(f"{C_YELLOW}⚡ [UCRT64]:{C_RESET}")
    open(".tmp_cmd.sh", "w", encoding="utf-8", newline="\n").write(script + "\n")
    subprocess.run(["bash", ".tmp_cmd.sh"], cwd=ROOT)
    if os.path.exists(".tmp_cmd.sh"): os.remove(".tmp_cmd.sh")

def handle_slash(cmd):
    c = cmd.strip().lower()
    if c == "/help":
        print(f"\n{C_CYAN}Comandos:{C_RESET} /save | /clip | /dash | /brain | /compact | /sync | /model | /paste\n")
        return True
    elif c == "/ipad": start_ipad_bridge(); return True
    elif c == "/mentor":
        tdir = select_task()
        if tdir:
            import gemini_mentor
            print(f"{C_CYAN}?? Consultando a Gemini Mentor...{C_RESET}")
            print(f"{C_GREEN}? Sugerencia:{C_RESET} {gemini_mentor.ask_mentor(tdir)}")
        return True
    elif c == "/ram":
        r_script = os.path.join(TASKS, "09_win_ram_optimizer", "verify.py")
        if os.path.exists(r_script):
            res = subprocess.run([sys.executable, r_script], capture_output=True, text=True)
            print(f"{C_GREEN}🧹 {res.stdout.strip() or res.stderr.strip()}{C_RESET}")
        return True
    elif c == "/keep" or c.startswith("/protect"):
        parts = c.split()
        pfile = os.path.join(BRAIN, "PROTECTED_APPS.txt")
        if len(parts) > 1:
            app = parts.__getitem__(1).lower()
            if not app.endswith(".exe"): app += ".exe"
            open(pfile, "a", encoding="utf-8").write(f"{app}\n")
            open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(f"- [????] ??????????????: {app}\n")
            print(f"{C_GREEN}??? '{app}' a�adido a PROTECTED_APPS.txt y al cerebro. Nunca volver� a cerrarse.{C_RESET}")
        else:
            lfile = os.path.join(TASKS, "09_win_ram_optimizer", ".tmp", "last_actions.json")
            if os.path.exists(lfile):
                import json as _j
                data = _j.loads(open(lfile, encoding="utf-8").read())
                print(f"{C_CYAN}?? Ultimos procesos cerrados:{C_RESET} {', '.join(data.get('closed', ())) or 'Ninguno'}")
                print(f"{C_DIM}   ?? Usa '/protect nombre.exe' para excluir cualquiera de ellos.{C_RESET}")
        return True
    elif c == "/test": run_system_tests(); return True
    elif c == "/save":
        import version_control; version_control.create_snapshot(); return True
    elif c == "/clip" or c.startswith("/clip "):
        parts = c.split()
        n = int(parts[1]) if (len(parts) > 1 and parts[1].isdigit()) else 10
        copy_report(n); return True
    elif c == "/dash": subprocess.run([sys.executable, os.path.join(CORE, "dashboard.py")]); return True
    elif c == "/brain": subprocess.run([sys.executable, os.path.join(CORE, "brain_viewer.py")]); return True
    elif c == "/compact": subprocess.run([sys.executable, os.path.join(CORE, "compact_brain.py")]); return True
    elif c == "/paste": run_ucrt("/paste"); return True
    elif c == "/sync":
        subprocess.run(["git", "add", "BRAIN/", "CORE/", "TASKS/"], cwd=ROOT)
        subprocess.run(["git", "commit", "-m", "chore: sync v4.3 full harness"], cwd=ROOT)
        subprocess.run(["git", "push"], cwd=ROOT)
        return True
    elif c == "/model":
        m = input("Nuevo modelo Ollama: ").strip()
        if m:
            p = os.path.join(BRAIN, "CONFIG.env")
            open(p, "w", encoding="utf-8").writelines([l if not l.startswith("MODEL_NAME=") else f'MODEL_NAME="{m}"\n' for l in open(p, encoding="utf-8")])
        return True
    return False

def esc_pressed():
    return os.name == "nt" and msvcrt.kbhit() and msvcrt.getch() == b"\x1b"

def stream_llm(messages, num_predict=800):
    cfg = load_cfg()
    body = json.dumps({"model": cfg["MODEL_NAME"], "messages": messages, "stream": True, "think": False,
                       "options": {"num_predict": int(num_predict), "temperature": 0.25}}).encode("utf-8")
    conn = http.client.HTTPConnection(cfg["OLLAMA_HOST"], int(cfg["OLLAMA_PORT"]), timeout=180)
    conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    out, aborted = "", False
    try:
        for raw in resp:
            if esc_pressed(): aborted = True; break
            line = raw.decode("utf-8").strip()
            if not line: continue
            tok = json.loads(line).get("message", {}).get("content", "")
            out += tok; sys.stdout.write(tok); sys.stdout.flush()
    except KeyboardInterrupt: aborted = True
    finally: conn.close()
    print(f"\n{C_RED}⏹️ [Interrumpido con ESC]{C_RESET}" if aborted else "")
    return out, aborted

def run_agent_chat():
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read()
    tmem = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read()
    sys_prompt = f"You are an autonomous local Windows agent.\nKNOWLEDGE:\n{prin}\nTOOLS_MEMORY:\n{tmem}\nTOOLS: [[RUN: <bash_cmd>]], [[ARXIV: <query>]], [[LEARN: <under_25_chinese_chars>]]. Use [[RUN: ...]] immediately."
    messages = [{"role": "system", "content": sys_prompt}]
    while True:
        print()
        statusbar.render_prompt_bar("AGENT MODE | 'salir' to menu | !<cmd> UCRT64", BG_PROC, BG_TASK)
        try: q = input(f"{C_YELLOW}Tú > {C_RESET}").strip()
        except KeyboardInterrupt: break
        if q.lower() in ("salir", "exit", "0"): break
        if not q: continue
        if q.startswith("/") and handle_slash(q): continue
        if q.startswith("!"): run_ucrt(q[1:].strip()); continue
        messages.append({"role": "user", "content": q})
        for _ in range(4):
            print(f"{C_CYAN}AI > {C_RESET}", end="")
            reply, aborted = stream_llm(messages)
            if aborted or not reply: break
            messages.append({"role": "assistant", "content": reply})
            for lesson in re.findall(r"\[\[LEARN:\s*(.*?)\]\]", reply):
                open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), "a", encoding="utf-8").write(f"- {lesson.strip()}\n")
                print(f"{C_GREEN}🧠 [Aprendido]: {lesson.strip()}{C_RESET}")
            run_m = re.search(r"\[\[RUN:\s*(.*?)\]\]", reply, re.S)
            if run_m:
                cmd = run_m.group(1).strip()
                print(f"{C_YELLOW}⚡ [Ejecutando]: {cmd}{C_RESET}")
                res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=30)
                obs = (res.stdout + res.stderr).strip() or f"EXIT_CODE={res.returncode} (Success)"
                print(f"{C_CYAN}   ↳ {obs[:250]}{C_RESET}")
                messages.append({"role": "user", "content": f"TOOL_RESULT (exit={res.returncode}):\n{obs[:1500]}"})
                continue
            break

def start_ipad_bridge():
    bdir = os.path.join(TASKS, "06_ipad_worker")
    script = os.path.join(bdir, "start_bridge.py")
    if not os.path.exists(script):
        print(f"{C_RED}❌ No se encontró 06_ipad_worker/start_bridge.py{C_RESET}"); return
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen([sys.executable, "start_bridge.py"], cwd=bdir, creationflags=flags)
    time.sleep(0.8)

def select_task():
    tasks = sorted([d for d in os.listdir(TASKS) if os.path.isdir(os.path.join(TASKS, d))])
    if not tasks: return None
    print(f"\n{C_YELLOW}Tareas disponibles:{C_RESET}")
    for idx, t in enumerate(tasks, 1): print(f"  [{idx}] {t}")
    c = input("Elige número: ").strip()
    return os.path.join(TASKS, tasks[int(c) - 1]) if (c.isdigit() and 1 <= int(c) <= len(tasks)) else None

while True:
    import shutil
    cfg = load_cfg()
    p_cnt = len([l for l in open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8") if l.strip().startswith("-")])
    t_cnt = len([l for l in open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8") if l.strip().startswith("-")])
    w = min(78, max(54, shutil.get_terminal_size((76, 24)).columns - 2))
    title = f" ✳ Welcome to AI-LAB v4.3 | Cerebro Agnóstico ({p_cnt}+{t_cnt} reglas)"
    print(f"\n{C_CYAN}{C_BOLD}╭{'─'*w}╮")
    print(f"│{title:<{w}}│")
    print(f"╰{'─'*w}╯{C_RESET}")
    print(f"  {C_GREEN}(1){C_RESET} Iniciar Bucle Evolutivo    {C_GREEN}(5){C_RESET} Dashboard y Gráficas (/dash)")
    print(f"  {C_GREEN}(2){C_RESET} Agente con Herramientas    {C_GREEN}(6){C_RESET} Copiar Reporte (/clip)")
    print(f"  {C_GREEN}(3){C_RESET} Probar Script Optimizado   {C_GREEN}(7){C_RESET} Cambiar Modelo (/model)")
    print(f"  {C_GREEN}(4){C_RESET} Investigar en arXiv        {C_GREEN}(8){C_RESET} Nueva Tarea   {C_GREEN}(9){C_RESET} Sync Git (/sync)")
    print(f"  {C_CYAN}(b){C_RESET} Ver Cerebro (/brain)       {C_YELLOW}(c){C_RESET} Compactar     {C_MAGENTA}(v){C_RESET} Backups (/save)")
    print(f"  {C_CYAN}(i){C_RESET} Conectar iPad (/ipad)     {C_YELLOW}(t){C_RESET} Test Systems (/test)   {C_RED}(0){C_RESET} Salir\n")
    statusbar.render_prompt_bar("MAIN MENU", BG_PROC, BG_TASK)
    try: op = input(f"{C_CYAN}> {C_RESET}").strip()
    except KeyboardInterrupt: break
    if not op: continue
    if op.startswith("/") and handle_slash(op):
        input(f"{C_DIM}Pulsa Enter para refrescar...{C_RESET}"); continue
    if op in ("1", "1_resume"):
        if op == "1":
            tdir = select_task()
        if tdir:
            print(f"{C_GREEN}🚀 Corriendo en esta misma ventana (Ctrl+C para volver al menú)...{C_RESET}\n")
            try:
                subprocess.run(["bash", os.path.join(CORE, "engine.sh")], cwd=tdir)
            except KeyboardInterrupt:
                print(f"\n{C_YELLOW}⏸️ Pausado. Progreso guardado.{C_RESET}")
                time.sleep(1.0)
    elif op == "2": run_agent_chat()
    elif op == "3":
        tdir = select_task()
        if tdir:
            t0 = time.perf_counter()
            res = subprocess.run([sys.executable, "verify.py"], cwd=tdir, capture_output=True, text=True)
            print(f"\n{C_GREEN}({int((time.perf_counter()-t0)*1000)}ms):{C_RESET}\n{res.stdout or res.stderr}")
            input("Enter...")
    elif op == "4":
        q = input("Query arXiv (inglés): ").strip()
        if q:
            res = subprocess.run([sys.executable, os.path.join(CORE, "arxiv_scout.py"), q], capture_output=True, text=True)
            print(f"\n{res.stdout}")
            if "http" in res.stdout:
                lesson, _ = stream_llm([{"role": "user", "content": f"Summarize ONE optimization principle in ONE brief Chinese sentence:\n{res.stdout}"}], 120)
                open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(f"- [论文启发] {lesson.strip()}\n")
            input("Enter...")
    elif op == "5": subprocess.run([sys.executable, os.path.join(CORE, "dashboard.py")])
    elif op == "6": copy_report(); time.sleep(1.2)
    elif op == "7": handle_slash("/model")
    elif op == "8":
        n = input("Nombre nueva tarea: ").strip()
        if n:
            d = os.path.join(TASKS, n); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "target.py"), "w").write("def run(): return True\n")
            open(os.path.join(d, "verify.py"), "w").write("import target; assert target.run()\n")
    elif op == "9": handle_slash("/sync"); input("Enter...")
    elif op.lower() == "b": subprocess.run([sys.executable, os.path.join(CORE, "brain_viewer.py")])
    elif op.lower() == "c": subprocess.run([sys.executable, os.path.join(CORE, "compact_brain.py")]); input("Enter...")
    elif op.lower() == "v": subprocess.run([sys.executable, os.path.join(CORE, "version_control.py")])
    elif op.lower() == "t": run_system_tests(); input(f"{C_DIM}Pulsa Enter...{C_RESET}")
    elif op.lower() == "i": start_ipad_bridge(); input(f"{C_DIM}Pulsa Enter...{C_RESET}")
    elif op == "0": break
    else:
        run_ucrt(op)
        input(f"{C_DIM}Pulsa Enter para continuar...{C_RESET}")


