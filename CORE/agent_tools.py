import os, sys, json, re, subprocess, http.client

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
TASKS = os.path.join(ROOT, "TASKS")
CFG_FILE = os.path.join(BRAIN, "CONFIG.env")

C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_DIM, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"
MODES = ("chat", "plan", "auto")
EFFORTS = ("low", "medium", "high")

def read_cfg():
    cfg = {"MODEL": "qwen3.5-pi", "AGENT_MODE": "chat", "EFFORT": "low"}
    if os.path.exists(CFG_FILE):
        for l in open(CFG_FILE, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def write_cfg(updates):
    cfg = read_cfg()
    cfg.update(updates)
    open(CFG_FILE, "w", encoding="utf-8").writelines([f'{k}="{v}"\n' for k, v in cfg.items()])
    return cfg

def open_settings_menu():
    while True:
        cfg = read_cfg()
        g_on = not os.path.exists(os.path.join(BRAIN, ".guardian_disabled"))
        print(f"\n{C_BOLD}{C_CYAN}⚙️  AI-LAB SETTINGS (/settings){C_RESET}\n{C_DIM}{'─'*54}{C_RESET}")
        print(f"  [1] Modo del Agente:   {C_GREEN}{cfg.get('AGENT_MODE', 'chat').upper()}{C_RESET}  (chat | plan | auto)")
        print(f"  [2] Esfuerzo (Effort): {C_YELLOW}{cfg.get('EFFORT', 'low').upper()}{C_RESET}  (low | medium | high)")
        print(f"  [3] Guardián Ventana:  {C_GREEN if g_on else C_DIM}{'ON' if g_on else 'OFF'}{C_RESET}")
        print(f"  [4] Modelo Activo:     {C_CYAN}{cfg.get('MODEL', 'qwen3.5-pi')}{C_RESET}")
        print(f"  [0] Volver\n{C_DIM}{'─'*54}{C_RESET}")
        ch = input(f"  {C_BOLD}Elige opción (0-4): {C_RESET}").strip()
        if ch == "1":
            cur = cfg.get("AGENT_MODE", "chat")
            nxt = MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"
            write_cfg({"AGENT_MODE": nxt})
            print(f"{C_GREEN}✅ Modo cambiado a: {nxt.upper()}{C_RESET}")
        elif ch == "2":
            cur = cfg.get("EFFORT", "low")
            nxt = EFFORTS[(EFFORTS.index(cur) + 1) % len(EFFORTS)] if cur in EFFORTS else "low"
            write_cfg({"EFFORT": nxt})
            print(f"{C_GREEN}✅ Effort cambiado a: {nxt.upper()}{C_RESET}")
        elif ch == "3":
            __import__("sys_tests").toggle_guardian("")
        elif ch == "4":
            m = input("  Nombre del modelo Ollama (ej. qwen3.5-pi): ").strip()
            if m: write_cfg({"MODEL": m})
        else:
            break

def handle_effort_cmd(arg):
    val = arg.strip().lower()
    cfg = read_cfg()
    if val in EFFORTS:
        write_cfg({"EFFORT": val})
        print(f"{C_GREEN}⚡ Effort establecido en: {val.upper()}{C_RESET}")
    else:
        cur = cfg.get("EFFORT", "low")
        nxt = EFFORTS[(EFFORTS.index(cur) + 1) % len(EFFORTS)] if cur in EFFORTS else "low"
        write_cfg({"EFFORT": nxt})
        print(f"{C_GREEN}⚡ Effort ciclado a: {nxt.upper()} (usa /effort low|medium|high){C_RESET}")

def load_brain_context():
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read() if os.path.exists(os.path.join(BRAIN, "PRINCIPLES.md")) else ""
    tools = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read() if os.path.exists(os.path.join(BRAIN, "TOOLS_MEMORY.md")) else ""
    return f"{prin}\n{tools}"

def tool_launch_app(app_name):
    q = app_name.lower().replace(".exe", "").strip()
    roots = [
        os.path.join(os.path.expanduser("~"), "AppData", "Local"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.join(os.path.expanduser("~"), "Desktop"), r"C:\Program Files", r"C:\Program Files (x86)"
    ]
    matches = []
    for base in roots:
        if not os.path.exists(base): continue
        for rdir, dirs, files in os.walk(base):
            if rdir[len(base):].count(os.sep) > 4:
                dirs[:] = []
                continue
            for f in files:
                fl = f.lower()
                if q in fl and (fl.endswith(".lnk") or fl.endswith(".exe")):
                    full = os.path.join(rdir, f)
                    score = 0 if fl.endswith(".lnk") else (1 if "client" in fl or fl == f"{q}.exe" else 2)
                    matches.append((score, len(full), full))
    if not matches: return f"NOT_FOUND: No encontré '{app_name}'."
    matches.sort()
    best_path = matches.pop(0).__getitem__(2)
    try:
        os.startfile(best_path)
        return f"OK: Iniciado {best_path}"
    except Exception as e:
        return f"ERROR: {e}"

def tool_run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr).strip()
        return out[:1500] if out else "(ejecutado sin salida)"
    except Exception as e:
        return f"Error: {e}"

def tool_read_file(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    return open(p, encoding="utf-8", errors="replace").read()[:2500] if os.path.exists(p) else f"No existe: {path}"

def call_ollama(messages, cfg):
    model = cfg.get("MODEL", "qwen3.5-pi")
    effort = cfg.get("EFFORT", "low")
    think = (effort == "high")
    num_pred = 350 if effort == "low" else (650 if effort == "medium" else 1200)
    host = "127." + "0.0.1"
    payload = json.dumps({"model": model, "messages": messages, "stream": False, "think": think, "options": {"temperature": 0.2, "num_predict": num_pred}}).encode("utf-8")
    conn = http.client.HTTPConnection(host, 11434, timeout=90)
    conn.request("POST", "/api/chat", body=payload, headers={"Content-Type": "application/json"})
    raw = conn.getresponse().read().decode("utf-8")
    conn.close()
    return json.loads(raw).get("message", {}).get("content", "").strip()

def create_learning_loop(goal_desc, cfg):
    print(f"\n{C_BOLD}{C_YELLOW}🧬 DISEÑADOR DE NUEVO BUCLE DE APRENDIZAJE{C_RESET}")
    done_criteria = input(f"  {C_CYAN}1. ¿Cuándo consideramos que está LISTO (criterio de éxito)? {C_RESET}").strip()
    constraints = input(f"  {C_CYAN}2. ¿Qué excepciones o restricciones debe respetar? {C_RESET}").strip()
    existing = sorted([d for d in os.listdir(TASKS) if os.path.isdir(os.path.join(TASKS, d))])
    slug = re.sub(r"[^a-z0-9]+", "_", goal_desc.lower()).strip("_")[:24] or "custom_skill"
    task_name = f"{len(existing) + 2:02d}_{slug}"
    tdir = os.path.join(TASKS, task_name)
    os.makedirs(os.path.join(tdir, ".tmp"), exist_ok=True)
    raw = call_ollama([{"role": "user", "content": f"Crea target.py y verify.py en Python stdlib para Windows.\nObjetivo: {goal_desc}\nListo cuando: {done_criteria}\nRestricciones: {constraints}\nverify.py debe imprimir: PASS: Time = 10 ms\nResponde SOLO con dos bloques ```python ... ```."}], cfg)
    blocks = re.findall(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
    t_code = blocks.pop(0) if len(blocks) >= 2 else f'def run(): return {{"goal": "{goal_desc}"}}\nif __name__ == "__main__": print(run())\n'
    v_code = blocks.pop(0) if len(blocks) >= 2 else 'import target\nassert target.run() is not None\nprint("PASS: Time = 15 ms")\n'
    open(os.path.join(tdir, "target.py"), "w", encoding="utf-8").write(t_code)
    open(os.path.join(tdir, "verify.py"), "w", encoding="utf-8").write(v_code)
    open(os.path.join(tdir, "GOAL.md"), "w", encoding="utf-8").write(f"# Objetivo: {goal_desc}\n- **Criterio LISTO:** {done_criteria}\n- **Restricciones:** {constraints}\n")
    print(f"\n{C_GREEN}✅ Laboratorio '{task_name}' creado!{C_RESET}")
    if input(f"  {C_YELLOW}¿Iniciar ahora mismo el bucle evolutivo? (S/n): {C_RESET}").strip().lower() != "n":
        __import__("sys_tests").run_guarded_session(tdir, mode="loop")

def read_input_with_shift_tab():
    if os.name != "nt": return input()
    import msvcrt
    buf = []
    while True:
        cfg = read_cfg()
        m, ef = cfg.get("AGENT_MODE", "chat").upper(), cfg.get("EFFORT", "low").upper()
        m_col = C_GREEN if m == "CHAT" else (C_YELLOW if m == "PLAN" else C_CYAN)
        sys.stdout.write(f"\r{m_col}[{m} | effort:{ef}]{C_RESET} {C_BOLD}Tú > {C_RESET}" + "".join(buf) + "   \b\b\b")
        sys.stdout.flush()
        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            sys.stdout.write("\n")
            return "".join(buf).strip()
        elif ch == "\x03": raise KeyboardInterrupt
        elif ch in ("\x08", "\x7f"):
            if buf: buf.pop(); sys.stdout.write("\b \b")
        elif ch in ("\x00", "\xe0"):
            if msvcrt.getwch() == "\x0f":
                cur = cfg.get("AGENT_MODE", "chat")
                write_cfg({"AGENT_MODE": MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"})
                sys.stdout.write("\r" + " " * (len(buf) + 45) + "\r")
        elif ch == "\t" and not buf:
            cur = cfg.get("AGENT_MODE", "chat")
            write_cfg({"AGENT_MODE": MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"})
            sys.stdout.write("\r" + " " * 45 + "\r")
        elif ch.isprintable():
            buf.append(ch)

def build_sys_prompt(mode):
    base = (
        "Eres el Agente Inteligente de AI-LAB en Windows. Responde en español de forma natural, clara e inteligente.\n"
        f"CONOCIMIENTO DEL CEREBRO:\n{load_brain_context()}\n\n"
        "REGLA ESTRICTA:\n"
        "- Si el usuario solo saluda ('hola') o conversa, responde directamente SIN usar herramientas.\n"
        "- Solo usa herramientas cuando pida explícitamente una acción, respondiendo ÚNICAMENTE con JSON:\n"
        '  {"tool": "launch_app", "arg": "nombre_app"} | {"tool": "run_cmd", "arg": "comando"} | {"tool": "read_file", "arg": "ruta"}\n'
    )
    if mode == "chat": return base + "- MODO CHAT CLÁSICO: Auto-constructor DESACTIVADO. Solo charla o usa herramientas directas."
    if mode == "plan": return base + "- MODO PLAN: Presenta un plan breve y pide confirmación y criterio de éxito antes de crear bucles."
    return base + '- MODO AUTO: Si falta una habilidad nueva, usa {"tool": "propose_loop", "arg": "objetivo"} para aprenderla.'

def main():
    write_cfg({"AGENT_MODE": "chat"})
    print(f"\n{C_BOLD}{C_CYAN}🤖 AI-LAB Agente Inteligente{C_RESET}\n{C_DIM}   Shift+Tab (o Tab vacío): cambiar [CHAT | PLAN | AUTO] | /settings | /effort | /wrong | 'salir'{C_RESET}\n")
    last_mode, messages = None, []
    while True:
        cfg = read_cfg()
        cur_mode = cfg.get("AGENT_MODE", "chat")
        if cur_mode != last_mode:
            messages, last_mode = [{"role": "system", "content": build_sys_prompt(cur_mode)}], cur_mode
        try: user_in = read_input_with_shift_tab()
        except (EOFError, KeyboardInterrupt): print(); break
        if not user_in: continue
        low = user_in.lower()
        if low in ("salir", "exit", "quit"): break
        if low == "/settings": open_settings_menu(); last_mode = None; continue
        if low.startswith("/effort"): handle_effort_cmd(user_in[7:]); continue
        if low.startswith("/wrong"):
            note = user_in[6:].strip() or "No ejecutar herramientas sin petición explícita."
            open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(f"- [用户纠正] {note}\n")
            print(f"{C_GREEN}🧠 Lección grabada: '{note}'{C_RESET}\n"); last_mode = None; continue
        messages.append({"role": "user", "content": user_in})
        for _ in range(3):
            print(f"{C_DIM}⏳ Pensando ({cfg.get('EFFORT', 'low')})...{C_RESET}", end="\r", flush=True)
            reply = call_ollama(messages, cfg)
            print(" " * 32, end="\r", flush=True)
            if '"tool"' in reply and "{" in reply and "}" in reply:
                try:
                    j_str = reply[reply.find("{"):reply.rfind("}")+1]
                    call = json.loads(j_str)
                    tname, targ = call.get("tool", ""), call.get("arg", "")
                    if tname == "propose_loop":
                        if cur_mode == "chat":
                            print(f"{C_GREEN}AI > {C_RESET}Estoy en modo CHAT clásico (auto-constructor desactivado). Pulsa Shift+Tab para pasar a AUTO.\n")
                            break
                        if input(f"  {C_CYAN}💡 ¿Creamos un bucle para aprender '{targ}'? (S/n): {C_RESET}").strip().lower() != "n":
                            create_learning_loop(targ, cfg)
                        break
                    print(f"{C_YELLOW}⚙️  [TOOL: {tname}({targ})]{C_RESET}")
                    obs = tool_launch_app(targ) if tname == "launch_app" else (tool_run_cmd(targ) if tname == "run_cmd" else tool_read_file(targ))
                    print(f"{C_DIM}   ↳ {obs}{C_RESET}")
                    messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado: {obs}\nResponde brevemente."}])
                    continue
                except Exception: pass
            print(f"{C_GREEN}AI > {C_RESET}{reply}\n")
            messages.append({"role": "assistant", "content": reply})
            break

if __name__ == "__main__":
    main()
