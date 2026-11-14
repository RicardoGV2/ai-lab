import target
res = target.run()
assert res["after_mb"] > 450, f"RAM libre demasiado baja: {res['after_mb']} MB"
print(f"PASS: Free RAM = {res['after_mb']} MB (+{res['freed_mb']}MB | cerrados={res['closed']}, comprimidos={res['trimmed']})")
