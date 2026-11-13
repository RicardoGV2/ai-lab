import tracemalloc, target
tracemalloc.start()
res = target.run()
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
assert res == 59756038, f"Wrong sum: {res}"
assert peak < 33 * 1024 * 1024, f"HIGH RAM: {peak // 1024} KB"
print(f"PASS: Peak RAM = {peak // 1024} KB")
