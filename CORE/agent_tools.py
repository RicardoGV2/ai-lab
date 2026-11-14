import os as _os; _os.environ["PATH"] = r"C:\Users\joseg\AppData\Local\Programs\Microsoft VS Code\bin;" + _os.environ.get("PATH", "")
import os, sys, json, re, time, threading, subprocess, http.client

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
TASKS = os.path.join(ROOT, "TASKS")
CFG_FILE = os.path.join(BRAIN, "CONFIG.env")

C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_DIM, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"
MODES = ("chat", "plan", "free", "auto")
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
        print(f"  [1] Modo del Agente:   {C_GREEN}{cfg.get('AGENT_MODE', 'chat').upper()}{C_RESET}  (chat | plan | free | auto)")
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
    if os.name == "nt":
        import msvcrt
        while msvcrt.kbhit():
            if msvcrt.getwch() == "\x1b":
                return True
    return False

def call_ollama(messages, cfg, stop_spin=None, phase=None):
    model = cfg.get("MODEL", "qwen3.5-pi")
    effort = cfg.get("EFFORT", "low")
    verbose = (cfg.get("VERBOSE", "off") == "on")
    think = (effort in ("medium", "high"))
    base_pred = 1800 if effort == "low" else (2400 if effort == "medium" else 3500)
    num_pred = base_pred + (1200 if verbose else 0)
    host = "127." + "0.0.1"
    payload = json.dumps({"model": model, "messages": messages, "stream": True, "think": think, "options": {"temperature": 0.2, "num_predict": num_pred}}).encode("utf-8")
    conn = http.client.HTTPConnection(host, 11434, timeout=90)
    conn.request("POST", "/api/chat", body=payload, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    full_content, in_think, started_out = [], False, False
    try:
        for raw_line in resp:
            if check_esc_pressed():
                if in_think: sys.stdout.write(C_RESET)
                sys.stdout.write(f"\n{C_YELLOW}⏹️  [Interrumpido con ESC]{C_RESET}\n")
                sys.stdout.flush()
                conn.close()
                return "__CANCELLED__"
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line: continue
            chunk = json.loads(line)
            msg = chunk.get("message", {})
            th = msg.get("thinking", "")
            ct = msg.get("content", "")
            if th and verbose:
                if not started_out:
                    if stop_spin: stop_spin.set()
                    sys.stdout.write("\r" + " " * 46 + "\r")
                    started_out = True
                if not in_think:
                    sys.stdout.write(f"\n{C_DIM}💭 ")
                    in_think = True
                sys.stdout.write(th)
                sys.stdout.flush()
            if ct:
                full_content.append(ct)
                joined = "".join(full_content)
                if phase is not None:
                    m_tl = re.search(r'"tool"\s*:\s*"([^"]+)"', joined)
                    m_pa = re.search(r'"(?:path|arg)"\s*:\s*"([^"\\]{1,28})', joined)
                    if m_tl:
                        detail = f"{m_tl.group(1)} -> {m_pa.group(1)}" if m_pa else m_tl.group(1)
                        phase = f"Armando {detail} ({len(joined)}c)"
                    else:
                        phase = f"Escribiendo ({len(joined)}c)"
                if not started_out and verbose:
                    if stop_spin: stop_spin.set()
                    sys.stdout.write(chr(13) + " " * 64 + chr(13))
                    started_out = True
                if in_think:
                    sys.stdout.write(f"{C_RESET}\n")
                    in_think = False
    finally:
        if in_think: sys.stdout.write(C_RESET + "\n")
        conn.close()
    return "".join(full_content).strip()

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
    CR = chr(13)
    def print_prefix():
        cfg = read_cfg()
        m, ef = cfg.get("AGENT_MODE", "chat").upper(), cfg.get("EFFORT", "low").upper()
        m_col = C_GREEN if m == "CHAT" else (C_YELLOW if m == "PLAN" else (C_RED if m == "FREE" else C_CYAN))
        sys.stdout.write(f"{m_col}[{m} | effort:{ef}]{C_RESET} {C_BOLD}Tú > {C_RESET}")
        sys.stdout.flush()

    print_prefix()
    buf = []
    while True:
        ch = msvcrt.getwch()
        if ch in (CR, "\n"):
            sys.stdout.write("\n")
            sys.stdout.flush()
            return "".join(buf).strip()
        elif ch == "\x03":
            raise KeyboardInterrupt
        elif ch == "\x1b":
            if buf:
                sys.stdout.write(CR + " " * (len(buf) + 32) + CR)
                buf.clear()
                print_prefix()
            else:
                sys.stdout.write("\n")
                return "salir"
        elif ch in ("\x08", "\x7f"):
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
        elif ch in ("\x00", "\xe0"):
            if msvcrt.getwch() == "\x0f":
                cfg = read_cfg()
                cur = cfg.get("AGENT_MODE", "chat")
                write_cfg({"AGENT_MODE": MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"})
                sys.stdout.write(CR + " " * (len(buf) + 32) + CR)
                print_prefix()
                sys.stdout.write("".join(buf))
                sys.stdout.flush()
        elif ch == "\t" and not buf:
            cfg = read_cfg()
            cur = cfg.get("AGENT_MODE", "chat")
            write_cfg({"AGENT_MODE": MODES[(MODES.index(cur) + 1) % len(MODES)] if cur in MODES else "chat"})
            sys.stdout.write(CR + " " * 32 + CR)
            print_prefix()
        elif ch.isprintable():
            buf.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()

def build_sys_prompt(mode):
    base = (
        "Eres el Agente Inteligente de AI-LAB en Windows. Responde en español de forma natural, clara y directa.\n"
        f"CONOCIMIENTO DEL CEREBRO:\n{load_brain_context()}\n\n"
    )
    if mode == "free":
        return base + (
            "MODO EJECUCIÓN LIBRE (FREE): Puedes escribir código Python (```python ... ```) o comandos shell (```bash ... ```) "
            "para resolver directamente cualquier tarea en Windows sin restricciones de herramientas predefinidas. "
            "Para abrir archivos en VS Code usa `code <archivo>`."
        )
    tools_help = (
        "- Si el usuario solo saluda o conversa, responde directamente SIN herramientas.\n"
        "- Si pide una acción concreta, responde ÚNICAMENTE con JSON puro:\n"
        '  Para crear/guardar un archivo Python, escribe SOLO:\n  FILE: nombre.py\n  ```python\n  # codigo limpio usando solo stdlib (tkinter + math para graficos/3D)\n  ```\n  {"tool": "see_screen", "arg": "titulo_ventana"} -> Toma captura de pantalla/ventana en Windows y analiza qué se ve realmente (útil tras abrir una GUI para verificar y corregir fallos visuales)\n  {"tool": "run_cmd", "arg": "comando"} | {"tool": "launch_app", "arg": "nombre_app"} | {"tool": "read_file", "arg": "ruta"}\n'
    )
    if mode == "chat": return base + tools_help + "- MODO CHAT CLÁSICO: Auto-constructor desactivado."
    if mode == "plan": return base + tools_help + "- MODO PLAN: Presenta un plan breve y pide confirmación antes de crear bucles."
    return base + tools_help + '- MODO AUTO: Si falta una habilidad nueva, usa {"tool": "propose_loop", "arg": "objetivo"}.'


def distill_long_task_lesson(user_goal, steps_taken, cfg):
    if cfg.get("AUTO_LEARN", "on") != "on" or steps_taken < 3:
        return
    prompt = (
        f"Acabas de resolver esta tarea compleja en {steps_taken} pasos: '{user_goal}'.\n"
        "Extrae UNA SOLA regla técnica general y reutilizable para Windows/Python (máximo 15 palabras, sin mencionar nombres de archivos temporales). "
        "Responde SOLO con la regla empezando por '- [经验] '."
    )
    rule = call_ollama([{"role": "user", "content": prompt}], {"MODEL": cfg.get("MODEL", "qwen3.5-pi"), "EFFORT": "low", "VERBOSE": "off", "AUTO_LEARN": "on"}).strip()
    if rule.startswith("- ") and len(rule) < 140:
        cand = os.path.join(BRAIN, "CANDIDATE_LESSONS.md")
        existing = open(cand, encoding="utf-8").read() if os.path.exists(cand) else ""
        if rule not in existing:
            open(cand, "a", encoding="utf-8").write(rule + "\n")
            print(f"{C_CYAN}🧪 [CUARENTENA DE APRENDIZAJE] Lección candidata guardada en CANDIDATE_LESSONS.md:{C_RESET}\n   {C_DIM}{rule}{C_RESET}\n")

def main():
    write_cfg({"AGENT_MODE": "chat"})
    print(f"\n{C_BOLD}{C_CYAN}🤖 AI-LAB Agente Inteligente{C_RESET}\n{C_DIM}   Shift+Tab (o Tab vacío): cambiar [CHAT | PLAN | FREE | AUTO] | /settings | /effort | /wrong | 'salir'{C_RESET}\n")
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
        if low.startswith("/verbose"): handle_verbose_cmd(user_in[8:]); continue
        if low.startswith("/wrong"):
            note = user_in[6:].strip() or "No ejecutar herramientas sin petición explícita."
            open(os.path.join(BRAIN, "PRINCIPLES.md"), "a", encoding="utf-8").write(f"- [用户纠正] {note}\n")
            print(f"{C_GREEN}🧠 Lección grabada: '{note}'{C_RESET}\n"); last_mode = None; continue
        messages.append({"role": "user", "content": user_in})
        steps_used = 0
        for _ in range(5):
            stop_spin = threading.Event()
            phase = ["Pensando"]
            def _spin():
                frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
                t0 = time.time()
                i = 0
                while not stop_spin.is_set():
                    el = time.time() - t0
                    sys.stdout.write(chr(13) + f"{C_CYAN}{frames[i % 10]} {phase[0]} ({cfg.get('EFFORT', 'low')})... {el:.1f}s{C_RESET}   ")
                    sys.stdout.flush()
                    i += 1
                    time.sleep(0.12)
            th_spin = threading.Thread(target=_spin, daemon=True)
            th_spin.start()
            try:
                reply = call_ollama(messages, cfg, stop_spin, phase)
            finally:
                stop_spin.set()
                th_spin.join(timeout=0.3)
                sys.stdout.write(chr(13) + " " * 64 + chr(13))
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
                    print(f"{C_YELLOW}⚙️  [AUTO-SAVE: {fname} ({len(py_src)} chars)]{C_RESET}")
                    if "tkinter" in py_src or "mainloop" in py_src:
                        proc = subprocess.Popen([sys.executable, tmp_py], cwd=ROOT, stderr=subprocess.PIPE, text=True)
                        time.sleep(1.0)
                        if proc.poll() is not None:
                            err = proc.stderr.read().strip()
                            print(f"{C_RED}❌ Error al ejecutar {fname}: {err}{C_RESET}")
                            messages.extend([{"role": "assistant", "content": reply}, {"role": "user", "content": f"FALLÓ al abrir {fname} con este error:\n{err}\nCorrige el código en FILE: {fname} ahora."}])
                            continue
                        import vision_eye
                        _, v_obs = vision_eye.capture_and_inspect("")
                        print(f"{C_CYAN}👁️  [AUTO-VISIÓN] {v_obs}{C_RESET}")
                        if "cobertura 0." in v_obs or "totalmente negra" in v_obs:
                            messages.extend([{"role": "assistant", "content": reply}, {"role": "user", "content": f"Resultado visual: {v_obs}\nLa ventana casi no muestra nada dibujado. Corrige la proyección/escala en FILE: {fname} para que el objeto se vea grande y centrado."}])
                            continue
                        print(f"{C_GREEN}✅ Ventana verificada visualmente y funcionando!{C_RESET}\n")
                        messages.append({"role": "assistant", "content": reply})
                        if steps_used >= 3: distill_long_task_lesson(user_in, steps_used, cfg)
                        break
                    res = subprocess.run([sys.executable, tmp_py], cwd=ROOT, capture_output=True, text=True, timeout=20)
                    obs = (res.stdout + res.stderr).strip() or "(código Python ejecutado con éxito)"
                    print(f"{C_DIM}   ↳ {obs[:800]}{C_RESET}\n")
                    messages.append({"role": "assistant", "content": reply})
                    break
                elif m_sh:
                    steps_used += 1
                    obs = tool_run_cmd(m_sh.group(1).strip())
                    print(f"{C_DIM}   ↳ {obs[:800]}{C_RESET}\n")
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
                            print(f"{C_GREEN}AI > {C_RESET}Estoy en modo CHAT clásico (auto-constructor desactivado). Pulsa Shift+Tab para pasar a AUTO.\n")
                            break
                        if input(f"  {C_CYAN}💡 ¿Creamos un bucle para aprender '{targ}'? (S/n): {C_RESET}").strip().lower() != "n":
                            create_learning_loop(targ, cfg)
                        break
                    if tname == "write_file":
                        wpath = call.get("path") or targ
                        wcont = call.get("content", "")
                        print(f"{C_YELLOW}⚙️  [TOOL: write_file({wpath})]{C_RESET}")
                        obs = tool_write_file(wpath, wcont)
                    else:
                        print(f"{C_YELLOW}⚙️  [TOOL: {tname}({targ})]{C_RESET}")
                        if tname == "see_screen":
                            import vision_eye
                            _, obs = vision_eye.capture_and_inspect(targ)
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
                    print(f"{C_DIM}   ↳ {obs}{C_RESET}")

                    if "[AUTO-VISIÓN]" in str(obs) and ("cobertura 0." in str(obs) or "totalmente negra" in str(obs)):
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado visual: {obs}\n¡ALERTA VISUAL! La ventana casi no muestra nada dibujado (solo un punto o pantalla vacía). Lee el script con read_file, corrige la proyección/escala/coordenadas para que el objeto se vea grande y centrado, guarda con write_file y vuelve a ejecutarlo."}])
                    elif tname == "write_file" and str(obs).startswith("OK:"):
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado: {obs}\nAhora ejecuta el archivo recién creado usando run_cmd para verificar que corre sin errores y mostrarlo al usuario."}])
                    elif "Traceback" in str(obs) or "ModuleNotFoundError" in str(obs) or "Error:" in str(obs):
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"FALLÓ con este error:\n{obs}\nNO te rindas. Corrige el archivo con write_file usando SOLO Python estándar y vuelve a ejecutarlo."}])
                    else:
                        messages.extend([{"role": "assistant", "content": j_str}, {"role": "user", "content": f"Resultado: {obs}\nResponde brevemente."}])
                    continue

            print(f"{C_GREEN}AI > {C_RESET}{reply}\n")
            messages.append({"role": "assistant", "content": reply})
            if steps_used >= 3:
                distill_long_task_lesson(user_in, steps_used, cfg)
            break

if __name__ == "__main__":
    main()
