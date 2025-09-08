#!/usr/bin/env python3

import os
import sys
import time
import shutil
import requests
import cups
from PyPDF2 import PdfFileWriter, PdfFileReader
import fitz  # PyMuPDF


# functions

# crop PDF (px or mm)
def crop_pdf(original: str, target: str, left: float, top: float, right: float, bottom: float, mm: bool = False):
    """Zuschneiden von PDF in Punkten (1/72 inch / default) oder Millimetern."""
    factor = 72 / 25.4 if mm else 1
    pdf = PdfFileReader(open(original, "rb"))
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
    with open(target, "wb") as ous:
        out.write(ous)

# scale stamp
def scale_stamp(input_pdf: str, output_pdf: str, rotation=270, offset_x=220, offset_y=0):
    """Skaliert Briefmarken-PDF auf 8x4 inch Seite (576x288pt)."""
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()
    for page in doc:
        media_box = page.mediabox
        orig_width, orig_height = media_box.width, media_box.height
        new_width, new_height = 576, 288  # 8x4 inch @ 72dpi
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
    new_doc.close()
    doc.close()

# switch tasmota plug
def power_switch(cmd: str):
    """Schaltet Tasmota Steckdose aus oder ein."""
    tasmota_host = "192.168.2.69"

    try:
        requests.post(
            "http://" + tasmota_host + "/cm",
            data={"cmnd": f"Power {cmd}"},
            timeout=5,
        )
    except requests.RequestException as e:
        print(f"[WARN] Power {cmd} failed: {e}")


# main

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} FILE BASEDIR")
        sys.exit(1)

    file = sys.argv[1]
    basedir = sys.argv[2]

    filename_base = os.path.splitext(os.path.basename(file))[0]
    printer = "VEVOR_Y486"
    lpoptions = {}

    # power on
    power_switch("On")
    time.sleep(5)

    # move incoming file to original
    incoming = os.path.join(basedir, "incoming", file)
    original = os.path.join(basedir, "original", file)
    shutil.move(incoming, original)

    # define destination
    printed_dir = os.path.join(basedir, "printed")
    #os.makedirs(printed_dir, exist_ok=True)

    # match label and process (scale/etc.)
    # DHL Paketmarke
    if "DHL-Paketmarke" in file:
        target = os.path.join(printed_dir, filename_base + ".cropped.pdf")
        crop_pdf(original, target, 20, 65, 20, 485)
        printfile = target
        lpoptions = {"fit-to-page": "true"}

    # Hermes Retoure
    elif "Rücksende-Etikett" in file:
        target = os.path.join(printed_dir, filename_base + ".cropped.pdf")
        crop_pdf(original, target, 20, 180, 20, 25, True)  # mm=True
        printfile = target
        lpoptions = {"fit-to-page": "true"}

    # DP Briefmarke mit Adresse (Zweckform 3425 - oben links, NUR 1 Label)
    elif "Briefmarken" in file:
        cropped_tmp = os.path.join(printed_dir, filename_base + ".cropped.pdf")
        target = os.path.join(printed_dir, filename_base + ".scaled.pdf")
        crop_pdf(original, cropped_tmp, 0, 30, 340, 670)
        scale_stamp(cropped_tmp, target)
        printfile = target

    # Amazon Retouren Label
    elif "ShipperLabel" in file:
        target = os.path.join(printed_dir, file)
        shutil.copy(original, target)  # nur kopieren
        printfile = target
        lpoptions = {"fit-to-page": "true"}

    # default
    else:
        target = os.path.join(printed_dir, file)
        shutil.copy(original, target)
        printfile = target

    # print with pycups
    conn = cups.Connection()
    job_id = conn.printFile(printer, printfile, "Print Job", lpoptions)
    print(f"Job {job_id} sent to {printer}")

    # power off (20s delay)
    time.sleep(20)
    power_switch("Off")


if __name__ == "__main__":
    main()
