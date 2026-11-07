"""Наш стиль монтажа: сборка. Исходник + оверлей (render.js) + эффекты по fx.json + звуки по events.json.

Использование: python compose.py source.mp4 overlay_dir out.mp4
Переменные: SPEED=1.0 (ускорение всего ролика), GRADE=1 (мягкая «эппловская» цветокоррекция), FROM/TO (секунды — кусок для проверки),
            SFX_GAIN=1.0 (общая громкость эффектов), AUDIO_ONLY=1 (пересобрать только звук),
            LOUDNORM=0 (не нормализовать громкость — для роликов без голоса),
            GRADE=cinema (кинотонировка: матовые тени в бирюзу, тёплая кожа, приглушённая зелень), VIGNETTE=1 (виньетка — только по просьбе),
            MATTE=папка (маска человека от matte.py — для текста «за спиной», силуэта и замены фона).
Звуки: сначала engine/sfx_local (собирает pack_to_sfx.py из вашего пака), иначе engine/sfx (синтез).
По кадру: наезд (по лицу) -> размытие+затемнение фона -> цвет -> оверлей -> стеклянная линза (настоящее преломление) -> засветка -> зерно.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf

src, ov_dir, out = sys.argv[1:4]
ov_dir = Path(ov_dir)
SPEED = float(os.environ.get("SPEED", "1.0"))
GMODE = os.environ.get("GRADE", "1")
GRAIN_AMT = float(os.environ.get("GRAIN", "0"))
FILM_AMT = float(os.environ.get("FILM", "1.0"))       # сила GRADE=film (0.5 — мягче, 1 — стандарт)      # 0 — без зерна (по умолчанию); 0.006 — лёгкое плёночное
GRADE = GMODE != "0"
MATTE = Path(os.environ["MATTE"]) if os.environ.get("MATTE") else None
SFX_GAIN = float(os.environ.get("SFX_GAIN", "1.0"))
FX = {int(k): v for k, v in json.load(open(ov_dir / "fx.json")).items()}
EV = json.load(open(ov_dir / "events.json"))
HERE = Path(__file__).resolve().parent
LOCAL = Path(os.environ["SFX_LOCAL"]) if os.environ.get("SFX_LOCAL") else HERE / "sfx_local"   # SFX_LOCAL — другой набор звуков
SFX_DIRS = [d for d in (LOCAL, HERE / "sfx") if d.exists()]   # сначала свой пак (sfx_local), потом синтез


ALIAS = {"aplkey1": "key1", "aplkey2": "key2", "aplkey3": "key3", "aplkey4": "key4", "wbwhoosh": "swoosh", "wbslide": "swoosh",
         "wbpop": "pop", "wbbounce": "tink", "wbclick": "click2", "wbselect": "typeone", "wbshimmer": "shimmer"}   # если пака нет — синтез


def sfx_path(role):
    for r in (role, ALIAS.get(role, role)):
        for d in SFX_DIRS:
            if (d / f"{r}.wav").exists():
                return d / f"{r}.wav"
    raise FileNotFoundError(f"нет звука «{role}» ни в sfx_local, ни в sfx")
cap = cv2.VideoCapture(src)
FPS = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
F0 = int(float(os.environ.get("FROM", 0)) * FPS)
F1 = min(N, int(float(os.environ.get("TO", N / FPS)) * FPS))
work = Path(out).with_suffix(".work")
work.mkdir(parents=True, exist_ok=True)
AUDIO_ONLY = os.environ.get("AUDIO_ONLY") == "1" and (work / "v.mp4").exists()
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# виньетка (затемнение углов) — только по просьбе: VIGNETTE=1 (правило пользователя: углы не затемнять)
VIG = ((1 - 0.16 * np.clip(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2, 0, 1.6) ** 1.4)[..., None].astype(np.float32)
       if os.environ.get("VIGNETTE") == "1" else np.float32(1.0))


# мягкая «эппловская» коррекция: лёгкая S-кривая, тёплые тени / холодные света, +4 % насыщенности (всё во float32 — быстро)
SH, HI = np.float32([1.02, 1.0, 0.98]), np.float32([0.99, 1.0, 1.015])
F = np.float32


def grade(x):
    s = x * x * (F(3) - F(2) * x)
    x = x + (s - x) * F(0.18)
    l = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)[..., None]
    x = x * (SH + (HI - SH) * l)
    l = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)[..., None]
    return np.clip(l + (x - l) * F(1.04), 0, 1)


def grade_cinema(x):
    """Кино: плотный контраст, тени в холодный бирюзовый, света тёплые, зелень приглушена, кожа сохраняется, мягкая виньетка."""
    s = x * x * (F(3) - F(2) * x)
    x = x + (s - x) * F(0.32)
    l = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)[..., None]
    x = x * (np.float32([1.07, 1.0, 0.93]) * (1 - l) + np.float32([0.95, 1.0, 1.06]) * l)   # BGR: тени синее, света теплее
    hsv = cv2.cvtColor(x, cv2.COLOR_BGR2HSV)
    h = hsv[..., 0]
    green = np.exp(-((h - 110) / 35) ** 2)                 # зелень (OpenCV float: H 0..360)
    hsv[..., 1] *= (1 - 0.45 * green) * F(0.9)
    x = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    x = x * F(0.96) + F(0.012)                              # матовые тени
    return np.clip(x * VIG, 0, 1)


def grade_film(x, amt=1.0):
    """«Как в кино», без передоза (просьба пользователя): плёночная S-кривая с мягким плечом в светах,
    лёгкий сплит-тон (тени чуть холоднее, света чуть теплее), вибранс (тусклое ярче, насыщенное и кожа — почти без изменений),
    зелень спокойнее и чуть в оливу. Средняя яркость кадра сохраняется — картинка не светлеет. amt 0..1 — сила."""
    src_l = float(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).mean())
    y = x
    # кривая: контраст в середине + мягкое плечо в светах + чуть приподнятый, но плотный чёрный
    s_ = y * y * (F(3) - F(2) * y)
    y = y + (s_ - y) * F(0.22 * amt)
    y = np.where(y > 0.78, F(0.78) + (y - F(0.78)) * F(1 - 0.35 * amt) / (F(1) + (y - F(0.78)) * F(1.2 * amt)), y)
    y = F(0.012 * amt) + y * F(1 - 0.012 * amt)
    # сплит-тон по яркости (BGR)
    l = cv2.cvtColor(y, cv2.COLOR_BGR2GRAY)[..., None]
    sh = np.clip(1 - l / 0.45, 0, 1) ** 1.5
    hi = np.clip((l - 0.55) / 0.45, 0, 1) ** 1.5
    y = y + (sh * np.float32([0.020, 0.006, -0.012]) + hi * np.float32([-0.016, 0.0, 0.020])) * F(amt)
    # вибранс + зелень + защита кожи
    hsv = cv2.cvtColor(np.clip(y, 0, 1), cv2.COLOR_BGR2HSV)
    h, sat = hsv[..., 0], hsv[..., 1]
    skin = np.exp(-((h - 25) / 18) ** 2)                      # оранжевые/телесные оттенки
    green = np.exp(-((h - 105) / 30) ** 2)
    boost = F(0.20 * amt) * (1 - sat) * (1 - 0.75 * skin) - F(0.12 * amt) * green
    hsv[..., 1] = np.clip(sat * (1 + boost), 0, 1)
    hsv[..., 0] = h - F(8 * amt) * green                      # зелень чуть в оливу
    y = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    # сохранить среднюю яркость исходного кадра
    # вернуть среднюю яркость кадра гаммой средних тонов (небо и чёрные остаются плотными, а не «умножаются» вверх)
    y = np.clip(y, 1e-5, 1)
    g = 1.0
    for _ in range(3):
        cur = float(cv2.cvtColor(y ** F(g), cv2.COLOR_BGR2GRAY).mean())
        g *= float(np.log(max(src_l, 1e-4)) / np.log(max(cur, 1e-4))) if 0 < cur < 1 else 1.0
    return np.clip(y ** F(g), 0, 1)


def mask_at(i, s, cx, cy):
    """Маска человека для кадра i, с тем же наездом, что и кадр."""
    if not MATTE:
        return None
    f = MATTE / f"{i:05d}.png"
    if not f.exists():
        return None
    m = cv2.resize(cv2.imread(str(f), cv2.IMREAD_GRAYSCALE), (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * (1 / 255)
    return zoom(m, s, cx, cy)[..., None]


_bgcap = {}


def bg_frame(src_, t):
    """Кадр фона для замены: картинка или видео (зациклено), заполняет кадр по размеру (cover)."""
    if src_.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        img = _bgcap.get(src_)
        if img is None:
            img = _bgcap[src_] = cv2.imread(src_)
    else:
        cap2 = _bgcap.get(src_)
        if cap2 is None:
            cap2 = _bgcap[src_] = cv2.VideoCapture(src_)
        n2 = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        cap2.set(cv2.CAP_PROP_POS_FRAMES, int(t * (cap2.get(cv2.CAP_PROP_FPS) or 30)) % n2)
        ok2, img = cap2.read()
    h0, w0 = img.shape[:2]
    k = max(W / w0, H / h0)
    img = cv2.resize(img, (int(w0 * k + 1), int(h0 * k + 1)))
    y0, x0 = (img.shape[0] - H) // 2, (img.shape[1] - W) // 2
    return img[y0:y0 + H, x0:x0 + W].astype(np.float32) * (1 / 255)


def zoom(img, s, cx, cy):
    if abs(s - 1) < 1e-4:
        return img
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), 0, s)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def lens(img, x, y, r, a):
    """Liquid-glass линза: увеличение в центре, сжатие и преломление у края, лёгкий расфокус, блик и тонкий светлый обод."""
    if a <= 0.01 or r < 4:
        return img
    p = int(r + 14)
    x0, x1, y0, y1 = int(max(0, x - p)), int(min(W, x + p)), int(max(0, y - p)), int(min(H, y + p))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return img
    gx, gy = xx[y0:y1, x0:x1] - x, yy[y0:y1, x0:x1] - y
    d = np.sqrt(gx * gx + gy * gy) / r
    dd = np.clip(d, 0, 1)
    k = 0.80 + 0.12 * dd ** 2 + 0.55 * np.clip(dd - 0.82, 0, 1) ** 1.5 * 6   # центр увеличен, край «загибается»
    mx, my = (x + gx * k).astype(np.float32), (y + gy * k + 4 * dd ** 3).astype(np.float32)
    ref = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ref = cv2.GaussianBlur(ref, (0, 0), 1.6)
    ref = ref * 1.04 + 0.035
    # блик сверху-слева и мягкая тень снизу внутри
    hl = np.exp(-(((gx + 0.35 * r) / (0.55 * r)) ** 2 + ((gy + 0.55 * r) / (0.28 * r)) ** 2)) * 0.22
    ref = ref + hl[..., None]
    ref = ref - (np.clip(gy / r, 0, 1) ** 2 * 0.05)[..., None]
    m = np.clip((1 - d) * r / 1.2, 0, 1)[..., None]                          # сглаженный край
    roi = img[y0:y1, x0:x1]
    res = roi * (1 - m) + ref * m
    # обод: тонкое светлое кольцо, ярче сверху-слева
    ring = np.exp(-((d - 1) * r / 1.3) ** 2)
    ang = np.clip(0.55 - 0.45 * (gx + gy) / (r * 1.4142), 0.15, 1)
    res = res + (ring * ang * 0.6)[..., None]
    # мягкая внешняя тень
    sh = np.exp(-(np.clip(d - 1, 0, None) * r / 6) ** 2) * (d > 1) * 0.12
    res = res * (1 - sh[..., None])
    out_ = img.copy()
    out_[y0:y1, x0:x1] = roi * (1 - a) + np.clip(res, 0, 1) * a
    return out_


def load_ov(f):
    """Кадр оверлея; если есть подкадры NNNNN.mJ.png (размытие в движении) — усреднить их с учётом прозрачности."""
    subs = [f] + sorted(f.parent.glob(f.stem + ".m*.png"))
    acc = None
    for g in subs:
        o = cv2.imread(str(g), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
        if o.shape[2] == 3:
            o = np.dstack([o, np.ones(o.shape[:2], np.float32)])
        o[..., :3] *= o[..., 3:4]
        acc = o if acc is None else acc + o
    acc /= len(subs)
    if len(subs) == 1 and acc[..., 3].min() > 0.999:
        return acc[..., :3]
    a = acc[..., 3:4]
    rgb = np.where(a > 1e-4, acc[..., :3] / np.maximum(a, 1e-4), 0)
    return np.dstack([rgb, a[..., 0]])


def ball(img, x, y, r, a, frost, sq=0.0, white=0.0, rot=0.0, m3=0.0, p3=0.0, m4=0.0, p4=0.0, flat=0.0, egg=0.0):
    """Стеклянная капля как в референсе: увеличивает то, что под ней, у края «стягивает» текст дугой (сильное
    преломление, цветная кайма). Форма живая, как резина: sq — сплющивание вдоль оси rot, m3/m4 — волна по краю
    (фазы p3/p4), flat — плоское донышко капли на стекле, egg — низ шире верха. frost 0..1 — мутнеет до
    голубо-сиреневого матового стекла, white 0..1 — белеет и мягко растворяет край (из него проявляется новая сцена)."""
    if a <= 0.01 or r < 4:
        return img
    A, B = 1 + sq, 1 / (1 + sq)
    p = int(r * max(A, B) * (1 + abs(m3) + abs(m4) + abs(egg)) + 30 + 60 * white)
    x0, x1, y0, y1 = int(max(0, x - p)), int(min(W, x + p)), int(max(0, y - p)), int(min(H, y + p))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return img
    gx, gy = xx[y0:y1, x0:x1] - x, yy[y0:y1, x0:x1] - y
    rho = np.sqrt(gx * gx + gy * gy)
    th = np.arctan2(gy, gx)
    c, s_ = np.cos(th - rot), np.sin(th - rot)
    shape = 1 / np.sqrt((c / A) ** 2 + (s_ / B) ** 2)                       # эллипс
    shape = shape * (1 + m3 * np.cos(3 * (th - p3)) + m4 * np.cos(4 * (th - p4)) + egg * np.sin(th))
    shape = shape * (1 - flat * np.clip(np.sin(th), 0, 1) ** 4)             # sin>0 — низ кадра
    Rth = r * shape
    d = rho / Rth
    ex, ey = gx / Rth, gy / Rth                                             # координаты внутри капли (единичный круг)
    dd = np.clip(d, 0, 0.999)
    z = np.sqrt(1 - dd * dd)                                                # «выпуклость»
    k = 0.56 + 0.70 * (1 - z) ** 2                                          # центр ×1.8, у края резкий рост -> текст тянется дугой
    chans = []
    for ci, ca in enumerate((1.035, 1.0, 0.965)):                           # B G R: лёгкая хроматическая кайма у края
        kc = k * (1 + (ca - 1) * (1 - z))
        mx, my = (x + gx * kc).astype(np.float32), (y + gy * kc).astype(np.float32)
        chans.append(cv2.remap(np.ascontiguousarray(img[..., ci]), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT))
    ref = np.dstack(chans)
    bl = 0.5 + 16 * frost + 14 * white
    if bl > 0.6:
        ref = cv2.GaussianBlur(ref, (0, 0), bl)
    # матовое стекло: сверху остаётся размытое содержимое, книзу — голубо-сиреневый, по нижнему краю светится
    lav = np.float32([0.95, 0.74, 0.74])                                    # BGR
    vg = np.clip(0.35 + 0.65 * (ey + 0.6) / 1.6, 0, 1)[..., None]
    tint = frost * (0.25 + 0.6 * vg) * (1 - white)
    ref = ref * (1 - tint) + lav * (0.92 + 0.08 * z[..., None]) * tint
    glow = np.exp(-((d - 0.92) * Rth / 12) ** 2) * np.clip(ey + 0.2, 0, 1) * 0.22 * frost * (1 - white)
    ref = ref + glow[..., None] * np.float32([1.0, 0.92, 0.9])
    hl = np.exp(-(((ex + 0.36) / 0.40) ** 2 + ((ey + 0.48) / 0.26) ** 2)) * (0.10 + 0.06 * frost) * (1 - white)
    ref = ref + hl[..., None] - (np.clip(ey, 0, 1) ** 2 * 0.05 * frost * (1 - white))[..., None]
    # тело стекла на белом: френелевский край (чуть темнее, холодный) + тонкая дуга-блик сверху-слева
    fres = ((1 - z) ** 3)[..., None] * (1 - white)
    ref = ref * (1 - 0.16 * fres) + np.float32([0.55, 0.45, 0.40]) * 0.16 * fres * 0.25
    arc = np.exp(-((d - 0.88) * Rth / 4.0) ** 2) * np.clip(-(ex + 1.3 * ey) / 1.2, 0, 1) ** 2 * 0.55 * (1 - frost) * (1 - white)
    ref = ref + arc[..., None]
    ref = ref * (1 - white) + np.float32([0.985, 0.985, 0.985]) * white
    rim = np.exp(-((d - 1) * Rth / 2.2) ** 2) * (0.10 + 0.12 * frost) * (1 - white)
    ang = np.clip(0.6 - 0.5 * (ex + ey) / 1.4142, 0.2, 1)
    m = np.clip((1 - d) * Rth / (1.5 + 70 * white), 0, 1)[..., None]
    sh = (np.exp(-(np.clip(d - 1, 0, None) * Rth / 18) ** 2) * (d > 1) * 0.03 * frost * (1 - white))[..., None]
    roi = img[y0:y1, x0:x1]
    res = roi * (1 - sh) * (1 - m) + np.clip(ref + (rim * ang)[..., None], 0, 1) * m
    out_ = img.copy()
    out_[y0:y1, x0:x1] = roi * (1 - a) + res * a
    return out_


def leak(img, k):
    """Световая засветка (оранжевый + розовый, диагональные лучи), режим screen; k 0..1."""
    a = np.sin(np.pi * np.clip(k, 0, 1)) ** 1.2
    cx1, cy1 = W * (-0.2 + 1.2 * k), H * 0.25
    cx2, cy2 = W * (1.1 - 0.9 * k), H * 0.7
    b1 = np.exp(-(((xx - cx1) / (0.55 * W)) ** 2 + ((yy - cy1) / (0.45 * H)) ** 2))
    b2 = np.exp(-(((xx - cx2) / (0.5 * W)) ** 2 + ((yy - cy2) / (0.4 * H)) ** 2))
    # мягкие лучи: несколько широких полос разной ширины, сильно размытые (как плёночная засветка, не «зебра»)
    band = (xx * 0.8 + yy) / 1.0 - (W + H) * (1.2 * k - 0.1)
    streak = sum(w_ * np.exp(-((band - o) / s_) ** 2) for o, s_, w_ in [(0, 260, 0.7), (-420, 120, 0.45), (380, 180, 0.5), (-800, 300, 0.35)])
    col = (b1[..., None] * np.array([0.10, 0.45, 1.0]) + b2[..., None] * np.array([0.55, 0.25, 1.0]) + streak[..., None] * np.array([0.35, 0.65, 1.0]) * 0.7)  # BGR
    col = cv2.GaussianBlur(np.clip(col * a * 1.05, 0, 1).astype(np.float32), (0, 0), 18)
    return 1 - (1 - img) * (1 - col)


face_last = [W / 2, H * 0.42, W * 0.4, H * 0.27]
enc = None if AUDIO_ONLY else subprocess.Popen(
    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(work / "v.mp4")], stdin=subprocess.PIPE)
rng = np.random.default_rng(3)
GRAIN = [cv2.resize(rng.normal(0, 0.006, (H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)[..., None] for _ in range(6)]
if enc:
    cap.set(cv2.CAP_PROP_POS_FRAMES, F0)
    for i in range(F0, F1):
        ok, fr = cap.read()
        if not ok:
            break
        x = fr.astype(np.float32) * (1 / 255)
        f = FX.get(i, {"blur": 0, "dim": 0, "zoom": 1, "lens": None, "ball": None, "leak": -1, "face": face_last})
        face_last = f["face"]
        fx_, fy_ = f["face"][0], f["face"][1]
        b = f["blur"]
        s = f["zoom"] * (1 + 0.05 * b)
        need_m = f.get("back") or f.get("sil", 0) > 0 or f.get("bg")
        m = mask_at(i, s, fx_, fy_) if need_m else None
        if f.get("bg") and f["bg"]["a"] > 0:          # замена фона: человек остаётся, всё вокруг — из другого кадра
            raw_m = mask_at(i, 1.0, fx_, fy_)
            if raw_m is not None:
                bgf = bg_frame(f["bg"]["src"], f["bg"]["t"]) * (1 - f["bg"].get("dim", 0))
                a_ = F(f["bg"]["a"])
                x = x * (1 - a_ * (1 - raw_m)) + bgf * a_ * (1 - raw_m)
        x = zoom(x, s, fx_, fy_)
        if b > 0.01:                               # сильное размытие считаем на 1/4 размера — тот же вид, в разы быстрее
            sg = 0.5 + 26 * b
            if sg > 6:
                sm = cv2.resize(x, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
                x = cv2.resize(cv2.GaussianBlur(sm, (0, 0), sg / 4), (W, H), interpolation=cv2.INTER_CUBIC)
            else:
                x = cv2.GaussianBlur(x, (0, 0), sg)
        x = x * (1 - f["dim"])
        if GRADE:
            x = grade_cinema(x) if GMODE == "cinema" else grade_film(x, FILM_AMT) if GMODE == "film" else grade(x)
        if m is not None and f.get("sil", 0) > 0:      # силуэт: человек залит цветом
            c = np.float32([int(f.get("silColor", "#000000")[k:k + 2], 16) / 255 for k in (5, 3, 1)])
            x = x * (1 - m * F(f["sil"])) + c * m * F(f["sil"])
        bkf = ov_dir / "back" / f"{i:05d}.png"
        if m is not None and bkf.exists():             # текст «за спиной»: кладём слой, потом возвращаем человека поверх
            person = x
            bk = cv2.imread(str(bkf), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
            if bk.shape[2] == 4:
                ab = bk[..., 3:4]
                x = x * (1 - ab) + bk[..., :3] * ab
                x = x * (1 - m) + person * m
        elif bkf.exists():                              # маски нет — слой «за спиной» ложится как обычный
            bk = cv2.imread(str(bkf), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
            if bk.shape[2] == 4:
                x = x * (1 - bk[..., 3:4]) + bk[..., :3] * bk[..., 3:4]
        ovf = ov_dir / f"{i:05d}.png"
        if ovf.exists():
            ov = load_ov(ovf)
            if ov.shape[2] == 3:                       # полностью непрозрачный кадр (вспышка) сохраняется без альфы
                x = ov
            else:
                al = ov[..., 3:4]
                x = x * (1 - al) + ov[..., :3] * al
        if f["lens"]:
            x = lens(x, *f["lens"])
        if f.get("ball"):
            x = ball(x, *f["ball"])
        if f["leak"] >= 0:
            x = leak(x, f["leak"])
        if GRAIN_AMT > 0:                              # зерно — только по просьбе (правка: «лишний шум убираем»)
            x = x + GRAIN[i % len(GRAIN)] * (GRAIN_AMT / 0.006)
        enc.stdin.write((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()

# --- звук: живой голос + эффекты по events.json ---
SR = 48000
t0, t1 = F0 / FPS, F1 / FPS
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", src, "-vn", "-ac", "2", "-ar", str(SR), str(work / "a.wav")], check=True)
voice, _ = sf.read(str(work / "a.wav"))
total = int((t1 - t0) * SR)
mixb = np.zeros((total, 2))
mixb[: min(total, len(voice))] = voice[:total]
# громкость голоса: RMS звучащих кадров; если голоса нет — как в референсах (≈ −24 dBFS)
_m = voice.mean(1) if voice.ndim > 1 else voice
_fr = np.sqrt(np.convolve(_m ** 2, np.ones(2048) / 2048, "valid")[::512] + 1e-12) if len(_m) > 4096 else np.array([1e-6])
_v = _fr[_fr > np.percentile(_fr, 40)]
VOICE_DB = float(20 * np.log10(np.percentile(_v, 60) + 1e-9)) if len(_v) else -90.0
if VOICE_DB < -45:
    VOICE_DB = -24.0
VREL = 10 ** ((VOICE_DB + 18) / 20)          # множитель для событий v:1
print(f"голос {VOICE_DB:.1f} dBFS")
cache = {}
for e in EV:
    if not (t0 - 1 <= e["t"] < t1):
        continue
    if e["s"] not in cache:
        cache[e["s"]], _ = sf.read(str(sfx_path(e["s"])))
    sig = cache[e["s"]] * e["g"] * SFX_GAIN * (VREL if e.get("v") else 1.0)
    st = int((e["t"] - t0) * SR)
    if st < 0:
        sig, st = sig[-st:], 0
    sig = sig[: total - st]
    mixb[st:st + len(sig)] += sig[:, None]
sf.write(str(work / "mix.wav"), mixb / max(1.0, np.abs(mixb).max() / 0.97), SR)
vf = f"setpts=PTS/{SPEED},fps={FPS}" if SPEED != 1 else "null"
af = ",".join(([f"atempo={SPEED}"] if SPEED != 1 else []) + (["loudnorm=I=-14:TP=-1.5:LRA=9"] if os.environ.get("LOUDNORM", "1") == "1" else ["anull"]))
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(work / "v.mp4"), "-i", str(work / "mix.wav"),
                "-filter:v", vf, "-af", af, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",   # явно SDR: телефон не примет за HDR
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-map_metadata", "-1", "-movflags", "+faststart", out], check=True)
print("готово:", out)
