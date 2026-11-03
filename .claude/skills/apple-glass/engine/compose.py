"""«Apple стекло»: сборка. Исходник + оверлей (render.js) + эффекты по fx.json + звуки по events.json.

Использование: python compose.py source.mp4 overlay_dir out.mp4
Переменные: SPEED=1.0 (ускорение всего ролика), GRADE=1 (мягкая «эппловская» цветокоррекция), FROM/TO (секунды — кусок для проверки),
            SFX_GAIN=1.0 (общая громкость эффектов), AUDIO_ONLY=1 (пересобрать только звук),
            LOUDNORM=0 (не нормализовать громкость — для роликов без голоса).
Звуки: сначала engine/sfx_local (собирает pack_to_sfx.py из вашего пака), иначе engine/sfx (синтез).
По кадру: наезд (по лицу) -> размытие+затемнение фона -> цвет -> оверлей -> стеклянная линза (настоящее преломление) -> засветка -> зерно.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

src, ov_dir, out = sys.argv[1:4]
ov_dir = Path(ov_dir)
SPEED = float(os.environ.get("SPEED", "1.0"))
GRADE = os.environ.get("GRADE", "1") == "1"
SFX_GAIN = float(os.environ.get("SFX_GAIN", "1.0"))
FX = {int(k): v for k, v in json.load(open(ov_dir / "fx.json")).items()}
EV = json.load(open(ov_dir / "events.json"))
HERE = Path(__file__).resolve().parent
SFX_DIRS = [d for d in (HERE / "sfx_local", HERE / "sfx") if d.exists()]   # сначала свой пак (sfx_local), потом синтез


def sfx_path(role):
    for d in SFX_DIRS:
        if (d / f"{role}.wav").exists():
            return d / f"{role}.wav"
    raise FileNotFoundError(f"нет звука «{role}» ни в sfx_local, ни в sfx")
cap = cv2.VideoCapture(src)
FPS = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
F0 = int(float(os.environ.get("FROM", 0)) * FPS)
F1 = min(N, int(float(os.environ.get("TO", N / FPS)) * FPS))
work = Path(out).with_suffix(".work")
work.mkdir(parents=True, exist_ok=True)
AUDIO_ONLY = os.environ.get("AUDIO_ONLY") == "1" and (work / "v.mp4").exists()
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


# мягкая «эппловская» коррекция: лёгкая S-кривая, тёплые тени / холодные света, +4 % насыщенности (всё во float32 — быстро)
SH, HI = np.float32([1.02, 1.0, 0.98]), np.float32([0.99, 1.0, 1.015])
F = np.float32


def grade(x):
    s = x * x * (F(3) - F(2) * x)
    x = x + (s - x) * F(0.18)
    l = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)[..., None]
    x = x * (SH + (HI - SH) * l)
    l = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)[..., None]
    return np.clip(l + (x - l) * F(1.04), 0, 1)


def zoom(img, s, cx, cy):
    if abs(s - 1) < 1e-4:
        return img
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), 0, s)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def lens(img, x, y, r, a):
    """Liquid-glass линза: увеличение в центре, сжатие и преломление у края, лёгкий расфокус, блик и тонкий светлый обод."""
    if a <= 0.01 or r < 4:
        return img
    p = int(r + 14)
    x0, x1, y0, y1 = int(max(0, x - p)), int(min(W, x + p)), int(max(0, y - p)), int(min(H, y + p))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return img
    gx, gy = xx[y0:y1, x0:x1] - x, yy[y0:y1, x0:x1] - y
    d = np.sqrt(gx * gx + gy * gy) / r
    dd = np.clip(d, 0, 1)
    k = 0.80 + 0.12 * dd ** 2 + 0.55 * np.clip(dd - 0.82, 0, 1) ** 1.5 * 6   # центр увеличен, край «загибается»
    mx, my = (x + gx * k).astype(np.float32), (y + gy * k + 4 * dd ** 3).astype(np.float32)
    ref = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ref = cv2.GaussianBlur(ref, (0, 0), 1.6)
    ref = ref * 1.04 + 0.035
    # блик сверху-слева и мягкая тень снизу внутри
    hl = np.exp(-(((gx + 0.35 * r) / (0.55 * r)) ** 2 + ((gy + 0.55 * r) / (0.28 * r)) ** 2)) * 0.22
    ref = ref + hl[..., None]
    ref = ref - (np.clip(gy / r, 0, 1) ** 2 * 0.05)[..., None]
    m = np.clip((1 - d) * r / 1.2, 0, 1)[..., None]                          # сглаженный край
    roi = img[y0:y1, x0:x1]
    res = roi * (1 - m) + ref * m
    # обод: тонкое светлое кольцо, ярче сверху-слева
    ring = np.exp(-((d - 1) * r / 1.3) ** 2)
    ang = np.clip(0.55 - 0.45 * (gx + gy) / (r * 1.4142), 0.15, 1)
    res = res + (ring * ang * 0.6)[..., None]
    # мягкая внешняя тень
    sh = np.exp(-(np.clip(d - 1, 0, None) * r / 6) ** 2) * (d > 1) * 0.12
    res = res * (1 - sh[..., None])
    out_ = img.copy()
    out_[y0:y1, x0:x1] = roi * (1 - a) + np.clip(res, 0, 1) * a
    return out_


def leak(img, k):
    """Световая засветка (оранжевый + розовый, диагональные лучи), режим screen; k 0..1."""
    a = np.sin(np.pi * np.clip(k, 0, 1)) ** 1.2
    cx1, cy1 = W * (-0.2 + 1.2 * k), H * 0.25
    cx2, cy2 = W * (1.1 - 0.9 * k), H * 0.7
    b1 = np.exp(-(((xx - cx1) / (0.55 * W)) ** 2 + ((yy - cy1) / (0.45 * H)) ** 2))
    b2 = np.exp(-(((xx - cx2) / (0.5 * W)) ** 2 + ((yy - cy2) / (0.4 * H)) ** 2))
    # мягкие лучи: несколько широких полос разной ширины, сильно размытые (как плёночная засветка, не «зебра»)
    band = (xx * 0.8 + yy) / 1.0 - (W + H) * (1.2 * k - 0.1)
    streak = sum(w_ * np.exp(-((band - o) / s_) ** 2) for o, s_, w_ in [(0, 260, 0.7), (-420, 120, 0.45), (380, 180, 0.5), (-800, 300, 0.35)])
    col = (b1[..., None] * np.array([0.10, 0.45, 1.0]) + b2[..., None] * np.array([0.55, 0.25, 1.0]) + streak[..., None] * np.array([0.35, 0.65, 1.0]) * 0.7)  # BGR
    col = cv2.GaussianBlur(np.clip(col * a * 1.05, 0, 1).astype(np.float32), (0, 0), 18)
    return 1 - (1 - img) * (1 - col)


face_last = [W / 2, H * 0.42, W * 0.4, H * 0.27]
enc = None if AUDIO_ONLY else subprocess.Popen(
    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(work / "v.mp4")], stdin=subprocess.PIPE)
rng = np.random.default_rng(3)
GRAIN = [cv2.resize(rng.normal(0, 0.006, (H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)[..., None] for _ in range(6)]
if enc:
    cap.set(cv2.CAP_PROP_POS_FRAMES, F0)
    for i in range(F0, F1):
        ok, fr = cap.read()
        if not ok:
            break
        x = fr.astype(np.float32) * (1 / 255)
        f = FX.get(i, {"blur": 0, "dim": 0, "zoom": 1, "lens": None, "leak": -1, "face": face_last})
        face_last = f["face"]
        fx_, fy_ = f["face"][0], f["face"][1]
        b = f["blur"]
        s = f["zoom"] * (1 + 0.05 * b)
        x = zoom(x, s, fx_, fy_)
        if b > 0.01:                               # сильное размытие считаем на 1/4 размера — тот же вид, в разы быстрее
            sg = 0.5 + 26 * b
            if sg > 6:
                sm = cv2.resize(x, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
                x = cv2.resize(cv2.GaussianBlur(sm, (0, 0), sg / 4), (W, H), interpolation=cv2.INTER_CUBIC)
            else:
                x = cv2.GaussianBlur(x, (0, 0), sg)
        x = x * (1 - f["dim"])
        if GRADE:
            x = grade(x)
        ovf = ov_dir / f"{i:05d}.png"
        if ovf.exists():
            ov = cv2.imread(str(ovf), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
            if ov.shape[2] == 3:                       # полностью непрозрачный кадр (вспышка) сохраняется без альфы
                x = ov
            else:
                al = ov[..., 3:4]
                x = x * (1 - al) + ov[..., :3] * al
        if f["lens"]:
            x = lens(x, *f["lens"])
        if f["leak"] >= 0:
            x = leak(x, f["leak"])
        x = x + GRAIN[i % len(GRAIN)]
        enc.stdin.write((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()

# --- звук: живой голос + эффекты по events.json ---
SR = 48000
t0, t1 = F0 / FPS, F1 / FPS
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", src, "-vn", "-ac", "2", "-ar", str(SR), str(work / "a.wav")], check=True)
voice, _ = sf.read(str(work / "a.wav"))
total = int((t1 - t0) * SR)
mixb = np.zeros((total, 2))
mixb[: min(total, len(voice))] = voice[:total]
cache = {}
for e in EV:
    if not (t0 - 1 <= e["t"] < t1):
        continue
    if e["s"] not in cache:
        cache[e["s"]], _ = sf.read(str(sfx_path(e["s"])))
    sig = cache[e["s"]] * e["g"] * SFX_GAIN
    st = int((e["t"] - t0) * SR)
    if st < 0:
        sig, st = sig[-st:], 0
    sig = sig[: total - st]
    mixb[st:st + len(sig)] += sig[:, None]
sf.write(str(work / "mix.wav"), mixb / max(1.0, np.abs(mixb).max() / 0.97), SR)
vf = f"setpts=PTS/{SPEED},fps={FPS}" if SPEED != 1 else "null"
af = ",".join(([f"atempo={SPEED}"] if SPEED != 1 else []) + (["loudnorm=I=-14:TP=-1.5:LRA=9"] if os.environ.get("LOUDNORM", "1") == "1" else ["anull"]))
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(work / "v.mp4"), "-i", str(work / "mix.wav"),
                "-filter:v", vf, "-af", af, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-map_metadata", "-1", "-movflags", "+faststart", out], check=True)
print("готово:", out)
