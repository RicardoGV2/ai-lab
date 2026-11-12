import http.client, json, sys, time, argparse
from datetime import datetime

p = argparse.ArgumentParser()
p.add_argument("role")
p.add_argument("model")
p.add_argument("host")
p.add_argument("port", type=int)
p.add_argument("num_predict", type=int)
p.add_argument("use_think")
args = p.parse_args()

prompt = sys.stdin.read()
body = json.dumps({
    "model": args.model,
    "messages": [{"role": "user", "content": prompt}],
    "stream": True,
    "think": args.use_think.lower() == "true",
    "options": {"num_predict": args.num_predict, "temperature": 0.25}
}).encode("utf-8")

t0 = time.time()
ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
conn = http.client.HTTPConnection(args.host, args.port, timeout=180)
conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
resp = conn.getresponse()

thinking, content = "", ""
for raw in resp:
    line = raw.decode("utf-8").strip()
    if not line: continue
    msg = json.loads(line).get("message", {})
    thinking += msg.get("thinking", "")
    content += msg.get("content", "")
    sys.stderr.write(f"\r  ⏱️ [{args.role}] {int(time.time()-t0)}s | out:{len(content)}c   ")
    sys.stderr.flush()

sys.stderr.write("\n")
conn.close()
dt = int(time.time() - t0)

with open("RUN.log", "a", encoding="utf-8") as f:
    f.write(f"\n--- [{args.role}] | {ts} | {dt}s ---\n")
    if thinking.strip():
        f.write(f"[THINKING]:\n{thinking.strip()}\n\n")
    f.write(f"[OUTPUT]:\n{content.strip()}\n")

print(content.strip())
