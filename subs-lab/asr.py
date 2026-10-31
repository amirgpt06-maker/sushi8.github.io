"""Распознавание речи офлайн: VAD (Silero) режет на фразы, Whisper turbo (sherpa-onnx) распознаёт каждую.

Использование: python asr.py audio16k.wav out.json [языки через запятую, напр. ru,ar ; пусто = авто]
"""
import json
import sys
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

M = Path.home() / "video-models" / "asr"
wav, out = sys.argv[1], sys.argv[2]
langs = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else [""]
x, sr = sf.read(wav, dtype="float32")
assert sr == 16000

cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = str(M / "silero_vad.onnx")
cfg.silero_vad.min_silence_duration = float(__import__("os").environ.get("MINSIL", "0.25"))
cfg.silero_vad.min_speech_duration = 0.2
cfg.silero_vad.threshold = 0.45
cfg.sample_rate = sr
vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
segs = []
win = cfg.silero_vad.window_size
for i in range(0, len(x), win):
    vad.accept_waveform(x[i:i + win])
    while not vad.empty():
        s = vad.front
        segs.append((s.start / sr, np.array(s.samples)))
        vad.pop()
vad.flush()
while not vad.empty():
    s = vad.front
    segs.append((s.start / sr, np.array(s.samples)))
    vad.pop()

W = M / "sherpa-onnx-whisper-turbo"
recs = {}
for lg in langs:
    recs[lg] = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(W / "turbo-encoder.int8.onnx"), decoder=str(W / "turbo-decoder.int8.onnx"),
        tokens=str(W / "turbo-tokens.txt"), language=lg, task="transcribe", num_threads=4, tail_paddings=800)
res = []
for t0, s in segs:
    item = {"t0": round(t0, 2), "t1": round(t0 + len(s) / sr, 2)}
    for lg, r in recs.items():
        st = r.create_stream()
        st.accept_waveform(sr, s)
        r.decode_stream(st)
        item[lg or "auto"] = st.result.text.strip()
        if not lg:
            item["lang"] = getattr(st.result, "lang", "")
    res.append(item)
    print(item, flush=True)
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
