"""Звук для кино-монтажа: голос (студийная обработка 35 %) + ветер пустыни + сердцебиение + удары/вжухи/нарастания
из паков пользователя точно на словах; с начала чтения Корана — только голос чтеца, без эффектов."""
import json, subprocess
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt

HERE = "/tmp/claude-0/-home-user-sushi8-github-io/e45a17fa-f666-558d-8135-60ef79d3ed2c/scratchpad/musab/"
PACK = "/tmp/claude-0/-home-user-sushi8-github-io/e45a17fa-f666-558d-8135-60ef79d3ed2c/scratchpad/pack2/files/"
SR, DUR = 48000, 49.95
N = int(DUR * SR)
QURAN = 35.6                                    # дальше — ни одного эффекта

def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)

# 1) голос: студийная обработка 35 % (эквалайзер к студийному спектру, компрессия, де-эссер)
import os
if not os.path.exists(HERE + "kino/voice.wav"): subprocess.run(["/root/venv-video/bin/python", "-I", "/home/user/sushi8.github.io/video-tools/voice_pro.py", HERE + "src.mp4", HERE + "kino/voice.wav", "--amount", "0.35"], check=True)
v, _ = sf.read(HERE + "kino/voice.wav"); v = v if v.ndim == 1 else v.mean(1)
voice = np.zeros(N); voice[:min(N, len(v))] = v[:N]

def db(x): return 10 ** (x / 20)
def rms(x): return np.sqrt(np.mean(x ** 2) + 1e-12)
VR = rms(voice[voice != 0]) if np.any(voice) else 0.05

# 2) ветер пустыни: «коричневый» шум, полоса 120–900 Гц, медленные порывы
rng = np.random.default_rng(3)
wn = np.cumsum(rng.standard_normal(N)); wn -= np.convolve(wn, np.ones(4801) / 4801, "same")
wind = sosfilt(butter(2, [120, 900], "bp", fs=SR, output="sos"), wn)
tt = np.arange(N) / SR
wind *= (0.65 + 0.35 * np.sin(2 * np.pi * 0.07 * tt + 1) * np.sin(2 * np.pi * 0.023 * tt)) ** 2
wind = wind / rms(wind) * VR * db(-26)
env = np.clip(tt / 1.5, 0, 1) * np.clip((QURAN - 0.2 - tt) / 0.8, 0, 1)
wind *= env

# 3) сердцебиение (синтез): «тук-тук» — низкий синус с быстрым спадом
def beat():
    n = int(0.35 * SR); x = np.arange(n) / SR
    th = np.sin(2 * np.pi * 52 * x) * np.exp(-x * 22) + 0.5 * np.sin(2 * np.pi * 95 * x) * np.exp(-x * 40)
    out = np.zeros(int(0.6 * SR)); out[:n] += th; k = int(0.22 * SR); out[k:k + n] += 0.7 * th
    return out / np.abs(out).max()

sfx = np.zeros(N)
def onset(x):
    a = np.abs(x); h = SR // 200; env_ = np.array([a[i:i + h].max() for i in range(0, len(a), h)])
    return int(np.argmax(env_ > env_.max() * 0.1)) * h
_cache = {}
def place(name, t, gain_db, start=0.0, dur=None, align=True, fade=0.05):
    """Звук из пака: его удар (onset) ставится ровно на t."""
    if t >= QURAN: return
    if name not in _cache: _cache[name] = load(PACK + name)
    x = _cache[name][int(start * SR):]
    if dur: x = x[:int(dur * SR)]
    x = x / (np.abs(x).max() + 1e-9)
    f = int(fade * SR); x = x.copy(); x[-f:] *= np.linspace(1, 0, f)
    a = int(t * SR) - (onset(x) if align else 0)
    if a < 0: x = x[-a:]; a = 0
    end = min(N, a + len(x), int(QURAN * SR)); sfx[a:end] += x[:end - a] * VR * 3.2 * db(gain_db + 4)
def place_arr(x, t, gain_db):
    a = int(t * SR); end = min(N, a + len(x)); sfx[a:end] += x[:end - a] * VR * 3.2 * db(gain_db)

BOOM, IMP4, IMP5, BELL = "impact eric.wav", "Импакт 4.wav", "Импакт 5.wav", "Импакт (колокольчик).wav"
place("Whoosh long (4).wav", 0.0, -16, align=False)            # вход: низкий вжух из тишины
place(BOOM, 0.16, -6)                                           # «Мусаб» — гул
place("DA - Whoosh Big - 6.mp3", 1.13, -12)                     # появляется картинка
for t in (3.26, 5.10): place("вуш с камерой.wav", t, -13)       # смена угла
place("Whoosh long (3).wav", 7.14, -18, align=False)            # медленный наезд
place(IMP4, 8.20, -5); place(BOOM, 8.20, -8)                    # «восьмидесяти»
place("Wall Hit 4.wav", 9.37, -16)
place("Резкие вуши.mp3", 10.97, -11, start=2.45, dur=0.45)      # взмах меча
place(IMP5, 11.56, -4); place(BOOM, 11.56, -8)                  # «правую»
place("вуш с камерой.wav", 12.77, -18)
place(IMP4, 15.72, -4); place(BOOM, 15.72, -8)                  # «левую»
place("Wall Hit 1.wav", 16.88, -9); place(BOOM, 16.88, -12)     # «колени» — глухой удар
for t in (17.95, 18.68, 19.42, 20.16): place_arr(beat(), t, -7) # сердце на «грудью»
for t in (20.60, 20.93, 21.73, 23.10, 24.47, 25.60):             # копья: свист + удар
    place("Резкие вуши.mp3", t - 0.12, -15, start=2.45, dur=0.45); place("Wall Hit 2.wav", t, -15)
place("Ревилер.wav", 22.40 - 2.1, -20, align=False, dur=2.15)    # нарастание к «Таким был Мусаб…»
place(BELL, 22.40, -8); place(BOOM, 22.40, -10)
for t in (26.75, 27.27, 27.91): place("Wall Hit 4.wav", t, -17)
place("DA - Whoosh Big - 6.mp3", 28.40, -14)
place(IMP5, 29.47, -8)                                          # «жертвовал»
place("Резкие вуши.mp3", 30.47, -16, start=2.45, dur=0.45)
place("Whoosh long (3).wav", 31.90, -19, align=False)
place(IMP4, 34.07, -6); place(BOOM, 34.07, -9)                  # «разрывали»
place("выспышка.mp3", 34.73, -15)

mix = voice + sfx + wind
sf.write(HERE + "kino/mix_raw.wav", np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")
# мастер: одна линейная подгонка до −14 LUFS (динамика ударов сохраняется), затем только пиковый лимитер −1.5 дБ
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", HERE + "kino/mix_raw.wav", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float([l for l in r.splitlines() if l.strip().startswith("I:")][-1].split()[1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", HERE + "kino/mix_raw.wav", "-af",
                f"volume={-14 - I:.2f}dB,alimiter=limit=0.84:attack=2:release=80:level=disabled,aresample=48000",
                "-c:a", "pcm_s16le", HERE + "kino/mix.wav"], check=True)
print("звук готов: голос + эффекты + ветер")
