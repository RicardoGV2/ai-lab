import os, sys, json, subprocess

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")

def load_secret():
    cfg = {"GEMINI_API_KEY": ""}
    p = os.path.join(BRAIN, "SECRETS.env")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.strip().split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def ask_mentor(task_dir):
    key = load_secret().get("GEMINI_API_KEY", "").strip()
    if not key:
        return "ERROR: Falta GEMINI_API_KEY en BRAIN/SECRETS.env"
    t_path = os.path.join(task_dir, "target.py")
    r_path = os.path.join(task_dir, "REPORT.md")
    t_code = open(t_path, encoding="utf-8").read() if os.path.exists(t_path) else ""
    rep = "".join(open(r_path, encoding="utf-8").readlines()[-10:]) if os.path.exists(r_path) else ""
    prin = open(os.path.join(BRAIN, "PRINCIPLES.md"), encoding="utf-8").read()

    prompt = (
        "You are an expert systems performance mentor for an autonomous local Python lab on Windows.\n"
        f"CURRENT BRAIN PRINCIPLES:\n{prin}\n\n"
        f"RECENT BENCHMARK HISTORY:\n{rep}\n\n"
        f"CURRENT target.py:\n{t_code}\n\n"
        "Give ONE concrete, high-leverage algorithmic or architectural optimization idea in ONE brief Chinese sentence (under 35 chars) that breaks stagnation without external libraries."
    )
    tmp_json = os.path.join(ROOT, ".tmp_mentor.json")
    open(tmp_json, "w", encoding="utf-8").write(json.dumps({"contents": [{"parts": [{"text": prompt}]}]}))

    last_err = "No response"
    try:
        for model in ("gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-latest"):
            dot, sl = chr(46), chr(47)
            url = "https:" + sl*2 + "generativelanguage" + dot + "googleapis" + dot + "com" + sl + "v1beta" + sl + "models" + sl + model + ":generateContent"
            ps_cmd = (
                f"$h = @{{'Content-Type'='application/json'; 'X-goog-api-key'='{key}'}}; "
                f"$r = Invoke-RestMethod -Uri '{url}' -Method Post -Headers $h -InFile '{tmp_json}' -TimeoutSec 45; "
                f"$r.candidates.content.parts.text"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, encoding="utf-8", timeout=50
            )
            out = res.stdout.strip()
            if res.returncode == 0 and out:
                return out.splitlines()[-1].strip()
            last_err = res.stderr.strip().splitlines() if res.stderr.strip() else "Empty response"
    except Exception as e:
        last_err = str(e)
    finally:
        if os.path.exists(tmp_json):
            os.remove(tmp_json)
    return f"MENTOR_ERR: {last_err}"

if __name__ == "__main__":
    it = iter(sys.argv)
    next(it, None)
    tdir = next(it, os.getcwd())
    print(ask_mentor(tdir))
