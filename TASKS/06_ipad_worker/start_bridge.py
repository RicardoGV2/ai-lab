import http.server, socketserver, json, socket, threading, queue

jobs = queue.Queue()
results = {}
res_event = threading.Event()

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/":
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(open("worker.html", "rb").read())
        elif self.path == "/task":
            try:
                job = jobs.get_nowait()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(json.dumps(job).encode())
            except queue.Empty:
                self.send_response(204); self.end_headers()
    def do_POST(self):
        if self.path == "/dispatch":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            results.pop(body["id"], None)
            jobs.put(body)
            self.send_response(200); self.end_headers()
        elif self.path == "/result":
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            results[body["id"]] = body["acc"]
            self.send_response(200); self.end_headers()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try: s.connect(("8.8.8.8", 80)); ip = s.getsockname()
except: ip = "127.0.0.1"
finally: s.close()

print(f"\n📱 ABRE SAFARI EN TU IPAD Y ENTRA A:  http://{ip}:8765\n")
with socketserver.ThreadingTCPServer(("0.0.0.0", 8765), Handler) as httpd:
    httpd.serve_forever()
