import urllib.request, json, time
from concurrent.futures import ThreadPoolExecutor

def compute_chunk(arr):
    acc = 0
    for x in arr:
        for _ in range(180):
            x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        acc = (acc + x) & 0xFFFFFFFF
    return acc

def offload_chunk(idx, ch, bridge_url):
    try:
        req = urllib.request.Request(
            f"{bridge_url}/dispatch",
            data=json.dumps({"id": idx, "data": ch}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=0.6).read()
        deadline = time.perf_counter() + 1.2
        while time.perf_counter() < deadline:
            res = urllib.request.urlopen(f"{bridge_url}/result/{idx}", timeout=0.6)
            if res.status == 200:
                return json.loads(res.read().decode("utf-8")).get("acc", 0)
            time.sleep(0.01)
    except Exception:
        pass
    return compute_chunk(ch)

def run(bridge_url="http://127.0.0.1:8765"):
    chunks = [[(b * 1000 + i) for i in range(2500)] for b in range(8)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(offload_chunk, i, ch, bridge_url) if i < 4 else ex.submit(compute_chunk, ch)
                for i, ch in enumerate(chunks)]
        total = 0
        for f in futs:
            total = (total + f.result()) & 0xFFFFFFFF
    return total

if __name__ == "__main__":
    print(run())
