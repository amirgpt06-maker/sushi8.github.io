#!/usr/bin/env bash
# Финальная сборка: композитинг всех кадров -> H.264 1080p30 + звук; метаданные исходника (в т.ч. GPS) удаляются.
# Использование: assemble.sh work_dir render_exr_dir sfx.wav out.mp4
set -euo pipefail
WORK="$1"; EXR="$2"; SFX="$3"; OUT="$4"
PY="${PY:-$HOME/venv-video/bin/python}"
DIR="$(cd "$(dirname "$0")" && pwd)"
COMP="$(dirname "$OUT")/comp_frames"
"$PY" -I "$DIR/comp.py" "$WORK" "$EXR" "$COMP" all > /dev/null
ffmpeg -hide_banner -loglevel error -y -framerate 30 -i "$COMP/%04d.png" -i "$SFX" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest \
  -map_metadata -1 -metadata title="Knight vs T-Rex" -movflags +faststart "$OUT"
echo "готово: $OUT"
