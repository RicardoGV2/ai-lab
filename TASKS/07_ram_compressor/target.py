import sys

def run():
    # 预计算标签到索引的映射，避免字典查找开销 (局部变量缓存)
    tag_to_idx = {f"node_{i%120}": i for i in range(120)}
    
    agg = {}
    # 使用 sys.intern 缓存字符串键以加速哈希计算
    interned_tags = [sys.intern(f"node_{i%120}") for i in range(120)]
    
    # 绑定局部变量，加速聚合循环
    for r in __builtins__['range'](120000):
        k = tag_to_idx[interned_tags[r % 120]]
        v = (r * 17) % 997
        agg[k] = agg.get(k, 0) + v
    
    return sum(agg.values())

if __name__ == "__main__":
    print(run())
