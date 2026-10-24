#!/usr/bin/env bash
# Делает вертикаль 9:16 (1080x1920) для Reels/Shorts/TikTok.
# mode=crop — обрезать по центру; mode=blur — вписать кадр на размытый фон.
# Использование: vertical.sh input.mp4 output.mp4 [crop|blur]
set -euo pipefail
IN="$1"; OUT="$2"; MODE="${3:-blur}"
if [ "$MODE" = crop ]; then
  VF="crop=ih*9/16:ih,scale=1080:1920,setsar=1"
else
  VF="split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3[bg];\
[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
fi
ffmpeg -hide_banner -y -i "$IN" -filter_complex "$VF" -c:v libx264 -preset medium -crf 20 -c:a copy "$OUT" 2>&1 | tail -1
