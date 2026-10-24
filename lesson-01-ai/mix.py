"""Сведение звука: голос + синтезированные звуковые эффекты (без музыки).

Использование: python mix.py timeline.json out.wav
timeline.json: {"total": сек, "voice": [{"t": сек, "file": wav}], "sfx": [{"t": сек, "name": str, "dur": сек}]}
"""
import json
import sys

import numpy as np
import soundfile as sf

SR = 48000
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(SR * d)) / SR


def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)


def lowpass(x, cutoff):
    # однополюсный фильтр; cutoff может быть массивом (развёртка)
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def bell(freqs, d, decay, amp=0.3):
    t = t_(d)
    return sum(np.sin(2 * np.pi * f * t) * np.exp(-t / (decay / (1 + k * 0.4))) / (1 + k) for k, f in enumerate(freqs)) * amp


def whoosh(d=0.55, up=True, amp=0.35):
    n = int(SR * d)
    sweep = np.linspace(400, 5000, n) if up else np.linspace(5000, 400, n)
    x = lowpass(rng.standard_normal(n), sweep) - lowpass(rng.standard_normal(n), sweep * 0.3) * 0.5
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return x * shape * amp / (np.abs(x).max() + 1e-9)


def pop(f0=820, f1=300, d=0.13, amp=0.42):
    t = t_(d)
    f = f1 + (f0 - f1) * np.exp(-t / 0.025)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.04) * amp


def tick(amp=0.18):
    n = int(SR * 0.025)
    x = rng.standard_normal(n)
    x = x - lowpass(x, 2500)  # высокие частоты — «щелчок клавиши»
    return x * env(n, 0.0005, 0.006) * amp


def type_(d):
    out = np.zeros(int(SR * (d + 0.1)))
    t = 0.0
    while t < d:
        s = int(t * SR)
        k = tick(0.05 + 0.03 * rng.random())
        out[s:s + len(k)] += k[: len(out) - s]
        t += 0.06 + 0.07 * rng.random()
    return out


def sparkle(amp=0.16):
    out = np.zeros(int(SR * 1.6))
    for i, f in enumerate([1568, 2093, 2637, 3136, 3951, 2637, 4186]):
        s = int(SR * (i * 0.075 + 0.02 * rng.random()))
        b = bell([f, f * 2.01], 0.9, 0.25, amp)
        out[s:s + len(b)] += b[: len(out) - s]
    return out


def add(*parts):
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[: len(p)] += p
    return out


def chime():
    return add(bell([659, 988, 1319, 1976], 2.2, 0.8, 0.22), np.pad(bell([1319, 1976], 1.8, 0.6, 0.12), (int(SR * 0.09), 0)))


def ding():
    a = bell([1047, 2093, 3140], 1.2, 0.35, 0.22)
    b = bell([1568, 3136], 1.2, 0.4, 0.2)
    out = np.zeros(int(SR * 1.4))
    out[: len(a)] += a
    out[int(SR * 0.11):int(SR * 0.11) + len(b)] += b
    return out


def buzz():
    t = t_(0.32)
    tone = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.5 + np.sin(2 * np.pi * 300 * t) * 0.5
    tone = lowpass(tone, 1400)
    gate = ((t % 0.16) < 0.12).astype(float)
    return tone * gate * env(len(t), 0.005, 0.25) * 0.22


def boop():
    return pop(520, 220, 0.25, 0.4)


def swish():
    return whoosh(0.45, up=False, amp=0.18)


def riser():
    return whoosh(1.0, up=True, amp=0.3) + sparkle(0.08)


def tap():
    # мягкий «стеклянный» щелчок в духе интерфейсов Apple
    return add(pop(1500 + 300 * rng.random(), 1100, 0.09, 0.16), bell([2400], 0.25, 0.05, 0.05))


def thud():
    # мягкий низкий «тук» вместо резкого «бзз»
    t = t_(0.35)
    return np.sin(2 * np.pi * (90 + 60 * np.exp(-t / 0.03)) * t) * env(len(t), 0.003, 0.09) * 0.4


SFX = {"whoosh": lambda d: whoosh(0.7, amp=0.16), "pop": lambda d: tap(), "type": type_, "sparkle": lambda d: sparkle(0.07),
       "chime": lambda d: chime(), "ding": lambda d: ding(), "buzz": lambda d: thud(), "boop": lambda d: tap(),
       "swish": lambda d: whoosh(0.8, up=False, amp=0.12), "riser": lambda d: add(whoosh(1.4, amp=0.18), chime() * 0.5)}


def place(buf, x, t, gain=1.0):
    s = int(t * SR)
    if s >= len(buf):
        return
    x = x[: len(buf) - s]
    buf[s:s + len(x)] += x * gain


def main():
    tl = json.load(open(sys.argv[1]))
    n = int(SR * tl["total"]) + SR
    voice = np.zeros((n, 2))
    fx = np.zeros(n)
    for v in tl["voice"]:
        x, sr = sf.read(v["file"], always_2d=True)
        assert sr == SR
        place(voice, x, v["t"])
    for e in tl["sfx"]:
        place(fx, SFX[e["name"]](e.get("dur", 1.0)), e["t"])
    # эффекты — тише голоса, чуть шире по стерео
    fx = np.stack([fx, np.roll(fx, int(SR * 0.004))], axis=1) * 0.5
    out = voice + fx
    out /= max(1.0, np.abs(out).max() / 0.98)
    sf.write(sys.argv[2], out[: int(SR * tl["total"])], SR, subtype="PCM_24")


if __name__ == "__main__":
    main()
