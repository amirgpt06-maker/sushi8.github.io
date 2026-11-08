#!/usr/bin/env bash
# Превью для сцены «ролики» (reels): кадры анимации в заданные секунды -> проект/thumbs/r0.jpg, r1.jpg …
# Использование: bash make_thumbs.sh папка_проекта 1.2 9.5 16.8 21.0
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; PY="${VENV:-$HOME/venv-video}/bin/python"
P="$(cd "$1" && pwd)"; shift
export SKILL_TEMPLATES="$HERE/templates" PROJECT="$P"; cd "$P" && "$PY" gen_cues.py >/dev/null
FR=$(printf "%s\n" "$@" | awk '{printf "%s%d", (NR>1?",":""), $1*60+0.5}')
rm -rf "$P/.thumbs" && node "$HERE/engine/render.js" cues.json "$P/.thumbs" 0 0 "$FR" >/dev/null
mkdir -p "$P/thumbs"
"$PY" - "$P" "$FR" <<'PY'
import sys, cv2, numpy as np
P, fr = sys.argv[1], [int(v) for v in sys.argv[2].split(",")]
for i, n in enumerate(fr):
    o = cv2.imread(f"{P}/.thumbs/{n:05d}.png", cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
    if o.shape[2] == 4:
        o = np.full(o.shape[:2] + (3,), 251 / 255, np.float32) * (1 - o[..., 3:4]) + o[..., :3] * o[..., 3:4]
    cv2.imwrite(f"{P}/thumbs/r{i}.jpg", (cv2.resize(o, (360, 640), interpolation=cv2.INTER_AREA) * 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"thumbs/r{i}.jpg <- {n / 60:.2f} с")
PY
