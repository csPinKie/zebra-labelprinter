# 🖨️ Zebra Label Printer Automation

Dieses Repository enthält ein einfaches, Python- und Bash-basiertes System zum **automatischen Drucken von Versandlabels** (100x150 mm, z. B. DHL, Hermes, Amazon) auf einem Zebra/VEVOR GK420d Labeldrucker unter Linux (getestet auf Raspberry Pi OS).

Das System überwacht einen **Ordner für eingehende Dateien** und druckt alles automatisch auf den Zebra-Drucker. Unterstützt werden **PDF, PNG, JPG, ZPL**.

---

## 📂 Ordnerstruktur

Alle Dateien werden in `/var/tmp/labels` verwaltet:

- `incoming/` → neue Dateien hier ablegen (werden automatisch verarbeitet)  
- `original/` → Kopie des Originals (Backup)  
- `printed/` → erfolgreich gedruckte Dateien  
- `failed/` → fehlerhafte Dateien landen hier  

---

## ⚙️ Installation

### 1. System-Pakete installieren
```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip inotify-tools
### 2. Repository klonen
bash
Code kopieren
git clone https://github.com/cs_pinkie/zebra-labelprinter.git
cd zebra-labelprinter
### 3. Python-Umgebung vorbereiten
bash
Code kopieren
python3 -m venv ~/zebra-venv
source ~/zebra-venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
### 4. Drucker einrichten
Der Drucker muss als CUPS-Raw-Queue existieren, z. B. gk420.
Test:

bash
Code kopieren
echo "^XA^FO50,50^A0N,50,50^FDHello Zebra!^FS^XZ" | lp -d gk420 -o raw
▶️ Autostart einrichten (systemd)
1. Script ins System kopieren
bash
Code kopieren
sudo cp zebra-watch.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/zebra-watch.sh
2. Service installieren
bash
Code kopieren
sudo cp zebra-watch.service.example /etc/systemd/system/zebra-watch.service
sudo systemctl daemon-reload
sudo systemctl enable --now zebra-watch.service
3. Status prüfen
bash
Code kopieren
systemctl status zebra-watch.service --no-pager
Logs anzeigen:

bash
Code kopieren
journalctl -u zebra-watch.service -e
📥 Nutzung
Einfach eine Label-Datei ins incoming-Verzeichnis legen:

bash
Code kopieren
cp ~/Downloads/dhl-label.pdf /var/tmp/labels/incoming/
Das Script wandelt die Datei automatisch in ZPL um, schickt sie an den Drucker und verschiebt die Datei nach printed/.

### 🔧 Troubleshooting
-Nichts wird gedruckt
→ Logs prüfen: journalctl -u zebra-watch.service -e
→ sicherstellen, dass Drucker in CUPS als gk420 vorhanden ist

-Qualität schlecht / zu hell
→ Schwellwert in print_label.py anpassen (lambda p: 0 if p < 200 else 255).
Niedrigerer Wert = dunklerer Druck.

-Andere Labelgröße (z. B. 50x30 mm)
→ In print_label.py TARGET_W und TARGET_H anpassen (bei 203 dpi: 400×240).

📜 Dateien in diesem Repo
print_label.py – wandelt PDF/PNG/JPG/ZPL in ZPL-Grafik und sendet an Drucker
zebra-watch.sh – Watcher-Script, überwacht incoming/ und ruft print_label.py auf
zebra-watch.service.example – systemd-Unit (Beispiel, wird ins System kopiert)
requirements.txt – Python-Abhängigkeiten
README.md – diese Dokumentation

🚀 To-Do / Ideen
Unterstützung mehrerer Druckerqueues / Labelgrößen

Templates für unterschiedliche Carrier (DHL, Hermes, Amazon, eBay)

Web-Frontend zum Hochladen von Labels


