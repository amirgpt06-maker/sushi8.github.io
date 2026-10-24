#!/usr/bin/env bash
# Базовая цветокоррекция: контраст, насыщенность, резкость. Можно передать .cube LUT.
# Использование: color.sh input.mp4 output.mp4 [file.cube]
set -euo pipefail
IN="$1"; OUT="$2"; LUT="${3:-}"
VF="eq=contrast=1.06:saturation=1.12:gamma=1.0,unsharp=5:5:0.6"
[ -n "$LUT" ] && VF="lut3d=$LUT,$VF"
ffmpeg -hide_banner -y -i "$IN" -vf "$VF" -c:v libx264 -preset medium -crf 18 -c:a copy "$OUT" 2>&1 | tail -1
