"""Композитинг: пластина + тени динозавра + динозавр + человек + латы/копьё + перчатки, грейдинг, зерно, тряска.

Использование: python comp.py work_dir render_dir out_dir [кадры через запятую | all]
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import OpenEXR

W, RD, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
T = json.load(open(f"{W}/track.json"))
FR = T["frames"]
N = len(FR)
w, h = T["size"]
sel = range(N) if len(sys.argv) < 5 or sys.argv[4] == "all" else [int(x) for x in sys.argv[4].split(",")]

to_lin = lambda x: np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
to_srgb = lambda x: np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0.0031308, None), 1 / 2.4) - 0.055)

# моменты удара/рёва -> тряска камеры (кадр, сила, затухание)
SHAKES = [(66, 9, 18), (114, 6, 8), (146, 4, 8), (204, 10, 10), (228, 7, 20), (262, 14, 14)]


def guided(I, p, r=8, eps=1e-3):
    box = lambda x: cv2.boxFilter(x, -1, (r, r))
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return box(a) * I + box(b)


def read_layers(i):
    f = OpenEXR.File(str(RD / f"{i:04d}.exr"))
    L = {}
    for p in f.parts:
        for k, c in p.channels.items():
            img = np.asarray(c.pixels, np.float32)
            L[k] = cv2.resize(img, (w, h), interpolation=cv2.INTER_CUBIC)
    return L


def hand_mask(i):
    m = np.zeros((h, w), np.uint8)
    f = FR[i]
    groups = [np.array(hd["pts"]) for hd in f["hands"]]
    P = np.array(f["pose"])[:, :2]
    have = {("R" if hd["side"] == "Left" else "L") for hd in f["hands"]}
    for side, ids in (("L", [15, 17, 19, 21]), ("R", [16, 18, 20, 22])):
        if side not in have:
            groups.append(P[ids])
    for g in groups:
        hull = cv2.convexHull(g.astype(np.int32))
        cv2.fillConvexPoly(m, hull, 255)
    return cv2.dilate(m, np.ones((31, 31), np.uint8))


def grain(shape, seed, amt):
    rng = np.random.default_rng(seed)
    g = rng.normal(0, 1, (shape[0] // 2, shape[1] // 2, 1)).astype(np.float32)
    g = cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)[..., None]
    return g * amt


for i in sel:
    plate = cv2.cvtColor(cv2.imread(f"{W}/frames/{i:04d}.png"), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    lin = to_lin(plate)
    gray = cv2.cvtColor(plate, cv2.COLOR_RGB2GRAY)
    pm = cv2.imread(f"{W}/masks/person_{i:04d}.png", 0).astype(np.float32) / 255
    pm = cv2.resize(pm, (w, h))
    pa = np.clip(guided(gray, pm, 12, 2e-3), 0, 1)
    pa = np.clip((pa - 0.25) / 0.5, 0, 1)[..., None]
    cl = cv2.resize(cv2.imread(f"{W}/masks/clothes_{i:04d}.png", 0), (w, h)).astype(np.float32) / 255
    sk = cv2.resize(cv2.imread(f"{W}/masks/skin_{i:04d}.png", 0), (w, h)).astype(np.float32) / 255

    Lr = read_layers(i)
    ARMOR = "spear_full.Combined" not in Lr
    # человек: с латами — футболка -> тёмный поддоспешник, руки -> кожаные перчатки; без лат — как есть
    person = lin.copy()
    lum = (lin @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    hsv = cv2.cvtColor(plate, cv2.COLOR_RGB2HSV)
    greenish = ((hsv[..., 0] > 35) & (hsv[..., 0] < 110) & (hsv[..., 1] > 0.12)).astype(np.float32)
    shirt = cv2.GaussianBlur(np.clip(cl, 0, 1) * greenish, (9, 9), 0)[..., None]
    mail = lum * np.array([0.78, 0.80, 0.86], np.float32) * 0.85
    if ARMOR:
        person = person * (1 - shirt) + mail * shirt
    hm = cv2.GaussianBlur(hand_mask(i).astype(np.float32) / 255 * np.clip(sk * 1.4, 0, 1), (7, 7), 0)[..., None]
    glove = lum * np.array([0.55, 0.36, 0.24], np.float32) * 0.7 if ARMOR else lin
    person = person * (1 - hm) + glove * hm

    tre, shd, fro = Lr["trex.Combined"], Lr["trex.Shadow Catcher"], Lr["front.Combined"]
    # CG мягче, как оптика телефона
    tre = cv2.GaussianBlur(tre, (0, 0), 0.9)
    fro = cv2.GaussianBlur(fro, (0, 0), 0.7)
    # тени динозавра на стене/полу (только вне человека)
    shadow = np.clip(shd, 0, 1.0)
    base = lin * (shadow * (1 - pa) + pa)
    base = base * (1 - pa) + person * pa
    # динозавр позади человека
    ta = np.clip(tre[..., 3:4], 0, 1)
    base = tre[..., :3] + base * (1 - ta)
    base = base * (1 - pa * (ta > 0)) + person * pa * (ta > 0)
    # латы и копьё
    if not ARMOR:
        # копьё за телом прячется только внутри силуэта человека
        full = cv2.GaussianBlur(Lr["spear_full.Combined"], (0, 0), 0.7)
        fro = fro + (full - fro) * (1 - pa)
    fa = np.clip(fro[..., 3:4], 0, 1)
    frgb = fro[..., :3]
    frgb = frgb / (1 + frgb * 0.25)                      # мягкое сжатие бликов стали
    base = frgb + base * (1 - fa)
    # перчатки поверх древка
    base = base * (1 - hm) + glove * hm

    # --- грейдинг: лёгкий «киношный» контраст, тёплые света / холодные тени, виньетка ---
    img = np.clip(base, 0, None)
    img = img / (1 + img * 0.08)
    srgb = to_srgb(img)
    srgb = np.clip((srgb - 0.5) * 1.08 + 0.5 - 0.01, 0, 1)
    l = srgb.mean(2, keepdims=True)
    srgb = srgb + (np.array([0.02, 0.005, -0.02]) * l + np.array([-0.012, 0.0, 0.015]) * (1 - l))
    yy, xx = np.mgrid[0:h, 0:w]
    vig = 1 - 0.28 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) ** 1.3
    srgb = srgb * vig[..., None]
    srgb = np.clip(srgb + grain(srgb.shape, i, 0.018), 0, 1)

    # тряска камеры
    dx = dy = rot = 0.0
    for f0, amp, dur in SHAKES:
        if f0 <= i < f0 + dur * 2:
            e = math.exp(-(i - f0) / dur)
            dx += amp * e * math.sin(i * 2.1)
            dy += amp * e * math.cos(i * 2.9)
            rot += amp * 0.03 * e * math.sin(i * 1.7)
    if dx or dy:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.03)
        M[:, 2] += (dx, dy)
        srgb = cv2.warpAffine(srgb, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    cv2.imwrite(str(OUT / f"{i:04d}.png"), cv2.cvtColor((srgb * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
    print("комп", i, flush=True)
