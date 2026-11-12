import re
from collections import Counter

def _compile_patterns():
    """封装正则编译，避免重复开销"""
    pattern_ip = re.compile(r"ip=([\d\.]+)")
    pattern_st = re.compile(r"status=(\d+)")
    return pattern_ip, pattern_st

def run(log_path):
    # 校验路径是否存在且可读
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            # 预编译正则表达式，仅在循环外执行一次
            pattern_ip, pattern_st = _compile_patterns()
            
            errors = {}
            
            for line in f:
                # 局部绑定方法，减少属性查找开销
                m_ip = pattern_ip.search(line)
                m_st = pattern_st.search(line)
                
                if m_ip and m_st:
                    status_code = int(m_st.group(1))
                    ip = m_ip.group(1)
                    
                    # 状态码校验与计数聚合
                    if status_code >= 400:
                        errors[ip] = errors.get(ip, 0) + 1
    except FileNotFoundError:
        return {}
    
    # 使用 Counter 进行高效排序
    top_errors = dict(Counter(errors).most_common(5))
    
    return top_errors

if __name__ == "__main__":
    run("access_100k.log")
