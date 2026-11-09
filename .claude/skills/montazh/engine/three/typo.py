"""Кинотипографика для t2v: субтитры по словам (Cormorant), крупные акценты (Forum, разрядка), титры, финал с аятом, ник."""
import difflib, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONTS = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/local/fonts/"
W, H = 1080, 1920
RED = (229, 72, 61); WHITE = (245, 241, 234)
CORM, CORMI, FORUM, AMIRI = "CormorantGaramond.ttf", "CormorantGaramond-Italic.ttf", "Forum-Regular.ttf", "Amiri-Bold.ttf"
_fc, _sp = {}, {}

def F(name, size, wght=None):
    k = (name, size, wght)
    if k not in _fc:
        fo = ImageFont.truetype(FONTS + name, size)
        if wght:
            try: fo.set_variation_by_axes([wght])
            except Exception: pass
        _fc[k] = fo
    return _fc[k]

def sprite(text, fo, color, tracking=0.0, rtl=False):
    if rtl:
        bb = fo.getbbox(text, direction="rtl", language="ar"); w, h = bb[2] - bb[0] + 20, bb[3] - bb[1] + 30
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10 - bb[0], 15 - bb[1]), text, font=fo, fill=color + (255,), direction="rtl", language="ar"); return im
    asc, desc = fo.getmetrics()
    if tracking:
        ws = [fo.getlength(c) for c in text]; sp = fo.size * tracking; w = int(sum(ws) + sp * (len(text) - 1) + 20)
        im = Image.new("RGBA", (w, asc + desc + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 10
        for c, cw in zip(text, ws): d.text((x, 10), c, font=fo, fill=color + (255,)); x += cw + sp
        return im
    im = Image.new("RGBA", (int(fo.getlength(text) + 20), asc + desc + 20), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), text, font=fo, fill=color + (255,)); return im

def cached(key, fn):
    if key not in _sp: _sp[key] = fn()
    return _sp[key]

def shadow(sp, r=14):
    pad = 40; im = Image.new("RGBA", (sp.width + 2 * pad, sp.height + 2 * pad), (0, 0, 0, 0))
    blk = Image.new("RGBA", sp.size, (0, 0, 0, 255)); blk.putalpha(sp.getchannel("A")); im.alpha_composite(blk, (pad, pad)); return im.filter(ImageFilter.GaussianBlur(r))

def put(layer, im, cx, cy, alpha, blur=0.0, dy=0.0, scale=1.0):
    if alpha <= 0.01: return
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if blur > 0.3: im = im.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 0.999: a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    layer.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2 + dy)))

def reveal(t, t0, d=0.35):
    k = min(1, max(0, (t - t0) / d)); return k * k * (3 - 2 * k)

def fit(text, name, size, tracking, maxw=980):
    """Кегль, при котором строка (с учётом «наплыва» ×1.08) влезает в кадр."""
    while size > 30 and (sprite(text, F(name, size), WHITE, tracking).width - 20) * 1.08 > maxw: size -= 4
    return size

def grade(x):
    """Кино-грейд поверх 3D: мягкий S-контраст, тёплые света, свечение ярких мест."""
    x = np.clip(0.5 + (x - 0.5) * 1.08, 0, 1); x = x * x * (3 - 2 * x) * 0.35 + x * 0.65
    bl = cv2.GaussianBlur(np.clip(x - 0.7, 0, 1), (0, 0), 22); return np.clip(x + bl * 0.7, 0, 1)

def vignette(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w * .72)) ** 2 + ((yy - h * .46) / (h * .6)) ** 2)
    return np.clip(1 - (d - .5) * .9, .4, 1)[..., None]

def _norm(w): return "".join(c for c in w.lower().replace("ё", "е") if c.isalnum())

def build_captions(sentences, S, words, red):
    """Группы субтитров: строки ≤ 24 знаков, ≤ 2 строки; время каждого слова — из распознавания (выравнивание difflib)."""
    groups = []; redn = {_norm(r) for r in red}
    for k, s in enumerate(sentences):
        disp = s["text"].split(); a, b = S[k][0] - 0.15, S[k][1] + 0.15
        asr = [w for w in words if a <= w["t0"] <= b]
        tt = [None] * len(disp)
        sm = difflib.SequenceMatcher(None, [_norm(w) for w in disp], [_norm(w["w"]) for w in asr], autojunk=False)
        for blk in sm.get_matching_blocks():
            for j in range(blk.size): tt[blk.a + j] = asr[blk.b + j]["t0"]
        # пропуски — по соседям (линейно), края — по началу/концу фразы
        known = [(i, v) for i, v in enumerate(tt) if v is not None] or [(0, S[k][0]), (len(disp) - 1, S[k][1] - .3)]
        if known[0][0] != 0: known.insert(0, (0, S[k][0]))
        if known[-1][0] != len(disp) - 1: known.append((len(disp) - 1, max(known[-1][1] + .2, S[k][1] - .35)))
        xs, ys = zip(*known); tt = list(np.interp(range(len(disp)), xs, ys))
        lines, cur = [], []
        for i, w in enumerate(disp):
            if cur and len(" ".join(disp[j] for j in cur + [i])) > 24: lines.append(cur); cur = []
            cur.append(i)
        lines.append(cur)
        for g in range(0, len(lines), 2):
            gl = lines[g:g + 2]; first = gl[0][0]; nxt = lines[g + 2][0] if g + 2 < len(lines) else None
            end = (tt[nxt] - 0.05) if nxt is not None else S[k][1] + 0.35
            groups.append({"t0": tt[first], "end": end, "lines": [[(disp[i], tt[i], _norm(disp[i]) in redn) for i in ln] for ln in gl]})
    return groups

CAP_Y, CAP_LH = 1610, 80

def draw(layer, t, P, S, caps, acc, dur):
    fo = F(CORM, 60, 600)
    for g in caps:                                                     # субтитры по словам
        if not (g["t0"] - .05 <= t <= g["end"] + .3): continue
        out = 1 - reveal(t, g["end"], .3)
        for li, ln in enumerate(g["lines"]):
            sps = [cached(("c", w, r), lambda w=w, r=r: sprite(w, fo, RED if r else WHITE)) for w, _, r in ln]
            sh = [cached(("cs", w), lambda sp=sp: shadow(sp, 8)) for sp, (w, _, _) in zip(sps, ln)]
            total = sum(s.width - 20 for s in sps) + 16 * (len(sps) - 1); x = W / 2 - total / 2
            for (w, tw, r), sp, sd in zip(ln, sps, sh):
                k = reveal(t, tw - .04, .3); cx = x + (sp.width - 20) / 2
                put(layer, sd, cx, CAP_Y + li * CAP_LH + 4, k * out * .7)
                put(layer, sp, cx, CAP_Y + li * CAP_LH, k * out, blur=(1 - k) * 8, dy=(1 - k) * 14)
                x += sp.width - 20 + 16
    for i, a in enumerate(acc):                                        # крупные акценты сверху
        if not a.get("big"): continue
        nxt = min([b["t"] for b in acc[i + 1:] if b.get("big")] + [a["t"] + a.get("hold", 1.6)])
        t1 = min(a["t"] + a.get("hold", 1.6), nxt - .05)
        if not (a["t"] - .05 <= t <= t1 + .4): continue
        k = reveal(t, a["t"], .45); out = 1 - reveal(t, t1, .4); col = RED if a.get("red", True) else WHITE
        size = fit(a["big"], FORUM, a.get("size", 120), .18)
        sp = cached(("b", a["big"], size, col), lambda: sprite(a["big"], F(FORUM, size), col, .18)); sd = cached(("bs", a["big"], size), lambda: shadow(sp))
        y = a.get("y", 330)
        put(layer, sd, W / 2, y + 6, k * out * .8, scale=1.08 - .08 * k); put(layer, sp, W / 2, y, k * out, blur=(1 - k) * 14 + (1 - out) * 10, scale=1.08 - .08 * k)
        if a.get("sub"):
            s2 = cached(("bsub", a["sub"]), lambda: sprite(a["sub"], F(FORUM, 34), WHITE, .32)); put(layer, s2, W / 2, y + size * .62 + 20, reveal(t, a["t"] + .15, .4) * out)
    T = P["title"]; t_end = S[0][0] - .1                                 # титр вступления
    if t < t_end + .6:
        out = 1 - reveal(t, t_end, .5)
        put(layer, cached("top", lambda: sprite(T["top"], F(FORUM, 32), RED, .36)), W / 2, 790, reveal(t, .3, .7) * out)
        name = T["name"].split(" "); half = max(1, len(name) // 2); rows = [" ".join(name[:half]), " ".join(name[half:])] if len(name) > 1 else name
        for r, txt in enumerate(rows):
            size = fit(txt, FORUM, 118, .2); sp = cached(("tn", txt), lambda txt=txt: sprite(txt, F(FORUM, size), WHITE, .2))
            k = reveal(t, .9 + r * .45, .6); put(layer, cached(("tns", txt), lambda sp=sp: shadow(sp)), W / 2, 905 + r * 130, k * out * .8)
            put(layer, sp, W / 2, 900 + r * 130, k * out, blur=(1 - k) * 12, scale=1.06 - .06 * k)
        if T.get("sub"): put(layer, cached("tsub", lambda: sprite(T["sub"], F(CORMI, 42, 500), WHITE)), W / 2, 900 + len(rows) * 130 + 10, reveal(t, 1.9, .7) * out)
    E = P.get("ending"); t0 = S[-1][1] + .5                              # финал
    if E and t > t0 - .1:
        fade = 1 - reveal(t, dur - .9, .8)
        for k, txt in enumerate(E.get("arabic", [])):
            tk = t0 + k * 1.1; sp = cached(("ar", k), lambda txt=txt: sprite(txt, F(AMIRI, 76), WHITE, rtl=True))
            put(layer, cached(("ars", k), lambda sp=sp: shadow(sp)), W / 2, 300 + k * 118 + 5, reveal(t, tk, .9) * fade * .7)
            put(layer, sp, W / 2, 300 + k * 118, reveal(t, tk, .9) * fade, blur=(1 - reveal(t, tk, .9)) * 10)
        for k, txt in enumerate(E.get("lines", [])):
            tk = t0 + .6 + k * 1.1; sp = cached(("tr", k), lambda txt=txt: sprite(txt, F(CORMI, 54, 500), WHITE))
            put(layer, sp, W / 2, CAP_Y - 20 + k * 70, reveal(t, tk, .9) * fade, blur=(1 - reveal(t, tk, .9)) * 8)
        if E.get("ref"): put(layer, cached("ref", lambda: sprite(E["ref"], F(FORUM, 30), RED, .32)), W / 2, CAP_Y - 20 + len(E.get("lines", [])) * 70 + 50, reveal(t, t0 + 1.4, .9) * fade)
    if P.get("nick"):
        put(layer, cached("nick", lambda: sprite(P["nick"], F(FORUM, 40), WHITE, .12)), W / 2, 1852, .72 * reveal(t, .3, .8) * (1 - reveal(t, dur - .5, .45)))
