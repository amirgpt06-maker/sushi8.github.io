"""Живая нейросетевая озвучка (Piper, офлайн).

Использование: python tts.py <голос: ruslan|dmitri|denis> jobs.json
jobs.json: [{"text": "...", "out": "file.wav"}, ...]
Модели: ~/video-models/tts/<голос>/ru_RU-<голос>-medium.onnx (+ .onnx.json), скачиваются с релизов k2-fsa/sherpa-onnx.
"""
import json
import sys
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig


def main():
    name, jobs = sys.argv[1], json.load(open(sys.argv[2]))
    voice = PiperVoice.load(str(Path.home() / "video-models" / "tts" / name / f"ru_RU-{name}-medium.onnx"))
    # чуть медленнее обычного и с живой интонацией
    cfg = SynthesisConfig(length_scale=1.07, noise_scale=0.72, noise_w_scale=0.9)
    for job in jobs:
        with wave.open(job["out"], "wb") as w:
            voice.synthesize_wav(job["text"], w, syn_config=cfg)


if __name__ == "__main__":
    main()
