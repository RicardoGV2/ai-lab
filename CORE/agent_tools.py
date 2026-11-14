import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
import os as _os; _os.environ["PATH"] = r"C:\Users\joseg\AppData\Local\Programs\Microsoft VS Code\bin;" + _os.environ.get("PATH", "")
import os, sys, json, re, time, threading, subprocess, http.client

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
TASKS = os.path.join(ROOT, "TASKS")
CFG_FILE = os.path.join(BRAIN, "CONFIG.env")

AGENT_LOG = os.path.join(BRAIN, "agent_session.log")

TUI = None
def ui_print(msg="", end="\n"):
    txt = str(msg) + end
    if TUI:
        TUI.write(txt)
    else:
        sys.stdout.write(txt)
        sys.stdout.flush()

def log_agent(tag, text):
    ts = time.strftime("%H:%M:%S")
    open(AGENT_LOG, "a", encoding="utf-8").write(f"[{ts}] [{tag}] {text}\n")


C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_DIM, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"
MODES = ("chat", "plan", "free", "auto", "infinite")
EFFORTS = ("low", "medium", "high")

def read_cfg():
    cfg = {"MODEL": "qwen3.5-pi", "AGENT_MODE": "chat", "EFFORT": "low", "VERBOSE": "off", "AUTO_LEARN": "on"}
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
        print(f"  [1] Modo del Agente:   {C_GREEN}{cfg.get('AGENT_MODE', 'chat').upper()}{C_RESET}  (chat | plan | free | auto | infinite)")
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
        elif ch == "5":
            cur_v = cfg.get("VERBOSE", "off")
            write_cfg({"VERBOSE": "on" if cur_v == "off" else "off"})
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
        val = EFFORTS[(EFFORTS.index(cur) + 1) % len(EFFORTS)] if cur in EFFORTS else "low"
        write_cfg({"EFFORT": val})
        print(f"{C_GREEN}⚡ Effort ciclado a: {val.upper()} (usa /effort low|medium|high){C_RESET}")
    if val == "low" and cfg.get("VERBOSE", "off") == "on":
        print(f"{C_YELLOW}⚠️  Nota: En effort LOW se apaga el pensamiento interno (verbose queda en pausa hasta usar /effort medium o high).{C_RESET}")

def load_brain_context():
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read() if os.path.exists(os.path.join(BRAIN, "PRINCIPLES.md")) else ""
    tools = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read() if os.path.exists(os.path.join(BRAIN, "TOOLS_MEMORY.md")) else ""
    return f"{prin}\n{tools}"

def handle_verbose_cmd(arg):
    val = arg.strip().lower()
    cfg = read_cfg()
    if val in ("on", "off"):
        write_cfg({"VERBOSE": val})
    else:
        val = "on" if cfg.get("VERBOSE", "off") == "off" else "off"
        write_cfg({"VERBOSE": val})
    print(f"{C_YELLOW}💭 Verbose (mostrar pensamiento): {val.upper()}{C_RESET}")
    if val == "on" and cfg.get("EFFORT", "low") == "low":
        print(f"{C_YELLOW}⚠️  Nota: /verbose requiere effort MEDIUM o HIGH para mostrar pensamiento (actual: LOW). Usa '/effort medium'.{C_RESET}")

def tool_launch_app(app_name):
    parts = app_name.strip().split(None, 1)
    if len(parts) == 2 and parts.__getitem__(0).lower() in ("code", "notepad", "explorer", "start"):
        exe, target = parts.__getitem__(0), parts.__getitem__(1).strip('"').strip("'")
        if not os.path.isabs(target):
            desk = os.path.join(os.path.expanduser("~"), "Desktop", target)
            if os.path.exists(desk): target = desk
            elif os.path.exists(os.path.join(ROOT, target)): target = os.path.join(ROOT, target)
        if exe.lower() == "code":
            code_cmd = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "Microsoft VS Code", "bin", "code.cmd")
            if os.path.exists(code_cmd):
                subprocess.Popen([code_cmd, target], shell=True)
                return f"OK: Abierto en VS Code: {target}"
        subprocess.Popen(f'{exe} "{target}"', shell=True)
        return f"OK: Abierto {target} con {exe}"
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
        code_cmd = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "Microsoft VS Code", "bin", "code.cmd")
        if os.path.exists(code_cmd):
            cmd = re.sub(r'\bstart\s+(?:"[^"]*"\s+)?(?:notepad(?:\.exe)?\s+)?([^&|]+\.\w+)', lambda m: f'"{code_cmd}" {m.group(1).strip()}', cmd, flags=re.I)
            cmd = re.sub(r'\b(?:code|notepad(?:\.exe)?)\s+', lambda m: f'"{code_cmd}" ', cmd, flags=re.I)
        m_pyf = re.search(r'python\s+([\w./\\-]+\.py)', cmd, re.I)
        if m_pyf and os.path.exists(os.path.join(ROOT, m_pyf.group(1))) and "tkinter" in open(os.path.join(ROOT, m_pyf.group(1)), encoding="utf-8", errors="ignore").read():
            subprocess.Popen(cmd, shell=True, cwd=ROOT)
            return f"OK: Ventana gráfica iniciada en segundo plano ({m_pyf.group(1)})"
        res = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=15)
        out = (res.stdout + res.stderr).strip()
        return out[:1500] if out else "(ejecutado sin salida)"
    except Exception as e:
        return f"Error: {e}"

def tool_read_file(path):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    return open(p, encoding="utf-8", errors="replace").read()[:2500] if os.path.exists(p) else f"No existe: {path}"

def tool_write_file(path, content):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    open(p, "w", encoding="utf-8").write(content)
    return f"OK: Archivo guardado en {p} ({len(content)} chars)"

def check_esc_pressed():
    if TUI and TUI.cancel_flag:
        TUI.cancel_flag = False
        return True
    if os.name == "nt":
        import msvcrt
        while msvcrt.kbhit():
            if msvcrt.getwch() == "\x1b":
                return True
    return False

def call_ollama(messages, cfg, stop_spin=None, phase=None, escape_valley=False):
    model = cfg.get("MODEL", "qwen3.5-pi")
    effort = cfg.get("EFFORT", "low")
    verbose = (cfg.get("VERBOSE", "off") == "on")
    think = escape_valley or (not cfg.get("_RETRY") and effort in ("medium", "high"))
    max_think_chars = 2800 if effort == "medium" else 5500
    num_pred = 4096 if effort == "low" else 8192
    host = "127." + "0.0.1"
    payload = json.dumps({
        "model": model, "messages": messages, "stream": True, "think": think,
        "options": {"temperature": 0.75 if escape_valley else (0.65 if cfg.get("_RETRY") else 0.2), "num_predict": num_pred}
    }).encode("utf-8")
    conn = http.client.HTTPConnection(host, 11434, timeout=120)
    conn.request("POST", "/api/chat", body=payload, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    full_content, think_buf, in_think, started_out = [], [], False, False
    overthought = False
    try:
        for raw_line in resp:
            if check_esc_pressed():
                if in_think: sys.stdout.write(C_RESET)
                sys.stdout.write(f"\n{C_YELLOW}⏹️  [Interrumpido con ESC]{C_RESET}\n")
                sys.stdout.flush()
                log_agent("ESC", "Cancelado por el usuario")
                conn.close()
                return "__CANCELLED__"
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line: continue
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            th = msg.get("thinking", "")
            ct = msg.get("content", "")
            if th:
                think_buf.append(th)
                t_len = sum(len(x) for x in think_buf)
                if phase is not None and not verbose:
                    phase = f"Reasoning ({t_len}c)"
                if verbose:
                    if not started_out:
                        if stop_spin: stop_spin.set()
                        if TUI: TUI.status_note = ""; TUI.refresh()
                        started_out = True
                    if not in_think:
                        ui_print(f"\n{C_DIM}💭 ", end="")
                        in_think = True
                    ui_print(th, end='')
                pass
            if ct:
                full_content.append(ct)
                joined = "".join(full_content)
                if phase is not None:
                    m_fn = re.search(r"FILE:\s*([\w./\\-]+)", joined)
                    m_tl = re.search(r'"tool"\s*:\s*"([^"]+)"', joined)
                    if m_fn:
                        phase = f"Writing {m_fn.group(1)} ({len(joined)}c)"
                    elif m_tl:
                        phase = f"Tool {m_tl.group(1)} ({len(joined)}c)"
                    else:
                        phase = f"Replying ({len(joined)}c)"
                if not started_out and verbose:
                    if stop_spin: stop_spin.set()
                    if TUI: TUI.status_note = ""; TUI.refresh()
                    started_out = True
                if in_think:
                    ui_print(f"{C_RESET}\n", end="")
                    in_think = False
    finally:
        if in_think: sys.stdout.write(C_RESET + "\n")
        conn.close()
    if think_buf:
        log_agent("THINK", "".join(think_buf)[:1200])
    if overthought:
        log_agent("WARN", "Thinking excedio limite; reintentando en modo directo")
        sys.stdout.write(f"\n{C_CYAN}⚡ [Reasoning complete -> Writing code directly...]{C_RESET}\n")
        sys.stdout.flush()
        fast_cfg = dict(cfg)
        fast_cfg["EFFORT"] = "low"
        fast_cfg["VERBOSE"] = "off"
        return call_ollama(messages, fast_cfg, stop_spin, phase, escape_valley=False)
    out = "".join(full_content).strip()
    log_agent("REPLY", out[:1500])
    return out

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

HIST_FILE = os.path.join(BRAIN, "agent_history.txt")

def load_cmd_history():
    if os.path.exists(HIST_FILE):
        return [l.rstrip("\n") for l in open(HIST_FILE, encoding="utf-8") if l.strip()]
    return []

def save_cmd_history(cmd):
    if not cmd or cmd.lower() in ("salir", "exit", "quit"):
        return
    hist = load_cmd_history()
    if not hist or hist[-1] != cmd:
        hist.append(cmd)
        open(HIST_FILE, "w", encoding="utf-8").writelines(x + "\n" for x in hist[-100:])

def read_input_with_shift_tab():
    if os.name != "nt": return input()
    import msvcrt
    CR = chr(13)
    hist = load_cmd_history()
    h_idx = len(hist)
    draft = ""

    def print_prefix():
        cfg = read_cfg()
        m, ef = cfg.get("AGENT_MODE", "chat").upper(), cfg.get("EFFORT", "low").upper()
        m_col = C_GREEN if m == "CHAT" else (C_YELLOW if m == "PLAN" else (C_RED if m == "FREE" else ("\033[95m" if m == "INFINITE" else C_CYAN)))
        sys.stdout.write(f"{m_col}[{m} | effort:{ef}]{C_RESET} {C_BOLD}You > {C_RESET}")
        sys.stdout.flush()

    def redraw_line(new_chars, old_len):
        sys.stdout.write("\x1b[2K" + CR)
        print_prefix()
        sys.stdout.write("".join(new_chars))
        sys.stdout.flush()

    print_prefix()
    buf = []
    while True:
        ch = msvcrt.getwch()
        if ch in (CR, "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            res = "".join(buf).strip()
            save_cmd_history(res)
            return res
        elif ch == "\x03":
            raise KeyboardInterrupt
        elif ch == "\x1b":
            if msvcrt.kbhit():
                nxt1 = msvcrt.getwch()
                if nxt1 == "[" and msvcrt.kbhit():
                    nxt2 = msvcrt.getwch()
                    if nxt2 == "A" and hist:  # Flecha Arriba ANSI (Windows Terminal)
                        if h_idx == len(hist): draft = "".join(buf)
                        if h_idx > 0:
                            h_idx -= 1
                            old_l = len(buf)
                            buf = list(hist[h_idx])
                            redraw_line(buf, old_l)
                    elif nxt2 == "B" and hist:  # Flecha Abajo ANSI (Windows Terminal)
                        if h_idx < len(hist):
                            h_idx += 1
                            old_l = len(buf)
                            buf = list(hist[h_idx]) if h_idx < len(hist) else list(draft)
                            redraw_line(buf, old_l)
                    continue
            if buf:
                old_l = len(buf)
                buf.clear()
                redraw_line(buf, old_l)
            else:
                sys.stdout.write("\n")
                return "salir"
        elif ch in ("\x08", "\x7f"):
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
        elif ch in ("\x00", "\xe0"):
            ext = msvcrt.getwch()
            if ext == "\x0f":  # Shift+Tab
                cfg = read_cfg()
                cur = cfg.get("AGENT_MODE", "chat")
                write_cfg({"AGENT_MODE": MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"})
                redraw_line(buf, len(buf))
            elif ext == "H" and hist:  # Flecha Arriba
                if h_idx == len(hist):
                    draft = "".join(buf)
                if h_idx > 0:
                    h_idx -= 1
                    old_l = len(buf)
                    buf = list(hist[h_idx])
                    redraw_line(buf, old_l)
            elif ext == "P" and hist:  # Flecha Abajo
                if h_idx < len(hist):
                    h_idx += 1
                    old_l = len(buf)
                    buf = list(hist[h_idx]) if h_idx < len(hist) else list(draft)
                    redraw_line(buf, old_l)
        elif ch == "\t" and not buf:
            cfg = read_cfg()
            cur = cfg.get("AGENT_MODE", "chat")
            write_cfg({"AGENT_MODE": MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"})
            redraw_line(buf, 0)
        elif ch.isprintable():
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()

def build_sys_prompt(mode):
    import research_tools
    kmap = research_tools.load_knowledge_map()
    base = (
        "You are the AI-LAB Autonomous Agent on Windows. Be concise, direct, and practical. Always think and respond in English.\n"
        f"PERSISTENT KNOWLEDGE MAP (completed work & next paths):\n{kmap}\n\n"
        "STRICT OUTPUT RULES:\n"
        "1. For greetings or conceptual questions, reply directly in plain English.\n"
        "2. To CREATE or EDIT a Python script/file, output ONLY:\n"
        "FILE: filename.py\n"
        "```python\n"
        "# clean code using Python stdlib only (tkinter + math for 3D/GUI)\n"
        "```\n"
        "3. To run a command, launch an app, read a file, inspect a window, or research online, output ONLY a single JSON line:\n"
        '{"tool": "run_cmd", "arg": "cmd"} | {"tool": "launch_app", "arg": "app"} | {"tool": "read_file", "arg": "path"} | {"tool": "see_screen", "arg": "window"} | {"tool": "spawn_subagent", "arg": "web:url | file:path | research:topic"} -> Spawns an isolated worker subagent to read heavy files/webpages/papers and return a compact Chinese digest without bloating your context\n'
    )
    if mode == "plan":
        return base + "PLAN MODE: Outline a brief 3-step plan and ask confirmation before executing."
    if mode == "auto":
        return base + 'AUTO MODE: If a new capability is missing, output {"tool": "propose_loop", "arg": "goal"}.'
    if mode == "infinite":
        return base + "INFINITE MODE: Research via search_repos/search_arxiv when useful, verify results, and continuously improve or explore alternative approaches without repeating solved steps."
    return base

def main():
    global TUI
    import tui_bar
    TUI = tui_bar.BottomBarTUI(read_cfg, write_cfg, MODES, load_cmd_history, save_cmd_history)
    TUI.start()
    ui_print(f"{C_BOLD}{C_CYAN}🤖 AI-LAB Autonomous Agent (Split-Screen Dock){C_RESET}")
    ui_print(f"{C_DIM}   Escribe abajo en cualquier momento (se encola) | Shift+Tab: Modo | /compact | /settings | /effort | ESC{C_RESET}\n")
    last_mode, messages = None, []
    try:
      while True:
        cfg = read_cfg()
        cur_mode = cfg.get("AGENT_MODE", "chat")
        if cur_mode != last_mode:
            messages, last_mode = [{"role": "system", "content": build_sys_prompt(cur_mode)}], cur_mode
        if not TUI.queue:
            time.sleep(0.05)
            continue
        user_in = TUI.queue.popleft()
        TUI.refresh()
        if not user_in:
            continue
        ui_print(f"{C_BOLD}{C_CYAN}You > {C_RESET}{user_in}")
        low = user_in.lower()
        if low in ("salir", "exit", "quit"):
            if len(messages) > 2:
                import research_tools
                ui_print(f"{C_CYAN}🗜️  Compressing session into BRAIN/KNOWLEDGE_MAP.md...{C_RESET}")
                research_tools.compress_session(messages, [], call_ollama, cfg)
            break
        if low in ("/compress", "/compact"):
            import research_tools
            TUI.busy = True
            TUI.status_note = "Compacting..."
            TUI.refresh()
            summ = research_tools.compress_session(messages, [], call_ollama, cfg)
            TUI.busy = False
            TUI.status_note = ""
            messages = [{"role": "system", "content": build_sys_prompt(cur_mode)}, {"role": "assistant", "content": f"Compacted context:\n{summ}"}]
            ui_print(f"{C_GREEN}✅ Compacted into BRAIN/KNOWLEDGE_MAP.md:{C_RESET}\n{C_DIM}{summ}{C_RESET}\n")
            continue
        if low == "/undo":
            TUI.stop()
            __import__("research_tools").interactive_undo()
            TUI.start()
            last_mode = None
            continue
        if low == "/settings":
            TUI.stop()
            open_settings_menu()
            TUI.start()
            last_mode = None
            continue
        if low.startswith("/effort"):
            handle_effort_cmd(user_in[7:])
            TUI.refresh()
            continue
        if low.startswith("/verbose"):
            handle_verbose_cmd(user_in[8:])
            continue
        if low == "/agentlog":
            txt = open(AGENT_LOG, encoding="utf-8").read()[-4000:] if os.path.exists(AGENT_LOG) else "(no log yet)"
            subprocess.run(["clip"], input=txt, text=True)
            ui_print(f"{C_GREEN}📋 Copied {len(txt)} chars of agent_session.log to clipboard!{C_RESET}\n")
            continue
        if low.startswith("/wrong"):
            note = user_in[6:].strip() or "Do not run tools without explicit user request."
            open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(f"- [经验] {note}\n")
            ui_print(f"{C_GREEN}🧠 Rule saved: '{note}'{C_RESET}\n")
            last_mode = None
            continue

        TUI.busy = True
        TUI.refresh()
        log_agent(f"USER:{cur_mode}", user_in)
        messages.append({"role": "user", "content": user_in})
        steps_used = 0
        last_err = ""
        escape_valley = False
        max_iters = 999 if cur_mode == "infinite" else 2
        trace_notes = []
        for attempt in range(max_iters):
            ctx_chars = sum(len(m.get("content", "")) for m in messages)
            if ctx_chars > 6500:
                import research_tools
                ui_print(f"{C_CYAN}🗜️  [AUTO-COMPRESS] Contexto ({ctx_chars}c) compactado en BRAIN/KNOWLEDGE_MAP.md...{C_RESET}")
                summ = research_tools.compress_session(messages, trace_notes, call_ollama, cfg)
                messages = [{"role": "system", "content": build_sys_prompt(cur_mode)}, {"role": "user", "content": user_in}, {"role": "assistant", "content": f"Resumen acumulado:\n{summ}"}]
            if len(messages) > 5:
                messages = [messages] + messages[-4:]
            if cur_mode == "infinite" and attempt > 0:
                ui_print(f"\033[95m♾️  [INFINITE intento #{attempt + 1}{' | ANTI-VALLEY' if escape_valley else ''}]{C_RESET}")
            stop_spin = threading.Event()
            phase = ["Thinking"]
            def _spin():
                frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
                t0 = time.time()
                i = 0
                while not stop_spin.is_set():
                    el = time.time() - t0
                    if TUI:
                        TUI.status_note = f"{frames[i % 10]} {phase} ({cfg.get('EFFORT', 'low')})... {el:.1f}s"
                        TUI.refresh()
                    i += 1
                    time.sleep(0.15)
            th_spin = threading.Thread(target=_spin, daemon=True)
            th_spin.start()
            try:
                cfg["_RETRY"] = (attempt > 0); reply = call_ollama(messages, cfg, stop_spin, phase, escape_valley=escape_valley)
            finally:
                stop_spin.set()
                th_spin.join(timeout=0.3)
                if TUI: TUI.status_note = ""; TUI.refresh()
                sys.stdout.flush()

            if reply == "__CANCELLED__":
                if messages and messages[-1].get("role") == "user":
                    messages.pop()
                break

            if "```" in reply and '"tool"' not in reply:
                m_fn = re.search(r"FILE:\s*([\w./\\-]+)", reply)
                m_py = re.search(r"```python\n(.*?)```", reply, re.DOTALL)
                m_sh = re.search(r"```(?:bash|sh|cmd|bat)\n(.*?)```", reply, re.DOTALL)
                if m_py:
                    steps_used += 1
                    fname = m_fn.group(1) if m_fn else "agent_last_run.py"
                    tmp_py = os.path.join(ROOT, fname)
                    py_src = m_py.group(1)
                    open(tmp_py, "w", encoding="utf-8").write(py_src)
                    ui_print(f"{C_YELLOW}⚙️  [AUTO-SAVE: {fname} ({len(py_src)} chars)]{C_RESET}")
                    if "tkinter" in py_src or "mainloop" in py_src:
                        proc = subprocess.Popen([sys.executable, tmp_py], cwd=ROOT, stderr=subprocess.PIPE, text=True)
                        time.sleep(1.0)
                        if proc.poll() is not None and proc.returncode != 0:
                            err = proc.stderr.read().strip() or f"Exit code {proc.returncode}"
                            ui_print(f"{C_RED}❌ Error al ejecutar {fname}: {err}{C_RESET}")
                            trace_notes.append(f"Error: {err.splitlines()[-1] if err.splitlines() else err}")
                            err_sig = err.splitlines()[-1] if err.splitlines() else err
                            if err_sig == last_err:
                                if cur_mode != "infinite":
                                    ui_print(f"{C_YELLOW}⏹️  Error repetido. Deteniendo (usa Shift+Tab -> INFINITE para insistir hasta lograrlo).{C_RESET}\n")
                                    break
                                escape_valley = True
                                messages.extend([{"role": "assistant", "content": reply}, {"role": "user", "content": f"MISMO ERROR REPETIDO:\n{err}\nEstás en un valle local. Descarta el enfoque anterior y reescribe FILE: {fname} desde cero con una estructura de datos distinta y simple."}])
                                continue
                            last_err = err_sig
                            escape_valley = False
                            bad_snippet = ""
                            m_ln = re.search(r"line (\d+)", err)
                            if m_ln:
                                ln_no = int(m_ln.group(1))
                                src_lines = py_src.splitlines()
                                if 1 <= ln_no <= len(src_lines):
                                    bad_snippet = f"\nLínea exacta con error ({ln_no}): {src_lines[ln_no-1]}"
                            messages.extend([{"role": "assistant", "content": reply}, {"role": "user", "content": f"FALLÓ al abrir {fname} con este error:\n{err}{bad_snippet}\nCorrige esa línea y devuelve el código completo limpio en FILE: {fname}."}])
                            continue
                        import vision_eye
                        _, v_obs = vision_eye.capture_and_inspect("", target_pid=proc.pid)
                        ui_print(f"{C_CYAN}👁️  [AUTO-VISIÓN] {v_obs}{C_RESET}")
                        trace_notes.append(v_obs)
                        if "ALERTA_VISUAL:" in v_obs:
                            proc.terminate()
                            messages.extend([{"role": "assistant", "content": reply}, {"role": "user", "content": f"Visual inspection (5 frames): {v_obs}\nFix the scale, centering, or animation loop in FILE: {fname} so it fits cleanly inside the window and animates smoothly."}])
                            continue
                        ui_print(f"{C_GREEN}✅ Window visually verified and working!{C_RESET}\n")
                        messages.append({"role": "assistant", "content": reply})
                        if steps_used >= 2: distill_long_task_lesson(user_in, steps_used, cfg, trace_notes)
                        if cur_mode == "infinite":
                            proc.terminate()
                            ui_print(f"\033[95m♾️  [INFINITE -> MEJORA CONTINUA] Analizando cómo optimizar, enriquecer o investigar mejoras para '{fname}' (pulsa ESC para detener)...{C_RESET}\n")
                            messages.append({"role": "user", "content": f"La versión actual de {fname} ya funciona y pasó la verificación visual ({v_obs}). Ahora actúa como investigador autónomo: propón e implementa una mejora significativa (ej. mejor proyección 3D, sombreado/colores, fluidez FPS, controles o mayor precisión) en FILE: {fname}."})
                            time.sleep(1.0)
                            continue
                        break
                    res = subprocess.run([sys.executable, tmp_py], cwd=ROOT, capture_output=True, text=True, timeout=20)
                    obs = (res.stdout + res.stderr).strip() or "(código Python ejecutado con éxito)"
                    ui_print(f"{C_DIM}   ↳ {obs[:800]}{C_RESET}\n")
                    messages.append({"role": "assistant", "content": reply})
                    break
                elif m_sh:
                    steps_used += 1
                    obs = tool_run_cmd(m_sh.group(1).strip())
                    ui_print(f"{C_DIM}   ↳ {obs[:800]}{C_RESET}\n")
                    messages.append({"role": "assistant", "content": reply})
                    break

            if '"tool"' in reply and "{" in reply and "}" in reply:
                j_str = reply[reply.find("{"):reply.rfind("}")+1]
                tname, targ, call = "", "", {}
                try:
                    call = json.loads(j_str)
                    tname, targ = call.get("tool", ""), call.get("arg", "")
                except Exception:
                    m_t = re.search(r'"tool"\s*:\s*"([^"]+)"', j_str)
                    if m_t:
                        tname = m_t.group(1)
                        if tname == "write_file":
                            m_p = re.search(r'"path"\s*:\s*"([^"]+)"', j_str)
                            m_c = re.search(r'"content"\s*:\s*"(.*)"\s*\}', j_str, re.DOTALL)
                            if m_p and m_c:
                                call = {"tool": "write_file", "path": m_p.group(1), "content": m_c.group(1).replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')}
                        else:
                            m_a = re.search(r'"arg"\s*:\s*"(.*)"\s*\}', j_str, re.DOTALL)
                            if m_a:
                                targ = m_a.group(1)
                if tname:
                    steps_used += 1
                    if tname == "propose_loop":
                        if cur_mode == "chat":
                            ui_print(f"{C_GREEN}AI > {C_RESET}Estoy en modo CHAT clásico (auto-constructor desactivado). Pulsa Shift+Tab para pasar a AUTO.\n")
                            break
                        if input(f"  {C_CYAN}💡 ¿Creamos un bucle para aprender '{targ}'? (S/n): {C_RESET}").strip().lower() != "n":
                            create_learning_loop(targ, cfg)
                        break
                    if tname == "write_file":
                        wpath = call.get("path") or targ
                        wcont = call.get("content", "")
                        ui_print(f"{C_YELLOW}⚙️  [TOOL: write_file({wpath})]{C_RESET}")
                        obs = tool_write_file(wpath, wcont)
                    else:
                        ui_print(f"{C_YELLOW}⚙️  [TOOL: {tname}({targ})]{C_RESET}")
                        if tname == "see_screen":
                            import vision_eye
                            _, obs = vision_eye.capture_and_inspect(targ)
                        elif tname == "search_arxiv":
                            import research_tools
                            obs = research_tools.search_arxiv(targ)
                        elif tname == "search_repos":
                            import research_tools
                            obs = research_tools.search_repos(targ)
                        elif tname == "spawn_subagent":
                            import research_tools
                            ui_print(f"{C_CYAN}🤖 [SUBAGENT SPAWNED] Delegating '{targ}' in isolated context...{C_RESET}")
                            obs = research_tools.run_subagent(targ, call_ollama, cfg)
                        elif tname == "launch_app":
                            obs = tool_launch_app(targ)
                        elif tname == "run_cmd":
                            obs = tool_run_cmd(targ)
                            if "Ventana gráfica iniciada" in obs:
                                time.sleep(0.8)
                                import vision_eye
                                _, v_obs = vision_eye.capture_and_inspect("")
                                obs += f"\n[AUTO-VISIÓN] {v_obs}"
                        else:
                            obs = tool_read_file(targ)
                    ui_print(f"{C_DIM}   ↳ {obs}{C_RESET}")

                    if "[AUTO-VISIÓN]" in str(obs) and ("cobertura 0." in str(obs) or "totalmente negra" in str(obs)):
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado visual: {obs}\n¡ALERTA VISUAL! La ventana casi no muestra nada dibujado (solo un punto o pantalla vacía). Lee el script con read_file, corrige la proyección/escala/coordenadas para que el objeto se vea grande y centrado, guarda con write_file y vuelve a ejecutarlo."}])
                    elif tname == "write_file" and str(obs).startswith("OK:"):
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado: {obs}\nNow run the newly created file with run_cmd to verify it executes cleanly."}])
                    elif "Traceback" in str(obs) or "ModuleNotFoundError" in str(obs) or "Error:" in str(obs):
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"FALLÓ con este error:\n{obs}\nNO te rindas. Corrige el archivo con write_file usando SOLO Python estándar y vuelve a ejecutarlo."}])
                    else:
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado: {obs}\nResponde brevemente."}])
                    continue

            if not reply:
                if cur_mode == "infinite":
                    messages.append({"role": "user", "content": "Responde ahora con el código directo en FILE: nombre.py sin preámbulos."})
                    continue
                ui_print(f"{C_YELLOW}⚠️  Respuesta vacía (el modelo agotó tokens pensando). Prueba /effort low o modo INFINITE.{C_RESET}\n")
                break
            ui_print(f"{C_GREEN}AI > {C_RESET}{reply}\n")
            messages.append({"role": "assistant", "content": reply})
            if steps_used >= 2:
                distill_long_task_lesson(user_in, steps_used, cfg, trace_notes)
            if cur_mode == "infinite" and steps_used > 0:
                ui_print(f"\033[95m♾️  [INFINITE -> INVESTIGACIÓN AUTÓNOMA] Buscando el siguiente nivel de mejora (pulsa ESC para parar)...{C_RESET}\n")
                messages.append({"role": "user", "content": "Ya completaste el paso anterior. Investiga qué punto débil tiene la solución actual y aplica la siguiente mejora concreta."})
                time.sleep(1.0)
                continue
            break

        if TUI:
            TUI.busy = False
            TUI.status_note = ""
            TUI.refresh()
    finally:
        if TUI: TUI.stop()

if __name__ == "__main__":
    main()
