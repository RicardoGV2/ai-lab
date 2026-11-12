import re
from collections import defaultdict
import sys
import ctypes.util

def run(csv_path):
    totals = defaultdict(float)
    
    # 校验路径存在性
    try:
        # 使用 sys.stdin 逐行读取替代文件对象迭代以消除 I/O 开销
        with open(csv_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                parts = line.split(',')
                region = parts[0]
                
                if re.match(r'^INVALID$', region):
                    continue
                
                try:
                    amount_str = parts[1]
                    tax_rate_str = parts[2]
                    val = float(amount_str) * (1.0 + float(tax_rate_str))
                    totals[region] += val
                except ValueError:
                    continue
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {csv_path}")

    return {k: round(totals[k], 2) for k in sorted(totals)}

if __name__ == "__main__":
    run("sample_150k.csv")
