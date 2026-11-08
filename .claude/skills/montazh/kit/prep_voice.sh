#!/usr/bin/env bash
# Подготовка голоса: 48 кГц моно -> чистка (шумодав, мягкий компрессор) -> срез тишины в начале (за 0.1 с до первого звука)
# -> тайминги каждого слова (words.json) -> печать слов и пауз.
# Использование: bash prep_voice.sh запись.(mp3|m4a|wav|mov|mp4) папка_проекта
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="${VENV:-$HOME/venv-video}"; MODELS="${MODELS:-$HOME/video-models}"; PY="$VENV/bin/python"
IN="$1"; OUT="${2:-project}"
mkdir -p "$OUT"
ffmpeg -hide_banner -loglevel error -y -i "$IN" -vn -ac 1 -ar 48000 "$OUT/voice48.wav"
ffmpeg -hide_banner -loglevel error -y -i "$OUT/voice48.wav" \
  -af "highpass=f=80:poles=2,arnndn=m=$MODELS/rnnoise/std.rnnn:mix=0.7,acompressor=threshold=-22dB:ratio=2:attack=8:release=120:makeup=1.5" \
  -ac 1 "$OUT/voice_c.wav"
START=$("$PY" -I - "$OUT/voice_c.wav" <<'PY'
import sys, numpy as np, soundfile as sf
x, sr = sf.read(sys.argv[1]); x = x if x.ndim == 1 else x.mean(1)
h = int(0.02 * sr); db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(h) / h, "valid")[::h]) + 1e-9)
i = int(np.argmax(db > db.max() - 35)); print(max(0.0, i * 0.02 - 0.1))
PY
)
ffmpeg -hide_banner -loglevel error -y -ss "$START" -i "$OUT/voice_c.wav" -c:a pcm_s16le "$OUT/voice.wav"
"$PY" "$HERE/tools/words.py" "$OUT/voice.wav" "$OUT/words.json"
# уточнение начала слов после пауз по реальному началу звука (распознавание ставит короткие слова на 0.1–0.2 с позже)
"$PY" -I - "$OUT/words.json" "$OUT/voice.wav" <<'PY'
import sys, json, numpy as np, soundfile as sf
d = json.load(open(sys.argv[1])); x, sr = sf.read(sys.argv[2]); x = x if x.ndim == 1 else x.mean(1)
h = int(0.01 * sr); db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(h) / h, "valid")[::h]) + 1e-9); thr = db.max() - 32
prev = 0.0
for w in d["words"]:
    if w["t0"] - prev >= 0.15:
        a, b = int(max(prev + 0.05, w["t0"] - 0.35) * 100), int(w["t0"] * 100)
        on, quiet = None, False                    # начало = первый громкий кадр ПОСЛЕ тихого (хвост прошлого слова не считаем)
        for i in range(a, b):
            if db[i] <= thr: quiet = True
            elif quiet: on = i; break
        if on is not None:
            w["t0_asr"] = w["t0"]; w["t0"] = round(on / 100, 3)
    prev = w["t1"]
json.dump(d, open(sys.argv[1], "w"), ensure_ascii=False)
PY
"$PY" -I - "$OUT/words.json" "$OUT/voice.wav" "$START" <<'PY'
import sys, json, soundfile as sf
w = json.load(open(sys.argv[1]))["words"]; d = sf.info(sys.argv[2]).duration
print(f"срезано в начале: {float(sys.argv[3]):.2f} с; длина голоса (= длина ролика): {d:.2f} с; слов: {len(w)}")
prev = 0
for x in w:
    if x["t0"] - prev >= 0.5: print(f"   --- пауза {x['t0'] - prev:.2f} с ---")
    print(f"{x['t0']:6.2f}–{x['t1']:6.2f}  {x['w']}"); prev = x["t1"]
PY
