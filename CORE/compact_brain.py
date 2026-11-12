import os, http.client, json

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")

def load_cfg():
    cfg = {"MODEL_NAME": "qwen3.5-pi", "OLLAMA_HOST": "127.0.0.1", "OLLAMA_PORT": "11434"}
    p = os.path.join(BRAIN, "CONFIG.env")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def ask_compact(title, raw_text, max_rules=6):
    cfg = load_cfg()
    prompt = (
        f"You are a memory compressor for an AI agent. Deduplicate and merge these {title} into at most {max_rules} "
        f"ultra-concise Chinese bullet points (each starting with '- [类别] ', under 30 Chinese chars). "
        f"Keep ONLY unique, high-value engineering rules. Output ONLY the bullet points:\n\n{raw_text}"
    )
    body = json.dumps({
        "model": cfg["MODEL_NAME"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False, "think": False,
        "options": {"num_predict": 400, "temperature": 0.1}
    }).encode("utf-8")
    conn = http.client.HTTPConnection(cfg["OLLAMA_HOST"], int(cfg["OLLAMA_PORT"]), timeout=120)
    conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
    res = json.loads(conn.getresponse().read().decode("utf-8"))["message"]["content"].strip()
    conn.close()
    clean = [l.strip() for l in res.splitlines() if l.strip().startswith("-")]
    return "\n".join(clean[:max_rules])

def run_compaction():
    p_path = os.path.join(BRAIN, "PRINCIPLES.md")
    t_path = os.path.join(BRAIN, "TOOLS_MEMORY.md")

    p_raw = open(p_path, encoding="utf-8").read()
    t_raw = open(t_path, encoding="utf-8").read()

    p_lines = [l for l in p_raw.splitlines() if l.strip().startswith("-")]
    t_lines = [l for l in t_raw.splitlines() if l.strip().startswith("-")]

    if len(p_lines) > 6:
        comp_p = ask_compact("engineering principles", p_raw, 6)
        if comp_p:
            open(p_path, "w", encoding="utf-8").write(f"# 通用工程原则 (UNIVERSAL_PRINCIPLES)\n{comp_p}\n")
            print(f"🧹 PRINCIPLES.md compactado: {len(p_lines)} -> {len(comp_p.splitlines())} reglas.")

    if len(t_lines) > 4:
        comp_t = ask_compact("OS/tool environment tricks", t_raw, 4)
        if comp_t:
            open(t_path, "w", encoding="utf-8").write(f"# 环境与工具记忆 (TOOLS_MEMORY)\n{comp_t}\n")
            print(f"🧹 TOOLS_MEMORY.md compactado: {len(t_lines)} -> {len(comp_t.splitlines())} reglas.")

    if len(p_lines) <= 6 and len(t_lines) <= 4:
        print("✨ El cerebro ya está compacto y óptimo (sin exceso de reglas).")

if __name__ == "__main__":
    run_compaction()
