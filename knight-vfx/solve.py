"""3D-решение сцены: суставы человека в координатах камеры + вращение камеры по фону.

Использование: python solve.py work_dir
Пишет work/solve.json: {"f": фокус_px, "cam_R": [3x3 на кадр, поворот камеры относительно кадра 0],
                         "joints": [[33 x [x,y,z] в метрах, камера: x вправо, y вниз, z вперёд] на кадр],
                         "hands": [{"L": [x,y,z], "R": [x,y,z]} на кадр]}
"""
import json
import sys

import cv2
import numpy as np
from scipy.signal import savgol_filter

W = sys.argv[1]
T = json.load(open(f"{W}/track.json"))
F = T["frames"]
N = len(F)
w, h = T["size"]
cx, cy = w / 2, h / 2

img2d = np.array([[p[:2] for p in f["pose"]] for f in F], float)      # N x 33 x 2
vis = np.array([[p[3] for p in f["pose"]] for f in F], float)
world = np.array([f["world"] for f in F], float)                      # N x 33 x 3 (метры, от центра таза)

# сглаживание 2D-точек по времени (убирает дрожание, сохраняет резкие движения)
img2d = savgol_filter(img2d, 9, 2, axis=0)
world = savgol_filter(world, 9, 2, axis=0)

BODY = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26]


def pnp(fpx):
    K = np.array([[fpx, 0, cx], [0, fpx, cy], [0, 0, 1]], float)
    err, poses = 0, []
    for i in range(N):
        ok, rv, tv = cv2.solvePnP(world[i, BODY], img2d[i, BODY], K, None, flags=cv2.SOLVEPNP_SQPNP)
        proj, _ = cv2.projectPoints(world[i, BODY], rv, tv, K, None)
        err += np.mean(np.linalg.norm(proj[:, 0] - img2d[i, BODY], axis=1))
        poses.append((rv, tv))
    return err / N, poses, K


best = min((pnp(f)[0], f) for f in range(900, 2601, 100))
fpx = best[1]
for f in np.arange(fpx - 90, fpx + 91, 30):
    e = pnp(f)[0]
    if e < best[0]:
        best = (e, f)
fpx = float(best[1])
err, poses, K = pnp(fpx)
print(f"фокус {fpx:.0f}px, ошибка проекции {err:.1f}px")

# суставы в координатах камеры; глубина из PnP, а x/y точно по 2D-точкам
joints = np.zeros((N, 33, 3))
for i, (rv, tv) in enumerate(poses):
    R, _ = cv2.Rodrigues(rv)
    cam = world[i] @ R.T + tv[:, 0]
    z = cam[:, 2]
    joints[i, :, 0] = (img2d[i, :, 0] - cx) / fpx * z
    joints[i, :, 1] = (img2d[i, :, 1] - cy) / fpx * z
    joints[i, :, 2] = z
joints = savgol_filter(joints, 11, 2, axis=0)

# руки: центр ладони (среднее точек 0,5,9,13,17), глубина — от запястья
hands = []
for i, f in enumerate(F):
    d = {}
    for hd in f["hands"]:
        p = np.array(hd["pts"])[[0, 5, 9, 13, 17]].mean(0)
        # MediaPipe называет руку по зеркальному изображению: "Left" = правая рука человека
        side = "R" if hd["side"] == "Left" else "L"
        wj = 16 if side == "R" else 15
        z = joints[i, wj, 2]
        d[side] = [(p[0] - cx) / fpx * z, (p[1] - cy) / fpx * z, z]
    for side, wj, ij in (("L", 15, 19), ("R", 16, 20)):  # нет детекции — запястье + к указательному
        if side not in d:
            d[side] = (joints[i, wj] * 0.4 + joints[i, ij] * 0.6).tolist()
    hands.append(d)
for s in "LR":
    arr = savgol_filter(np.array([hd[s] for hd in hands]), 9, 2, axis=0)
    for i in range(N):
        hands[i][s] = arr[i].tolist()

# Камера: длинные треки точек фона (стена, ТВ, мебель справа) от кадра 0; их 3D — на плоскости глубиной WALL;
# по ним на каждом кадре PnP+RANSAC -> поза камеры (R, t): x_тек = R x_0 + t
WALL = 3.4
gray = lambda i: cv2.cvtColor(cv2.imread(f"{W}/frames/{i:04d}.png"), cv2.COLOR_BGR2GRAY)
pmask = lambda i: cv2.dilate((cv2.resize(cv2.imread(f"{W}/masks/person_{i:04d}.png", 0), (w, h)) > 60).astype(np.uint8), np.ones((41, 41)))
prev = gray(0)
bg = ((pmask(0) == 0) * 255).astype(np.uint8)
bg[:, : w // 2] = 0                                    # опорные точки — правая половина (там будет динозавр)
pts = cv2.goodFeaturesToTrack(prev, 600, 0.008, 14, mask=bg)[:, 0]
X0 = np.c_[(pts[:, 0] - cx) / fpx * WALL, (pts[:, 1] - cy) / fpx * WALL, np.full(len(pts), WALL)]
alive = np.ones(len(pts), bool)
cur_pts = pts.copy()
cam_R, cam_t = [np.eye(3)], [np.zeros(3)]
rv0, tv0 = np.zeros((3, 1)), np.zeros((3, 1))
for i in range(1, N):
    cur = gray(i)
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, cur_pts.astype(np.float32), None, winSize=(31, 31), maxLevel=4)
    back, st2, _ = cv2.calcOpticalFlowPyrLK(cur, prev, nxt, None, winSize=(31, 31), maxLevel=4)
    fb = np.linalg.norm(back - cur_pts, axis=1)
    pm = pmask(i)
    inside = (nxt[:, 0] > 2) & (nxt[:, 0] < w - 2) & (nxt[:, 1] > 2) & (nxt[:, 1] < h - 2)
    occl = np.zeros(len(nxt), bool)
    occl[inside] = pm[nxt[inside, 1].astype(int), nxt[inside, 0].astype(int)] > 0
    alive &= (st[:, 0] == 1) & (st2[:, 0] == 1) & (fb < 1.0) & inside & ~occl
    cur_pts = nxt
    ok, rv0, tv0, inl = cv2.solvePnPRansac(X0[alive], cur_pts[alive], K, None, rv0, tv0, useExtrinsicGuess=True,
                                           reprojectionError=3.0, iterationsCount=200)
    cam_R.append(cv2.Rodrigues(rv0)[0])
    cam_t.append(tv0[:, 0].copy())
    prev = cur
print("живых треков к концу:", int(alive.sum()))
rv = savgol_filter(np.array([cv2.Rodrigues(r)[0][:, 0] for r in cam_R]), 9, 2, axis=0)
tv = savgol_filter(np.array(cam_t), 9, 2, axis=0)
cam_R = [cv2.Rodrigues(v)[0].tolist() for v in rv]
cam_t = tv.tolist()
print(f"панорама камеры: {np.degrees(rv[:, 1]).min():.1f}°..{np.degrees(rv[:, 1]).max():.1f}°, сдвиг до {np.abs(tv).max():.2f} м")
print("глубина человека (м):", np.round(joints[::40, 23:25, 2].mean(1), 2))

json.dump({"f": fpx, "size": [w, h], "fps": T["fps"], "cam_R": cam_R, "cam_t": cam_t, "joints": joints.tolist(), "hands": hands},
          open(f"{W}/solve.json", "w"))
