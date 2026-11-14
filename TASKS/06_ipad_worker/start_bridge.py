import http.server, socketserver, json, socket, queue, urllib.request

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    ip = next(iter(s.getsockname()))
except Exception:
    ip = "127.0.0.1"
finally:
    s.close()

try:
    urllib.request.urlopen("http://127.0.0", timeout=0.5)
    print(f"\n🟢 El puente con tu iPad YA está activo en: http://{ip}:8765")
    print("   👉 Abre esa URL en Safari de tu iPad y pulsa (1) -> 06_ipad_worker.\n")
    raise SystemExit(0)
except SystemExit:
    raise
except Exception:
    pass

jobs = queue.Queue()
results = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/":
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(open("worker.html", "rb").read())
        elif self.path == "/ping":
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
        elif self.path == "/task":
            try:
                job = jobs.get_nowait()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps(job).encode())
            except queue.Empty:
                self.send_response(204); self.end_headers()
        elif self.path.startswith("/result/"):
            jid = int(self.path.rpartition("/").__getitem__(2))
            if jid in results:
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps({"acc": results.pop(jid)}).encode())
            else:
                self.send_response(204); self.end_headers()
    def do_POST(self):
        if self.path == "/dispatch":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            results.pop(body.get("id"), None)
            jobs.put(body)
            self.send_response(200); self.end_headers()
        elif self.path == "/result":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            results.update({body.get("id"): body.get("acc")})
            self.send_response(200); self.end_headers()

try:
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", 8765), Handler) as httpd:
        print(f"\n📱 PUENTE LISTO: Abre Safari en tu iPad y entra a -> http://{ip}:8765\n")
        httpd.serve_forever()
except OSError:
    print(f"\n🟢 El puente con tu iPad YA está activo en: http://{ip}:8765")
    print("   👉 Si ya abriste Safari en el iPad, ve directo a (1) -> 06_ipad_worker.\n")
