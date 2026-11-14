import os, sys, time, zlib, struct, ctypes
from ctypes import wintypes

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def _find_target_window(title_hint=""):
    target_rect = None
    fg = user32.GetForegroundWindow()
    if not title_hint and fg and user32.IsWindowVisible(fg):
        length = user32.GetWindowTextLengthW(fg)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(fg, buf, length + 1)
            if "AI-LAB" not in buf.value and "Chrome" not in buf.value:
                rect = wintypes.RECT()
                user32.GetWindowRect(fg, ctypes.byref(rect))
                if (rect.right - rect.left) > 80 and (rect.bottom - rect.top) > 80:
                    return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top, buf.value)

    q = title_hint.lower()
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        nonlocal target_rect
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                t = buf.value
                if (q and q in t.lower()) or (not q and any(k in t.lower() for k in ("cubo", "cube", "tk", "3d", "python", "rotat"))):
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    if (rect.right - rect.left) > 80 and (rect.bottom - rect.top) > 80:
                        target_rect = (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top, t)
                        return False
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if target_rect:
        return target_rect
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

def capture_and_inspect(title_hint=""):
    x, y, w, h, win_title = _find_target_window(title_hint)
    frame1 = _grab_rect(x, y, w, h)
    time.sleep(0.6)
    frame2 = _grab_rect(x, y, w, h)

    y_start = 32 if win_title != "FullScreen" and h > 60 else 0
    min_x, min_y, max_x, max_y = w, h, 0, 0
    active_px, diff_px = 0, 0
    for row in range(y_start, h):
        row_off = row * w * 3
        for col in range(w):
            i = row_off + col * 3
            r, g, b = frame2[i], frame2[i+1], frame2[i+2]
            if r > 25 or g > 25 or b > 25:
                active_px += 1
                if col < min_x: min_x = col
                if col > max_x: max_x = col
                if row < min_y: min_y = row
                if row > max_y: max_y = row
            if abs(r - frame1[i]) + abs(g - frame1[i+1]) + abs(b - frame1[i+2]) > 30:
                diff_px += 1

    out_png = os.path.join(BRAIN, "last_screen.png")
    _write_png(out_png, w, h, frame2)
    total_client = max(1, w * (h - y_start))
    pct = (active_px / total_client) * 100.0
    motion_pct = (diff_px / total_client) * 100.0
    motion_str = f"MOVIMIENTO ACTIVO ({motion_pct:.2f}% píxeles cambiaron en 0.6s)" if diff_px > 15 else "ESTÁTICO (0% movimiento entre frames)"
    if active_px == 0:
        bbox_str = f"Pantalla negra/vacía | {motion_str}"
    else:
        bbox_str = f"Objeto en ({min_x},{min_y})->({max_x},{max_y}) [{max_x-min_x}x{max_y-min_y}px, cobertura {pct:.2f}%] | {motion_str}"
    return out_png, f"Ventana '{win_title}' ({w}x{h}px) -> {bbox_str}"

if __name__ == "__main__":
    _, rep = capture_and_inspect(sys.argv if len(sys.argv) > 1 else "")
    print(rep)
