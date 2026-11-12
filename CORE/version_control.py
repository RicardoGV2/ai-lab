import os, subprocess, datetime

ROOT = os.path.expanduser("~/ai-lab")
C_CYAN, C_GREEN, C_YELLOW, C_RED, C_BOLD, C_RESET = "\033[96m", "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[0m"

def create_snapshot(note=None):
    if not note:
        note = input(f"{C_YELLOW}📝 Descripción breve del cambio (ej. 'Blindaje stdin OK'): {C_RESET}").strip()
    if not note:
        note = "Checkpoint estable"
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    tag_id = datetime.datetime.now().strftime("snap-%Y%m%d-%H%M%S")

    # Detectar archivos modificados para el CHANGELOG
    status = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    changed = ", ".join([l.strip().split()[-1] for l in status.splitlines()]) if status else "Sin cambios nuevos"

    # Escribir entrada arriba en CHANGELOG.md
    clog_path = os.path.join(ROOT, "CHANGELOG.md")
    old_clog = open(clog_path, encoding="utf-8").read() if os.path.exists(clog_path) else "# 📜 AI-LAB CHANGELOG & BACKUPS\n\n"
    header = "# 📜 AI-LAB CHANGELOG & BACKUPS\n\n"
    body = old_clog.replace(header, "")
    entry = f"### 🏷️ `{tag_id}` — {ts}\n- **Nota:** {note}\n- **Archivos:** `{changed}`\n\n"
    open(clog_path, "w", encoding="utf-8").write(header + entry + body)

    subprocess.run(["git", "add", "BRAIN/", "CORE/", "TASKS/", "CHANGELOG.md"], cwd=ROOT)
    subprocess.run(["git", "commit", "-m", f"[{tag_id}] {note}"], cwd=ROOT)
    subprocess.run(["git", "tag", tag_id], cwd=ROOT)
    subprocess.run(["git", "push"], cwd=ROOT)
    subprocess.run(["git", "push", "--tags"], cwd=ROOT)
    print(f"{C_GREEN}✅ Backup '{tag_id}' guardado en CHANGELOG.md y subido a GitHub!{C_RESET}")

def selective_rollback():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{C_CYAN}{C_BOLD}================================================================================")
    print("  ⏪ GESTOR DE BACKUPS Y ROLLBACK SELECTIVO (Git Snapshots)")
    print(f"================================================================================{C_RESET}")
    log_res = subprocess.run(["git", "log", "-n", "12", "--pretty=format:%h|%ad|%s", "--date=format:%Y-%m-%d %H:%M"],
                             cwd=ROOT, capture_output=True, text=True)
    commits = [l.split("|", 2) for l in log_res.stdout.splitlines() if "|" in l]
    for idx, (h, dt, msg) in enumerate(commits, 1):
        print(f"  {C_GREEN}[{idx:>2}]{C_RESET} {C_YELLOW}{h}{C_RESET} ({dt}) -> {msg}")

    print(f"\n{C_CYAN}Opciones:{C_RESET}")
    print("  • Escribe el NÚMERO de versión para restaurar un archivo o carpeta puntual")
    print("  • Escribe 's' para crear un nuevo Backup + Changelog ahora mismo")
    print("  • Pulsa Enter para volver")
    sel = input(f"\n{C_YELLOW}Elige > {C_RESET}").strip().lower()
    if sel == "s":
        create_snapshot()
        input("Pulsa Enter...")
    elif sel.isdigit() and 1 <= int(sel) <= len(commits):
        target_hash, dt, msg = commits[int(sel) - 1]
        print(f"\n{C_CYAN}Versión elegida:{C_RESET} {target_hash} ({msg})")
        print("  [1] Solo CORE/engine.sh")
        print("  [2] Solo CORE/harness.py")
        print("  [3] Solo BRAIN/ (reglas aprendidas)")
        print("  [4] Toda la carpeta CORE/ (motor completo, conserva BRAIN/)")
        scope = input("¿Qué quieres restaurar? (1-4): ").strip()
        paths = {"1": "CORE/engine.sh", "2": "CORE/harness.py", "3": "BRAIN/", "4": "CORE/"}
        if scope in paths:
            target_path = paths[scope]
            subprocess.run(["git", "checkout", target_hash, "--", target_path], cwd=ROOT)
            print(f"{C_GREEN}✅ Restaurado '{target_path}' a la versión {target_hash}!{C_RESET}")
        input("Pulsa Enter...")

if __name__ == "__main__":
    selective_rollback()
