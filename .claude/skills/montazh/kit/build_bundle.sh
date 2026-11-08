#!/usr/bin/env bash
# Собирает переносимую папку skill.ai (+ zip) из репозитория и ЛОКАЛЬНЫХ ассетов пользователя
# (engine/local — шрифты и UI, engine/sfx_local — звуки, исходники пака). Ассеты в git не хранятся (лицензия паков).
# Использование: bash build_bundle.sh /куда [папка_исходников_пака ...] [--example видео.mp4]
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"; ENG="$KIT/../engine"; DEST="$(mkdir -p "$1" && cd "$1" && pwd)"; OUT="$DEST/skill.ai"; shift
EXAMPLE=""; PACKS=()
while [ $# -gt 0 ]; do case "$1" in --example) EXAMPLE="$2"; shift 2;; *) PACKS+=("$1"); shift;; esac; done
rm -rf "$OUT"; mkdir -p "$OUT/engine" "$OUT/pack/sounds" "$OUT/tools" "$OUT/example" "$OUT/templates"
cp "$KIT"/{PROMPT.md,README.txt,setup.sh,prep_voice.sh,make_video.sh,requirements.txt} "$OUT/"
cp "$KIT"/templates/*.py "$OUT/templates/"; cp "$KIT"/tools/* "$OUT/tools/"; cp "$KIT"/example/*.py "$OUT/example/"
cp "$KIT/../../../../video-tools/words.py" "$OUT/tools/" 2>/dev/null || true
sed -i 's|^M = Path.home() / "video-models" / "asr"|import os\nM = Path(os.environ.get("MODELS", Path.home() / "video-models")) / "asr"|' "$OUT/tools/words.py"
cp "$ENG"/{engine.html,render.js,compose.py,sfx_map.json,pack_to_sfx.py,pack_assets.py,sfx.py,anchor.py,matte.py} "$OUT/engine/"
cp -r "$ENG/fonts" "$ENG/sfx" "$OUT/engine/"; mkdir -p "$OUT/engine/examples" && cp "$ENG/examples/white_apple.json" "$OUT/engine/examples/"
[ -d "$ENG/local" ] && cp -r "$ENG/local" "$OUT/engine/" || echo "!! нет engine/local (шрифты SF Pro, UI) — запусти pack_assets.py"
[ -d "$ENG/sfx_local" ] && cp -r "$ENG/sfx_local" "$OUT/engine/" || echo "!! нет engine/sfx_local — запусти pack_to_sfx.py"
cp "$KIT/../SKILL.md" "$OUT/STYLE.md"
if [ ${#PACKS[@]} -gt 0 ]; then
  python3 - "$OUT" "${PACKS[@]}" <<'PY'
import json, os, re, shutil, sys
out, packs = sys.argv[1], sys.argv[2:]
norm = lambda n: re.sub(r"(\(\d+\))+$", "", os.path.splitext(n)[0]).strip().lower()
idx = {}
for p in packs:
    for root, _, fs in os.walk(p):
        for f in fs:
            q = os.path.join(root, f)
            if norm(f) not in idx or len(q) < len(idx[norm(f)]): idx[norm(f)] = q
m = json.load(open(f"{out}/engine/sfx_map.json", encoding="utf-8"))
for k, v in m.items():
    if not k.startswith("_") and norm(v["file"]) in idx:
        shutil.copy2(idx[norm(v["file"])], f"{out}/pack/sounds/{v['file']}")
print(len(os.listdir(f"{out}/pack/sounds")), "исходников звуков")
PY
fi
[ -n "$EXAMPLE" ] && cp "$EXAMPLE" "$OUT/example/primer-rolika.mp4"
find "$OUT" -name "__pycache__" -prune -exec rm -rf {} \;
(cd "$DEST" && rm -f skill.ai.zip && zip -qr -9 skill.ai.zip skill.ai && ls -la "$DEST/skill.ai.zip")
