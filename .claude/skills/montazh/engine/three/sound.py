"""Звуковой дизайн для t2v: голос рассказчика + ветер (синтез) + удары/гул/колокол/сердце/свист из паков пользователя
точно на словах-акцентах, вжухи на смене сцен, нарастание к кульминации. Мастер: линейно до −14 LUFS + пиковый лимитер."""
import subprocess
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

import os
PACK = os.environ.get("T2V_PACK", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pack", "sounds")) + "/"   # исходники звуков пака (skill.ai/pack/sounds)
SR = 48000
_c = {}

def load(name):
    if name not in _c:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", PACK + name, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
        _c[name] = np.frombuffer(raw, np.float32).astype(np.float64)
    return _c[name]

def onset(x):
    a = np.abs(x); h = SR // 200; e = np.array([a[i:i + h].max() for i in range(0, len(a), h)]); return int(np.argmax(e > e.max() * .1)) * h

def mix(voice_path, tm, acc, cuts, P, out):
    v, _ = sf.read(voice_path); v = v if v.ndim == 1 else v.mean(1); N = len(v)
    VR = np.sqrt(np.mean(v[np.abs(v) > 1e-4] ** 2))
    sfx = np.zeros(N); db = lambda x: 10 ** (x / 20)
    def place(name, t, g, start=0.0, dur=None, align=True, fade=.05):
        x = load(name)[int(start * SR):]
        if dur: x = x[:int(dur * SR)]
        x = x / (np.abs(x).max() + 1e-9); f = int(fade * SR); x = x.copy(); x[-f:] *= np.linspace(1, 0, f)
        a = int(t * SR) - (onset(x) if align else 0)
        if a < 0: x = x[-a:]; a = 0
        e = min(N, a + len(x)); sfx[a:e] += x[:e - a] * VR * 4 * db(g)
    def beat(t, g):
        n = int(.35 * SR); x = np.arange(n) / SR
        th = np.sin(2 * np.pi * 52 * x) * np.exp(-x * 22) + .5 * np.sin(2 * np.pi * 95 * x) * np.exp(-x * 40)
        b = np.zeros(int(.6 * SR)); b[:n] += th; k = int(.22 * SR); b[k:k + n] += .7 * th; b /= np.abs(b).max()
        a = int(t * SR); e = min(N, a + len(b)); sfx[a:e] += b[:e - a] * VR * 4 * db(g)
    S = tm["sent"]; dur = tm["dur"]
    # вступление: низкий вжух из тишины, гул на имени
    place("Whoosh long (4).wav", 0.0, -14, align=False); place("impact eric.wav", 0.9, -6)
    # смена сцен — вжухи по кругу
    wh = ["вуш с камерой.wav", "DA - Whoosh Big - 6.mp3", "вуш с камерой.wav", "Whoosh long (3).wav"]
    for i, c in enumerate(cuts[:-1]): place(wh[i % len(wh)], c, -17 if i % 2 else -15, align=not wh[i % len(wh)].startswith("Whoosh long"))
    imp = ["Импакт 4.wav", "Импакт 5.wav"]
    for i, a in enumerate(acc):
        t, kind = a["t"], a.get("sfx", "impact")
        if a.get("riser"): place("Ревилер.wav", t - 2.1, -18, align=False, dur=2.15)
        if kind == "impact": place(imp[i % 2], t, -4); place("impact eric.wav", t, -8)
        elif kind == "thud": place("Wall Hit 1.wav", t, -8); place("impact eric.wav", t, -11)
        elif kind == "bell": place("Импакт (колокольчик).wav", t, -7); place("impact eric.wav", t, -10)
        elif kind == "heart":
            for k in range(4): beat(t - .74 + k * .74, -6)
        elif kind == "swish": place("Резкие вуши.mp3", t - .1, -12, start=2.45, dur=.45)
        elif kind == "arrows":
            for k in range(5): place("Резкие вуши.mp3", t - .12 + k * .33, -15, start=2.45, dur=.45); place(["Wall Hit 2.wav", "Wall Hit 4.wav"][k % 2], t + k * .33, -16)
    # ветер пустыни под всем рассказом, в финале тише
    rng = np.random.default_rng(3); wn = np.cumsum(rng.standard_normal(N)); wn -= np.convolve(wn, np.ones(4801) / 4801, "same")
    wind = sosfilt(butter(2, [120, 900], "bp", fs=SR, output="sos"), wn); tt = np.arange(N) / SR
    wind *= (.65 + .35 * np.sin(2 * np.pi * .07 * tt + 1) * np.sin(2 * np.pi * .023 * tt)) ** 2
    wind = wind / np.sqrt(np.mean(wind ** 2)) * VR * db(-24) * np.clip(tt / 1.5, 0, 1) * np.clip((dur - tt) / 2, 0, 1)
    m = v + sfx + wind
    sf.write(out + ".raw.wav", np.stack([m, m], 1).astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out + ".raw.wav", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float([l for l in r.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out + ".raw.wav", "-af", f"volume={-14 - I:.2f}dB,alimiter=limit=0.84:attack=2:release=80:level=disabled,aresample=48000",
                    "-c:a", "pcm_s16le", out], check=True)
