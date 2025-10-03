sudo tee /usr/local/bin/zebra-watch.sh >/dev/null <<'SH'
#!/usr/bin/env bash
set -euo pipefail

BASEDIR="/var/tmp/labels"
INCOMING="$BASEDIR/incoming"
ORIGINAL="$BASEDIR/original"
PRINTED="$BASEDIR/printed"
FAILED="$BASEDIR/failed"

PRINTER="gk420"
VENV="/home/pi/zebra-venv"
SCRIPT="/home/pi/zebra-labelprinter/print_label.py"

mkdir -p "$INCOMING" "$ORIGINAL" "$PRINTED" "$FAILED"

# Endlosschleife mit inotifywait: reagiert auf create/close_write/moved_to
inotifywait -m -e close_write,create,moved_to --format "%f" "$INCOMING" | while read -r FILE; do
  FULL="$INCOMING/$FILE"
  # kurze Wartezeit, falls Datei noch geschrieben wird
  sleep 0.3

  # Kopie ablegen
  cp -f "$FULL" "$ORIGINAL/$FILE" || true

  echo "[ZEBRA] processing: $FILE"
  if source "$VENV/bin/activate"; then
    if ZEBRA_PRINTER="$PRINTER" python "$SCRIPT" "$FULL"; then
      mv -f "$FULL" "$PRINTED/$FILE" || rm -f "$FULL"
      echo "[ZEBRA] OK: $FILE"
    else
      mv -f "$FULL" "$FAILED/$FILE" || true
      echo "[ZEBRA] FAIL: $FILE"
    fi
    deactivate || true
  else
    echo "[ZEBRA] FAIL: could not activate venv"
    mv -f "$FULL" "$FAILED/$FILE" || true
  fi
done
SH

sudo chmod +x /usr/local/bin/zebra-watch.sh
