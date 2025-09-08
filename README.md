# VEVOR Y486 Labelprinter

Dieses Script druckt diverse Label (zugeschnitten und/oder skaliert) auf dem VEVOR Y486 Label Drucker unter Linux aus. Genutzt werden 8x4" Label, 6x4" Label sollten aber auch problemlos funktionieren.

## Prerequisites

- Installierter und funktionsfaehiger Drucker in CUPS
- python: requests, cups, PyPDF2, fitz
- Ordnerstruktur: incoming, original, printed
- optional: inoticoming

## Treiber

Original-Treiber: https://www.vevor.com/pages/download-center-label-printer

Alternativ-Treiber (z.B. fuer Raspberry/aarch64): https://help.flashlabel.com/support/solutions/folders/150000439213

Leider liegt der rastertolabel Sourcecode aus dem Treiber nicht vor, weswegen die PPD Datei alleine leider nicht ausreicht und daher eine Treiberversion passend fuer die Architektur installiert werden muss.

Installation des Druckers in CUPS als "VEVOR_Y486", alternativ anpassbar im Script.

## Scripts

- start.sh: startet inoticoming und wartet auf eingehende Files im definierten "incoming", bei neuer, abgelegter Datei (z.B. per Samba Share, etc.) wird das Script "incoming_label.py" aufgerufen (optional)
- incoming_label.py: schneidet bzw. skaliert das Label anhand des jeweiligen Dateinamens und druckt es per lp

## Miscellaneous

Im Script wird zusaetzlich eine Tasmota-Steckdose am Labelprinter geschaltet (Funktion power_switch). Das kann man bei Bedarf natuerlich entfernen.
Alternativ kann das Script auch einfach direkt ohne inoticoming aufgerufen werden (Usage: ./incoming_label.py FILE BASEDIR)

## Example
- cd /var/tmp/testlabel
- mkdir {incoming,original,printed}
- neue Dateien landen IMMER im Verzeichnis "incoming"
- ./incoming_label.py DHL-Paketmarke_XYZ_Bla_Bla.pdf /var/tmp/testlabel

Job 14 sent to VEVOR_Y486
