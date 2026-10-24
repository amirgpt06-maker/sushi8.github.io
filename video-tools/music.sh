#!/usr/bin/env bash
# Подкладывает фоновую музыку, которая автоматически приглушается, когда вы говорите (ducking).
# Использование: music.sh video.mp4 music.mp3 output.mp4 [громкость музыки, по умолчанию 0.25]
set -euo pipefail
IN="$1"; MUS="$2"; OUT="$3"; VOL="${4:-0.25}"
ffmpeg -hide_banner -y -i "$IN" -stream_loop -1 -i "$MUS" -filter_complex "\
[1:a]volume=$VOL[m];[0:a]asplit[v][sc];\
[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[duck];\
[v][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest "$OUT" 2>&1 | tail -1
