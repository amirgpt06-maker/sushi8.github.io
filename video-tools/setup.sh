#!/usr/bin/env bash
# Ставит всё для монтажа: ffmpeg, Python-инструменты, модели шумодава, шрифт, Whisper.
# Контейнер облачной сессии временный — запускайте этот скрипт в начале каждой новой сессии.
set -euo pipefail
VENV="${VENV:-$HOME/venv-video}"
MODELS="${MODELS:-$HOME/video-models}"

command -v ffmpeg >/dev/null || { apt-get update && apt-get install -y ffmpeg; }

[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$(dirname "$0")/requirements.txt"

mkdir -p "$MODELS/rnnoise" "$MODELS/fonts" "$MODELS/whisper" "$HOME/.fonts"
for m in std.rnnn bd.rnnn cb.rnnn; do
  [ -f "$MODELS/rnnoise/$m" ] || curl -sSfL -o "$MODELS/rnnoise/$m" \
    "https://raw.githubusercontent.com/richardpl/arnndn-models/master/$m"
done
[ -f "$MODELS/fonts/Montserrat.ttf" ] || curl -sSfL -o "$MODELS/fonts/Montserrat.ttf" \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
cp "$MODELS/fonts/Montserrat.ttf" "$HOME/.fonts/" && fc-cache -f >/dev/null

# Модели Whisper лежат на huggingface.co — этот домен должен быть разрешён в сетевых настройках окружения.
HF_HUB_CACHE="$MODELS/whisper" "$VENV/bin/python" -I -c "
from faster_whisper import WhisperModel
for m in ('small', 'medium'):
    WhisperModel(m, device='cpu', compute_type='int8'); print('whisper', m, 'ok')
" || echo "!! Whisper-модели не скачались (нет доступа к huggingface.co). Субтитры будут недоступны."
# Живые русские мужские нейроголоса Piper (с релизов k2-fsa/sherpa-onnx на GitHub) + офлайн-синтезатор RHVoice как запасной
"$VENV/bin/pip" install -q piper-tts
for v in ruslan dmitri denis; do
  [ -f "$MODELS/tts/$v/ru_RU-$v-medium.onnx" ] && continue
  mkdir -p "$MODELS/tts/$v"
  curl -sSfL "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-ru_RU-$v-medium.tar.bz2" \
    | tar -xj -C "$MODELS/tts/$v" --strip-components=1
done
command -v RHVoice-test >/dev/null || { apt-get update -q && apt-get install -y -q rhvoice rhvoice-russian; } || true
echo "Готово."
