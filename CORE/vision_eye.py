import os, sys, time, zlib, struct, ctypes
from ctypes import wintypes

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def _find_window_by_pid_or_title(target_pid=0, title_hint=""):
    found = None
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    q = title_hint.lower()

    def cb(hwnd, lparam):
        nonlocal found
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w < 80 or h < 80:
            return True
        if target_pid and pid.value == target_pid:
            found = (rect.left, rect.top, w, h, title or f"PID:{target_pid}")
            return False
        if not target_pid and q and q in title.lower():
            found = (rect.left, rect.top, w, h, title)
            return False
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if found:
        return found
    return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1), "FullScreen")

def _grab_rect(x, y, w, h):
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc_mem, hbmp)
    gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = w, -h, 1, 24
    row_padded = (w * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(row_padded * h)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    rgb = bytearray(w * h * 3)
    raw = buf.raw
    for row in range(h):
        src_off, dst_off = row * row_padded, row * w * 3
        for col in range(w):
            rgb[dst_off + col * 3] = raw[src_off + col * 3 + 2]
            rgb[dst_off + col * 3 + 1] = raw[src_off + col * 3 + 1]
            rgb[dst_off + col * 3 + 2] = raw[src_off + col * 3]
    return bytes(rgb)

def _write_png(path, w, h, rgb_bytes):
    raw_rows = bytearray()
    stride = w * 3
    for y in range(h):
        raw_rows.append(0)
        raw_rows.extend(rgb_bytes[y * stride:(y + 1) * stride])
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw_rows), 6)) + chunk(b"IEND", b""))

def capture_and_inspect(title_hint="", target_pid=0):
    x, y, w, h, win_title = _find_window_by_pid_or_title(target_pid, title_hint)
    frames = []
    for _ in range(5):
        frames.append(_grab_rect(x, y, w, h))
        time.sleep(0.2)

    y_start = 32 if win_title != "FullScreen" and h > 60 else 0
    total_client = max(1, (w - 16) * max(1, h - y_start - 8))
    coverages, motion_diffs = [], []
    global_min_x, global_min_y, global_max_x, global_max_y = w, h, 0, 0
    clipped_hits = 0

    for idx, fr in enumerate(frames):
        active_px, diff_px = 0, 0
        prev = frames[idx - 1] if idx > 0 else None
        for row in range(y_start, h - 8):
            row_off = row * w * 3
            for col in range(8, w - 8):
                i = row_off + col * 3
                r, g, b = fr[i], fr[i+1], fr[i+2]
                if r > 28 or g > 28 or b > 28:
                    active_px += 1
                    if col < global_min_x: global_min_x = col
                    if col > global_max_x: global_max_x = col
                    if row < global_min_y: global_min_y = row
                    if row > global_max_y: global_max_y = row
                    if col <= 14 or col >= w - 14 or row <= y_start + 6 or row >= h - 14:
                        clipped_hits += 1
                if prev and (abs(r - prev[i]) + abs(g - prev[i+1]) + abs(b - prev[i+2]) > 35):
                    diff_px += 1
        coverages.append((active_px / total_client) * 100.0)
        if prev:
            motion_diffs.append((diff_px / total_client) * 100.0)

    out_png = os.path.join(BRAIN, "last_screen.png")
    _write_png(out_png, w, h, frames[-1])
    avg_cov = sum(coverages) / len(coverages)
    avg_mot = sum(motion_diffs) / max(1, len(motion_diffs))
    issues = []
    if avg_cov < 0.3:
        issues.append("VACÍA/NEGRA (casi sin píxeles visibles)")
    if clipped_hits > 25:
        issues.append("DEMASIADO GRANDE / CORTADA EN LOS BORDES (reduce escala)")
    if avg_mot < 0.05:
        issues.append("ESTÁTICA (0% movimiento en 5 frames)")
    status = "OK_VISUAL" if not issues else "ALERTA_VISUAL: " + "; ".join(issues)
    return out_png, f"Ventana '{win_title}' ({w}x{h}px) | Cobertura media: {avg_cov:.2f}% | Movimiento (5 frames): {avg_mot:.2f}% | {status}"
