import re

def run(log_path):
    errors = {}
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            m_ip = re.search(r"ip=([\d\.]+)", line)
            m_st = re.search(r"status=(\d+)", line)
            if m_ip and m_st and int(m_st.group(1)) >= 400:
                ip = m_ip.group(1)
                errors[ip] = errors.get(ip, 0) + 1
    return dict(sorted(errors.items(), key=lambda x: (-x, x))[:5])

if __name__ == "__main__":
    run("access_100k.log")
