#!/usr/bin/env python3
# incoming_label.py  (Variante A: nur Routing/Cropping, Druck via print_label.py)

import os
import sys
import shutil
import subprocess
from pathlib import Path
from PyPDF2 import PdfFileWriter, PdfFileReader
import fitz  # PyMuPDF

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def crop_pdf(original: str, target: str,
             left: float, top: float, right: float, bottom: float,
             mm: bool = False):
    """
    Zuschneiden eines PDFs in Punkten (1/72") oder Millimetern.
    Schneidet an allen vier Seiten den angegebenen Rand ab.
    """
    factor = 72 / 25.4 if mm else 1
    with open(original, "rb") as fin:
        pdf = PdfFileReader(fin)
        out = PdfFileWriter()
        for page in pdf.pages:
            page.mediaBox.upperRight = (
                page.mediaBox.getUpperRight_x() - right * factor,
                page.mediaBox.getUpperRight_y() - top * factor,
            )
            page.mediaBox.lowerLeft = (
                page.mediaBox.getLowerLeft_x() + left * factor,
                page.mediaBox.getLowerLeft_y() + bottom * factor,
            )
            out.addPage(page)
        with open(target, "wb") as fout:
            out.write(fout)

def scale_stamp(input_pdf: str, output_pdf: str,
                rotation: int = 270, offset_x: int = 220, offset_y: int = 0):
    """
    Skaliert ein Briefmarken-/Adress-PDF auf eine 8x4 inch Seite (576x288 pt)
    und positioniert es mit optionaler Rotation/Offsets.
    """
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()
    try:
        for page in doc:
            media_box = page.mediabox
            orig_width, orig_height = media_box.width, media_box.height
            new_width, new_height = 576, 288  # 8x4" @ 72 DPI
            new_page = new_doc.new_page(width=new_width, height=new_height)
            scale_x = new_width / orig_width
            scale_y = new_height / orig_height
            scale_factor = min(scale_x, scale_y)
            scaled_width = orig_width * scale_factor
            scaled_height = orig_height * scale_factor
            new_rect = fitz.Rect(
                (new_width - scaled_width) / 2 + offset_x,
                (new_height - scaled_height) / 2 + offset_y,
                (new_width + scaled_width) / 2 + offset_x,
                (new_height + scaled_height) / 2 + offset_y,
            )
            new_page.show_pdf_page(new_rect, doc, page.number, rotate=rotation)
        new_doc.save(output_pdf)
    finally:
        new_doc.close()
        doc.close()

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    """
    Aufruf durch den Watcher:
      incoming_label.py <FILENAME> <BASEDIR>

    BASEDIR erwartet die Ordner:
      <BASEDIR>/{incoming,original,printed,failed}
    """
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} FILE BASEDIR")
        sys.exit(1)

    passed_name = sys.argv[1]   # vom Watcher übergebener Dateiname (oder Pfad)
    basedir = Path(sys.argv[2])

    filename = Path(passed_name).name
    filename_base, ext = os.path.splitext(filename)

    # Verzeichnisse
    INCOMING = basedir / "incoming"
    ORIGINAL = basedir / "original"
    PRINTED  = basedir / "printed"
    FAILED   = basedir / "failed"
    for d in (INCOMING, ORIGINAL, PRINTED, FAILED):
        d.mkdir(parents=True, exist_ok=True)

    # Quellen-/Zieldateien
    src_incoming = INCOMING / filename
    dst_original = ORIGINAL / filename

    # print_label.py (liegt im selben Repo-Verzeichnis wie dieses Script)
    PRINT_HELPER = Path(__file__).resolve().parent / "print_label.py"

    # Datei nach original/ verschieben (Backup) und von dort weiterverarbeiten
    try:
        shutil.move(str(src_incoming), str(dst_original))
    except FileNotFoundError:
        # Falls der Watcher einen relativen Namen übergibt, aber Datei schon verschoben wurde
        if not dst_original.exists():
            raise

    # Standard: ohne besondere Behandlung -> 1:1 drucken (Konvertierung macht print_label.py)
    printfile = dst_original
    made_temp = None

    try:
        # --------------------------
        # Routing nach Dateiname
        # --------------------------

        # DHL Paketmarke (A4 -> Labelbereich ausschneiden, Werte ggf. anpassen)
        if "DHL-Paketmarke" in filename:
            target = PRINTED / f"{filename_base}.cropped.pdf"
            crop_pdf(str(dst_original), str(target), 20, 65, 20, 485)  # Punkte
            printfile = target
            made_temp = target

        # Hermes Retoure (Millimeter-Crop, Beispielwerte)
        elif "Rücksende-Etikett" in filename:
            target = PRINTED / f"{filename_base}.cropped.pdf"
            crop_pdf(str(dst_original), str(target), 20, 180, 20, 25, mm=True)
            printfile = target
            made_temp = target

        # Hermes Paketschein (Millimeter-Crop, Beispielwerte – feinjustieren!)
        elif "Paketschein" in filename:
            target = PRINTED / f"{filename_base}.cropped.pdf"
            crop_pdf(str(dst_original), str(target), 20, 180, 20, 25, mm=True)
            printfile = target
            made_temp = target

        # Deutsche Post Briefmarke mit Adresse (Zweckform 3425 – oben links, nur 1 Label)
        elif "Briefmarken" in filename:
            cropped_tmp = PRINTED / f"{filename_base}.cropped.pdf"
            target      = PRINTED / f"{filename_base}.scaled.pdf"
            crop_pdf(str(dst_original), str(cropped_tmp), 0, 30, 340, 670)
            scale_stamp(str(cropped_tmp), str(target))
            printfile = target
            made_temp = target
            # optional: tmp wieder weg, wenn nicht benötigt
            try:
                cropped_tmp.unlink(missing_ok=True)
            except Exception:
                pass

        # Amazon Retouren (meist schon 100x150)
        elif "ShipperLabel" in filename:
            target = PRINTED / filename
            shutil.copyfile(str(dst_original), str(target))
            printfile = target
            made_temp = target

        # TODO: UPS / DPD – hier eigene Crops/Regeln ergänzen

        else:
            # Default: 1:1 kopieren (print_label.py kümmert sich um Skalierung/ZPL)
            target = PRINTED / filename
            shutil.copyfile(str(dst_original), str(target))
            printfile = target
            made_temp = target

        # --------------------------
        # Drucken via print_label.py
        # --------------------------
        # PRINTER per Env überschreibbar (sonst Default in print_label.py = gk420)
        env = os.environ.copy()
        # Beispiel: env["ZEBRA_PRINTER"] = "gk420"

        subprocess.check_call(
            ["python3", str(PRINT_HELPER), str(printfile)],
            env=env
        )
        print(f"[OK] printed: {printfile.name}")

    except Exception as e:
        # In failed/ verschieben (Original bleibt in original/)
        failed_target = FAILED / filename
        try:
            if made_temp and Path(made_temp).exists():
                # Falls wir in PRINTED/ etwas erzeugt hatten, verschiebe es nach failed/
                shutil.move(str(made_temp), str(FAILED / Path(made_temp).name))
            else:
                # sonst das Original nach failed/ kopieren
                shutil.copyfile(str(dst_original), str(failed_target))
        except Exception:
            pass
        print(f"[FAIL] {filename}: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
