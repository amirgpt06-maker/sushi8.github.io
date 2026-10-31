"""Звук появления слова: чистый стеклянный щелчок (uisfx glass/snap, CC0) + короткий яркий «воздушный» тик сверху.

Использование: python make_appear.py  ->  appear.wav рядом
"""
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

D = Path(__file__).resolve().parent
SR = 48000
snap, _ = librosa.load(str(D / "glass_snap.mp3"), sr=SR)
snap = sosfilt(butter(2, 160, "highpass", fs=SR, output="sos"), snap)        # без низкого «бубнения»
snap /= np.abs(snap).max()
n = int(0.06 * SR)
t = np.arange(n) / SR
air = np.random.default_rng(5).standard_normal(n)
air = sosfilt(butter(2, [3200, 9000], "bandpass", fs=SR, output="sos"), air) * np.minimum(1, t / 0.002) * np.exp(-t / 0.012)
air /= np.abs(air).max()
out = snap.copy()
out[:n] += 0.32 * air
out = out / np.abs(out).max() * 0.9
fade = int(0.03 * SR)
out[-fade:] *= np.linspace(1, 0, fade)
sf.write(str(D / "appear.wav"), out.astype(np.float32), SR)
print("appear.wav", round(len(out) / SR, 3), "с")
