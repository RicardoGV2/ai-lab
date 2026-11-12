# 通用工程原则 (UNIVERSAL_PRINCIPLES)
- [环境约束] 仅用 Python 标准库，严禁引入 pandas/numpy/numba 等第三方库或子进程。
- [I/O与解析] 接收文件路径参数时必须用 `open()` 流式读取，严禁改用 `sys.stdin`；优先 `line.split(',')` 替代 `csv.DictReader`。
- [循环加速] 将热点方法绑定到局部变量（如 `get = dict.get`），避免循环内重复属性查找与正则编译。
- [系统调用] Windows 硬件查询优先用 `ctypes` 调用 Win32 API，严禁拉起 PowerShell。
- [算法核心] 大规模数据处理优先单次遍历、哈希聚合与切片索引以降低内存分配开销。
- [校验规范] 调用系统工具前增加参数与路径校验层，避免重复无效尝试。
