"""Звук перелистывания страницы (синтез): шорох бумаги с «трепетом» листа и затухающей яркостью.

Использование: python make_page.py  ->  page.wav рядом
"""
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
D = Path(__file__).resolve().parent
rng = np.random.default_rng(11)
n = int(0.34 * SR)
t = np.arange(n) / SR
noise = sosfilt(butter(2, [700, 8000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
# яркость падает: лист «уходит» — режем верх всё сильнее (по блокам)
out = np.zeros(n)
blk = 512
for i in range(0, n, blk):
    fc = 7500 - 5000 * min(1, i / n * 1.3)
    seg = sosfilt(butter(1, fc, "lowpass", fs=SR, output="sos"), noise[max(0, i - 2048):i + blk])[-min(blk, n - i):]
    out[i:i + len(seg)] = seg
# огибающая: мягкий вход, три «взмаха» листа и спад
env = np.minimum(1, t / 0.02) * np.exp(-t / 0.11)
for t0, a in ((0.0, 1.0), (0.05, 0.6), (0.095, 0.35)):
    env *= 1 + 0.9 * a * np.exp(-((t - t0 - 0.02) / 0.016) ** 2)
x = out * env
body = np.sin(2 * np.pi * 150 * t) * np.exp(-t / 0.03) * 0.12                # лёгкая «плотность» бумаги
x = x / np.abs(x).max() + body
x = x / np.abs(x).max() * 0.9
x[-int(0.04 * SR):] *= np.linspace(1, 0, int(0.04 * SR))
sf.write(str(D / "page.wav"), x.astype(np.float32), SR)
print("page.wav", round(n / SR, 2), "с")
