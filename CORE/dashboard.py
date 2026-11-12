import os, re, subprocess, ctypes
from collections import defaultdict

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
TASKS = os.path.join(ROOT, "TASKS")
C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[0m"

def get_ram_status():
    try:
        class MEMSTAT(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = MEMSTAT()
        s.dwLength = ctypes.sizeof(MEMSTAT)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        used_gb = (s.ullTotalPhys - s.ullAvailPhys) / (1024**3)
        tot_gb = s.ullTotalPhys / (1024**3)
        return f"{used_gb:.1f}/{tot_gb:.1f} GB ({s.dwMemoryLoad}%)"
    except Exception:
        return "N/A"

def load_cfg():
    cfg = {"MODEL_NAME": "qwen3.5-pi", "NUM_PREDICT": "900"}
    p = os.path.join(BRAIN, "CONFIG.env")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def parse_llm_timings():
    role_times = defaultdict(list)
    for tname in os.listdir(TASKS):
        log_p = os.path.join(TASKS, tname, "RUN.log")
        if not os.path.exists(log_p): continue
        for line in open(log_p, encoding="utf-8", errors="ignore"):
            m = re.search(r"--- \[(\w+)\] \| .*? \| (\d+)s ---", line)
            if m:
                role, secs = m.groups()
                role_times[role].append(int(secs))
    return role_times

def build_dashboard_text():
    cfg = load_cfg()
    ram_str = get_ram_status()
    lines = [
        "================================================================================",
        "  📊 AI-LAB SUPERVISOR TELEMETRY v4.0 (Zero-Overhead Snapshot)",
        "================================================================================",
        f"  🤖 Motor Activo : {cfg.get('MODEL_NAME')} (max_tokens: {cfg.get('NUM_PREDICT')}) | 💾 RAM PC: {ram_str}"
    ]

    tot_cycles = tot_kept = tot_slower = tot_err = tot_arxiv = 0
    model_stats = defaultdict(lambda: {"kept": 0, "total": 0})
    task_blocks = []

    for tname in sorted(os.listdir(TASKS)):
        rep_path = os.path.join(TASKS, tname, "REPORT.md")
        if not os.path.exists(rep_path): continue
        cur_model = cfg.get("MODEL_NAME")
        kept = slower = err = learned = 0
        timeline = []
        for row in open(rep_path, encoding="utf-8"):
            mm = re.search(r"\*\*Motor:\*\*\s*`([^`]+)`", row)
            if mm: cur_model = mm.group(1)
            if not row.startswith("| #"): continue
            parts = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(parts) < 7: continue
            ciclo, hora, modo, accion, before, after, status = parts[:7]
            if "KEPT" in status:
                kept += 1; model_stats[cur_model]["kept"] += 1; model_stats[cur_model]["total"] += 1
            elif "SLOWER" in status:
                slower += 1; model_stats[cur_model]["total"] += 1
            elif "ERROR" in status:
                err += 1; model_stats[cur_model]["total"] += 1
            elif "LEARNED" in status:
                learned += 1
            mb = re.search(r"(\d+)ms", before)
            ma = re.search(r"(\d+)ms", after)
            if not timeline and mb:
                timeline.append(("Base", int(mb.group(1)), "BASE"))
            if ma:
                tag = "KEPT" if "KEPT" in status else ("ERR" if "ERROR" in status else "SLOW")
                timeline.append((ciclo, int(ma.group(1)), tag))

        cycles = kept + slower + err
        tot_cycles += cycles; tot_kept += kept; tot_slower += slower; tot_err += err; tot_arxiv += learned
        hit_rate = (kept / cycles * 100) if cycles > 0 else 0.0

        b = [f"\n  📁 Tarea: {tname} ({cycles} ciclos | Hit Rate: {hit_rate:.1f}%)"]
        b.append(f"     ✅ Kept: {kept} | ➖ Slower: {slower} | ❌ Err: {err} | 📚 arXiv: {learned}")
        if timeline:
            max_ms = max(ms for _, ms, _ in timeline) or 1
            _, first_ms, _ = next(iter(timeline))
            valid_ms = [ms for _, ms, t in timeline if t in ("BASE", "KEPT")]
            best_ms = min(valid_ms) if valid_ms else first_ms
            gain = ((best_ms - first_ms) / first_ms) * 100
            b.append(f"     ⚡ Velocidad: {first_ms}ms (Base) -> {best_ms}ms (Récord) [{gain:+.1f}%] | Ahorro: {first_ms - best_ms}ms/run")
            for lbl, ms, tag in timeline[-7:]:
                bar = "█" * max(1, int((ms / max_ms) * 28))
                b.append(f"     {lbl:<5} | {bar:<28} {ms:>4}ms ({tag})")
        task_blocks.extend(b)

    global_hit = (tot_kept / tot_cycles * 100) if tot_cycles > 0 else 0.0
    lines.append(f"\n🏆 RESUMEN HISTÓRICO Y COMPARATIVA DE MODELOS:")
    lines.append(f"  • Ciclos Totales : {tot_cycles} ejecuciones ({tot_kept} mejoras | {tot_slower} lentas | {tot_err} errores)")
    lines.append(f"  • Eficiencia     : Hit Rate Global {global_hit:.1f}% | Investigaciones arXiv: {tot_arxiv}")
    for m_name, st in model_stats.items():
        m_hit = (st["kept"] / st["total"] * 100) if st["total"] > 0 else 0.0
        lines.append(f"  • Modelo [{m_name}]: {st['kept']}/{st['total']} mejoras ({m_hit:.1f}% éxito)")

    timings = parse_llm_timings()
    lines.append(f"\n⏱️ LATENCIA DEL LLM POR ROL (RUN.log):")
    if timings:
        for role, vals in sorted(timings.items()):
            avg_s = sum(vals) / len(vals)
            lines.append(f"  • {role:<14} : {avg_s:>5.1f}s media ({len(vals)}x | min {min(vals)}s / max {max(vals)}s)")
    else:
        lines.append("  • Sin datos de latencia registrados aún.")

    prin_txt = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read()
    tmem_txt = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read()
    prin_l = [l.strip() for l in prin_txt.splitlines() if l.strip().startswith("-")]
    tmem_l = [l.strip() for l in tmem_txt.splitlines() if l.strip().startswith("-")]
    tot_chars = len(prin_txt) + len(tmem_txt)
    est_tokens = int(tot_chars / 2.5)
    health = "🟢 ÓPTIMO" if est_tokens < 1200 else ("🟡 COMPACTAR PRONTO" if est_tokens < 2200 else "🔴 PODAR MEMORIA")

    lines.append(f"\n🧠 SALUD DEL CEREBRO Y HERRAMIENTAS (5 módulos):")
    lines.append(f"  • Carga Contexto : {tot_chars} chars (~{est_tokens} tokens) -> Estado: {health}")
    lines.append(f"  • Inventario     : {len(prin_l)} principios + {len(tmem_l)} trucos PC | Tools: RUN, ARXIV, LEARN, MS, GIT")
    if prin_l:
        lines.append(f"  • Último Saber   : {next(iter(reversed(prin_l)))[:66]}...")
    if tmem_l:
        lines.append(f"  • Último Entorno : {next(iter(reversed(tmem_l)))[:66]}...")

    lines.append("\n📈 EVOLUCIÓN POR TAREA:")
    lines.extend(task_blocks)
    lines.append("\n================================================================================")
    return "\n".join(lines)

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    try:
        txt = build_dashboard_text()
        print(txt)
    except Exception as e:
        txt = f"Error generando dashboard: {e}"
        print(txt)
    op = input(f"\n{C_YELLOW}[c] Copiar Dashboard | [Enter] Volver | [comando UCRT64] Ejecutar: {C_RESET}").strip()
    if op.lower() == "c":
        subprocess.run(["clip"], input=txt.encode("utf-8"))
        print(f"{C_GREEN}✅ Dashboard copiado al portapapeles.{C_RESET}")
        input("Pulsa Enter...")
    elif op:
        subprocess.run(["bash", "-c", op], cwd=ROOT)
        input("Pulsa Enter...")
