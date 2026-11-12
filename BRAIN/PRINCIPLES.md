# 通用工程原则 (UNIVERSAL_PRINCIPLES)
- [环境约束] 仅用 Python 标准库，严禁引入 pandas/numpy/numba 等第三方库或子进程。
- [文本解析] 严禁在循环中使用 `re.search` 或 `re.match`；结构化日志/CSV 必用 `'status=5' in line` 预过滤加 `line.split()` 切片提取。
- [I/O与循环] 接收路径时必用 `open()` 流式读取；将热点方法绑定局部变量（如 `get = dict.get`）减少属性查找。
- [系统调用] Windows 硬件查询优先用 `ctypes` 调用 Win32 API，严禁拉起 PowerShell。
- [算法核心] 大规模数据处理优先单次遍历、哈希聚合与字节流 (`rb`) 切片以降低内存分配开销。
