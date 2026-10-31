"""Поиск и сопровождение всех лиц в ролике (YuNet) -> эллипсы для размытия по кадрам.

Использование: python facetrack.py source.mp4 cues.json out.json [preview.png]
Лицо держится «треком»: если детектор на пару кадров его теряет (поворот головы), эллипс остаётся на месте;
на склейках треки сбрасываются. Эллипс берётся с запасом — лоб, волосы, борода.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

src, cues_f, out = sys.argv[1:4]
CUTS = json.load(open(cues_f))["cuts"]
det = cv2.FaceDetectorYN.create(str(Path.home() / "video-models/face/yunet.onnx"), "", (1080, 1920), 0.5, 0.3, 5000)
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
det.setInputSize((W, H))
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cut_frames = {int(round(c * fps)) for c in CUTS}

cache = Path(out).with_suffix(".raw.json")
raw = json.load(open(cache)) if cache.exists() else []
for i in range(len(raw), N if not raw else 0):
    ok, fr = cap.read()
    if not ok:
        break
    _, faces = det.detect(fr)
    # второй проход на увеличенном кадре — мелкие лица на заднем плане
    big = cv2.resize(fr, None, fx=1.6, fy=1.6)
    det.setInputSize((big.shape[1], big.shape[0]))
    _, f2 = det.detect(big)
    det.setInputSize((W, H))
    boxes = [] if faces is None else [[float(v) for v in f[:4]] + [float(f[14])] for f in faces]
    if f2 is not None:
        boxes += [[float(f[0]) / 1.6, float(f[1]) / 1.6, float(f[2]) / 1.6, float(f[3]) / 1.6, float(f[14])] for f in f2]
    # слить дубликаты
    keep = []
    for b in sorted(boxes, key=lambda b: -b[4]):
        cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        if all(abs(cx - (k[0] + k[2] / 2)) > 0.5 * k[2] or abs(cy - (k[1] + k[3] / 2)) > 0.5 * k[3] for k in keep):
            keep.append(b)
    raw.append(keep)
json.dump(raw, open(cache, "w"))

# --- треки ---
tracks, active = [], []
for i, boxes in enumerate(raw):
    if i in cut_frames:
        active = []
    used = set()
    for tr in active:
        lb = tr["boxes"][-1][1]
        lc = np.array([lb[0] + lb[2] / 2, lb[1] + lb[3] / 2])
        best, bd = None, 1e9
        for j, b in enumerate(boxes):
            if j in used:
                continue
            d = np.linalg.norm(np.array([b[0] + b[2] / 2, b[1] + b[3] / 2]) - lc)
            if d < 0.9 * max(lb[2], b[2]) and d < bd:
                best, bd = j, d
        if best is not None:
            used.add(best)
            tr["boxes"].append((i, boxes[best][:4]))
            tr["scores"].append(boxes[best][4])
            tr["last"] = i
    for j, b in enumerate(boxes):
        if j not in used:
            tr = {"boxes": [(i, b[:4])], "scores": [b[4]], "last": i, "start": i}
            tracks.append(tr)
            active.append(tr)
    active = [tr for tr in active if i - tr["last"] <= 20]

# сегмент между склейками для каждого кадра
bounds = [0] + sorted(cut_frames) + [N]
seg_of = lambda f: max(k for k in range(len(bounds) - 1) if bounds[k] <= f)
ell = [[] for _ in range(N)]
for tr in tracks:
    bw = np.median([b[2] for _, b in tr["boxes"]])
    bcy = np.median([b[1] + b[3] / 2 for _, b in tr["boxes"]])
    # случайные срабатывания: короткие, неуверенные, слишком большие/маленькие, или ниже уровня плеч (стол, руки)
    if len(tr["boxes"]) < 6 or np.mean(tr["scores"]) < 0.62 or not (22 < bw < 300) or bcy > 0.55 * H:
        continue
    fr = np.array([f for f, _ in tr["boxes"]])
    bx = np.array([b for _, b in tr["boxes"]], float)
    cx, cy, w, h = bx[:, 0] + bx[:, 2] / 2, bx[:, 1] + bx[:, 3] / 2, bx[:, 2], bx[:, 3]
    s = seg_of(fr[0])
    a, b = max(fr[0] - 12, bounds[s]), min(fr[-1] + 20, bounds[s + 1] - 1)
    full = np.arange(a, b + 1)
    vals = [np.interp(full, fr, v) for v in (cx, cy, w, h)]
    # сглаживание (без дрожания эллипса)
    k = np.ones(7) / 7
    vals = [np.convolve(np.pad(v, 3, mode="edge"), k, "valid") for v in vals]
    size = np.maximum(vals[2], vals[3])
    for f, x, y, sz in zip(full, vals[0], vals[1], size):
        ell[f].append([round(float(x), 1), round(float(y - 0.10 * sz), 1), round(float(0.95 * sz), 1), round(float(1.25 * sz), 1)])
json.dump({"fps": fps, "ellipses": ell}, open(out, "w"))
print("кадров с лицами:", sum(1 for e in ell if e), "эллипсов в среднем:", round(sum(len(e) for e in ell) / N, 2))

if len(sys.argv) > 4:   # контрольный лист: кадры раз в 2 с с эллипсами
    tiles = []
    cap = cv2.VideoCapture(src)
    for i in range(0, N, int(fps * 2)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, fr = cap.read()
        for x, y, rx, ry in ell[i]:
            cv2.ellipse(fr, (int(x), int(y)), (int(rx), int(ry)), 0, 0, 360, (0, 0, 255), 6)
        tiles.append(cv2.resize(fr, (216, 384)))
    while len(tiles) % 8:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(sys.argv[4], np.vstack([np.hstack(tiles[r:r + 8]) for r in range(0, len(tiles), 8)]))
