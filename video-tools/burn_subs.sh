#!/usr/bin/env bash
# Вшивает субтитры в видео крупным жирным шрифтом с обводкой (стиль Reels/Shorts).
# Использование: burn_subs.sh input.mp4 subs.srt output.mp4 [размер шрифта, по умолчанию 18]
set -euo pipefail
IN="$1"; SRT="$2"; OUT="$3"; SIZE="${4:-18}"
STYLE="FontName=Montserrat ExtraBold,FontSize=$SIZE,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=60"
ffmpeg -hide_banner -y -i "$IN" -vf "subtitles=$SRT:force_style='$STYLE'" \
  -c:v libx264 -preset medium -crf 18 -c:a copy "$OUT" 2>&1 | tail -1
