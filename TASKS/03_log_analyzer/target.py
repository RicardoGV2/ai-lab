import re
from io import BytesIO

def run(log_path):
    errors = {}
    with open(log_path, "rb") as f:
        # 预编译正则以复用编译对象，避免每次循环重新编译
        ip_pattern = re.compile(rb"ip=([\d\.]+)")
        status_pattern = re.compile(rb"status=(\d+)")
        
        for line in f:
            # 使用字节流进行单次遍历读取
            m_ip = ip_pattern.search(line)
            m_st = status_pattern.search(line)
            
            if m_ip and m_st:
                try:
                    status_code = int(m_st.group(1))
                    if status_code >= 400:
                        ip_addr = m_ip.group(1).decode('utf-8')
                        errors[ip_addr] = errors.get(ip_addr, 0) + 1
                except ValueError:
                    continue
    
    # 排序并返回前 5 个错误 IP
    sorted_errors = sorted(errors.items(), key=lambda x: (-x[1], x[0]))[:5]
    return dict(sorted_errors)

if __name__ == "__main__":
    run("access_100k.log")
