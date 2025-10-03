#!/usr/bin/env python3
# print_label.py – Helper für Variante A (PDF/IMG -> ZPL -> raw zu Zebra)

import os, sys, subprocess
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import numpy as np

# -----------------------------
# Konfiguration (per ENV änderbar)
# -----------------------------
PRINTER = os.environ.get("ZEBRA_PRINTER", "gk420")  # CUPS-Queue-Name
LABEL_SIZE = os.environ.get("LABEL_SIZE", "100x150mm")  # z.B. "100x150mm" oder "50x30mm"
DPI = int(os.environ.get("ZEBRA_DPI", "203"))           # 203 oder 300
THRESHOLD = int(os.environ.get("ZEBRA_THRESHOLD", "200"))

def size_to_pixels(size_str: str, dpi: int):
    """
    Wandelt "100x150mm" oder "4x6in" in Pixel (Breite, Höhe) um.
    Default: mm.
    """
    s = size_str.strip().lower().replace(" ", "")
    if s.endswith("mm"):
        w_mm, h_mm = s[:-2].split("x")
        w_px = int(round(float(w_mm) / 25.4 * dpi))
        h_px = int(round(float(h_mm) / 25.4 * dpi))
    elif s.endswith("in"):
        w_in, h_in = s[:-2].split("x")
        w_px = int(round(float(w_in) * dpi))
        h_px = int(round(float(h_in) * dpi))
    else:
        # Fallback: "WxH" als Pixel
        w_px, h_px = map(int, s.split("x"))
    return w_px, h_px

TARGET_W, TARGET_H = size_to_pixels(LABEL_SIZE, DPI)

# -----------------------------
# Core
# -----------------------------

def print_raw_zpl(zpl: str):
    p = subprocess.run(
        ["lpr", "-P", PRINTER, "-o", "raw"],
        input=zpl.encode("ascii", "ignore")
    )
    if p.returncode != 0:
        raise RuntimeError("lpr failed")

def bitmap_to_gfa(img_1bit: Image.Image, target_w: int, target_h: int) -> str:
    """
    1-bit PIL Image -> ZPL ^GFA
    """
    # sicherstellen, dass die Bildgröße passt
    if img_1bit.size != (target_w, target_h):
        img_1bit = img_1bit.resize((target_w, target_h))
    w, h = img_1bit.size
    row_bytes = (w + 7) // 8
    total_bytes = row_bytes * h

    arr = 1 - np.array(img_1bit, dtype=np.uint8)  # Schwarz = 1
    packed = np.packbits(arr, axis=1)
    hex_blob = "".join(row.tobytes().hex().upper() for row in packed)

    # ^PW (Breite), ^LL (Höhe) setzen
    return f"^XA^PW{w}^LL{h}^FO0,0^GFA,{total_bytes},{total_bytes},{row_bytes},{hex_blob}^FS^XZ"

def render_pdf_to_1bit(pdf_path: Path, target_w: int, target_h: int, thr: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[0]
    # Seite in Graustufen rastern; skalieren ungefähr auf Zielrahmen
    mx = fitz.Matrix(target_w / page.rect.width, target_h / page.rect.height)
    pix = page.get_pixmap(matrix=mx, colorspace=fitz.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)

    # In Zielcanvas einpassen (zentriert), dann binarisieren
    img.thumbnail((target_w, target_h), Image.LANCZOS)
    canvas = Image.new("L", (target_w, target_h), 255)
    ox = (target_w - img.width) // 2
    oy = (target_h - img.height) // 2
    canvas.paste(img, (ox, oy))
    mono = canvas.point(lambda p: 0 if p < thr else 255, mode="1")
    return mono

def image_to_1bit(img_path: Path, target_w: int, target_h: int, thr: int) -> Image.Image:
    img = Image.open(img_path).convert("L")
    img = img.resize((target_w, target_h))
    mono = img.point(lambda p: 0 if p < thr else 255, mode="1")
    return mono

def main():
    if len(sys.argv) < 2:
        print("Usage: print_label.py <file>")
        sys.exit(2)

    f = Path(sys.argv[1])
    if not f.exists():
        raise FileNotFoundError(f)

    ext = f.suffix.lower()

    if ext == ".zpl":
        # ZPL direkt durchreichen
        zpl = f.read_text(encoding="utf-8", errors="ignore")
        print_raw_zpl(zpl)

    elif ext == ".pdf":
        mono = render_pdf_to_1bit(f, TARGET_W, TARGET_H, THRESHOLD)
        zpl = bitmap_to_gfa(mono, TARGET_W, TARGET_H)
        print_raw_zpl(zpl)

    elif ext in (".png", ".jpg", ".jpeg"):
        mono = image_to_1bit(f, TARGET_W, TARGET_H, THRESHOLD)
        zpl = bitmap_to_gfa(mono, TARGET_W, TARGET_H)
        print_raw_zpl(zpl)

    else:
        # Fallback: Text als großes Label
        text = f.read_text(encoding="utf-8", errors="ignore").strip()[:200]
        zpl = f"^XA^PW{TARGET_W}^LL{TARGET_H}^FO40,60^A0N,40,40^FD{text}^FS^XZ"
        print_raw_zpl(zpl)

    print(f"[OK] sent to {PRINTER} ({LABEL_SIZE} @ {DPI}dpi, thr={THRESHOLD})")

if __name__ == "__main__":
    main()
