"""Голос «как с хорошего микрофона» из петлички/телефона.
Использование: python voice_pro.py вход выход.wav [--strength 1.0] [--max 11] [--air -20] [--report]
(по умолчанию — вариант, утверждённый на петличке пользователя: верх +9…11 дБ к эталону, «воздух» −20 дБ)
Цепочка: 48 кГц моно -> срез НЧ 70 Гц -> подгоночный эквалайзер (match EQ) к спектру студийного голоса
(средний спектр речи этой записи сравнивается с эталонной кривой, поправка сглажена по 1/3 октавы, подъём ≤ +11 дБ, спад ≤ −6 дБ)
-> «воздух» 12–16 кГц (гармонический эксайтер, если верх срезан) -> де-эссер -> компрессор 3:1 + выравниватель 2:1 -> лимитер −1.5 дБ -> паузы исходника снова тишина (фон и щелчки −36 дБ).
Шумодав не включается, если шум в паузах ниже −70 дБ (на чистой записи он только портит тембр)."""
import subprocess, sys, tempfile, os
import numpy as np, soundfile as sf
from scipy.signal import firwin2, fftconvolve, butter, sosfiltfilt

src, dst = sys.argv[1], sys.argv[2]
STRENGTH = float(sys.argv[sys.argv.index("--strength") + 1]) if "--strength" in sys.argv else 1.0
SR = 48000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).astype(np.float64)

# 1. срез НЧ (гул, удары по петличке)
x = sosfiltfilt(butter(4, 70, "hp", fs=SR, output="sos"), x)

# 2. анализ: средний спектр звучащих кадров и шум
N = 4096; hop = 1024
frames = np.lib.stride_tricks.sliding_window_view(x, N)[::hop] * np.hanning(N)
lvl = 10 * np.log10((frames ** 2).mean(1) + 1e-12)
speech = lvl > np.percentile(lvl, 55)
S = (np.abs(np.fft.rfft(frames[speech], axis=1)) ** 2).mean(0)
f = np.fft.rfftfreq(N, 1 / SR)
noise_db = np.percentile(lvl, 8)
# сглаживание по 1/3 октавы
def smooth(spec_db):
    out = np.empty_like(spec_db)
    for i, fi in enumerate(f):
        m = (f >= fi / 2 ** (1 / 6)) & (f <= fi * 2 ** (1 / 6))
        out[i] = spec_db[m].mean() if m.any() else spec_db[i]
    return out
Sdb = smooth(10 * np.log10(S + 1e-20))
# эталон: долговременный спектр студийного голоса (крупная мембрана, близко), дБ относительно 400 Гц
TF = [20, 60, 100, 160, 250, 400, 630, 1000, 1600, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]
TD = [-30, -12, -4, -1, 0, 0, -2, -5, -8, -10, -10.5, -11, -12.5, -14, -16, -18, -21, -25, -34]
tgt = np.interp(np.log10(np.maximum(f, 20)), np.log10(TF), TD)
ref = Sdb[(f > 250) & (f < 500)].mean()
cur = Sdb - ref
top = f[np.where(cur > -60)[0].max()] if (cur > -60).any() else 20000      # где кончается полезный верх (mp3/петличка)
corr = (tgt - cur) * STRENGTH
MAXB = float(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 11
corr = np.clip(corr, -6, MAXB)
corr[f < 70] = 0
corr[f > top * 0.97] = corr[np.argmin(np.abs(f - top * 0.9))]           # выше среза не задираем (там пусто — займётся эксайтер)
corr = smooth(corr)
fir = firwin2(4095, np.r_[f / (SR / 2)], 10 ** (corr / 20), fs=2)
y = fftconvolve(x, fir, "full")[2047:2047 + len(x)]

# 3. «воздух»: если верх срезан ниже 15 кГц — гармоники из полосы 5–10 кГц, мягко, выше 11 кГц
if top < 15000:
    band = sosfiltfilt(butter(4, [5000, min(10000, top * 0.95)], "bp", fs=SR, output="sos"), y)
    harm = np.abs(band)                                                  # выпрямление -> вторая гармоника (10–20 кГц)
    harm = sosfiltfilt(butter(4, 11000, "hp", fs=SR, output="sos"), harm)
    AIR = float(sys.argv[sys.argv.index("--air") + 1]) if "--air" in sys.argv else -20
    g = np.sqrt((y ** 2).mean()) / (np.sqrt((harm ** 2).mean()) + 1e-12) * 10 ** (AIR / 20)
    y = y + harm * g

y = y / (np.abs(y).max() + 1e-9) * 0.5
tmp = tempfile.mkdtemp()
sf.write(f"{tmp}/a.wav", y.astype(np.float32), SR, subtype="FLOAT")
# 4–6. де-эссер, двухступенчатая компрессия, лимитер (ffmpeg)
den = "" if noise_db < -70 else "afftdn=nr=8:nf=-50,"
chain = (den + "deesser=i=0.35:m=0.5:f=0.55:s=o,"
         "acompressor=threshold=-22dB:ratio=3:attack=4:release=70:knee=4:makeup=2,"
         "acompressor=threshold=-16dB:ratio=2:attack=20:release=250:knee=6:makeup=1.5,"
         "alimiter=limit=0.84:attack=3:release=40:level=disabled,"
         "loudnorm=I=-16:TP=-1.5:LRA=7,aresample=48000")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{tmp}/a.wav", "-af", chain, "-ac", "1", "-c:a", "pcm_f32le", f"{tmp}/b.wav"], check=True)
# 7. тишина остаётся тишиной: где в ИСХОДНИКЕ пауза (ниже пика −48 дБ, с запасом 80 мс вокруг звука), плавно гасим
#    поднятый компрессией/эквалайзером фон и щелчки (−36 дБ, переходы 25 мс). Хвосты слов и вдохи не трогаем.
z, _ = sf.read(f"{tmp}/b.wav")
h = SR // 100
env = np.sqrt(np.convolve(x ** 2, np.ones(h) / h, "same") + 1e-20)
edb = 20 * np.log10(env)
loud = edb > edb.max() - 48
pad = int(0.08 * SR)
loud = np.convolve(loud.astype(float), np.ones(2 * pad + 1), "same") > 0
gain = np.where(loud, 1.0, 10 ** (-36 / 20))
ramp = np.hanning(int(0.025 * SR)); ramp /= ramp.sum()
gain = np.convolve(gain, ramp, "same")
lag = 141                                                             # задержка лимитера (≈3 мс) — маску сдвигаем следом
gain = np.concatenate([np.ones(lag), gain])[:len(z)]
sf.write(dst, (z[:len(gain)] * gain).astype(np.float32), SR, subtype="PCM_16")
if "--report" in sys.argv:
    print(f"шум в паузах {noise_db:.1f} дБ, полезный верх до {top:.0f} Гц, сила {STRENGTH}")
    for a, b in [(100, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 12000), (12000, 16000)]:
        m = (f >= a) & (f < b)
        print(f"  {a:5d}-{b:5d} Гц: было {cur[m].mean():6.1f}  эталон {tgt[m].mean():6.1f}  поправка {corr[m].mean():+5.1f} дБ")
