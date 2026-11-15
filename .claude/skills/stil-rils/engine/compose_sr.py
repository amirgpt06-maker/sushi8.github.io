"""«Стиль рилс»: сборка. Основа (видео без текста) + слой PNG из render_sr.js + fx.json + звуки событий -> готовый mp4.
python compose_sr.py base.mp4 overlay_dir cues.json out.mp4 [--mix mix.wav]

Что делает с основой по fx кадра: размытие и затемнение под вставками, матовое стекло под плашкой (сильное размытие
внутри скруглённого прямоугольника), вспышка-пересвет. Всегда: тёмный градиент снизу. Звуки — cues["events"]:
[{"t": сек, "snd": "pop", "db": -6}], файлы — только из sfx_local (нарезка из папки пользователя «isla pac»); громкость к голосу.
"""
import json, os, subprocess, sys
import numpy as np, cv2, soundfile as sf

a = sys.argv[1:]; mix_f = None; AUDIO_ONLY = "--audio-only" in a
if AUDIO_ONLY: a.remove("--audio-only")
if "--mix" in a: i = a.index("--mix"); mix_f = a[i + 1]; del a[i:i + 2]
base, ov, cues_f, out = a
C = json.load(open(cues_f, encoding="utf-8")); FX = json.load(open(os.path.join(ov, "fx.json")))
W, H, FPS, SR = 1080, 1920, C.get("fps", 30), 48000
N = round(C["duration"] * FPS)
HERE = os.path.dirname(os.path.abspath(__file__)); ENG = os.path.abspath(os.path.join(HERE, "../../montazh/engine"))

# ---------- звук: основа (голос + вжухи + фон) и события слоя ----------
src = mix_f or base
y = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
L = int(C["duration"] * SR); mix = np.zeros(L); mix[:min(L, len(y))] = y[:L]
VR = C.get("voice_rms") or float(np.sqrt(np.mean(y[np.abs(y) > 1e-3] ** 2)))
cache = {}
def snd(name):
    if name not in cache:
        cache[name] = None
        for d in (os.path.join(ENG, "sfx_local"),):                 # только звуки из папки пользователя; синтез движка не берём
            for ext in (".wav", ".mp3"):
                f = os.path.join(d, name + ext)
                if os.path.exists(f) and cache[name] is None:
                    s = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
                    cache[name] = s / (np.abs(s).max() + 1e-9)
    return cache[name]
# Громкость эффекта задаётся относительно речи: ev["lvl"] = на сколько дБ самый громкий кусок звука (50 мс) тише/громче
# уровня речи (75-й перцентиль 50-мс окон). По референсам: вжух примерно на уровне голоса (чистые звуки в паузах речи),
# остальные — тише вжуха на столько же, на сколько в замере референсов (поп −5, щелчок −11, клавиша −13 дБ).
def win_rms(x, n=int(0.05 * SR)):
    k = max(1, len(x) // n); return np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-12) if len(x) >= n else np.array([np.sqrt((x ** 2).mean() + 1e-12)])
_w = win_rms(mix); SPR = float(np.percentile(_w[_w > _w.max() * 0.05], 75)); VPK = float(np.percentile(np.abs(mix), 99.9))
miss = set(); rep = []
for ev in C.get("events", []):
    s = snd(ev["snd"])
    if s is None: miss.add(ev["snd"]); continue
    if ev.get("max"): s = s[:int(ev["max"] * SR)] * np.minimum(1, (int(ev["max"] * SR) - np.arange(min(len(s), int(ev["max"] * SR)))) / (0.03 * SR))
    if "lvl" in ev:
        g = SPR * 10 ** (ev["lvl"] / 20) / float(win_rms(s).max())
        g = min(g, VPK * 10 ** (ev.get("cap", -1) / 20) / (np.abs(s).max() + 1e-9))   # пик эффекта не выше пика голоса
    else: g = VR * 4 * 10 ** (ev.get("db", -6) / 20)
    a0 = int(max(0, ev["t"]) * SR); e = min(L, a0 + len(s))
    if e > a0: mix[a0:e] += s[:e - a0] * g; rep.append((round(ev["t"], 2), ev["snd"], round(float(20 * np.log10(g * win_rms(s).max() / SPR + 1e-9)), 1)))
if miss: raise SystemExit(f"нет звуков из пака пользователя: {sorted(miss)} — запусти engine/pack_sr.py (подставлять свои звуки нельзя)")
print("звуков:", len(rep), "= 1 на", round(C["duration"] / max(1, len(rep)), 1), "с; уровень к речи, дБ:", rep)
pk = np.abs(mix).max()
if pk > 0.98: mix *= 0.98 / pk
wav = out + ".wav"; sf.write(wav, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")

if AUDIO_ONLY:                                         # картинка уже собрана (out существует): меняем только звук
    tmp = out + ".v.mp4"; os.replace(out, tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", "-shortest", out], check=True)
    os.remove(tmp); os.remove(wav); print("готово (только звук):", out); sys.exit(0)

# ---------- картинка ----------
grad = np.ones((H, 1, 1), np.float32)
g0 = int(H * 0.68); grad[g0:, 0, 0] = 1 - 0.42 * ((np.arange(H - g0) / (H - g0)) ** 1.5)       # тёмный градиент снизу
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", base, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", "-shortest", out], stdin=subprocess.PIPE)
last = None; adim = 0.0
for i in range(N):
    raw = dec.stdout.read(W * H * 3)
    fr = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255 if len(raw) == W * H * 3 else last
    last = fr; f = FX.get(str(i), {})
    img = fr
    if f.get("blur", 0) > 0.4: img = cv2.GaussianBlur(img, (0, 0), float(f["blur"]))
    img = img * grad
    if f.get("dim", 0) > 0.005: img = img * (1 - float(f["dim"]))
    g = f.get("glass")
    if g and g[5] > 0.01 and g[2] > 8 and g[3] > 8:                      # матовое стекло: под плашкой основа сильно размыта и чуть светлее
        x0, y0, w, h, r, al = g; x0, y0, w, h = int(round(x0)), int(round(y0)), int(round(w)), int(round(h)); r = int(max(2, min(r, w / 2, h / 2)))
        x1, y1 = min(W, x0 + w), min(H, y0 + h); x0, y0 = max(0, x0), max(0, y0)
        if x1 > x0 and y1 > y0:
            pad = 60; yy0, yy1, xx0, xx1 = max(0, y0 - pad), min(H, y1 + pad), max(0, x0 - pad), min(W, x1 + pad)
            reg = cv2.GaussianBlur(img[yy0:yy1, xx0:xx1], (0, 0), 26)[y0 - yy0:y1 - yy0, x0 - xx0:x1 - xx0] * 1.06 + 0.03
            m = np.zeros((y1 - y0, x1 - x0), np.float32); cv2.rectangle(m, (r, 0), (x1 - x0 - r - 1, y1 - y0 - 1), 1, -1); cv2.rectangle(m, (0, r), (x1 - x0 - 1, y1 - y0 - r - 1), 1, -1)
            for cx, cy in ((r, r), (x1 - x0 - r - 1, r), (r, y1 - y0 - r - 1), (x1 - x0 - r - 1, y1 - y0 - r - 1)): cv2.circle(m, (cx, cy), r, 1, -1, cv2.LINE_AA)
            m = (cv2.GaussianBlur(m, (0, 0), 0.8) * float(al))[..., None]
            img = img.copy(); img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - m) + reg * m
    if f.get("flash", 0) > 0.01: img = img + (1 - img) * float(f["flash"])
    p = cv2.imread(os.path.join(ov, f"{i:05d}.png"), cv2.IMREAD_UNCHANGED)
    if p is not None and p.shape[2] == 3: img = p.astype(np.float32) / 255            # карточка на весь кадр: PNG без прозрачности
    elif p is not None:
        al = p[..., 3:4].astype(np.float32) / 255
        if al.max() > 0:
            ys, xs = np.where(al[..., 0] > 0.25)                                       # где стоит текст: светлую основу под ним притемняем
            ys = ys[ys < 1560]
            if len(ys) > 400 and not g:
                lum = float(img[max(0, ys.min() - 40):ys.max() + 40, :, :].mean()); want = float(np.clip((lum - 0.30) * 0.95, 0, 0.5))
            else: want = 0.0
            adim += (want - adim) * (0.22 if want > adim else 0.05)                    # темнеет быстро, светлеет медленно: без мигания между фразами
            if adim > 0.01: img = img * (1 - adim)
            img = img * (1 - al) + (p[..., :3].astype(np.float32) / 255) * al
    enc.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait(); dec.kill(); os.remove(wav)
print("готово:", out)
