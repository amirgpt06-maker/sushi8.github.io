"""Тайминги каждого слова (русский): VAD (Silero) режет на фразы, GigaAM v2 CTC (sherpa-onnx) даёт время каждого токена.

Использование: python words.py audio_or_video out.json
Модель: ~/video-models/asr/gigaam_x/sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19 (GitHub-релиз sherpa-onnx).
Выход: {"words": [{"w": "слово", "t0": 1.23, "t1": 1.56}, ...], "phrases": [{"t0", "t1", "text"}]}
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

src, out = sys.argv[1], sys.argv[2]
M = Path.home() / "video-models" / "asr"
G = M / "gigaam_x" / "sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19"
with tempfile.TemporaryDirectory() as td:
    wav = Path(td) / "a.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    x, sr = sf.read(str(wav), dtype="float32")

cfg = sherpa_onnx.VadModelConfig()
cfg.silero_vad.model = str(M / "silero_vad.onnx")
cfg.silero_vad.min_silence_duration = 0.25
cfg.silero_vad.min_speech_duration = 0.15
cfg.silero_vad.threshold = 0.4
cfg.sample_rate = sr
vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=300)
segs = []
for i in range(0, len(x), cfg.silero_vad.window_size):
    vad.accept_waveform(x[i:i + cfg.silero_vad.window_size])
    while not vad.empty():
        segs.append((vad.front.start / sr, np.array(vad.front.samples)))
        vad.pop()
vad.flush()
while not vad.empty():
    segs.append((vad.front.start / sr, np.array(vad.front.samples)))
    vad.pop()

rec = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(model=str(G / "model.int8.onnx"), tokens=str(G / "tokens.txt"), num_threads=4)
words, phrases = [], []
for t0, samples in segs:
    pad = np.zeros(int(0.15 * sr), np.float32)
    s = rec.create_stream()
    s.accept_waveform(sr, np.concatenate([pad, samples, pad]))
    rec.decode_stream(s)
    r = s.result
    toks, ts = list(r.tokens), list(r.timestamps)
    cur = None
    for tok, tt in zip(toks, ts):                      # токены — буквы; пробел (или «▁») — граница слова
        t = t0 + tt - 0.15
        if tok.strip() == "" or tok == "▁":
            if cur:
                words.append(cur)
            cur = None
            continue
        if tok.startswith("▁") and cur:
            words.append(cur)
            cur = None
        if cur is None:
            cur = {"w": tok.lstrip("▁"), "t0": round(max(t0, t), 3), "t1": round(t + 0.06, 3)}
        else:
            cur["w"] += tok
            cur["t1"] = round(t + 0.06, 3)
    if cur:
        words.append(cur)
    # конец последнего слова — конец фразы
    if words:
        words[-1]["t1"] = round(max(words[-1]["t1"], t0 + len(samples) / sr), 3)
    phrases.append({"t0": round(t0, 3), "t1": round(t0 + len(samples) / sr, 3), "text": r.text})
# конец слова = начало следующего (если пауза короче 0.25 с)
for a, b in zip(words, words[1:]):
    if 0 < b["t0"] - a["t1"] < 0.25 or b["t0"] < a["t1"]:
        a["t1"] = b["t0"]
json.dump({"words": words, "phrases": phrases}, open(out, "w"), ensure_ascii=False, indent=1)
for p in phrases:
    print(f"{p['t0']:6.2f}–{p['t1']:6.2f}  {p['text']}")
