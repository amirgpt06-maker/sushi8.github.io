"""Стилизация видео покадрово: мультик (cel-shading), кино (teal & orange + широкий кадр), живопись.
Использование: python looks.py вход.mp4 выход.mp4 toon|cine|paint [--from 0] [--to 0]
Звук сохраняется. HDR (HLG с iPhone) автоматически переводится в SDR."""
import subprocess, sys
import cv2, numpy as np

src, dst, look = sys.argv[1], sys.argv[2], sys.argv[3]
a = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
T0, T1 = a("--from", 0), a("--to", 0)

def toon(im):
    """Мультик: плоские заливки (8 цветов после сглаживания), только сильные контуры, чуть сочнее цвета."""
    h, w = im.shape[:2]; s = 720 / max(h, w)
    small = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    sm = small
    for _ in range(4): sm = cv2.bilateralFilter(sm, 9, 75, 9)
    hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
    hsv[..., 2] = np.round(hsv[..., 2] / 255 * 8) / 8 * 255 * 0.9 + 22              # ступенчатый свет (8 уровней) — «рисованная» заливка
    flat = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    flat = cv2.pyrMeanShiftFiltering(flat, 5, 14)
    g = cv2.GaussianBlur(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), (0, 0), 1.6)
    e = cv2.Canny(g, 45, 115)
    num, lab, st, _ = cv2.connectedComponentsWithStats(e, 8)                         # мелкий «мусор» из краёв убираем
    keep = np.isin(lab, np.where(st[:, cv2.CC_STAT_AREA] >= 28)[0][1:])
    e = cv2.dilate((keep * 255).astype(np.uint8), np.ones((2, 2), np.uint8))
    flat[e > 0] = (flat[e > 0] * 0.25).astype(np.uint8)
    return cv2.resize(flat, (w, h), interpolation=cv2.INTER_CUBIC)

def cine(im):
    """Кино: бирюзовые тени, тёплые света, мягкий S-контраст, полосы 2.39:1 для горизонтали / 1.9:1 для вертикали."""
    f = im.astype(np.float32) / 255
    lum = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None] / 255
    teal = np.float32([0.58, 0.48, 0.28]); warm = np.float32([0.36, 0.56, 0.78])
    f = f * 0.82 + 0.18 * (teal * (1 - lum) + warm * lum)
    f = 0.5 + (f - 0.5) * 1.1; f = np.clip(f, 0, 1); f = f * f * (3 - 2 * f) * 0.35 + f * 0.65
    out = (f * 255).astype(np.uint8); h, w = out.shape[:2]
    bar = int((h - w / 2.39) / 2) if w > h else int(h * 0.1)
    out[:bar] = 0; out[h - bar:] = 0
    return out

def paint(im):
    return cv2.stylization(im, sigma_s=60, sigma_r=0.45)

FX = {"toon": toon, "cine": cine, "paint": paint}[look]
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,color_transfer",
                        "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip().split(",")
W, H, fr, trc = int(probe[0]), int(probe[1]), probe[2], probe[3] if len(probe) > 3 else ""
vf = ("zscale=t=linear:npl=150,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=bgr24"
      if trc in ("arib-std-b67", "smpte2084") else "format=bgr24")
cut = (["-ss", str(T0)] if T0 else []) + (["-t", str(T1 - T0)] if T1 else [])
dec = subprocess.Popen(["ffmpeg", "-v", "error"] + cut + ["-i", src, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", fr, "-i", "-"] + cut + ["-i", src,
                        "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k", "-shortest", dst], stdin=subprocess.PIPE)
n = W * H * 3; k = 0
while True:
    buf = dec.stdout.read(n)
    if len(buf) < n: break
    enc.stdin.write(FX(np.frombuffer(buf, np.uint8).reshape(H, W, 3)).tobytes()); k += 1
enc.stdin.close(); enc.wait(); print(f"{look}: кадров {k} -> {dst}")
