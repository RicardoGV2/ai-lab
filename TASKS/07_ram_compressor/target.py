def run():
    records = [{"id": i, "tag": f"node_{i%120}", "val": (i * 17) % 997} for i in range(120000)]
    agg = {}
    for r in records:
        k = r["tag"]
        agg[k] = agg.get(k, 0) + r["val"]
    return sum(agg.values())

if __name__ == "__main__":
    print(run())
