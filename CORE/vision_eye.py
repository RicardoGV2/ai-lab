import os, sys, zlib, struct, ctypes
from ctypes import wintypes

ROOT = os.path.expanduser("~/ai-lab")
BRAIN = os.path.join(ROOT, "BRAIN")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def _find_window_rect(title_hint=""):
    target_rect = None
    if title_hint:
        q = title_hint.lower()
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, lparam):
            nonlocal target_rect
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if q in buf.value.lower():
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        if (rect.right - rect.left) > 50 and (rect.bottom - rect.top) > 50:
                            target_rect = (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top, buf.value)
                            return False
            return True
        user32.EnumWindows(WNDENUMPROC(cb), 0)
    if target_rect:
        return target_rect
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return (0, 0, w, h, "FullScreen")

def _write_png(path, w, h, rgb_bytes):
    raw_rows = bytearray()
    stride = w * 3
    for y in range(h):
        raw_rows.append(0)
        raw_rows.extend(rgb_bytes[y * stride:(y + 1) * stride])
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw_rows), 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)

def capture_and_inspect(title_hint=""):
    x, y, w, h, win_title = _find_window_rect(title_hint)
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
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 24
    bmi.biCompression = 0
    row_padded = (w * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(row_padded * h)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)

    # Convert BGR padded to RGB and compute visual coverage & bounding box of drawn content
    rgb = bytearray(w * h * 3)
    raw = buf.raw
    min_x, min_y, max_x, max_y = w, h, 0, 0
    active_px = 0
    # Ignore title bar (~32px) when inspecting client content
    y_start = 32 if win_title != "FullScreen" and h > 60 else 0
    for row in range(h):
        src_off = row * row_padded
        dst_off = row * w * 3
        for col in range(w):
            b = raw[src_off + col * 3]
            g = raw[src_off + col * 3 + 1]
            r = raw[src_off + col * 3 + 2]
            rgb[dst_off + col * 3] = r
            rgb[dst_off + col * 3 + 1] = g
            rgb[dst_off + col * 3 + 2] = b
            if row >= y_start and (r > 25 or g > 25 or b > 25):
                active_px += 1
                if col < min_x: min_x = col
                if col > max_x: max_x = col
                if row < min_y: min_y = row
                if row > max_y: max_y = row

    out_png = os.path.join(BRAIN, "last_screen.png")
    _write_png(out_png, w, h, rgb)
    total_client = max(1, w * (h - y_start))
    pct = (active_px / total_client) * 100.0
    if active_px == 0:
        bbox_str = "NINGÚN píxel dibujado (pantalla totalmente negra/vacía)"
    else:
        bbox_str = f"Contenido visible en caja ({min_x},{min_y})->({max_x},{max_y}) [tamaño {max_x-min_x}x{max_y-min_y}px, cobertura {pct:.2f}%]"
    return out_png, f"Captura '{win_title}' ({w}x{h}px) guardada en {out_png}. Diagnóstico visual: {bbox_str}"

if __name__ == "__main__":
    hint = sys.argv[1] if len(sys.argv) > 1 else ""
    _, report = capture_and_inspect(hint)
    print(report)
