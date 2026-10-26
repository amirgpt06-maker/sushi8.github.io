"""Звуковой дизайн «Рыцарь против Ти-Рекса»: синтез рёва, шагов, лязга лат, свиста копья, ударов. Без музыки.

Использование: python sfx_knight.py work_dir room_tone.wav out.wav
"""
import json
import sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, find_peaks, lfilter, sosfilt

SR = 48000
FPS = 30
rng = np.random.default_rng(11)
W = sys.argv[1]
S = json.load(open(f"{W}/solve.json"))
N = len(S["joints"])
DUR = N / FPS + 1.5
out = np.zeros((int(DUR * SR), 2))


def t_(d):
    return np.arange(int(d * SR)) / SR


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)


def place(x, t, gain=1.0, pan=0.0):
    s = int(t * SR)
    if s >= len(out) or s + len(x) <= 0:
        return
    if s < 0:
        x, s = x[-s:], 0
    x = x[: len(out) - s]
    l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    out[s:s + len(x), 0] += x * gain * l
    out[s:s + len(x), 1] += x * gain * r


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


# ---------- Ти-Рекс ----------
def roar(d, f0=70, bright=1.0, intensity=1.0, shriek=False):
    """Голосовой источник (импульсы с дрожащей высотой) -> форманты пасти -> рык (АМ) -> сатурация."""
    t = t_(d)
    n = len(t)
    env = np.minimum(1, t / 0.18) * np.minimum(1, (d - t) / (0.35 * d)) ** 1.3
    pitch = f0 * (1 + 0.25 * np.sin(np.pi * t / d)) * (1 + 0.06 * lp(rng.standard_normal(n), 6) * 8)
    if shriek:
        pitch *= 1.0 + 1.6 * np.exp(-t / 0.5)
    ph = 2 * np.pi * np.cumsum(pitch) / SR
    src = sum(np.sin(k * ph) / k ** 0.8 for k in range(1, 40))                    # богатая гармониками пила
    src += 0.6 * np.sin(0.5 * ph)                                                # субгармоника — «грудь»
    src += 0.9 * lp(rng.standard_normal(n), 3500) * (0.6 + 0.4 * np.sin(ph))     # хрип/воздух
    growl = 1 + 0.55 * np.sin(2 * np.pi * (28 + 6 * np.sin(t * 3)) * t)          # рычащая модуляция
    src *= growl
    # форманты: открытие пасти двигает их вверх по ходу рёва
    op = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7
    y = np.zeros(n)
    for fc, bw, g in ((280, 140, 1.0), (650, 260, 0.8 * bright), (1400, 500, 0.45 * bright), (2600, 900, 0.2 * bright)):
        # переменный формант: собираем из трёх фиксированных полос с перекрёстным смешиванием
        lo_b = bp(src, fc * 0.75 - bw / 2, fc * 0.75 + bw / 2)
        hi_b = bp(src, fc * 1.25 - bw / 2, fc * 1.25 + bw / 2)
        y += g * (lo_b * (1 - op) + hi_b * op)
    y += 0.5 * lp(src, 180)                                                      # низ, который «чувствуется»
    y = np.tanh(2.2 * intensity * norm(y)) * env
    return norm(y)


def growl_low(d):
    t = t_(d)
    n = len(t)
    src = lp(rng.standard_normal(n), 250) * 6
    src *= 1 + 0.8 * np.sin(2 * np.pi * 22 * t + 3 * np.sin(2 * np.pi * 0.7 * t))
    ph = 2 * np.pi * np.cumsum(45 + 6 * np.sin(2 * np.pi * 0.5 * t)) / SR
    src += 0.6 * np.sign(np.sin(ph)) * 0.5
    env = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.8)
    return norm(lp(np.tanh(src), 600)) * env


def breath(d, f=900):
    t = t_(d)
    x = bp(rng.standard_normal(len(t)), f * 0.5, f * 1.6) * np.sin(np.pi * t / d) ** 2
    return norm(x)


def snap():
    t = t_(0.35)
    click = hp(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.006)
    thump = np.sin(2 * np.pi * (90 + 120 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.07)
    return norm(click * 0.8 + thump)


def footstep(big=1.0):
    t = t_(1.2)
    thump = np.sin(2 * np.pi * (34 + 40 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.25)
    crunch = lp(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.05) * 0.5
    rattle = bp(rng.standard_normal(len(t)), 2000, 6000) * np.exp(-((t - 0.08) / 0.12) ** 2) * 0.08  # дребезг в комнате
    return norm(thump + crunch + rattle) * big


# ---------- рыцарь ----------
def clank(base=None):
    base = base or rng.uniform(420, 900)
    t = t_(0.6)
    x = sum(a * np.sin(2 * np.pi * base * k * t + rng.uniform(0, 6)) * np.exp(-t / (dcy))
            for k, a, dcy in ((1.0, 1, 0.20), (2.76, 0.7, 0.12), (5.40, 0.5, 0.08), (8.93, 0.35, 0.05), (13.3, 0.2, 0.03)))
    x += hp(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.01) * 0.8
    return norm(x)


def chain_rustle(d=0.35):
    t = t_(d)
    x = np.zeros(len(t))
    for _ in range(int(d * 60)):
        s = rng.integers(0, len(t) - 2000)
        x[s:s + 2000] += clank(rng.uniform(2500, 5000))[:2000] * rng.uniform(0.1, 0.4)
    return norm(hp(x, 1500)) * np.sin(np.pi * t / d)


def whoosh(d=0.35, f0=300, f1=2500):
    t = t_(d)
    n = len(t)
    x = rng.standard_normal(n)
    y = np.zeros(n)
    fc = np.geomspace(f0, f1, 6)
    for k, f in enumerate(fc):
        w = np.exp(-((t / d - (k + 0.5) / 6) / 0.22) ** 2)
        y += bp(x, f * 0.7, f * 1.3) * w
    return norm(y) * np.sin(np.pi * t / d) ** 2


def body_hit():
    t = t_(0.8)
    thud = np.sin(2 * np.pi * (60 + 90 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.12)
    crack = hp(rng.standard_normal(len(t)), 800) * np.exp(-t / 0.015)
    return norm(thud + 0.6 * crack)


def stab():
    """Удар копья в плоть: тяжёлый удар + влажное «хлюп» + бульканье."""
    t = t_(1.4)
    thud = np.sin(2 * np.pi * (48 + 110 * np.exp(-t / 0.025)) * t) * np.exp(-t / 0.18)
    tear = bp(rng.standard_normal(len(t)), 300, 2500) * np.exp(-t / 0.08)
    wet = np.zeros(len(t))
    for _ in range(26):
        s = int(rng.uniform(0.02, 0.9) * SR)
        f = rng.uniform(250, 900)
        b = t_(0.06)
        blob = np.sin(2 * np.pi * f * (1 + 2 * b) * b) * np.exp(-b / 0.015)
        wet[s:s + len(b)] += blob[: len(wet) - s] * rng.uniform(0.2, 0.6) * np.exp(-s / SR / 0.5)
    return norm(thud + 0.7 * tear + 0.5 * wet)


def splatter():
    t = t_(1.0)
    x = np.zeros(len(t))
    for _ in range(40):
        s = int(rng.uniform(0.05, 0.8) * SR)
        b = hp(rng.standard_normal(600), 1200) * np.exp(-np.arange(600) / 80)
        x[s:s + 600] += b * rng.uniform(0.1, 0.5)
    return norm(x)


def boom():
    t = t_(2.5)
    x = np.sin(2 * np.pi * (30 + 25 * np.exp(-t / 0.2)) * t) * np.exp(-t / 0.9)
    x += lp(rng.standard_normal(len(t)), 300) * np.exp(-t / 0.4) * 0.4
    return norm(x)


def room_ir(d=0.7):
    t = t_(d)
    ir = rng.standard_normal(len(t)) * np.exp(-t / 0.16)
    ir = lp(ir, 5000)
    ir[0] = 4
    return ir / np.abs(ir).sum() * 6


f2t = lambda f: f / FPS
# --- Ти-Рекс ---
for f, big in ((4, 0.6), (20, 0.8), (36, 0.9), (100, 0.7), (180, 0.8), (248, 1.0), (280, 0.9)):
    place(footstep(big), f2t(f), 0.55, pan=0.6)
place(growl_low(2.0), f2t(16), 0.30, pan=0.5)
place(breath(0.8, 700), f2t(50), 0.12, pan=0.5)
place(roar(1.0, 62, 1.0, 1.2), f2t(64), 0.85, pan=0.45)
place(snap(), f2t(113), 0.7, pan=0.3)
place(breath(0.6, 1200), f2t(132), 0.15, pan=0.5)     # шипение
place(roar(0.5, 85, 1.2, 1.0), f2t(145), 0.55, pan=0.5)
place(growl_low(1.2), f2t(160), 0.25, pan=0.5)
place(snap(), f2t(201), 0.55, pan=0.3)
place(roar(0.6, 95, 1.3, 1.1), f2t(206), 0.7, pan=0.45)
place(roar(1.0, 58, 1.0, 1.3), f2t(224), 0.95, pan=0.5)
place(roar(1.1, 120, 1.5, 1.2, shriek=True), f2t(263), 1.0, pan=0.45)
place(growl_low(1.5), f2t(276), 0.35, pan=0.6)

# --- рыцарь: лязг лат и свист копья по пикам скорости рук ---
J = np.array(S["joints"])
f_px = S["f"]
uv = J[:, :, :2] / J[:, :, 2:3] * f_px
spd = np.linalg.norm(np.diff(uv[:, [15, 16]], axis=0), axis=2).max(1)
spd = np.convolve(spd, np.ones(3) / 3, "same")
peaks, props = find_peaks(spd, height=18, distance=8)
for p in peaks:
    v = min(1.0, spd[p] / 60)
    place(whoosh(0.32, 250, 2200 + 1500 * v), f2t(p - 4), 0.22 + 0.4 * v, pan=-0.1)
    place(clank(), f2t(p + 1), 0.10 + 0.12 * v, pan=-0.2)
    place(chain_rustle(0.3), f2t(p - 2), 0.10 * v, pan=-0.2)
print("взмахов:", len(peaks), list(peaks))

# --- удары ---
place(body_hit(), f2t(204), 0.8, pan=0.3)
place(clank(380), f2t(204), 0.35, pan=0.2)
place(boom(), f2t(261), 0.55)
place(stab(), f2t(261), 1.0, pan=0.3)
place(splatter(), f2t(263), 0.35, pan=0.3)

# --- комната: реверберация + тихая подложка из оригинала ---
wet = np.stack([fftconvolve(out[:, c], room_ir(), mode="full")[: len(out)] for c in range(2)], 1)
mix = out * 0.85 + wet * 0.35
tone, sr = sf.read(sys.argv[2])
tone = tone if tone.ndim == 1 else tone.mean(1)
tone = tone[: len(mix)]
mix[: len(tone)] += (tone * 10 ** (18 / 20))[:, None] * 0.5
mix = mix[: int(N / FPS * SR)]
mix /= np.abs(mix).max() / 0.95
sf.write(sys.argv[3], mix, SR, subtype="PCM_24")
print("звук готов", mix.shape[0] / SR, "с")
