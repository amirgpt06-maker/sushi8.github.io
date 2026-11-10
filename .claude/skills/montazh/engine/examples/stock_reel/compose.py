"""Такси-рилс: сборка видео. python compose.py out.mp4 [FROM TO] [--frames n1,n2,...  -> png для проверки]"""
import sys, os, math, subprocess, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); SRC = HERE + "/src/"; UI = HERE + "/work/ui/"; ENG = HERE + "/work/apple/ov/"
ENGINE = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/"
FONTS = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/local/fonts/"
W, H, FPS = 1080, 1920, 30
DUR = 42.30
N = int(round(DUR * FPS))

def zc(a, b, c0, c1):            # зум по времени клипа (для бесшовной петли)
    return lambda c: a + (b - a) * (c - c0) / (c1 - c0)
ZLOOP = zc(1.04, 1.10, 2.0, 3.81)
# спокойный монтаж: планы длиннее, мягкие медленные наезды, без тряски и смазанных переходов; между частями — мягкий наплыв
S = [
    dict(t0=0.00, t1=1.21, src='49878', c0=2.6, zf=ZLOOP),
    dict(t0=1.21, t1=2.37, src='17293', c0=3.7, sp=.7, cx=.25, z=(1.10, 1.13)),
    dict(t0=2.37, t1=4.34, src='27717', c0=1.2, sp=.8, cx=.36, z=(1.06, 1.10)),
    dict(t0=4.34, t1=5.73, src='42039', c0=14.3, sp=.6, cx=.56, z=(1.06, 1.10)),
    dict(t0=5.73, t1=6.55, src='28096', c0=9.0, sp=.8, cx=.5, z=(1.10, 1.13)),
    dict(t0=6.55, t1=8.22, ui='nav_chaos', bg=dict(src='42039', c0=3.0, cx=.5), g='ui', keep=True, tr='fade'),
    dict(t0=8.22, t1=9.36, freeze=True, z=(1.0, 1.06), g='ui'),
    dict(t0=9.36, t1=14.79, ui='apA', g='white', tr='fade'),
    dict(t0=14.79, t1=15.70, ui='ugly', g='ui', shake=2, tr='fade'),
    dict(t0=15.70, t1=16.95, ui='lean', g='ui', punch=16.01),
    dict(t0=16.95, t1=17.95, src='17291', c0=3.0, sp=.6, cx=.5, z=(1.05, 1.07)),
    dict(t0=17.95, t1=18.90, src='4331', c0=6.45, sp=.45, cx=.25, z=(1.16, 1.18), pan=((0, 260), (-15, 255))),
    dict(t0=18.90, t1=19.90, src='39774', c0=3.0, sp=.8, cx=.45, z=(1.06, 1.08)),
    dict(t0=19.90, t1=21.90, ui='nav_addr', bg=dict(src='42039', c0=7.5, cx=.5), g='ui', tr='fade'),
    dict(t0=21.90, t1=35.70, ui='apB', g='white', tr='fade'),
    dict(t0=35.70, t1=37.75, src='41161', c0=4.0, sp=.7, cx=.5, z=(1.04, 1.09), tr='fade'),
    dict(t0=37.75, t1=38.90, ui='nav_arrive', bg=dict(src='41161', c0=8.0, cx=.5), g='ui', tr='fade'),
    dict(t0=38.90, t1=41.70, ui='apC', g='white', tr='fade'),
    dict(t0=41.70, t1=DUR + .2, src='49878', c0=2.0, zf=ZLOOP, tr='fade'),
]
WHITE_SPANS = [(s['t0'], s['t1']) for s in S if s.get('g') == 'white']

# ---------------- субтитры (дословно по речи) ----------------
SUBS = [(0.22, 1.15, "Слушай"), (1.21, 2.20, "Вот ты садишься"), (2.21, 3.30, "в такси"), (3.36, 4.30, "Водитель:"),
        (4.34, 5.66, "«Куда едем?»"), (5.73, 6.55, "А ты:"), (6.61, 7.00, "«Ну-у…"), (7.01, 8.20, "*куда-нибудь»"),
        (8.25, 9.34, "Бред, да?)"), (9.39, 10.35, "А нейросетями"), (10.36, 11.19, "так пользуются"), (11.20, 12.40, "почти все"),
        (12.49, 13.62, "«Сделай сайт."), (13.65, 14.78, "Сделай монтаж»"), (14.81, 15.70, "А потом:"), (15.73, 16.95, "«ИИ _тупой»"),
        (17.03, 17.48, "Нет,"), (17.51, 18.88, "ИИ не _тупой"), (18.92, 19.72, "Ты ему просто"), (19.73, 20.40, "не сказал"),
        (20.41, 21.90, "свой _адрес"), (25.64, 27.08, "Сайт для общепита"), (29.45, 30.16, "Чтобы люди"),
        (30.18, 31.93, "заказывали онлайн"), (33.36, 34.06, "Вот сайт,"), (34.08, 35.68, "который мне нравится"),
        (35.78, 36.88, "Скажешь так —"), (36.91, 37.70, "и он доведёт"), (37.72, 38.88, "куда надо")]
YEL = (10, 214, 255)   # BGR #FFD60A
SUBY = 1335
FB = FONTS + "SF-Pro-Display-Bold.otf"
_spr = {}
def sub_sprite(text):
    if text in _spr: return _spr[text]
    words = text.split(" "); toks = []
    for w in words:
        if w.startswith("*"): toks.append((w[1:], "shake"))
        elif w.startswith("_"): toks.append((w[1:], "y"))
        else: toks.append((w, None))
    for size in range(96, 66, -4):
        fo = ImageFont.truetype(FB, size); sp = fo.getlength(" ")
        widths = [fo.getlength(w) for w, _ in toks]
        if sum(widths) + sp * (len(toks) - 1) <= 900: lines = [list(range(len(toks)))]; break
    else:
        fo = ImageFont.truetype(FB, 86); sp = fo.getlength(" "); widths = [fo.getlength(w) for w, _ in toks]
        lines, cur, cw = [], [], 0
        for i, wd in enumerate(widths):
            if cur and cw + sp + wd > 900: lines.append(cur); cur, cw = [], 0
            cur.append(i); cw += (sp if cur[:-1] else 0) + wd
        lines.append(cur)
    asc, desc = fo.getmetrics(); lh = int((asc + desc) * 1.08); pad = 80
    Wd = int(max(sum(widths[i] for i in ln) + sp * (len(ln) - 1) for ln in lines)) + 2 * pad; Ht = lh * len(lines) + 2 * pad
    parts = []                                                     # отдельные слои: обычные слова и «трясущиеся»
    base = Image.new("RGBA", (Wd, Ht), (0, 0, 0, 0)); shake = Image.new("RGBA", (Wd, Ht), (0, 0, 0, 0))
    for li, ln in enumerate(lines):
        x = (Wd - (sum(widths[i] for i in ln) + sp * (len(ln) - 1))) / 2; y = pad + li * lh
        for i in ln:
            w, k = toks[i]; col = (255, 214, 10, 255) if k else (255, 255, 255, 255)
            ImageDraw.Draw(shake if k == "shake" else base).text((x, y), w, font=fo, fill=col); x += widths[i] + sp
    def withshadow(im):
        a = np.array(im.getchannel("A")).astype(np.float32) / 255
        sh = np.roll(cv2.GaussianBlur(a, (0, 0), 10), 5, 0) * .85; halo = cv2.GaussianBlur(a, (0, 0), 34) * .45; sh = np.clip(sh + halo * (1 - sh), 0, 1)
        rgb = np.array(im.convert("RGB")).astype(np.float32)[..., ::-1] / 255
        A = a + sh * (1 - a); C = (rgb * a[..., None]) / np.maximum(A[..., None], 1e-4)
        return C.astype(np.float32), A.astype(np.float32)
    _spr[text] = (withshadow(base), withshadow(shake) if any(k == "shake" for _, k in toks) else None)
    return _spr[text]

def blit(x, C, A, cx, cy, alpha=1.0, scale=1.0, rot=0.0, dx=0, dy=0):
    h, w = A.shape
    if scale != 1.0 or rot:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, scale)
        C = cv2.warpAffine(C, M, (w, h), flags=cv2.INTER_LINEAR); A = cv2.warpAffine(A, M, (w, h), flags=cv2.INTER_LINEAR)
    x0 = int(cx - w / 2 + dx); y0 = int(cy - h / 2 + dy)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    a = A[ya - y0:yb - y0, xa - x0:xb - x0, None] * alpha
    x[ya:yb, xa:xb] = x[ya:yb, xa:xb] * (1 - a) + C[ya - y0:yb - y0, xa - x0:xb - x0] * a

def draw_subs(x, t, y=SUBY):
    for i, (a, b, txt) in enumerate(SUBS):
        if not (a <= t < b + .09): continue
        if any(s0 <= t < s1 for s0, s1 in WHITE_SPANS): continue
        nxt = SUBS[i + 1][0] if i + 1 < len(SUBS) else 99
        k = min(1, (t - a) / .16); e = 1 - (1 - k) ** 3; sc = .86 + .14 * (1 + 2.2 * (k - 1) ** 3 + 1.2 * (k - 1) ** 2 if k < 1 else 1)
        sc = .86 + .14 * min(1.06, e + .25 * math.sin(math.pi * k) * (k < 1))
        al = min(1, (t - a) / .07)
        if t >= b: al *= 0 if nxt - b <= .05 else max(0, 1 - (t - b) / .09)
        (C, A), sh = sub_sprite(txt)
        blit(x, C, A, W / 2, y, al, sc)
        if sh:
            C2, A2 = sh; dx = 7 * math.sin(t * 53) + 4 * math.sin(t * 91); dy = 5 * math.sin(t * 67); r = 2.6 * math.sin(t * 41)
            blit(x, C2, A2, W / 2, y, al, sc, r, dx, dy)

# ---------------- источники ----------------
def probe(f):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", f], capture_output=True, text=True).stdout.strip().split(",")
    a, b = o[2].split("/"); return int(o[0]), int(o[1]), float(a) / float(b)
class Clip:
    def __init__(self, src, c_from, c_to, cx=.5, blur=0):
        f = SRC + src + ".mp4"; w, h, self.fps = probe(f); self.c_from = max(0, c_from)
        if w > h: cw = int(h * 9 / 16) // 2 * 2; x0 = int(min(max(cx * w - cw / 2, 0), w - cw)); vf = f"crop={cw}:{h}:{x0}:0,"
        else: vf = ""
        vf += f"scale={W}:{H}:flags=lanczos" + (",unsharp=5:5:0.5" if not blur else "")
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{self.c_from:.3f}", "-t", f"{c_to - self.c_from + .2:.3f}", "-i", f, "-vf", vf,
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
        self.fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
        if blur:
            self.fr = np.stack([cv2.resize(cv2.GaussianBlur(cv2.resize(q, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), blur / 4), (W, H)) for q in self.fr])
    def at(self, c):
        p = (c - self.c_from) * self.fps; i = int(math.floor(p)); k = p - i
        i0 = min(max(i, 0), len(self.fr) - 1); i1 = min(i0 + 1, len(self.fr) - 1)
        a = self.fr[i0].astype(np.float32) / 255
        if k > .02 and i1 != i0: a = a * (1 - k) + self.fr[i1].astype(np.float32) / 255 * k
        return a

def load_ui(name, n):
    d = UI + name; fs = sorted(os.listdir(d)); f = d + "/" + fs[min(max(n, 0), len(fs) - 1)]
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
    if im.shape[2] == 4: return im[..., :3], im[..., 3:4]
    return im, None

def cam(img, z=1.0, rot=0.0, dx=0.0, dy=0.0):
    if abs(z - 1) < 1e-4 and abs(rot) < 1e-4 and abs(dx) < .01 and abs(dy) < .01: return img
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, z); M[0, 2] += dx; M[1, 2] += dy
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

# ---------------- белые Apple-сцены из движка ----------------
_src = open(ENGINE + "compose.py", encoding="utf-8").read()
exec(_src[_src.index("def load_ov("):_src.index("def leak(")])          # load_ov() и ball() — та же стеклянная капля, что в движке
FXE = {}
def eng_frame(n):
    global FXE
    if not FXE and os.path.exists(ENG + "fx.json"): FXE = {int(k): v for k, v in json.load(open(ENG + "fx.json")).items()}
    from pathlib import Path
    f = Path(ENG + f"{n:05d}.png")
    ov = load_ov(f)
    if ov.shape[2] == 4: x = np.float32(.984) * (1 - ov[..., 3:4]) + ov[..., :3] * ov[..., 3:4]
    else: x = ov
    b = FXE.get(n, {}).get("ball")
    if b: x = ball(np.ascontiguousarray(x, dtype=np.float32), *b)
    return np.clip(x, 0, 1).astype(np.float32)

# ---------------- грейд / зерно ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = np.clip(1 - (np.sqrt(((xx - W / 2) / (W * .78)) ** 2 + ((yy - H * .47) / (H * .62)) ** 2) - .45) * .85, .45, 1)[..., None]
rng = np.random.default_rng(5)
GRAIN = [cv2.resize(rng.standard_normal((H // 2, W // 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR) for _ in range(8)]
def grade(x, kind):
    if kind == 'white': return x
    l = (x[..., 0] * .11 + x[..., 1] * .59 + x[..., 2] * .30)[..., None]
    x = np.clip(.5 + (x - .5) * 1.07, 0, 1)
    sh, hi = (1 - l) ** 2, l ** 2
    x = x + np.concatenate([.032 * sh - .045 * hi, .010 * sh + .004 * hi, -.018 * sh + .055 * hi], 2) * (1 if kind == 'stock' else .5)
    l2 = (x[..., 0] * .11 + x[..., 1] * .59 + x[..., 2] * .30)[..., None]; x = l2 + (x - l2) * (1.10 if kind == 'stock' else 1.03)
    small = cv2.resize(np.clip(x - .72, 0, 1), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    x = x + cv2.resize(cv2.GaussianBlur(small, (0, 0), 9), (W, H))[..., :3] * .55
    return np.clip(x, 0, 1)
def finish(x, n, kind):
    if kind == 'white': return x                     # белые Apple-сцены — чистые, без зерна
    s = 3.4 / 255
    x = x + GRAIN[n % 8][..., None] * s
    # без виньетки (правило стиля пользователя)
    return x

# ---------------- переходы ----------------
def radial(img, k, n=6):
    acc = np.zeros_like(img)
    for i in range(n): acc += cam(img, 1 + k * i / (n - 1))
    return acc / n
def whip(img, k, d=1):
    L = int(4 + 140 * k) | 1; ker = np.zeros((1, L), np.float32); ker[0] = 1 / L
    return cv2.filter2D(cam(img, 1, 0, d * 260 * k * k, 0), -1, ker, borderType=cv2.BORDER_REFLECT)

# ---------------- рендер ----------------
CLIPS = {}
def shot_frame(i, t, raw=False):
    s = S[i]; lt = t - s['t0']; T = s['t1'] - s['t0']; p = min(max(lt / T, 0), 1)
    kind = s.get('g', 'stock')
    if 'src' in s:
        sp = s.get('sp', 1.0); key = i
        if key not in CLIPS: CLIPS[key] = Clip(s['src'], s['c0'] - .25 * sp, s['c0'] + (T + .3) * sp, s.get('cx', .5))
        c = s['c0'] + lt * sp; img = CLIPS[key].at(c)
        z = s['zf'](c) if 'zf' in s else s.get('z', (1.08, 1.14))[0] + (s.get('z', (1.08, 1.14))[1] - s.get('z', (1.08, 1.14))[0]) * p
        (px0, py0), (px1, py1) = s.get('pan', ((0, 0), (0, 0))); r0, r1 = s.get('rot', (0, 0))
        img = cam(img, z, r0 + (r1 - r0) * p, px0 + (px1 - px0) * p, py0 + (py1 - py0) * p)
    elif 'ui' in s:
        fg, a = load_ui(s['ui'], int(round(lt * FPS)))
        if a is not None:
            b = s['bg']; key = ('bg', i)
            if key not in CLIPS: CLIPS[key] = Clip(b['src'], b['c0'] - .2, b['c0'] + T + .5, b.get('cx', .5), blur=26)
            bg = cam(CLIPS[key].at(b['c0'] + lt), 1.1 + .05 * p) * .5
            img = bg * (1 - a) + fg * a
        else: img = fg
        if s.get('shake'): a_ = s['shake']; img = cam(img, 1.03, .5 * math.sin(lt * 37), a_ * math.sin(lt * 61) + a_ * .5 * math.sin(lt * 23), a_ * math.cos(lt * 53))
        if s.get('punch') and t >= s['punch']: q = t - s['punch']; img = cam(img, 1 + .03 * math.exp(-q * 5) * min(1, q / .06), 0, 0, 0)
    elif s.get('eng'):
        img = eng_frame(int(round(t * FPS)))
    elif s.get('freeze'):
        img = cam(FROZEN, s['z'][0] + (s['z'][1] - s['z'][0]) * (1 - (1 - p) ** 2))
        l = img.mean(2, keepdims=True); img = l + (img - l) * .55; img = img * .9
    if raw: return img
    return grade(img, kind)

FROZEN = None
def render_frame(n):
    global FROZEN
    t = n / FPS; i = next(k for k, s in enumerate(S) if s['t0'] <= t < s['t1'])
    s = S[i]; kind = s.get('g', 'stock')
    x = shot_frame(i, t)
    if s.get('keep'): FROZEN = shot_frame(i, min(t, s['t1'] - 1 / FPS), raw=True) if t + 1 / FPS >= s['t1'] else FROZEN
    # переходы: вход (tr у текущего) и выход (tr у следующего)
    if i + 1 < len(S) and S[i + 1].get('tr') not in (None, 'fade') and t > S[i + 1]['t0'] - .1:
        k = (t - (S[i + 1]['t0'] - .1)) / .1; tr = S[i + 1]['tr']
        if tr == 'zoom': x = cam(radial(x, .30 * k * k), 1 + .35 * k * k)
        elif tr == 'whip': x = whip(x, k, 1)
        elif tr == 'flash': x = x + (1 - x) * k ** 2
    if s.get('tr') == 'fade' and t - s['t0'] < .3 and i > 0:
        k = (t - s['t0']) / .3; k = k * k * (3 - 2 * k)
        x = shot_frame(i - 1, t) * (1 - k) + x * k
    if s.get('tr') and s.get('tr') != 'fade' and t - s['t0'] < .12:
        k = 1 - (t - s['t0']) / .12; tr = s['tr']
        if tr == 'zoom': x = cam(radial(x, .22 * k * k), 1 + .22 * k * k)
        elif tr == 'whip': x = whip(x, k, 1)
        elif tr == 'flash': x = x + (1 - x) * k ** 1.5
    x = finish(x, n, kind)
    draw_subs(x, t, s.get('suby', SUBY))
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)

if __name__ == "__main__":
    out = sys.argv[1]
    if "--frames" in sys.argv:
        ns = [int(v) for v in sys.argv[sys.argv.index("--frames") + 1].split(",")]
        for n in sorted(ns):
            # для заморозки нужен последний кадр навигатора
            fi = next(k for k, q in enumerate(S) if q.get('freeze')); ki = fi - 1
            if S[fi]['t0'] <= n / FPS and FROZEN is None: render_frame(math.ceil(S[ki]['t1'] * FPS) - 1)
            cv2.imwrite(f"{out}_{n:05d}.png", render_frame(n))
        sys.exit()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", out], stdin=subprocess.PIPE)
    last_shot = -1
    for n in range(N):
        t = n / FPS; i = next(k for k, s in enumerate(S) if s['t0'] <= t < s['t1'])
        if i != last_shot:
            for k in list(CLIPS):
                kk = k if isinstance(k, int) else k[1]
                if kk < i - 1: del CLIPS[k]
            last_shot = i
        enc.stdin.write(render_frame(n).tobytes())
        if n % 60 == 0: print(f"{t:.1f} c", flush=True)
    enc.stdin.close(); enc.wait(); print("готово", out)
