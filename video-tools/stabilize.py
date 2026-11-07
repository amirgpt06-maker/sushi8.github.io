"""Стабилизация по фону: следим только за неподвижным (стена, картина, мебель), человек в расчёт не идёт.

Использование: python stabilize.py in.mp4 out.mp4 [сглаживание_с=1.5] [исключить=x0,y0,x1,y1 в долях кадра]
  сглаживание — сколько секунд «плывущей» камеры оставить (0 — штатив; 1.5 — мягкая ручная камера без дрожи).
  исключить — область человека (по умолчанию центр кадра), там точки не берутся.
Выход без звука; масштаб подбирается минимальный, чтобы не было чёрных краёв.
"""
import subprocess
import sys

import cv2
import numpy as np

src, out = sys.argv[1], sys.argv[2]
SM = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
EX = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else [0.15, 0.28, 0.88, 1.0]
BOTTOM = float(__import__("os").environ.get("BOTTOM", "0.80"))   # ниже — тёмный низ кадра, точек там нет

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
sc = 0.5
w, h = int(W * sc), int(H * sc)
mask = np.full((h, w), 255, np.uint8)
mask[int(EX[1] * h):int(EX[3] * h), int(EX[0] * w):int(EX[2] * w)] = 0
mask[int(BOTTOM * h):] = 0

# каждый кадр сравниваем с опорным (раз в 2 с опорный обновляется через уже найденное преобразование) — без накопления ошибки
ref_g, ref_T, ref_pts = None, np.eye(3), None
T = []
guess = np.eye(3)
fi = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(cv2.resize(f, (w, h)), cv2.COLOR_BGR2GRAY)
    if ref_g is None:
        ref_g, ref_pts = g, cv2.goodFeaturesToTrack(g, 500, 0.004, 6, mask=mask)
        T.append(np.eye(3)); fi += 1; continue
    p0 = ref_pts
    init = cv2.transform(p0, guess[:2]).astype(np.float32)
    q, st, _ = cv2.calcOpticalFlowPyrLK(ref_g, g, p0, init.copy(), winSize=(41, 41), maxLevel=4,
                                        flags=cv2.OPTFLOW_USE_INITIAL_FLOW)
    o = st.ravel() == 1
    M = None
    if o.sum() > 10:
        M, _ = cv2.estimateAffinePartial2D(p0[o], q[o], method=cv2.RANSAC, ransacReprojThreshold=1.5)
    M = guess if M is None else np.vstack([M, [0, 0, 1]])   # кадр ref -> текущий (в масштабе sc)
    if np.abs(M[:2, 2] - guess[:2, 2]).max() > 12 or abs(np.hypot(M[0, 0], M[1, 0]) - 1) > 0.05:   # сбой слежения — держим прошлое
        M = guess
    guess = M
    full = M.copy(); full[0, 2] /= sc; full[1, 2] /= sc
    cur = full @ ref_T
    T.append(cur)
    if fi % int(2 * fps) == 0:                               # новый опорный кадр
        ref_g, ref_T, guess = g, cur, np.eye(3)
        ref_pts = cv2.goodFeaturesToTrack(g, 500, 0.004, 6, mask=mask)
    fi += 1
N = len(T)
# путь камеры: сдвиг, поворот, масштаб
path = np.array([[t[0, 2], t[1, 2], np.arctan2(t[1, 0], t[0, 0]), np.hypot(t[0, 0], t[1, 0])] for t in T])
if SM > 0:
    k = int(SM * fps * 3) | 1
    x = np.arange(k) - k // 2
    ker = np.exp(-0.5 * (x / (SM * fps)) ** 2)
    ker /= ker.sum()
    sm = np.stack([np.convolve(np.pad(path[:, i], k // 2, mode="edge"), ker, "valid") for i in range(4)], 1)
else:
    sm = np.tile(path.mean(0), (N, 1))
corr = []
for (x, y, a, s), (xs, ys, as_, ss) in zip(path, sm):
    # поправка: перевести кадр из реального положения камеры в сглаженное
    R = lambda ang, s_: np.array([[s_ * np.cos(ang), -s_ * np.sin(ang)], [s_ * np.sin(ang), s_ * np.cos(ang)]])
    A = np.eye(3)
    A[:2, :2] = R(as_ - a, ss / s)
    A[:2, 2] = [xs - x, ys - y]
    corr.append(A)
if __import__("os").environ.get("DEBUG"):
    for i in range(0, N, int(fps // 2)):
        A = corr[i]; print(f"{i / fps:5.1f}s  путь x {path[i,0]:7.1f} y {path[i,1]:7.1f} угол {np.degrees(path[i,2]):6.2f}° масштаб {path[i,3]:.3f} | поправка x {A[0,2]:6.1f} y {A[1,2]:6.1f}")
# минимальный масштаб без чёрных краёв (по углам кадра)
cs = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1]], float).T
need = 1.0
for A in corr:
    c = A @ cs
    for (px, py), (cx, cy) in zip(c[:2].T, cs[:2].T):
        # насколько угол «уехал» внутрь — столько и увеличить вокруг центра
        dx = abs(px - cx) / (W / 2)
        dy = abs(py - cy) / (H / 2)
        need = max(need, 1 + 1.02 * max(dx, dy))
print(f"нужный масштаб без обрезки краёв: {need:.3f}")
need = min(need, float(__import__("os").environ.get("ZMAX", 1.15)))
print(f"кадров {N}, масштаб {need:.3f}, макс. поправка x {max(abs(a[0,2]) for a in corr):.0f}px y {max(abs(a[1,2]) for a in corr):.0f}px")
Z = np.array([[need, 0, W / 2 * (1 - need)], [0, need, H / 2 * (1 - need)], [0, 0, 1]])
cap = cv2.VideoCapture(src)
enc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
                        "-i", "-", "-c:v", "libx264", "-crf", "13", "-preset", "medium", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
for i in range(N):
    ok, f = cap.read()
    if not ok:
        break
    M = (Z @ corr[i])[:2]
    enc.stdin.write(cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).tobytes())
enc.stdin.close()
enc.wait()
