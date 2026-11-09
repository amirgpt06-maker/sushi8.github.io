"""Кинематографичный монтаж «Мусаб ибн Умейр»: тёмный кадр, виртуальная камера по анимации (разные планы и углы,
наезды, наклоны, толчки, вспышки, смазанные переходы), киношная типографика по словам диктора, ник внизу.
Запуск: python kino.py [from to]  -> video.mp4 (без звука; звук собирает mix.py)."""
import json, math, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = "/tmp/claude-0/-home-user-sushi8-github-io/e45a17fa-f666-558d-8135-60ef79d3ed2c/scratchpad/musab/"
FONTS = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/local/fonts/"
W, H, FPS = 1080, 1920, 30
DUR = 49.95
WS = json.load(open(HERE + "words.json"))["words"]; T = [w["t0"] for w in WS]
AN = json.load(open(HERE + "kino/analysis.json")); CENT = np.array(AN["cent"])
RED = (229, 72, 61)

# ---------------- кадры исходника (полоса анимации 720x426) ----------------
cap = cv2.VideoCapture(HERE + "src.mp4"); NSRC = int(cap.get(7)); _cache = {}
def band(i):
    i = max(0, min(NSRC - 1, i))
    if i not in _cache:
        if len(_cache) > 40: _cache.clear()
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read(); _cache[i] = f[425:851].copy()
    return _cache[i]
# сглаженный «где герой» (центр тёмных линий/силуэта)
cx_s = np.copy(CENT[:, 0]); cy_s = np.copy(CENT[:, 1])
for arr in (cx_s, cy_s):
    for k in range(1, len(arr)): arr[k] = arr[k - 1] * 0.88 + arr[k] * 0.12

# ---------------- план съёмки: виртуальные кадры ----------------
FMT = {"W": (1080, 608), "M": (1080, 1080), "T": (1080, 1440)}
CY = {"W": 840, "M": 840, "T": 810}
S = []   # (t0, t1, fmt, z0, z1, r0, r1, follow, dx, dy, whip_in)
def shot(t0, t1, f, z0=1.0, z1=1.1, r0=0.0, r1=0.0, fol=0.7, dx=0.0, dy=0.0, whip=False): S.append((t0, t1, f, z0, z1, r0, r1, fol, dx, dy, whip))
shot(1.13, 2.27, "T", 1.05, 1.18, 0, 1.5, .85)
shot(2.27, 3.26, "W", 1.00, 1.07, 0, 0, .35)                      # общий план — пустыня
shot(3.26, 5.10, "M", 1.30, 1.50, -4.5, -2.5, .8, 0, -36, True)    # снизу, «голландский» угол
shot(5.10, 7.14, "T", 1.75, 1.95, 3, 5, .95, 20, 0, True)           # крупно, с рук
shot(7.14, 9.37, "M", 1.12, 1.65, 0, 0, .9, 0, 0, True)             # медленный наезд -> «80 ударов»
shot(9.37, 10.67, "T", 1.10, 1.28, 4, 2, .8)
shot(10.67, 10.97, "W", 1.15, 1.25, 0, 0, .5)
shot(10.97, 11.40, "M", 1.00, 1.10, 0, 0, .5)
shot(11.40, 12.37, "M", 1.00, 1.18, 0, 0, .6)
shot(12.37, 12.77, "T", 1.10, 1.20, 2, 2, .8)
shot(12.77, 13.97, "T", 1.20, 1.48, -3, -1, .9)
shot(13.97, 14.27, "M", 1.10, 1.15, 0, 0, .6)
shot(14.27, 16.50, "M", 1.00, 1.20, 0, 0, .6)
shot(16.50, 17.40, "W", 1.05, 1.22, 0, -3, .7, 0, 40)               # падает — камера уходит вниз
shot(17.40, 18.33, "T", 1.10, 1.20, 0, 0, .7)
shot(18.33, 20.60, "T", 1.15, 1.42, 2, 0, .8)
red_cuts = [20.60, 20.93, 21.73, 22.23, 23.10, 23.60, 24.47, 24.93, 25.60, 26.07, 28.40]
for k in range(len(red_cuts) - 1):                                  # красные силуэты — монтаж в ритм копий
    f = ["M", "T", "M", "W", "T"][k % 5]
    shot(red_cuts[k], red_cuts[k + 1], f, 1.0 + 0.05 * (k % 3), 1.12 + 0.05 * (k % 3), (-3, 3, 0, -2, 2)[k % 5], (-1, 1, 0, -3, 3)[k % 5], .7)
shot(28.40, 28.80, "M", 1.0, 1.05)
shot(28.80, 29.50, "W", 1.10, 1.25, 0, 0, .7)
shot(29.50, 30.47, "M", 1.30, 1.50, -3, -1, .9, 0, 0, True)
shot(30.47, 31.90, "T", 1.00, 1.12, 0, 2, .7)
shot(31.90, 32.83, "W", 1.10, 1.22, 0, 0, .6, -30, 30)
shot(32.83, 34.73, "M", 1.20, 1.42, 2, -2, .8, 30, 0, True)
shot(34.73, 35.00, "M", 1.00, 1.08)
shot(35.00, 49.95, "M", 1.00, 1.30, 0, 0, .55)                      # финал — аят: долгий медленный наезд

IMP = [(8.20, 1.0, "w"), (11.56, 1.0, "w"), (15.72, 1.0, "w"), (16.88, .6, ""), (18.68, .7, ""), (22.40, .5, ""),
       (20.60, .35, ""), (20.93, .3, ""), (21.73, .35, ""), (23.10, .3, ""), (24.47, .35, ""), (25.60, .3, ""),
       (29.47, .6, ""), (34.07, .6, "w")]

def shot_at(t):
    for s in S:
        if s[0] <= t < s[1]: return s
    return S[-1] if t >= S[-1][0] else None

def ease(u): u = min(1, max(0, u)); return u * u * (3 - 2 * u)

def camera(t, i):
    s = shot_at(t)
    t0, t1, f, z0, z1, r0, r1, fol, dx, dy, _ = s
    u = ease((t - t0) / max(1e-3, t1 - t0))
    cw, ch = FMT[f]; a = cw / ch
    bh = min(426, 720 / a); bw = bh * a
    z = z0 + (z1 - z0) * u
    pk = sum(st * 0.12 * math.exp(-(t - ti) * 9) for ti, st, _ in IMP if 0 <= t - ti < 0.6)   # толчок на ударе
    z *= 1 + pk
    w, h = bw / z, bh / z
    sx = 360 + fol * (cx_s[i] * 720 - 360) + dx * (u - .5) * 2
    sy = 213 + fol * 0.6 * (cy_s[i] * 426 - 213) + dy * (u - .5) * 2
    shk = sum(st * 9 * math.exp(-(t - ti) * 7) for ti, st, _ in IMP if 0 <= t - ti < 0.8)
    sx += shk * math.sin(t * 91); sy += shk * math.cos(t * 77)
    sx += 1.6 * math.sin(t * 1.3) + 0.8 * math.sin(t * 3.1); sy += 1.2 * math.cos(t * 1.7)      # «с рук», едва заметно
    sx = min(max(sx, w / 2), 720 - w / 2); sy = min(max(sy, h / 2), 426 - h / 2)
    r = r0 + (r1 - r0) * u
    return f, sx, sy, cw / w, r

def grade(img):
    f = img.astype(np.float32) / 255
    lum = f.mean(2, keepdims=True)
    f = f * 0.9 + 0.1 * (np.float32([0.55, 0.42, 0.25]) * (1 - lum) + np.float32([0.40, 0.58, 0.78]) * lum)   # бирюзовые тени, тёплые света
    f = np.clip(0.5 + (f - 0.5) * 1.12, 0, 1); f = f * f * (3 - 2 * f) * 0.4 + f * 0.6
    bl = cv2.GaussianBlur(np.clip(f - 0.75, 0, 1), (0, 0), 18)                                              # мягкое свечение светов
    return np.clip(f + bl * 0.6, 0, 1)

VIG = None
def vignette():
    global VIG
    if VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H * .45) / (H * .62)) ** 2)
        VIG = np.clip(1 - (d - .45) * .9, .35, 1)[..., None]
    return VIG

def frame_video(t):
    i = min(int(round(t * FPS)), len(CENT) - 1)
    out = np.zeros((H, W, 3), np.float32)
    if t < 1.13:                                                 # титр на чёрном
        return out
    f, sx, sy, sc, r = camera(t, i)
    b = band(i)
    amb = cv2.resize(cv2.GaussianBlur(cv2.resize(b, (48, 28)), (0, 0), 2.5), (3300, 1920), interpolation=cv2.INTER_CUBIC)[:, 1110:2190]
    out = amb.astype(np.float32) / 255 * 0.26
    cw, ch = FMT[f]
    M = cv2.getRotationMatrix2D((sx, sy), r, sc); M[0, 2] += cw / 2 - sx; M[1, 2] += ch / 2 - sy
    can = cv2.warpAffine(b, M, (cw, ch), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    can = cv2.addWeighted(can, 1.35, cv2.GaussianBlur(can, (0, 0), 1.6), -0.35, 0)                          # резкость после увеличения
    can = grade(can)
    y0 = int(CY[f] - ch / 2)
    # смазанный переход (whip) на стыке кадров
    for s in S:
        if s[10] and abs(t - s[0]) < 0.07:
            k = 70; ker = np.zeros((1, k), np.float32); ker[0] = 1 / k
            can = cv2.filter2D(can, -1, ker); can = np.roll(can, int((s[0] - t) * 1400), axis=1)
    out[y0:y0 + ch] = can
    fade = min(1, (t - 1.13) / 0.3)
    out *= fade
    for ti, st, kind in IMP:                                     # вспышки
        if kind == "w" and 0 <= t - ti < 0.16: out = out + (1 - out) * (1 - (t - ti) / 0.16) * 0.85
    if t > DUR - 0.6: out *= max(0, (DUR - t) / 0.6)
    return out * vignette()

# ---------------- типографика ----------------
def font(name, size): return ImageFont.truetype(FONTS + name, size)
CORM = "CormorantGaramond.ttf"; FORUM = "Forum-Regular.ttf"; AMIRI = "Amiri-Bold.ttf"
_fc = {}
def F(name, size, wght=None):
    k = (name, size, wght)
    if k not in _fc:
        fo = font(name, size)
        if wght:
            try: fo.set_variation_by_axes([wght])
            except Exception: pass
        _fc[k] = fo
    return _fc[k]

def sprite(text, fo, color, tracking=0.0, direction=None):
    """Слово/строка в RGBA (с разрядкой). Арабский — целиком (raqm)."""
    if direction == "rtl":
        bb = fo.getbbox(text, direction="rtl", language="ar"); w, h = bb[2] - bb[0] + 20, bb[3] - bb[1] + 30
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10 - bb[0], 15 - bb[1]), text, font=fo, fill=color + (255,), direction="rtl", language="ar")
        return im
    if tracking:
        ws = [fo.getlength(c) for c in text]; sp = fo.size * tracking
        w = int(sum(ws) + sp * (len(text) - 1) + 20); asc, desc = fo.getmetrics()
        im = Image.new("RGBA", (w, asc + desc + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 10
        for c, cw in zip(text, ws): d.text((x, 10), c, font=fo, fill=color + (255,)); x += cw + sp
        return im
    asc, desc = fo.getmetrics(); w = int(fo.getlength(text) + 20)
    im = Image.new("RGBA", (w, asc + desc + 20), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), text, font=fo, fill=color + (255,))
    return im

_sp = {}
def S_(key, fn):
    if key not in _sp: _sp[key] = fn()
    return _sp[key]

def shadow(sp):
    """Мягкая тёмная подложка под крупный текст (читается на любом фоне)."""
    pad = 40; im = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    a = sp.getchannel("A"); blk = Image.new("RGBA", sp.size, (0, 0, 0, 255)); blk.putalpha(a)
    im.alpha_composite(blk, (pad, pad)); return im.filter(ImageFilter.GaussianBlur(14))

def put(layer, im, cx, cy, alpha, blur=0.0, dy=0.0, scale=1.0):
    if alpha <= 0.01: return
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if blur > 0.3: im = im.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 0.999:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    layer.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2 + dy)))

def reveal(t, t0, d=0.35):
    k = min(1, max(0, (t - t0) / d)); k = k * k * (3 - 2 * k); return k

CH = [  # субтитры: (строки [(слово, индекс)], конец)
    ([[("Он", 3), ("нёс", 4), ("знамя", 5), ("мусульман.", 6)]], 3.20),
    ([[("Многобожники", 7), ("начали", 8)], [("атаковать", 9), ("его,", 10)]], 5.05),
    ([[("забрасывая", 11), ("его", 12)], [("стрелами", 13), ("и", 14), ("копьями.", 15)]], 7.08),
    ([[("Ему", 16), ("нанесли", 17), ("более", 18)], [("восьмидесяти", 19), ("ударов.", 20)]], 9.40),
    ([[("В", 21), ("бою", 22), ("Мусабу", 23), ("ибн", 24), ("Умейру", 25)]], 11.05),
    ([[("отрубили", 26), ("правую", 27), ("руку,", 28)]], 12.18),
    ([[("и", 29), ("тогда", 30), ("он", 31), ("взял", 32), ("знамя", 33)], [("в", 34), ("левую", 35), ("руку.", 36)]], 14.32),
    ([[("Когда", 37), ("же", 38), ("ему", 39), ("отрубили", 40)], [("и", 41), ("левую", 42), ("руку,", 43)]], 16.20),
    ([[("он", 44), ("упал", 45), ("на", 46), ("колени", 47)]], 17.26),
    ([[("и", 48), ("придерживал", 49), ("его", 50)], [("своей", 51), ("грудью,", 52)]], 19.16),
    ([[("а", 53), ("в", 54), ("него", 55), ("всё", 56), ("летели", 57)], [("и", 58), ("летели", 59), ("копья.", 60)]], 21.60),
    ([[("Таким", 61), ("был", 62), ("Мусаб", 63), ("ибн", 64), ("Умейр.", 65)]], 23.70),
    ([[("Это", 66), ("тот", 67), ("самый", 68), ("юноша", 69)], [("из", 70), ("Мекки,", 71)]], 25.98),
    ([[("который", 72), ("был", 73), ("знатный,", 74)], [("богатый", 75), ("и", 76), ("изнеженный,", 77)]], 28.58),
    ([[("а", 78), ("сейчас", 79), ("он", 80)], [("жертвовал", 81), ("собой", 82)]], 30.25),
    ([[("ради", 83), ("Посланника", 84), ("Аллаха", 85)]], 31.58),
    ([[("и", 86), ("ради", 87), ("этой", 88), ("религии,", 89)]], 32.82),
    ([[("а", 90), ("многобожники", 91)], [("разрывали", 92), ("его", 93), ("тело.", 94)]], 35.60),
]
KEY = {19, 20, 27, 35, 42, 52, 60, 63, 64, 65, 81, 82, 85}          # ключевые слова — красным
CAP_Y = 1650; CAP_LH = 82

def captions(layer, t):
    fo = F(CORM, 62, 600)
    for lines, end in CH:
        t0 = T[lines[0][0][1]]
        if not (t0 - 0.05 <= t <= end + 0.3): continue
        out = 1 - reveal(t, end, 0.3)
        for li, ln in enumerate(lines):
            sps = [S_(("cap", w, i), lambda w=w, i=i: sprite(w, fo, RED if i in KEY else (245, 241, 234))) for w, i in ln]
            gap = 16; total = sum(s.width - 20 for s in sps) + gap * (len(sps) - 1); x = W / 2 - total / 2
            for (w, i), sp in zip(ln, sps):
                k = reveal(t, T[i] - 0.04, 0.3)
                put(layer, sp, x + (sp.width - 20) / 2, CAP_Y + li * CAP_LH, k * out, blur=(1 - k) * 8, dy=(1 - k) * 14)
                x += sp.width - 20 + gap

def big(layer, t, text, t0, t1, y, size, color, tracking=0.18, fontname=FORUM, sub=None):
    if not (t0 - 0.05 <= t <= t1 + 0.4): return
    k = reveal(t, t0, 0.45); out = 1 - reveal(t, t1, 0.4)
    sp = S_(("big", text, size, color), lambda: sprite(text, F(fontname, size), color, tracking))
    sh = S_(("bigsh", text, size), lambda: shadow(sp))
    put(layer, sh, W / 2, y + 6, k * out * 0.75, scale=1.08 - 0.08 * k)
    put(layer, sp, W / 2, y, k * out, blur=(1 - k) * 14 + (1 - out) * 10, scale=1.08 - 0.08 * k)
    if sub:
        s2 = S_(("sub", sub), lambda: sprite(sub, F(FORUM, 34), (235, 230, 222), 0.32))
        put(layer, s2, W / 2, y + size * 0.62 + 18, reveal(t, t0 + 0.15, 0.4) * out)

def overlays(layer, t):
    # вступление: на чёрном, имя — ровно когда его произносят
    if t < 2.0:
        out = 1 - reveal(t, 1.35, 0.5)
        put(layer, S_("ohud", lambda: sprite("БИТВА ПРИ УХУДЕ · 625", F(FORUM, 32), RED, 0.36)), W / 2, 760, reveal(t, 0.10, 0.6) * out)
        for wd, ti, x in [("МУСАБ", T[0], 0), ("ИБН УМЕЙР", T[1], 1)]:
            sp = S_(("t", wd), lambda wd=wd: sprite(wd, F(FORUM, 118), (245, 241, 234), 0.2))
            k = reveal(t, ti, 0.5); put(layer, sp, W / 2, 870 + x * 130, k * out, blur=(1 - k) * 12, scale=1.06 - 0.06 * k)
    big(layer, t, "80+", T[19], 9.30, 300, 300, RED, 0.02, sub="УДАРОВ")
    big(layer, t, "ПРАВУЮ РУКУ", T[27], 12.30, 300, 104, RED)
    big(layer, t, "ЗНАМЯ — В ЛЕВУЮ", T[35], 14.25, 300, 92, (245, 241, 234))
    big(layer, t, "И ЛЕВУЮ", T[42], 16.35, 300, 120, RED)
    big(layer, t, "ГРУДЬЮ", T[52], 20.40, 300, 150, RED, 0.24)
    big(layer, t, "МУСАБ ИБН УМЕЙР", T[63], 23.55, 300, 92, (245, 241, 234), 0.16)
    for k, (wd, i) in enumerate([("ЗНАТНЫЙ", 74), ("БОГАТЫЙ", 75), ("ИЗНЕЖЕННЫЙ", 77)]):
        big(layer, t, wd, T[i], 28.45, 220 + k * 112, 84, (245, 241, 234), 0.22)
    big(layer, t, "ЖЕРТВОВАЛ СОБОЙ", T[81], 31.55, 300, 92, RED)
    # финал: аят 3:146 (арабский — целиком, без звуковых эффектов поверх чтения)
    if t > 35.6:
        for k, (txt, ti) in enumerate([("فَمَا وَهَنُوا لِمَا أَصَابَهُمْ", 36.0), ("فِي سَبِيلِ اللَّهِ وَمَا ضَعُفُوا", 40.0), ("وَمَا اسْتَكَانُوا", 46.7)]):
            sp = S_(("ar", k), lambda txt=txt: sprite(txt, F(AMIRI, 74), (245, 241, 234), direction="rtl"))
            a = reveal(t, ti, 0.9) * (1 - reveal(t, DUR - 0.6, 0.55)); put(layer, sp, W / 2, 210 + k * 112, a, blur=(1 - reveal(t, ti, 0.9)) * 10)
        for k, (txt, ti) in enumerate([("Они не пали духом от того, что постигло их", 36.2), ("на пути Аллаха, не проявили слабости", 40.2), ("и не покорились.", 46.9)]):
            sp = S_(("tr", k), lambda txt=txt: sprite(txt, F("CormorantGaramond-Italic.ttf", 54, 500), (245, 241, 234)))
            a = reveal(t, ti, 0.9) * (1 - reveal(t, DUR - 0.6, 0.55)); put(layer, sp, W / 2, CAP_Y - 10 + k * 70, a, blur=(1 - reveal(t, ti, 0.9)) * 8)
        put(layer, S_("q", lambda: sprite("КОРАН · 3:146", F(FORUM, 30), RED, 0.32)), W / 2, CAP_Y + 215, reveal(t, 37.0, 0.9) * (1 - reveal(t, DUR - 0.6, 0.55)))
    # ник — всегда внизу
    put(layer, S_("nick", lambda: sprite("saidulaev.ai", F(FORUM, 40), (245, 241, 234), 0.12)), W / 2, 1852, 0.72 * reveal(t, 0.3, 0.8) * (1 - reveal(t, DUR - 0.4, 0.4)))

def render(t):
    v = frame_video(t)
    img = Image.fromarray((np.clip(v[..., ::-1], 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t > 1.0 and t < 35.9: captions(layer, t)
    overlays(layer, t)
    img.alpha_composite(layer)
    return np.asarray(img.convert("RGB"))[..., ::-1]

if __name__ == "__main__":
    a = float(sys.argv[1]) if len(sys.argv) > 2 else 0.0; b = float(sys.argv[2]) if len(sys.argv) > 2 else DUR
    out = sys.argv[3] if len(sys.argv) > 3 else HERE + "kino/video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    for n in range(n0, n1):
        enc.stdin.write(np.ascontiguousarray(render(n / FPS)).tobytes())
        if n % 150 == 0: print(f"{n / FPS:.1f} с", flush=True)
    enc.stdin.close(); enc.wait(); print("готово", out)
