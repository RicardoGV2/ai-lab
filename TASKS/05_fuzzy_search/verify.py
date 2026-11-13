import json, target
res = target.run("vocab.txt", "queries.json")
exp = json.load(open("baseline.json", encoding="utf-8"))
assert res == exp, "Top-3 fuzzy results mismatch!"
print("PASS: 40/40 fuzzy queries exact match!")
