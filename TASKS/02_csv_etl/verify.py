import json, target
res = target.run("sample_150k.csv")
exp = json.load(open("baseline.json"))
assert res == exp, f"Mismatch: {res} != {exp}"
print("PASS:", res)
