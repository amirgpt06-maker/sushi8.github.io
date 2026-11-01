"""«Apple стекло»: набор звуков, синтезированных с нуля (свои, без чужих сэмплов -> без проблем с правами).
Параметры сняты со спектрограммы референса:
  key1..4  механическая клавиатура: щелчок 3-5 мс (2-9 кГц) + «тело» 160-220 Гц; в пачке — шаг 35-60 мс
  tink     стекло: гармоники 3.25 / 6.5 / 9.8 / 13 кГц, затухание 25-60 мс (два «тинь» с шагом 0.14 с в референсе)
  click2   мышь: два щелчка (нажал/отпустил) через 70 мс
  pop      мягкий «пузырь» < 2 кГц, 20 мс — появление первого текста
  swoosh   короткий воздушный свайп 0.25 с
  shimmer  стеклянное растворение: шорох + тихие высокие «искры»
  air      ровный широкополосный шум 0.55 с (под чёрный экран)
  riser    низкий нарастающий гул -> 5 кГц, 0.7 с (световая засветка)
  cash     «ка-чинг»: механика + звенящие частоты 2.2 / 5.6 / 6.1 / 10.2 кГц, хвост ~1 с
  focus    тихий тон 1.25 + 2.7 кГц, 0.45 с (фокус-рамка)
Использование: python sfx.py [папка=./sfx]
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "sfx")
out.mkdir(parents=True, exist_ok=True)
R = np.random.default_rng(5)


def t_(d):
    return np.arange(int(d * SR)) / SR


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def hp(x, f, o=2):
    return sosfilt(butter(o, f, "highpass", fs=SR, output="sos"), x)


def lp(x, f, o=2):
    return sosfilt(butter(o, f, "lowpass", fs=SR, output="sos"), x)


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)


def norm(x, peak=0.9):
    x = x - np.mean(x[: 32]) * 0
    fade = np.ones(len(x))
    k = min(len(x) // 4, int(0.004 * SR))
    fade[-k:] = np.linspace(1, 0, k)
    x = x * fade
    return x / (np.abs(x).max() + 1e-9) * peak


def save(name, x, peak=0.9):
    sf.write(str(out / f"{name}.wav"), norm(x, peak).astype(np.float32), SR)


def key(seed):
    r = np.random.default_rng(seed)
    n = int(0.06 * SR)
    click = bp(r.normal(0, 1, n), 2000 + 400 * seed, 9000, 2) * env(n, 0.0004, 0.0018 + 0.0004 * seed)
    tt = t_(0.06)
    body = np.sin(2 * np.pi * (170 + 15 * seed) * tt) * env(n, 0.001, 0.012) * 0.55
    rattle = bp(r.normal(0, 1, n), 900, 3500) * env(n, 0.002, 0.006) * 0.35
    # отпускание клавиши — тише, через 28-40 мс
    rel = np.zeros(n)
    d = int((0.028 + 0.004 * seed) * SR)
    m = n - d
    rel[d:] = bp(r.normal(0, 1, m), 3000, 8000) * env(m, 0.0003, 0.0012) * 0.35
    return click + body + rattle + rel


for s in range(1, 5):
    save(f"key{s}", key(s), 0.85)

# стекло
tt = t_(0.35)
g = sum(a * np.sin(2 * np.pi * f * tt + p) * np.exp(-tt / d) for f, a, d, p in
        [(3250, 1.0, 0.060, 0), (6510, 0.55, 0.036, 1.1), (9790, 0.32, 0.022, 2.0), (13050, 0.16, 0.013, .4), (4410, 0.12, 0.03, 0)])
g = g + hp(R.normal(0, 1, len(tt)), 6000) * env(len(tt), 0.0002, 0.002) * 0.6
save("tink", g * np.minimum(1, tt / 0.0008), 0.8)

# мышь: два щелчка
def mclick(gain, f0):
    n = int(0.03 * SR)
    x = bp(R.normal(0, 1, n), 1500, 8000) * env(n, 0.0003, 0.0015)
    x += np.sin(2 * np.pi * f0 * t_(0.03)) * env(n, 0.0003, 0.004) * 0.5
    return x * gain


c2 = np.zeros(int(0.15 * SR))
a = mclick(1.0, 3000)
b = mclick(0.7, 3300)
c2[: len(a)] += a
c2[int(0.07 * SR): int(0.07 * SR) + len(b)] += b
save("click2", c2, 0.8)

# пузырь
tt = t_(0.06)
f = 900 * np.exp(-tt / 0.012) + 240
save("pop", np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(tt), 0.001, 0.012), 0.8)

# свайп
tt = t_(0.32)
n = R.normal(0, 1, len(tt))
sw = np.zeros_like(n)
for k in range(0, len(tt), 480):        # полоса скользит вверх
    c = 900 + 5000 * (k / len(tt)) ** 1.4
    seg = slice(k, k + 480)
    sw[seg] = bp(n, c * 0.6, min(c * 1.6, 20000))[seg]
save("swoosh", sw * np.sin(np.pi * tt / tt[-1]) ** 1.6, 0.6)

# стеклянное растворение
tt = t_(0.6)
sh = hp(R.normal(0, 1, len(tt)), 3500) * np.sin(np.pi * tt / tt[-1]) ** 2 * 0.5
for k in range(9):
    t0 = R.uniform(0.05, 0.45)
    f0 = R.uniform(5000, 11000)
    m = tt >= t0
    sh[m] += np.sin(2 * np.pi * f0 * (tt[m] - t0)) * np.exp(-(tt[m] - t0) / 0.03) * 0.35
save("shimmer", sh, 0.55)

# воздух
tt = t_(0.6)
save("air", bp(R.normal(0, 1, len(tt)), 300, 14000) * np.sin(np.pi * tt / tt[-1]) ** 0.8, 0.5)

# засветка: нарастающий гул
tt = t_(0.75)
n = R.normal(0, 1, len(tt))
rs = np.zeros_like(n)
for k in range(0, len(tt), 480):
    c = 120 * (40 ** (k / len(tt)))
    rs[k:k + 480] = bp(n, max(40, c * 0.5), min(c * 1.8, 20000))[k:k + 480]
rs = rs * np.minimum(1, tt / 0.55) ** 2 * np.exp(-np.maximum(0, tt - 0.55) / 0.07)
rs += np.sin(2 * np.pi * 55 * tt) * np.minimum(1, tt / 0.5) * np.exp(-np.maximum(0, tt - 0.5) / 0.1) * 0.3
save("riser", rs, 0.7)

# ка-чинг
tt = t_(1.2)
mech = bp(R.normal(0, 1, len(tt)), 1500, 9000) * env(len(tt), 0.0005, 0.02)
mech2 = np.roll(bp(R.normal(0, 1, len(tt)), 2500, 12000) * env(len(tt), 0.0005, 0.012), int(0.05 * SR)) * 0.8
bell = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt / d) for f, a, d in
           [(2210, 0.5, 0.35), (5580, 0.8, 0.45), (6120, 0.7, 0.5), (10200, 0.35, 0.3), (7450, 0.25, 0.25)])
bell = np.roll(bell * np.minimum(1, tt / 0.003), int(0.06 * SR))
bell[: int(0.06 * SR)] = 0
save("cash", mech * 0.7 + mech2 + bell * 0.6, 0.8)

# фокус
tt = t_(0.45)
fo = (np.sin(2 * np.pi * 1250 * tt) + 0.4 * np.sin(2 * np.pi * 2700 * tt)) * np.minimum(1, tt / 0.02) * np.exp(-tt / 0.18)
save("focus", fo, 0.5)
print("звуки:", sorted(p.name for p in out.glob("*.wav")))
