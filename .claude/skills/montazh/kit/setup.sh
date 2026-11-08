#!/usr/bin/env bash
# skill.ai — установка всего, что нужно для монтажа (запускать один раз в новом окружении):
#   ffmpeg, Python-окружение с пакетами, Node + Playwright (Chromium) для рендера анимаций,
#   модели распознавания слов (GigaAM v2 + Silero VAD) и шумодава (RNNoise).
# Нужен доступ в интернет к: github.com, objects.githubusercontent.com, raw.githubusercontent.com, pypi.org, registry.npmjs.org.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="${VENV:-$HOME/venv-video}"
MODELS="${MODELS:-$HOME/video-models}"

command -v ffmpeg >/dev/null || { apt-get update -q && apt-get install -y -q ffmpeg; }
command -v node >/dev/null || { apt-get update -q && apt-get install -y -q nodejs npm; }

[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$HERE/requirements.txt"

# Playwright: если уже стоит глобально (облачные сессии Claude Code) — используем его, иначе ставим в engine/
if ! (cd "$HERE/engine" && node -e "require('playwright')" 2>/dev/null); then
  (cd "$HERE/engine" && npm init -y >/dev/null 2>&1; npm i -s playwright && npx playwright install --with-deps chromium)
fi

mkdir -p "$MODELS/asr/gigaam_x" "$MODELS/rnnoise"
G=sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19
[ -d "$MODELS/asr/gigaam_x/$G" ] || curl -sSfL "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$G.tar.bz2" | tar -xj -C "$MODELS/asr/gigaam_x"
[ -f "$MODELS/asr/silero_vad.onnx" ] || curl -sSfL -o "$MODELS/asr/silero_vad.onnx" "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
[ -f "$MODELS/rnnoise/std.rnnn" ] || curl -sSfL -o "$MODELS/rnnoise/std.rnnn" "https://raw.githubusercontent.com/richardpl/arnndn-models/master/std.rnnn"

# проверка
(cd "$HERE/engine" && node -e "require('playwright').chromium.launch().then(b=>{console.log('chromium ok');return b.close()})")
"$VENV/bin/python" -c "import cv2, sherpa_onnx, soundfile, librosa; print('python ok')"
ls "$HERE/engine/local/fonts/SF-Pro-Display-Bold.otf" >/dev/null && echo "шрифты ok"
ls "$HERE/engine/sfx_local/wbpop.wav" >/dev/null && echo "звуки ok ($(ls "$HERE/engine/sfx_local" | wc -l) ролей)"
echo "Готово."
