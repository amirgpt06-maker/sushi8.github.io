"""Сборка ролика «Арабский алфавит» в стиле Apple: исходник + оверлей (arabic.html) + переходы + звук.

Использование: python compose.py source.mp4 arabic_cues.json overlay_dir out.mp4 [хвост_с=3.0] [faces.json]
Переходы на склейках — размытие + «проход сквозь» кадр (наезд/отъезд) + лёгкая засветка;
внутри планов — медленный наезд; в конце — стоп-кадр, уходящий в размытие под итоговую карточку.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lesson-01-ai"))
import mix as sfx  # noqa: E402  синтез эффектов (SR=48000)

src, cues_f, ov_dir, out = sys.argv[1:5]
TAIL = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
SPEED = 1.03                                        # лёгкое незаметное ускорение всего ролика
FACES = json.load(open(sys.argv[6]))["ellipses"] if len(sys.argv) > 6 else None
D = json.load(open(cues_f))
CUTS, END = D["cuts"], D["end"]
cap = cv2.VideoCapture(src)
FPS = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
NT = N + int(TAIL * FPS)
shots = [0.0] + CUTS + [N / FPS]
work = Path(out).with_suffix(".work")            # промежуточное видео без звука — для быстрой замены звука
work.mkdir(parents=True, exist_ok=True)
AUDIO_ONLY = os.environ.get("AUDIO_ONLY") == "1" and (work / "v.mp4").exists()

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = (1 - 0.14 * np.clip(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2, 0, 1.6) ** 1.3)[..., None]


def grade(x):
    # мягкий «эппловский» вид: чуть больше контраста, прохладные тени, тёплые света, без пересвета
    l = x.mean(2, keepdims=True)
    s = x * x * (3 - 2 * x)
    x = x + (s - x) * 0.22
    x = x * (np.array([1.025, 1.0, 0.975]) * (1 - l) + np.array([0.985, 1.0, 1.02]) * l)   # BGR
    l = x.mean(2, keepdims=True)
    x = l + (x - l) * 1.06
    return np.clip(x, 0, 1)           # без виньетки: углы не затемняются


def xform(img, sc, cy=0.42):
    if abs(sc - 1) < 1e-4:
        return img
    M = cv2.getRotationMatrix2D((W / 2, H * cy), 0, sc)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def blur_faces(img, ells):
    """Аккуратное размытие лиц: сильный гаусс внутри эллипса, мягкий растушёванный край."""
    out = img.copy()
    for x, y, rx, ry in ells:
        pad = 1.35
        x0, x1 = int(max(0, x - rx * pad)), int(min(W, x + rx * pad))
        y0, y1 = int(max(0, y - ry * pad)), int(min(H, y + ry * pad))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        roi = out[y0:y1, x0:x1]
        bl = cv2.GaussianBlur(roi, (0, 0), max(6.0, 0.30 * rx))
        bl = cv2.GaussianBlur(bl, (0, 0), max(4.0, 0.15 * rx))
        m = np.zeros(roi.shape[:2], np.float32)
        cv2.ellipse(m, (int(x - x0), int(y - y0)), (int(rx), int(ry)), 0, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), max(3.0, 0.16 * rx))[..., None]
        out[y0:y1, x0:x1] = roi * (1 - m) + bl * m
    return out


def shot_scale(t):
    for a, b in zip(shots, shots[1:]):
        if a <= t < b:
            return 1.0 + 0.04 * (t - a) / max(b - a, 1e-3)
    return 1.04


enc = None if AUDIO_ONLY else subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                        str(work / "v.mp4")], stdin=subprocess.PIPE)
last = None
rng = np.random.default_rng(3)
for i in range(0 if enc else NT, NT):
    t = i / FPS
    if i < N:
        ok, fr = cap.read()
        if ok:
            last = fr
    fr = last
    x = fr.astype(np.float32) / 255
    if FACES:
        x = blur_faces(x, FACES[min(i, N - 1)])
    sc, blur, lift = shot_scale(t), 0.0, 0.0
    # переход: за 0.3 с до склейки кадр «уходит» вперёд и размывается, после — новый приходит из размытия
    for c in CUTS:
        d = t - c
        if -0.30 <= d < 0:
            e = (1 + d / 0.30) ** 2
            sc *= 1 + 0.07 * e
            blur += 28 * e
            lift += 0.10 * e
        elif 0 <= d <= 0.36:
            e = (1 - d / 0.36) ** 2
            sc *= 1 + 0.07 * e
            blur += 28 * e
            lift += 0.10 * e
    if t < 0.5:                                     # начало из размытия
        e = (1 - t / 0.5) ** 2
        blur += 24 * e
        lift -= 0.5 * e
    if t > END - 0.8:                               # финал: мягкий наезд, размытие и затемнение
        e = min(1, (t - (END - 0.8)) / 0.8) ** 2
        blur += 14 * e
        sc *= 1 + 0.03 * e
        lift -= 0.98 * e
    x = xform(x, sc)
    if blur > 0.3:
        x = cv2.GaussianBlur(x, (0, 0), blur)
    x = grade(x)
    x = np.clip(x + lift, 0, 1) if lift > 0 else x * (1 + lift)
    ovf = Path(ov_dir) / f"{i:05d}.png"
    if ovf.exists():
        ov = cv2.imread(str(ovf), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        a = ov[..., 3:4]
        x = x * (1 - a) + ov[..., :3] * a
    if t > END - 0.8:                               # оверлей тоже уходит в затемнение
        x = x * (1 - min(1, (t - (END - 0.8)) / 0.8) ** 2)
    x = x + rng.normal(0, 0.008, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
    enc.stdin.write((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
if enc:
    enc.stdin.close()
    enc.wait()

# --- звук: оригинал + мягкие эффекты (без музыки) ---
SR = sfx.SR
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", str(SR), str(work / "a.wav")], check=True)
voice, _ = sf.read(str(work / "a.wav"))
total = int(NT / FPS * SR) + SR
mixb = np.zeros((total, 2))
mixb[: len(voice)] = voice[:total]
fxb = np.zeros(total)


def put(sig, t, g):
    s = max(0, int(t * SR))
    sig = sig[: total - s]
    fxb[s:s + len(sig)] += sig * g


# звук эффектов: TRANS=page.wav | mouse_studio.mp3 | mouse_soft.mp3 — на переходах; по умолчанию без эффектов
import librosa  # noqa: E402
SFX_DIR = Path(__file__).resolve().parent / "sfx"
TRANS = os.environ.get("TRANS", "none")          # по умолчанию звуков нет: только живая речь
if TRANS != "none":
    trans, _ = librosa.load(str(SFX_DIR / TRANS), sr=SR)
    trans /= np.abs(trans).max()
    for c in CUTS:
        put(trans, c - 0.12, 0.3)
mixb += fxb[:, None]
mixb = mixb[: int(NT / FPS * SR)]
sf.write(str(work / "mix.wav"), mixb / max(1.0, np.abs(mixb).max() / 0.95), SR)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(work / "v.mp4"), "-i", str(work / "mix.wav"),
                "-filter:v", f"setpts=PTS/{SPEED},fps={FPS}", "-af", f"atempo={SPEED},loudnorm=I=-14:TP=-1.5:LRA=9",
                "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-map_metadata", "-1", "-movflags", "+faststart", out], check=True)
print("готово:", out, f"{NT / FPS / SPEED:.1f} с")
