"""Шаблон «apple-reels»: вертикальный ролик из исходника + списка реплик (cues.json) + эффектов.

Использование:
  python reel.py source.mp4 cues.json out.mp4 [--follow track.json] [--style style.json] [--keep work_dir]

cues.json:
  {"cues": [{"t": 0.4, "d": 1.8, "kind": "title", "tag": "через неделю", "lines": ["вот почему", "машина"], "sub": "лак тускнеет"},
            {"t": 3.0, "d": 1.0, "kind": "card", "text": "прописан"},
            {"t": 5.0, "d": 1.2, "kind": "number", "text": "2025", "ghost": "2000"},
            {"t": 6.0, "d": 1.5, "kind": "pills", "items": [{"text": "просмотров"}, {"text": "ответов", "style": "blue"}]}],
   "punches": [{"t": 2.0}, {"t": 5.5, "scale": 1.18}], "flashes": [{"t": 4.0}], "glitches": [{"t": 4.0}]}
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from scipy.signal import savgol_filter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lesson-01-ai"))
import mix as sfxlib  # noqa: E402  (синтез звуковых эффектов, SR=48000)

ap = argparse.ArgumentParser()
ap.add_argument("source")
ap.add_argument("cues")
ap.add_argument("out")
ap.add_argument("--follow")
ap.add_argument("--fit", choices=["cover", "blur"], default="cover", help="cover — на весь кадр (обрезка), blur — целиком поверх размытого фона")
ap.add_argument("--style", default=str(HERE / "style.json"))
ap.add_argument("--keep")
a = ap.parse_args()

ST = json.load(open(a.style))
CU = json.load(open(a.cues))
W, H, FPS = ST["format"]["w"], ST["format"]["h"], ST["format"]["fps"]
work = Path(a.keep or tempfile.mkdtemp(prefix="reel_"))
work.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(a.source)
sw, sh = int(cap.get(3)), int(cap.get(4))
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
dur = N / FPS

# --- оверлей (текст) ---
ov_dir = work / "overlay"
for f in ov_dir.glob("*.png") if ov_dir.exists() else []:
    f.unlink()
subprocess.run(["node", str(HERE / "render_overlay.js"), a.cues, a.style, str(ov_dir), str(dur), str(FPS)], check=True)

# --- вписывание кадра: cover по высоте, окно следует за человеком ---
scale = H / sh
cw = W / scale                                  # ширина окна в пикселях исходника
cx = np.full(N, sw / 2.0)
if a.follow:
    T = json.load(open(a.follow))["frames"]
    xs = np.array([np.mean([T[min(i, len(T) - 1)]["pose"][k][0] for k in (11, 12, 23, 24)]) if "pose" in T[min(i, len(T) - 1)] else np.nan for i in range(N)])
    xs = np.where(np.isnan(xs), np.nanmean(xs), xs)
    cx = savgol_filter(xs, 31, 2)
cx = np.clip(cx, cw / 2, sw - cw / 2) if cw < sw else np.full(N, sw / 2.0)


def fit_blur(fr):
    bgs = max(W / sw, H / sh)
    bg = cv2.resize(fr, (int(sw * bgs) + 1, int(sh * bgs) + 1))
    y0, x0 = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2
    bg = cv2.GaussianBlur(bg[y0:y0 + H, x0:x0 + W], (0, 0), 38)
    bg = (bg.astype(np.float32) * 0.55).astype(np.uint8)
    fh = int(sh * W / sw)
    fg = cv2.resize(fr, (W, fh), interpolation=cv2.INTER_AREA)
    top = int(0.42 * H - fh / 2)
    bg[top:top + fh] = fg
    return bg


def fit(fr, i):
    if a.fit == "blur":
        return fit_blur(fr)
    if cw >= sw:                                # исходник уже вертикальный/узкий
        return cv2.resize(fr, (W, H), interpolation=cv2.INTER_CUBIC)
    x0 = cx[i] - cw / 2
    M = np.array([[scale, 0, -x0 * scale], [0, scale, 0]], np.float32)
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_CUBIC)


# --- эффекты ---
G = ST["grade"]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - G["vignette"] * np.clip(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2, 0, 1.6) ** 1.2
sh_t, hi_t = np.array(G["shadows_tint_bgr"], np.float32), np.array(G["highlights_tint_bgr"], np.float32)


def grade(img):
    x = img.astype(np.float32) / 255
    x = G["lift"] + x * (1 - G["lift"])
    s = x * x * (3 - 2 * x)                      # S-кривая
    x = x + (s - x) * (G["contrast"] - 1) * 3
    l = x.mean(2, keepdims=True)
    x = l + (x - l) * G["saturation"]
    x = x * (sh_t + (hi_t - sh_t) * np.clip(l, 0, 1))
    hl = np.clip(x - 0.72, 0, 1)
    x = x + cv2.GaussianBlur(hl, (0, 0), 28) * G["bloom"] * 3
    x = x * vig[..., None]
    return np.clip(x, 0, 1)


M_ = ST["motion"]


def zoom_env(t):
    s = 1 + M_["base_push"] * t / dur
    for p in CU.get("punches", []):
        k = (p.get("scale", M_["punch"]["scale"]) - 1)
        u = t - p["t"]
        if u < 0:
            continue
        i_, h_, o_ = M_["punch"]["in_s"], M_["punch"]["hold_s"], M_["punch"]["out_s"]
        e = (1 - (1 - min(u / i_, 1)) ** 3) if u < i_ + h_ else max(0, 1 - (u - i_ - h_) / o_) ** 2
        s += k * e
    return s


def punch(img, t):
    s = zoom_env(t)
    if s <= 1.0005:
        return img
    M = cv2.getRotationMatrix2D((W / 2, H * 0.42), 0, s)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def flash(x, t):
    for f in CU.get("flashes", []):
        p = (t - f["t"]) / M_["flash"]["dur_s"]
        if 0 <= p <= 1:
            col = np.array(f.get("color", M_["flash"]["color_rgb"])[::-1], np.float32) / 255
            al = M_["flash"]["peak"] * (1 - p) ** 2
            x = x * (1 - al) + col * al
    return x


def glitch(x, t, i):
    for g in CU.get("glitches", []):
        p = (t - g["t"]) / M_["glitch"]["dur_s"]
        if 0 <= p <= 1:
            rng = np.random.default_rng(i)
            gl = M_["glitch"]
            y = x.copy()
            for _ in range(gl["bands"]):
                y0 = int(rng.uniform(0.15, 0.85) * H)
                hh = int(rng.uniform(0.01, 0.06) * H)
                sh_ = int(rng.uniform(-1, 1) * gl["max_shift_px"] * (1 - p))
                y[y0:y0 + hh] = np.roll(x[y0:y0 + hh], sh_, axis=1)
                if rng.random() < 0.4:
                    y[y0:y0 + max(2, hh // 5)] = np.clip(y[y0:y0 + max(2, hh // 5)] + 0.5, 0, 1)
            d = int(8 * (1 - p)) + 1
            y[..., 2] = np.roll(y[..., 2], d, axis=1)
            y[..., 0] = np.roll(y[..., 0], -d, axis=1)
            x = y
    return x


# --- кадры -> ffmpeg ---
wav = work / "src.wav"
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.source, "-vn", "-ac", "2", "-ar", "48000", str(wav)], check=True)
enc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(work / "video.mp4")], stdin=subprocess.PIPE)
rng = np.random.default_rng(1)
for i in range(N):
    ok, fr = cap.read()
    if not ok:
        break
    t = i / FPS
    x = grade(punch(fit(fr, i), t))
    x = glitch(flash(x, t), t, i)
    ovf = ov_dir / f"{i:05d}.png"
    if ovf.exists():
        ov = cv2.imread(str(ovf), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        al = ov[..., 3:4]
        x = x * (1 - al) + ov[..., :3] * al
    x = x + rng.normal(0, G["grain"], (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
    enc.stdin.write((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
enc.stdin.close()
enc.wait()

# --- звук: оригинал + SFX на акцентах, без музыки ---
SR = sfxlib.SR
voice, sr = sf.read(str(wav))
mixbuf = np.zeros((len(voice), 2))
mixbuf[:] = voice
fxb = np.zeros(len(voice))


def put(sig, t, g):
    s = max(0, int(t * SR))
    sig = sig[: len(fxb) - s]
    fxb[s:s + len(sig)] += sig * g


for p in CU.get("punches", []):
    put(sfxlib.whoosh(0.5, up=True, amp=0.5), p["t"] - 0.15, 1.0)
for f in CU.get("flashes", []):
    put(sfxlib.sparkle(0.2), f["t"], 1.0)
    put(sfxlib.whoosh(0.6, up=False, amp=0.5), f["t"] - 0.05, 0.8)
for g in CU.get("glitches", []):
    put(sfxlib.whoosh(0.3, up=False, amp=0.6), g["t"], 0.7)
for c in CU["cues"]:
    put(sfxlib.tap(), c["t"] + 0.02, 0.5)
mixbuf += (fxb * ST["audio"]["sfx_gain"])[:, None]
sf.write(str(work / "mix.wav"), mixbuf / max(1.0, np.abs(mixbuf).max() / 0.95), SR)
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(work / "video.mp4"), "-i", str(work / "mix.wav"),
                "-af", f"loudnorm=I={ST['audio']['target_lufs']}:TP=-1.5:LRA=9", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-map_metadata", "-1", "-movflags", "+faststart", a.out], check=True)
print("готово:", a.out)
