"""Звук такси-рилса: голос (студийная обработка) + наши звуковые эффекты + городской фон + тихий размытый вокальный фон
(мужской хор «м-м/о-о» в макаме хиджаз, без инструментов). Всё фоновое — кольцевое (бесшовная петля). Мастер −14 LUFS."""
import subprocess, math
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt

SR = 48000; DUR = 42.30; N = int(DUR * SR)
import os
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
PACK = os.environ.get("PACK", HERE + "pack/")                  # папка пака пользователя (в git не кладём)
db = lambda x: 10 ** (x / 20)
rng = np.random.default_rng(42)
tt = np.arange(N) / SR

v, _ = sf.read(HERE + "work/voice_studio.wav"); v = np.pad(v, (0, max(0, N - len(v))))[:N]
VR = np.sqrt(np.mean(v[np.abs(v) > 1e-3] ** 2))

def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], "bp", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, "lp", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "hp", fs=SR, output="sos"), x)
def cfilt(x, H):   # кольцевая фильтрация через БПФ (без шва на петле)
    return np.fft.irfft(np.fft.rfft(x) * H, len(x))
F = np.fft.rfftfreq(N, 1 / SR)
def shape(lo, hi, slope=2):
    h = 1 / np.sqrt(1 + (lo / np.maximum(F, 1)) ** (2 * slope)) if lo else np.ones_like(F)
    if hi: h = h / np.sqrt(1 + (F / hi) ** (2 * slope))
    return h
def norm_rms(x, r=1.0): return x / (np.sqrt(np.mean(x ** 2)) + 1e-12) * r
def env(points):   # огибающая по точкам (время, дБ), кусочно-линейно
    ts, ds = zip(*points); return db(np.interp(tt, ts, ds))

# ---------------- фон: город / салон / дождь (кольцевые) ----------------
def cnoise(): return rng.standard_normal(N)
city = cfilt(cnoise(), shape(40, 380, 2)) * 1.0 + cfilt(cnoise(), shape(300, 2500, 2)) * .35
for c in [3.1, 11.8, 19.5, 27.2, 33.9, 40.6]:          # далёкие проезды машин (кольцом)
    d = ((tt - c + DUR / 2) % DUR) - DUR / 2; e = np.exp(-(d / 1.3) ** 2)
    city += cfilt(cnoise(), shape(200, 1500, 2)) * e * 1.6
cabin = cfilt(cnoise(), shape(30, 160, 3)) * 1.0 + cfilt(cnoise(), shape(160, 600, 2)) * .25
rain = cfilt(cnoise(), shape(1800, 9000, 2)) + cfilt(cnoise(), shape(400, 1800, 2)) * .3
city, cabin, rain = norm_rms(city), norm_rms(cabin), norm_rms(rain)
# где что звучит (дБ относительно голоса)
G_city = env([(0, -27), (2.3, -27), (2.45, -60), (6.5, -60), (6.6, -33), (8.22, -33), (8.25, -90), (9.30, -90), (9.40, -31), (12.4, -31), (12.5, -36),
              (16.90, -36), (16.95, -90), (17.45, -90), (17.9, -33), (21.85, -33), (21.95, -42), (25.5, -42), (25.6, -33), (27.0, -33), (27.1, -42),
              (29.35, -42), (29.45, -35), (31.9, -35), (32.0, -42), (33.25, -42), (33.35, -35), (35.6, -35), (35.75, -27), (38.85, -27), (38.95, -40),
              (41.6, -40), (41.75, -27), (DUR, -27)])
G_cabin = env([(0, -90), (2.33, -90), (2.40, -25), (6.5, -25), (6.6, -40), (8.22, -40), (8.25, -90), (DUR, -90)])
G_rain = env([(0, -90), (1.15, -90), (1.25, -34), (2.3, -34), (2.4, -90), (16.95, -90), (17.45, -90), (17.8, -31), (18.9, -31), (19.2, -40), (21.85, -40), (21.95, -90), (DUR, -90)])
amb = (city * G_city + cabin * G_cabin + rain * G_rain) * VR
amb_st = np.stack([amb, np.roll(amb, 911)], 1)            # лёгкая ширина

# ---------------- вокальный фон (нашид-подобный хор «м-м», размытый) ----------------
def voice_line(notes, base, detune=0.0, delay=0.0, vowel=(330, 760, 2400), bright=1.0):
    # notes: [(полутон, длительность)], итог кольцом на всю длину
    tot = sum(d for _, d in notes); k = DUR / tot
    tl, pl, t0 = [], [], 0.0
    for st, d in notes: tl += [t0, t0 + d * k]; pl += [st, st]; t0 += d * k
    tl = np.array(tl); pl = np.array(pl, float)
    tq = (tt - delay) % DUR
    # плавное легато (глиссандо ~90 мс): сглаживаем ступеньки высоты
    semi = np.interp(tq, tl, pl)
    g = np.hanning(int(.09 * SR)); g /= g.sum(); semi = np.convolve(np.concatenate([semi[-len(g):], semi, semi[:len(g)]]), g, "same")[len(g):-len(g)]
    vib = .28 * np.sin(2 * np.pi * 5.1 * tt + rng.random() * 6) * np.clip(np.sin(np.pi * ((tq - tl[np.searchsorted(tl, tq, side='right') - 1]) / .9)), 0, 1)
    f0 = base * 2 ** ((semi + vib + detune / 100) / 12)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    ph *= (np.floor(ph[-1] / (2 * np.pi)) * 2 * np.pi) / ph[-1]   # целое число периодов -> петля без щелчка
    src = np.zeros(N)
    for h in range(1, 26):
        src += np.sin(h * ph) / h ** (1.35 / bright) * (f0 * h < 4500)
    # форманты (резонаторы) + «носовой» гул
    y = sum(bp(src, f * .82, f * 1.18, 2) * a for f, a in zip(vowel, (1.0, .55, .18)))
    y += lp(src, 300, 2) * .8
    # дыхание между фразами (шум, очень тихо)
    y += bp(rng.standard_normal(N), 600, 3000) * .004
    am = .85 + .15 * np.sin(2 * np.pi * .13 * tt + rng.random() * 6)
    return y * am
D3 = 146.83
# макам хиджаз от D: 0 D, 1 Eb, 4 F#, 5 G, 7 A, 8 Bb, 10 C, 12 D
A = [(7, 1.4), (8, .7), (7, .7), (5, .9), (4, 1.4), (5, .6), (4, .6), (1, .9), (0, 2.6)]
B = [(12, 1.3), (10, .7), (8, .7), (7, 1.2), (8, .6), (7, .6), (5, .9), (4, 1.6), (0, 2.0)]
C = [(4, 1.0), (5, .7), (7, 1.4), (8, .8), (7, .8), (5, .8), (4, 1.0), (1, .8), (0, 2.6)]
MEL = A + B + A + C
lead = voice_line(MEL, D3) + .7 * voice_line(MEL, D3, 7, .035, (360, 820, 2450)) + .7 * voice_line(MEL, D3, -6, .06, (310, 700, 2300))
drone = voice_line([(0, 1)], D3 / 2, 0, 0, (280, 600, 2200), .8) + .6 * voice_line([(7, 1)], D3 / 2, 4, 0, (300, 650, 2200), .8)
choir = norm_rms(lead) + .55 * norm_rms(drone)
# кольцевая реверберация (хвост 3 с) и «размытие»: срез верха 1.4 кГц
irn = int(3.2 * SR); ir = rng.standard_normal(irn) * np.exp(-np.arange(irn) / SR * 2.3); ir = lp(ir, 3000); ir[:int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))
IR = np.zeros(N); IR[:irn] = ir; IRf = np.fft.rfft(IR)
IR2 = np.zeros(N); IR2[:irn] = np.roll(ir, 377); IR2f = np.fft.rfft(IR2)
chf = np.fft.rfft(choir) * shape(90, 1400, 3)
wetL = np.fft.irfft(chf * IRf, N); wetR = np.fft.irfft(chf * IR2f, N); dry = np.fft.irfft(chf, N)
nas = np.stack([.35 * dry + norm_rms(wetL, np.sqrt(np.mean(dry ** 2))) * .9, .35 * dry + norm_rms(wetR, np.sqrt(np.mean(dry ** 2))) * .9], 1)
nas = nas / np.sqrt(np.mean(nas ** 2))
G_nas = env([(0, -25), (8.22, -25), (8.26, -90), (9.30, -90), (9.40, -25), (16.90, -25), (16.95, -90), (17.45, -90), (18.4, -25), (21.85, -25), (21.95, -23),
             (38.85, -23), (38.95, -21), (DUR, -25)])
nas = nas * (G_nas * VR)[:, None]

# ---------------- звуковые эффекты ----------------
sfx = np.zeros((N, 2)); _c = {}
def load(name):
    if name not in _c:
        import os
        path = PACK + name if os.path.exists(PACK + name) else "/home/user/sushi8.github.io/.claude/skills/montazh/engine/sfx_local/" + name
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
        _c[name] = np.frombuffer(raw, np.float32).astype(np.float64)
    return _c[name]
def onset(x):
    a = np.abs(x); h = SR // 400; e = np.array([a[i:i + h].max() for i in range(0, len(a) - h, h)]); return int(np.argmax(e > e.max() * .15)) * h
def peak(x):
    a = np.abs(x); h = SR // 100; e = np.array([np.sqrt(np.mean(a[i:i + h] ** 2)) for i in range(0, len(a) - h, h)]); return int(np.argmax(e)) * h
def put(x, t, g, align="onset", pan=0.0, fade=.03, maxlen=None, lpf=None, hpf=None, stop=None):
    x = np.array(x, float)
    if maxlen: x = x[:int(maxlen * SR)]
    if lpf: x = lp(x, lpf, 4)
    if hpf: x = hp(x, hpf, 2)
    x = x / (np.abs(x).max() + 1e-9); f = int(fade * SR); x[-f:] *= np.linspace(1, 0, f)
    a = int(t * SR) - (onset(x) if align == "onset" else peak(x) if align == "peak" else 0)
    if a < 0: x = x[-a:]; a = 0
    e = min(N, a + len(x)); seg = x[:e - a] * VR * 4 * db(g)
    if stop: s_ = int(stop * SR) - a; seg[max(0, s_):] *= 0 if s_ < len(seg) else 1
    sfx[a:e, 0] += seg * np.sqrt(.5 - pan / 2) * 1.414; sfx[a:e, 1] += seg * np.sqrt(.5 + pan / 2) * 1.414
def P(name, t, g, **k): put(load(name), t, g, **k)
def syn_thump(f0=70, f1=42, d=.35):
    n = int(d * SR); x = np.arange(n) / SR; f = f1 + (f0 - f1) * np.exp(-x * 14)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)
def syn_door():
    n = int(.5 * SR); x = np.arange(n) / SR
    th = syn_thump(85, 48, .5) * 1.0
    body = lp(rng.standard_normal(n), 900, 2) * np.exp(-x * 30) * .6
    latch = bp(rng.standard_normal(n), 2200, 5000, 2) * np.exp(-((x - .012) / .004) ** 2) * 1.2
    rattle = bp(rng.standard_normal(n), 400, 1500) * np.exp(-x * 12) * .15 * (1 + np.sin(2 * np.pi * 38 * x))
    return th + body + latch + rattle
def syn_handle():
    n = int(.25 * SR); x = np.arange(n) / SR
    return bp(rng.standard_normal(n), 1500, 4500, 2) * (np.exp(-((x - .01) / .003) ** 2) + .7 * np.exp(-((x - .09) / .004) ** 2))
def syn_tick(hi=True):
    n = int(.06 * SR); x = np.arange(n) / SR
    return bp(rng.standard_normal(n), 2500 if hi else 1600, 6000 if hi else 3500, 2) * np.exp(-x * 160)
def syn_pass(d=1.6, f0=500, f1=1800):
    n = int(d * SR); x = np.arange(n) / SR; c = d * .5
    e = np.exp(-((x - c) / (d * .22)) ** 2); y = rng.standard_normal(n)
    lo = bp(y, 120, 900, 2); hi_ = bp(y, 900, 4000, 2)
    w = 1 / (1 + np.exp(-(x - c) * 10))       # доплер: до проезда выше, после ниже
    return (lo * (.6 + .4 * w) + hi_ * (1 - w) * .7) * e
def syn_sizzle(d=.55):
    n = int(d * SR); y = bp(rng.standard_normal(n), 2500, 9000, 2)
    cr = (rng.random(n) > .9993) * rng.standard_normal(n) * 6; cr = bp(cr, 1500, 7000)
    return (y * (.7 + .3 * rng.random(n)) + cr) * np.minimum(1, np.arange(n) / (.05 * SR))
def syn_clink():
    n = int(.6 * SR); x = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * x) * np.exp(-x * dcy) * a for f, dcy, a in [(2630, 9, 1), (4120, 14, .6), (5870, 20, .35), (1310, 7, .3)]) * (1 - np.exp(-x * 900))
def syn_boom():
    n = int(1.1 * SR); x = np.arange(n) / SR
    f = 34 + 26 * np.exp(-x * 9); sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 3.2)
    body = lp(rng.standard_normal(n), 260, 4) * np.exp(-x * 7) * .9
    return sub + body
def syn_scratch(src):
    # «скретч пластинки»: читаем звучащий фон туда-обратно с переменной скоростью + шум иглы
    d = .46; n = int(d * SR); x = np.arange(n) / SR
    pos = .12 * SR + np.cumsum(3.4 * np.sin(2 * np.pi * x / .23) * np.exp(-x * 1.5) + .2)
    s = np.interp(np.clip(pos, 0, len(src) - 1), np.arange(len(src)), src)
    spd = np.abs(np.gradient(pos))
    nz = bp(rng.standard_normal(n), 700, 4500) * spd * .35
    y = (s * 2.2 + nz) * np.minimum(1, x / .01) * np.exp(-np.maximum(0, x - .36) * 30)
    return y
def syn_subway(d=.85):
    n = int(d * SR); x = np.arange(n) / SR
    rumble = lp(rng.standard_normal(n), 220, 3) * 1.0
    clack = sum(bp(rng.standard_normal(n), 300, 2500) * np.exp(-((x - c) / .012) ** 2) for c in (.18, .30, .62, .74)) * 1.6
    return rumble + clack

# --- расстановка (время = время ролика) ---
P("sc_camwhoosh.wav", .60, -15, align="peak", pan=-.2)                        # камера опускается к дороге
put(syn_pass(1.5), 1.25, -18, align="none", pan=.3)                             # такси проезжает
put(syn_handle(), 2.10, -20, align="none")                                      # ручка двери
put(syn_door(), 2.37, -9, align="none")                                         # хлопок двери (на склейке внутрь)
for k, tk in enumerate(np.arange(3.40, 6.50, .44)): put(syn_tick(k % 2 == 0), tk, -30, align="none", pan=-.35)   # поворотник
P("ui-pop-up-2-197887.mp3", 6.55, -18)                                          # навигатор
for j, d in enumerate([.12, .36, .58, .80, .99, 1.17, 1.34, 1.50]):              # маршрут перестраивается
    P(["MA_BANT_Modern_Clicks_And_Beeps_2.wav", "MA_BANT_Modern_Clicks_And_Beeps_5.wav", "sc_bleep.wav"][j % 3], 6.55 + d, -22 + j * .6, maxlen=.3, pan=(-.3 if j % 2 else .3))
def typed(text, t0, dt, g, pan=0.0):
    # печать — не на каждую букву: щелчок на начало слова и дальше раз в 3 буквы
    k, j = 0, 0
    for i, ch in enumerate(text):
        if not ch.isalnum(): j = 0; continue
        if j % 3 == 0: P(["aplkey1.wav", "aplkey2.wav", "aplkey3.wav", "aplkey4.wav"][k % 4], t0 + i * dt, g, pan=pan); k += 1
        j += 1
typed("куда-нибудь", 6.95, .055, -27)
# скретч: из звучащего фона перед заморозкой
pre = (amb_st[:, 0] + nas[:, 0])[int(7.6 * SR):int(8.25 * SR)]
put(syn_scratch(pre / (np.abs(pre).max() + 1e-9)), 8.23, -8, align="none")
P("Whoosh long (2).wav", 9.36, -15, align="peak")                               # зум-переход
put(syn_subway(), 9.36, -20, align="none")                                       # метро
P("sc_whclick.wav", 10.10, -23); P("swoosh.wav", 10.80, -25); P("sc_whclick.wav", 11.45, -24)
put(load("Резкие вуши.mp3")[int(2.45 * SR):int(2.9 * SR)], 12.30, -17, align="peak")
typed("Сделай сайт", 12.46, .085, -20, .1)
P("tagpop.wav", 13.50, -18)
typed("Сделай монтаж", 13.66, .062, -20, .1)
P("tagpop.wav", 14.54, -18)
P("231188_Mechanics, Electronics, Micro, Glitch x3 09_cut(0003-0004).mp3", 14.75, -15)   # кривой сайт
P("Interface App 4.wav", 15.20, -19)                                            # «ошибка»
put(syn_boom(), 16.00, -5, align="none"); P("impact eric.wav", 16.01, -13, lpf=320)      # глухой «бум» на «тупой»
P("iphone-keyboard-typing-sound-effect-336778.mp3", 18.92, -22, maxlen=.95)      # руки печатают
typed("тверская, 7", 19.95, .055, -22)
P("App Click 3.wav", 20.62, -17); P("swoosh.wav", 20.70, -27)
P("small_whoosh_chimes_1.wav", 20.74, -24)                                      # маршрут рисуется
P("tink.wav", 21.00, -13)                                                       # мягкий «дзинь»
P("sc_whoosh.wav", 21.90, -16, align="peak")                                     # в белый
P("blockpop.wav", 21.93, -21); P("linepop.wav", 22.01, -23); P("swoosh.wav", 22.12, -29); P("linepop.wav", 22.45, -25); P("linepop.wav", 22.69, -25)
put(load("Резкие вуши.mp3")[int(2.45 * SR):int(2.9 * SR)], 23.85, -19, align="peak")
P("tagpop.wav", 23.93, -20); P("linepop.wav", 24.44, -23); P("swoosh.wav", 24.64, -29)
put(syn_sizzle(), 25.55, -24, align="none"); P("swoosh.wav", 26.05, -28); put(syn_clink(), 26.62, -24, align="none")
put(load("Резкие вуши.mp3")[int(2.45 * SR):int(2.9 * SR)], 27.10, -19, align="peak")
P("tagpop.wav", 27.15, -20); P("linepop.wav", 27.63, -24); P("linepop.wav", 27.91, -24); P("linepop.wav", 28.35, -24); P("swoosh.wav", 28.42, -29)
P("Whoosh long (3).wav", 29.40, -17, align="peak")
P("App Click 1.wav", 30.20, -15); P("notification3.mp3", 30.88, -13)            # «Заказать» / «Заказ принят»
put(load("Резкие вуши.mp3")[int(2.45 * SR):int(2.9 * SR)], 31.95, -19, align="peak")
P("tagpop.wav", 32.03, -20); P("linepop.wav", 32.53, -23)
P("sc_whoosh.wav", 33.30, -17, align="peak"); P("swoosh.wav", 33.55, -27); P("sc_whclick.wav", 34.30, -24); P("swoosh.wav", 34.6, -28)
P("Whoosh long (4).wav", 35.70, -15, align="peak")
put(syn_pass(1.2), 35.85, -19, align="none", pan=-.3); P("DA - Whoosh Big - 6.mp3", 36.85, -19, align="peak"); put(syn_pass(.8), 36.95, -18, align="none", pan=.3)
put(load("Резкие вуши.mp3")[int(2.45 * SR):int(2.9 * SR)], 37.75, -19, align="peak")
P("sc_chimes.wav", 38.27, -14)                                                  # «Вы прибыли»
P("sc_flash.wav", 38.90, -17); P("Импакт (колокольчик).wav", 39.00, -13)         # «Подпишись»
P("blockpop.wav", 39.48, -23); P("blockpop.wav", 39.62, -24)
P("App Click 5.wav", 40.90, -15); P("bells.wav", 41.00, -19, maxlen=1.0)
P("sc_whoosh.wav", 41.72, -15, align="peak", stop=DUR - .02)                     # в город (петля)

# ---------------- сведение ----------------
vo = np.stack([v, v], 1)
duck = np.convolve((np.abs(v) > VR * .25).astype(float), np.ones(int(.25 * SR)) / (.25 * SR), "same")
duck = 1 - .35 * np.clip(duck * 3, 0, 1)                                   # фон уступает голосу
mix = vo + sfx + (amb_st + nas) * duck[:, None]
sf.write(HERE + "work/mix_raw.wav", mix.astype(np.float32), SR, subtype="FLOAT")
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", HERE + "work/mix_raw.wav", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float([l for l in r.splitlines() if l.strip().startswith("I:")][-1].split()[1])
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", HERE + "work/mix_raw.wav", "-af", f"volume={-14 - I:.2f}dB,alimiter=limit=0.74:attack=2:release=60:level=disabled",
                "-ar", "48000", "-c:a", "pcm_s16le", HERE + "work/mix.wav"], check=True)
for nm, x in [("голос", vo), ("эффекты", sfx), ("фон", amb_st), ("вокальный фон", nas)]:
    print(f"{nm:14s} RMS {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12):6.1f} дБ  пик {20 * np.log10(np.abs(x).max() + 1e-12):6.1f}")
print("исходно", I, "LUFS")
