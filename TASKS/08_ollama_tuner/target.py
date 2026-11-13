import http.client, json, gc

def run():
    gc.collect()
    body = json.dumps({
        "model": "qwen3.5-pi",
        "messages": [{"role": "user", "content": "Reply with OK only."}],
        "stream": False,
        "think": False,
        "options": {"num_predict": 8, "num_ctx": 2048, "num_batch": 128, "temperature": 0.1}
    }).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=30)
    conn.request("POST", "/api/chat", body=body, headers={"Content-Type": "application/json"})
    data = json.loads(conn.getresponse().read().decode("utf-8"))
    conn.close()
    return len(data.get("message", {}).get("content", "")) > 0

if __name__ == "__main__":
    print(run())
