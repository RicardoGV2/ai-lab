import sys, os; sys.path.insert(0, os.path.expanduser('~/ai-lab/CORE')); import statusbar
import os, subprocess, http.client, json, sys

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
C_CYAN, C_GREEN, C_YELLOW, C_BOLD, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[1m", "\033[0m"

def load_cfg():
    cfg = {"MODEL_NAME": "qwen3.5-pi", "OLLAMA_HOST": "127.0.0.1", "OLLAMA_PORT": "11434"}
    p = os.path.join(BRAIN, "CONFIG.env")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def translate_to_spanish(text):
    cfg = load_cfg()
    prompt = f"Translate these technical engineering rules from Chinese to clear, concise Spanish bullet points. Do not add fluff:\n\n{text}"
    body = json.dumps({
        "model": cfg["MODEL_NAME"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": True, "think": False,
        "options": {"num_predict": 800, "temperature": 0.2}
    }).encode("utf-8")
    conn = http.client.HTTPConnection(cfg["OLLAMA_HOST"], int(cfg["OLLAMA_PORT"]), timeout=120)
    conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    print(f"\n{C_GREEN}🇪🇸 TRADUCCIÓN AL ESPAÑOL (Solo lectura - el archivo sigue comprimido en chino):{C_RESET}\n")
    for raw in resp:
        line = raw.decode("utf-8").strip()
        if not line: continue
        tok = json.loads(line).get("message", {}).get("content", "")
        sys.stdout.write(tok); sys.stdout.flush()
    print("\n")
    conn.close()

def show_brain():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{C_CYAN}{C_BOLD}================================================================================")
    print("  🧠 VISOR DE CONOCIMIENTO ACUMULADO (BRAIN/)")
    print(f"================================================================================{C_RESET}")

    print(f"\n{C_GREEN}📘 1. PRINCIPIOS DE INGENIERÍA Y OPTIMIZACIÓN (PRINCIPLES.md):{C_RESET}")
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read().strip()
    print(prin if prin else "  (Vacío)")

    print(f"\n{C_YELLOW}🔧 2. TRUCOS DE ENTORNO Y HERRAMIENTAS PC (TOOLS_MEMORY.md):{C_RESET}")
    tmem = open(os.path.join(BRAIN, "TOOLS_MEMORY.md"), encoding="utf-8").read().strip()
    print(tmem if tmem else "  (Sin trucos de entorno aún)")

    print(f"\n{C_CYAN}================================================================================{C_RESET}")
    statusbar.render_prompt_bar('BRAIN VIEWER')
    op = input(f"\n{C_YELLOW}[t] Traducir al Español | [c] Copiar | [Enter] Volver: {C_RESET}").strip().lower()
    if op == "t":
        translate_to_spanish(f"PRINCIPIOS:\n{prin}\n\nENTORNO:\n{tmem}")
        input("Pulsa Enter para volver...")
    elif op == "c":
        subprocess.run(["clip"], input=f"{prin}\n\n{tmem}".encode("utf-8"))
        print(f"{C_GREEN}✅ Cerebro copiado al portapapeles.{C_RESET}")
        input("Pulsa Enter...")

if __name__ == "__main__":
    show_brain()
