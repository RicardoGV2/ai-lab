import urllib.request, json, time

# Estrategia inicial: procesa los 8 lotes secuencialmente en la CPU de la PC
# El bucle evolutivo debe aprender a repartir lotes al iPad (/dispatch) y procesar el resto en paralelo
def compute_chunk(arr):
    acc = 0
    for x in arr:
        for _ in range(180):
            x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        acc = (acc + x) & 0xFFFFFFFF
    return acc

def run(bridge_url="http://127.0.0.1:8765"):
    chunks = [[(b * 1000 + i) for i in range(2500)] for b in range(8)]
    total = 0
    for idx, ch in enumerate(chunks):
        total = (total + compute_chunk(ch)) & 0xFFFFFFFF
    return total

if __name__ == "__main__":
    print(run())
