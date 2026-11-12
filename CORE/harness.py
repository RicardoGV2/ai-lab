import os, sys, subprocess, http.client, json, time, re
if os.name == "nt":
    import msvcrt

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
CORE = os.path.join(ROOT, "CORE")
TASKS = os.path.join(ROOT, "TASKS")
C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[0m"

def load_cfg():
    cfg = {"MODEL_NAME": "qwen3.5-pi", "OLLAMA_HOST": "127.0.0.1", "OLLAMA_PORT": "11434", "NUM_PREDICT": "900"}
    cfg_path = os.path.join(BRAIN, "CONFIG.env")
    if os.path.exists(cfg_path):
        for line in open(cfg_path, encoding="utf-8"):
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def esc_pressed():
    return os.name == "nt" and msvcrt.kbhit() and msvcrt.getch() == b"\x1b"

def stream_llm(messages, num_predict=800):
    cfg = load_cfg()
    body = json.dumps({
        "model": cfg["MODEL_NAME"], "messages": messages,
        "stream": True, "think": False,
        "options": {"num_predict": int(num_predict), "temperature": 0.25}
    }).encode("utf-8")
    conn = http.client.HTTPConnection(cfg["OLLAMA_HOST"], int(cfg["OLLAMA_PORT"]), timeout=180)
    conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    out, aborted = "", False
    try:
        for raw in resp:
            if esc_pressed():
                aborted = True; break
            line = raw.decode("utf-8").strip()
            if not line: continue
            tok = json.loads(line).get("message", {}).get("content", "")
            out += tok
            sys.stdout.write(tok); sys.stdout.flush()
    except KeyboardInterrupt:
        aborted = True
    finally:
        conn.close()
    print(f"\n{C_RED}⏹️ [Interrumpido con ESC]{C_RESET}" if aborted else "")
    return out, aborted

def run_agent_chat():
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read()
    tmem = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read()
    sys_prompt = f"""You are an autonomous local Windows agent with real tool execution.
KNOWLEDGE:\n{prin}\nENVIRONMENT & TOOL MEMORY:\n{tmem}
TOOLS (Output exact tag to run):
1. [[RUN: <bash_command>]] -> Run shell command on user PC.
2. [[ARXIV: <query>]] -> Search arXiv papers.
3. [[LEARN: <under_25_chinese_chars>]] -> Save environment/tool lesson to memory.
RULES: Use [[RUN: ...]] immediately to act on files. If a path/command fails, learn the fix and emit [[LEARN: ...]]."""
    messages = [{"role": "system", "content": sys_prompt}]
    print(f"\n{C_GREEN}💬 Modo Agente con Herramientas (ESC para cortar | 'salir' para volver):{C_RESET}")
    while True:
        try: q = input(f"\n{C_YELLOW}Tú > {C_RESET}").strip()
        except KeyboardInterrupt: break
        if q.lower() in ("salir", "exit"): break
        if not q: continue
        messages.append({"role": "user", "content": q})
        for _ in range(4):
            print(f"{C_CYAN}AI > {C_RESET}", end="")
            reply, aborted = stream_llm(messages)
            if aborted or not reply: break
            messages.append({"role": "assistant", "content": reply})
            for lesson in re.findall(r"\[\[LEARN:\s*(.*?)\]\]", reply):
                open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), "a", encoding="utf-8").write(f"- {lesson.strip()}\n")
                print(f"{C_GREEN}🧠 [Aprendido]: {lesson.strip()}{C_RESET}")
            arxiv_m = re.search(r"\[\[ARXIV:\s*(.*?)\]\]", reply)
            if arxiv_m:
                res = subprocess.run([sys.executable, os.path.join(CORE, "arxiv_scout.py"), arxiv_m.group(1)], capture_output=True, text=True)
                messages.append({"role": "user", "content": f"TOOL_RESULT:\n{res.stdout[:1500]}"})
                continue
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

def select_task():
    tasks = sorted([d for d in os.listdir(TASKS) if os.path.isdir(os.path.join(TASKS, d))])
    if not tasks: return None
    print(f"\n{C_YELLOW}Tareas disponibles:{C_RESET}")
    for idx, t in enumerate(tasks, 1): print(f"  [{idx}] {t}")
    c = input("Elige número: ").strip()
    return os.path.join(TASKS, tasks[int(c) - 1]) if (c.isdigit() and 1 <= int(c) <= len(tasks)) else None

while True:
    cfg = load_cfg()
    p_cnt = len(open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").readlines())
    t_cnt = len(open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").readlines())
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{C_CYAN}{C_BOLD}==================================================================")
    print(f"  AI-LAB HARNESS v2.0  |  Motor: {cfg['MODEL_NAME']}  |  Reglas: {p_cnt}+{t_cnt}")
    print(f"=================================================================={C_RESET}")
    print("  [1] Iniciar Bucle Evolutivo   [5] Copiar Reporte (clip)")
    print("  [2] Agente con Herramientas   [6] Cambiar Modelo (CONFIG.env)")
    print("  [3] Probar Script Optimizado  [7] Crear Nueva Tarea")
    print("  [4] Investigar en arXiv       [0] Salir\n")
    try: op = input(f"{C_CYAN}ailab > {C_RESET}").strip()
    except KeyboardInterrupt: break
    if op == "1":
        tdir = select_task()
        if tdir:
            try: subprocess.run(["bash", os.path.join(CORE, "engine.sh")], cwd=tdir)
            except KeyboardInterrupt: pass
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
    elif op == "5":
        tdir = select_task()
        rep = open(os.path.join(tdir, "REPORT.md"), encoding="utf-8").read() if (tdir and os.path.exists(os.path.join(tdir, "REPORT.md"))) else ""
        prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read()
        tmem = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read()
        subprocess.run(["clip"], input=f"## 🎯 OBJETIVO\nCerebro evolutivo portátil.\n\n{rep}\n\n{prin}\n\n## 🔧 TOOLS\n{tmem}".encode("utf-8"))
        print(f"{C_GREEN}✅ Copiado al portapapeles.{C_RESET}"); time.sleep(1)
    elif op == "6":
        m = input("Nuevo modelo Ollama: ").strip()
        if m:
            p = os.path.join(BRAIN, "CONFIG.env")
            open(p, "w", encoding="utf-8").writelines([l if not l.startswith("MODEL_NAME=") else f'MODEL_NAME="{m}"\n' for l in open(p, encoding="utf-8")])
    elif op == "7":
        n = input("Nombre nueva tarea: ").strip()
        if n:
            d = os.path.join(TASKS, n); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "target.py"), "w").write("def run(): return True\n")
            open(os.path.join(d, "verify.py"), "w").write("import target; assert target.run()\n")
    elif op == "0": break
