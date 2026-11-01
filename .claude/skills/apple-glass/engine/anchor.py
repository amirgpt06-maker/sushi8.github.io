"""«Apple стекло»: якорь — лицо говорящего по кадрам (YuNet). Нужен, чтобы подписи держались под подбородком,
а фокус-рамка и наезды были по лицу.

Использование: python anchor.py source.mp4 anchor.json
Берётся самое крупное лицо; пропуски заполняются интерполяцией; дрожание сглаживается (на склейках — без смаза).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

src, out = sys.argv[1:3]
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
S = 0.5                                             # детекция на половинном размере — быстрее, точности хватает
det = cv2.FaceDetectorYN.create(str(Path.home() / "video-models/face/yunet.onnx"), "", (int(W * S), int(H * S)), 0.6, 0.3, 50)
boxes, cuts, prev = [], [0], None
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    sm = cv2.resize(fr, (int(W * S), int(H * S)))
    g = cv2.resize(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), (64, 114)).astype(np.float32)
    if prev is not None and np.abs(g - prev).mean() > 28:      # склейка
        cuts.append(i)
    prev = g
    _, f = det.detect(sm)
    if f is not None and len(f):
        b = max(f, key=lambda r: r[2] * r[3])
        boxes.append([float(b[0] + b[2] / 2) / S, float(b[1] + b[3] / 2) / S, float(b[2]) / S, float(b[3]) / S])
    else:
        boxes.append(None)
    i += 1
N = len(boxes)
cuts.append(N)
res = [None] * N
for a, b in zip(cuts, cuts[1:]):
    idx = [k for k in range(a, b) if boxes[k]]
    if not idx:
        continue
    arr = np.array([boxes[k] for k in idx])
    full = np.arange(a, b)
    vals = [np.interp(full, idx, arr[:, c]) for c in range(4)]
    k = 9
    vals = [np.convolve(np.pad(v, k // 2, mode="edge"), np.ones(k) / k, "valid") for v in vals]
    for j, f in enumerate(full):
        res[f] = [round(float(v[j]), 1) for v in vals]
json.dump({"fps": fps, "w": W, "h": H, "f": res}, open(out, "w"))
print(f"кадров {N}, с лицом {sum(1 for r in res if r)}, склеек {len(cuts) - 2}")
