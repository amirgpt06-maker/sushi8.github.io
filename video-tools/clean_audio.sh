#!/usr/bin/env bash
# Чистка голоса: срез низа, нейро-шумодав RNNoise, лёгкий де-эссер, компрессия, громкость -14 LUFS (YouTube/Reels).
# Использование: clean_audio.sh input.mp4 output.mp4 [std|bd|cb]
set -euo pipefail
IN="$1"; OUT="$2"; MODEL="${3:-std}"
RNN="${MODELS:-$HOME/video-models}/rnnoise/$MODEL.rnnn"
ffmpeg -hide_banner -y -i "$IN" -c:v copy -af "\
highpass=f=80,\
arnndn=m=$RNN:mix=0.85,\
deesser=i=0.4,\
acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,\
loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k "$OUT" 2>&1 | tail -2
