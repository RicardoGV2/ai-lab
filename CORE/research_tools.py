import os, re, html, json, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
KMAP_FILE = os.path.join(BRAIN, "KNOWLEDGE_MAP.md")
INFRA_FILE = os.path.join(BRAIN, "SYSTEM_IMPROVEMENTS.md")

def load_knowledge_map():
    if os.path.exists(KMAP_FILE):
        return open(KMAP_FILE, encoding="utf-8").read()[-2000:]
    return "(尚无历史知识图谱)"

def fetch_webpage(url, max_chars=8000):
    try:
        req = urllib.request.Request(url.strip(), headers={"User-Agent": "Mozilla/5.0 AI-LAB-Subagent/4.3"})
        raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
        txt = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        txt = re.sub(r"\s+", " ", txt).strip()
        return txt[:max_chars] if txt else "(Empty page)"
    except Exception as e:
        return f"Error web: {e}"

def search_arxiv(query, max_results=3):
    try:
        q = urllib.parse.quote(query)
        url = f"http://arxiv.org:{q}&start=0&max_results={max_results}"
        req = urllib.request.Request(url, headers={"User-Agent": "AI-LAB-Research/4.3"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=15).read())
        ns = {"a": "http://w3.org"}
        items = []
        for entry in root.findall("a:entry", ns):
            title = " ".join((entry.find("a:title", ns).text or "").split())
            summ = " ".join((entry.find("a:summary", ns).text or "").split())[:220]
            items.append(f"- {title}: {summ}...")
        return "\n".join(items) if items else f"No arXiv results for '{query}'."
    except Exception as e:
        return f"Error arXiv: {e}"

def search_repos(query, max_results=3):
    results = []
    q = urllib.parse.quote(query)
    for name, url, is_gl in [
        ("GitHub", f"https://github.com{q}&sort=stars&per_page={max_results}", False),
        ("GitLab", f"https://gitlab.com{q}&order_by=star_count&per_page={max_results}", True)
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-LAB-Research/4.3"})
            data = json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8"))
            items = data if is_gl else data.get("items", [])
            for r in items[:max_results]:
                fn = r.get("path_with_namespace") if is_gl else r.get("full_name")
                st = r.get("star_count") if is_gl else r.get("stargazers_count")
                u = r.get("web_url") if is_gl else r.get("html_url")
                desc = (r.get("description") or "")[:120]
                results.append(f"[{name}] {fn} (★{st}): {desc} | {u}")
        except Exception:
            pass
    return "\n".join(results) if results else f"No repos found for '{query}'."

def run_subagent(task_spec, call_ollama_fn, cfg):
    chunks = []
    for part in task_spec.split("|"):
        part = part.strip()
        if not part:
            continue
        kind, _, target = part.partition(":")
        kind, target = kind.strip().lower(), target.strip()
        if not target:
            kind, target = "research", part
        if kind == "web":
            if not target.startswith(("http://", "https://")):
                target = "https://" + target
            chunks.append(f"[WEB {target}]\n{fetch_webpage(target, max_chars=6000)}")
        elif kind == "file":
            fp = target if os.path.isabs(target) else os.path.join(ROOT, target)
            txt = open(fp, encoding="utf-8", errors="replace").read()[:9000] if os.path.exists(fp) else f"File not found: {target}"
            chunks.append(f"[FILE {target}]\n{txt}")
        else:
            chunks.append(f"[RESEARCH {target}]\nARXIV:\n{search_arxiv(target)}\n\nREPOS:\n{search_repos(target)}")

    raw_data = "\n\n".join(chunks)
    sub_prompt = (
        "You are an ephemeral AI-LAB Worker Subagent. Digest the raw data below into at most 5 ultra-dense Chinese bullet points "
        "(保留代码函数名/URL/关键参数为英文) so the Orchestrator gets pure signal with minimal tokens.\n\n"
        f"TASK: {task_spec}\nRAW DATA:\n{raw_data[:12000]}"
    )
    fast_cfg = {"MODEL": cfg.get("MODEL", "qwen3.5-pi"), "EFFORT": "low", "VERBOSE": "off"}
    digest = call_ollama_fn([{"role": "user", "content": sub_prompt}], fast_cfg).strip()
    return digest or raw_data[:600]

def compress_session(messages, trace_notes, call_ollama_fn, cfg):
    convo = [f"{m.get('role','user').upper()}: {m.get('content','')[:500]}" for m in messages[1:]]
    raw_log = "\n".join(convo[-12:]) + ("\nTRACES: " + " | ".join(trace_notes[-6:]) if trace_notes else "")
    if not raw_log.strip():
        return "Empty session."
    prev_map = load_knowledge_map()
    prompt = (
        "You are AI-LAB's Token-Dense Long-Term Memory Engine. Compress and merge this session with the previous map using ultra-dense Chinese "
        "(代码名/路径/命令保留英文) to save 40% tokens.\n"
        f"PREVIOUS MAP:\n{prev_map}\n\nRECENT SESSION:\n{raw_log}\n\n"
        "Output ONLY concise Markdown with these 3 exact headers:\n"
        "## ✅ 已完成与最佳路径 (Completed & Best Path)\n"
        "## ❌ 死胡同与避坑 (Dead Ends)\n"
        "## 🔭 待探索分支 (Alternative Paths)\n"
    )
    summary = call_ollama_fn([{"role": "user", "content": prompt}], {"MODEL": cfg.get("MODEL", "qwen3.5-pi"), "EFFORT": "low", "VERBOSE": "off"}).strip()
    if "## " in summary:
        open(KMAP_FILE, "w", encoding="utf-8").write(f"# AI-LAB 长期知识图谱 ({time.strftime('%Y-%m-%d %H:%M')})\n\n{summary}\n")
    return summary


def interactive_undo():
    import subprocess
    res = subprocess.run(["git", "log", "-n", "7", "--pretty=format:%h|%ad|%s", "--date=format:%m-%d %H:%M"],
                         cwd=ROOT, capture_output=True, text=True)
    commits = [l.split("|", 2) for l in res.stdout.strip().splitlines() if "|" in l]
    if len(commits) < 2:
        print("\033[93m⚠️  Aún no hay suficientes versiones guardadas. Usa /save para crear puntos de restauración.\033[0m")
        return
    print("\n\033[96m⏪ HISTORIAL DE VERSIONES (/undo - Restaurar Checkpoint):\033[0m")
    for idx, (h, dt, msg) in enumerate(commits):
        tag = " (ACTUAL)" if idx == 0 else ""
        print(f"  [{idx}] \033[1m{h}\033[0m ({dt}) - {msg}{tag}")
    ch = input("\n  Elige el número de versión a restaurar (o Enter para cancelar): ").strip()
    if not ch.isdigit() or int(ch) < 1 or int(ch) >= len(commits):
        print("  Cancelado.")
        return
    target_hash, target_dt, target_msg = commits[int(ch)]
    # Crear rama de respaldo antes de revertir por seguridad
    subprocess.run(["git", "branch", "-f", "safety_before_undo", "HEAD"], cwd=ROOT, capture_output=True)
    subprocess.run(["git", "reset", "--hard", target_hash], cwd=ROOT, capture_output=True)
    print(f"\033[92m✅ Restaurado a [{target_hash}] ({target_dt} - {target_msg})!\033[0m")
    print("\033[2m   (Respaldo de seguridad guardado en rama 'safety_before_undo')\033[0m\n")
