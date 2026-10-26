"""Панорама комнаты (equirect) из кадров ролика — для отражений в стали и освещения CG как в реальной комнате.

Использование: python envmap.py work_dir  ->  work/env.hdr (линейный цвет, ось Z — вверх, как в Blender)
"""
import json
import os
import sys

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402

W = sys.argv[1]
S = json.load(open(f"{W}/solve.json"))
f = S["f"]
EW, EH = 2048, 1024
u = (np.arange(EW) + 0.5) / EW
v = (np.arange(EH) + 0.5) / EH
U, V = np.meshgrid(u, v)
phi = -(U - 0.5) * 2 * np.pi
theta = (0.5 - V) * np.pi                  # верх картинки — зенит
dS = np.stack([np.cos(theta) * np.cos(phi), np.cos(theta) * np.sin(phi), np.sin(theta)], -1)
# Z-up (Blender) -> камера кадра 0 (x вправо, y вниз, z вперёд): вперёд сцены = +Y_S
cam0 = np.stack([dS[..., 0], -dS[..., 2], dS[..., 1]], -1)

to_lin = lambda x: np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
acc = np.zeros((EH, EW, 3), np.float32)
wsum = np.zeros((EH, EW, 1), np.float32)
for i in range(0, len(S["cam_R"]), 15):
    img = to_lin(cv2.cvtColor(cv2.imread(f"{W}/frames/{i:04d}.png"), cv2.COLOR_BGR2RGB).astype(np.float32) / 255)
    pm = cv2.imread(f"{W}/masks/person_{i:04d}.png", 0)
    keep = (cv2.dilate((cv2.resize(pm, (1920, 1080)) > 60).astype(np.uint8), np.ones((51, 51))) == 0).astype(np.float32)
    R = np.array(S["cam_R"][i])
    cur = cam0 @ R.T
    z = cur[..., 2]
    ok = z > 0.05
    px = np.where(ok, f * cur[..., 0] / np.maximum(z, 1e-3) + 960, -1).astype(np.float32)
    py = np.where(ok, f * cur[..., 1] / np.maximum(z, 1e-3) + 540, -1).astype(np.float32)
    smp = cv2.remap(img, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    km = cv2.remap(keep, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)[..., None]
    edge = np.clip(np.minimum.reduce([px, 1919 - px, py, 1079 - py]) / 80, 0, 1)[..., None]
    wgt = km * edge * ok[..., None]
    acc += smp * wgt
    wsum += wgt
known = acc / np.maximum(wsum, 1e-6)
cover = np.clip(wsum * 3, 0, 1)
# невидимые направления: «зеркальная» комната (то, что за камерой, похоже на то, что перед ней), сильно размытая
mir = known[:, ::-1]
mir_c = cover[:, ::-1]
bc = cv2.GaussianBlur(mir_c, (0, 0), 25)[..., None]
fill = cv2.GaussianBlur(mir * mir_c, (0, 0), 25) / np.maximum(bc, 1e-3)
avg = (known * cover).sum((0, 1)) / cover.sum()
fill = np.where(bc > 0.02, fill, avg)
env = known * cover + fill * (1 - cover)
# потолок светлее (светильники), пол темнее
env *= (1 + 0.6 * np.clip(np.sin(theta), 0, 1) ** 3)[..., None]
env *= (1 - 0.35 * np.clip(-np.sin(theta), 0, 1))[..., None]
env = cv2.GaussianBlur(env, (0, 0), 1.2)
cv2.imwrite(f"{W}/env.hdr", cv2.cvtColor(env.astype(np.float32), cv2.COLOR_RGB2BGR))
cv2.imwrite(f"{W}/env_preview.jpg", cv2.cvtColor((np.clip(env, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
print("панорама готова", env.shape, "покрытие", float(cover.mean()))
