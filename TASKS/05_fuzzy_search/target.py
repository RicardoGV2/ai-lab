import json

def edit_dist(a, b):
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, dp = dp, i
        for j, cb in enumerate(b, 1):
            temp = dp[j]
            dp[j] = prev if ca == cb else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[-1]

def run(vocab_path, queries_path):
    with open(vocab_path, "r", encoding="utf-8") as f:
        vocab = [line.strip() for line in f if line.strip()]
    with open(queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    results = {}
    for q in queries:
        scored = []
        for cand in vocab:
            scored.append((edit_dist(q, cand), cand))
        scored.sort()
        results[q] = [c for _, c in scored[:3]]
    return results

if __name__ == "__main__":
    run("vocab.txt", "queries.json")
