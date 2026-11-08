#!/usr/bin/env bash
# Сборка ролика из папки проекта (там voice.wav, words.json, gen_cues.py):
#   gen_cues.py -> cues.json -> белое видео 1080×1920 60 к/с с голосом -> рендер анимаций (Playwright) -> сборка (compose.py) -> video.mp4
# Использование: bash make_video.sh папка_проекта            — весь ролик
#                FROM=12 TO=16 bash make_video.sh папка        — быстрый просмотр куска (preview.mp4)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; E="$HERE/engine"
VENV="${VENV:-$HOME/venv-video}"; PY="$VENV/bin/python"
P="$(cd "$1" && pwd)"; cd "$P"; export SKILL_TEMPLATES="$HERE/templates" PROJECT="$P"
"$PY" gen_cues.py
DUR=$("$PY" -c "import soundfile as sf; print(sf.info('voice.wav').duration)")
[ -f src.mov ] && [ src.mov -nt voice.wav ] || ffmpeg -hide_banner -loglevel error -y -f lavfi -i "color=c=0xfbfbfb:s=1080x1920:r=60:d=$DUR" -i voice.wav \
  -map 0:v -map 1:a -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a pcm_s16le -ar 48000 -ac 2 -shortest src.mov
if [ -n "${FROM:-}" ]; then
  node "$E/render.js" cues.json ov "$FROM" "$TO"
  FROM="$FROM" TO="$TO" SFX_GAIN=0.85 GRADE=0 "$PY" "$E/compose.py" src.mov ov preview.mp4
  echo "кусок: $P/preview.mp4"; exit 0
fi
rm -rf ov
node "$E/render.js" cues.json ov
SFX_GAIN=0.85 GRADE=0 "$PY" "$E/compose.py" src.mov ov raw.mp4
ffmpeg -hide_banner -loglevel error -y -i raw.mp4 -c copy -map_metadata -1 -movflags +faststart video.mp4
echo "длина: $(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4) с (голос $DUR с)"
ffmpeg -hide_banner -nostats -i video.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):"
echo "готово: $P/video.mp4"
