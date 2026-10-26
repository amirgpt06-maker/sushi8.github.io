"""Матрицы для доспехов и копья по 3D-суставам (координаты камеры: x вправо, y вниз, z вперёд).

Использование: python rig.py work_dir  ->  work/rig.json
Каждая «кость»: 4x4 (столбцы: ось X, ось Y вдоль кости, ось Z, начало), плюс длина.
"""
import json
import sys

import numpy as np
from scipy.signal import savgol_filter

W = sys.argv[1]
S = json.load(open(f"{W}/solve.json"))
J = np.array(S["joints"])
N = len(J)
HL = np.array([h["L"] for h in S["hands"]])
HR = np.array([h["R"] for h in S["hands"]])
nrm = lambda v: v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9)


def frame(o, y, xref):
    """Ортонормированный базис: Y вдоль кости, X — ближе всего к xref, Z = X × Y."""
    y = nrm(y)
    x = nrm(xref - (xref * y).sum(-1, keepdims=True) * y)
    z = np.cross(x, y)
    M = np.zeros((len(o), 4, 4))
    M[:, :3, 0], M[:, :3, 1], M[:, :3, 2], M[:, :3, 3], M[:, 3, 3] = x, y, z, o, 1
    return M


Lsh, Rsh, Lhip, Rhip = J[:, 11], J[:, 12], J[:, 23], J[:, 24]
smid, hmid = (Lsh + Rsh) / 2, (Lhip + Rhip) / 2
left = Lsh - Rsh                                # X торса — влево от человека
torso = frame(smid, smid - hmid, left)          # Y вверх, Z вперёд (к камере, если человек к ней лицом)
fwd = torso[:, :3, 2]
out = {"N": N, "torso": torso, "torso_len": np.linalg.norm(smid - hmid, axis=1),
       "shoulder_w": float(np.median(np.linalg.norm(left, axis=1)))}

# руки/ноги: Y от проксимального сустава к дистальному; X — «наружу» (от тела)
for side, sgn, (a, b, c), (h, k, an) in (("L", 1, (11, 13, 15), (23, 25, 27)), ("R", -1, (12, 14, 16), (24, 26, 28))):
    outward = torso[:, :3, 0]          # X всех конечностей — «влево торса»; «наружу» учитывает armor.py
    out[f"uarm_{side}"] = frame(J[:, a], J[:, b] - J[:, a], outward)
    out[f"farm_{side}"] = frame(J[:, b], J[:, c] - J[:, b], outward)
    out[f"thigh_{side}"] = frame(J[:, h], J[:, k] - J[:, h], outward)
    out[f"shin_{side}"] = frame(J[:, k], J[:, an] - J[:, k], outward)
    for n, (p, q) in ((f"uarm_{side}", (a, b)), (f"farm_{side}", (b, c)), (f"thigh_{side}", (h, k)), (f"shin_{side}", (k, an))):
        out[n + "_len"] = np.linalg.norm(J[:, q] - J[:, p], axis=1)

# голова: центр между ушами, X влево, Z вперёд (к носу), Y вверх
earL, earR, nose = J[:, 7], J[:, 8], J[:, 0]
emid = (earL + earR) / 2
X = nrm(earL - earR)
F = nose - emid
Z = nrm(F - (F * X).sum(-1, keepdims=True) * X)
Y = np.cross(Z, X)
head = np.zeros((N, 4, 4))
head[:, :3, 0], head[:, :3, 1], head[:, :3, 2], head[:, :3, 3], head[:, 3, 3] = X, Y, Z, emid, 1
out["head"] = head
out["head_w"] = float(np.median(np.linalg.norm(earL - earR, axis=1)))

# копьё: ось через обе ладони; при сближенных руках — направление «от плеч к рукам» (выпад);
# знак выбирается непрерывно, на кадре 0 остриё смотрит вправо (на динозавра)
hm = (HL + HR) / 2
base = HR - HL
blen = np.linalg.norm(base, axis=1)
thrust = nrm(hm - smid)
d = np.zeros((N, 3))
prev = np.array([1.0, -0.25, -0.3])
for i in range(N):
    c1 = nrm(base[i])
    if c1 @ prev < 0:
        c1 = -c1
    w = np.clip((blen[i] - 0.10) / 0.22, 0, 1)
    c2 = thrust[i] if thrust[i] @ prev > -0.3 else prev
    v = nrm(w * c1 + (1 - w) * c2)
    v = nrm(0.55 * v + 0.45 * prev)          # инерция древка
    d[i] = prev = v
d = nrm(savgol_filter(d, 9, 2, axis=0))
# в кадре копьё должно продолжать руки: ограничиваем наклон по глубине (иначе при выпаде — «обрубок» на камеру)
xy = np.linalg.norm(d[:, :2], axis=1)
d[:, 2] = np.sign(d[:, 2]) * np.minimum(np.abs(d[:, 2]), 0.22 * xy)
# выпады вправо (на динозавра) — остриё уходит чуть вглубь сцены, а не на камеру
k = np.clip((d[:, 0] / (xy + 1e-9) - 0.35) / 0.4, 0, 1)
d[:, 2] = d[:, 2] * (1 - k) + 0.28 * xy * k
d = nrm(d)
# передняя рука — та, что дальше вдоль оси
front = np.where(((HR - HL) * d).sum(1)[:, None] > 0, HR, HL)
SPEAR = 2.3
tip = front + d * 0.75
butt = tip - d * SPEAR
out["spear"] = frame(butt, d, np.tile([0, 0, 1.0], (N, 1)))
out["spear_tip"] = tip
out["hands_mid"] = hm

for n in ("uarm", "farm", "thigh", "shin"):
    out[n + "_ref"] = float(np.median(np.r_[out[n + "_L_len"], out[n + "_R_len"]]))
out["torso_ref"] = float(np.median(out["torso_len"]))
for k, v in list(out.items()):
    if isinstance(v, np.ndarray):
        out[k] = v.tolist()
json.dump(out, open(f"{W}/rig.json", "w"))

np.set_printoptions(precision=2, suppress=True)
R = np.array(S["cam_R"]); t = np.array(S["cam_t"])
to_world = lambda i, p: R[i].T @ (p - t[i])
for i in list(range(0, 286, 12)) + list(range(250, 272, 2)):
    print(f"кадр {i:3d}: таз(мир) {to_world(i, hmid[i])}, нос(мир) {to_world(i, nose[i])}, остриё(мир) {to_world(i, tip[i])}, напр {d[i]}")
