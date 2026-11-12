import re
from collections import defaultdict

def run(csv_path):
    totals = defaultdict(float)
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split(',')
            region = parts[0]
            amount_str = parts[1]
            tax_rate_str = parts[2]
            
            if re.match(r'^INVALID$', region):
                continue
            
            try:
                val = float(amount_str) * (1.0 + float(tax_rate_str))
                totals[region] += val
            except ValueError:
                continue
    
    return {k: round(totals[k], 2) for k in sorted(totals)}

if __name__ == "__main__":
    run("sample_150k.csv")
