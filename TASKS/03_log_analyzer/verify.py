import json, target
res = target.run("access_100k.log")
exp = json.load(open("baseline.json", encoding="utf-8"))
assert res == exp, f"Mismatch: {res} != {exp}"
print("PASS:", res)
