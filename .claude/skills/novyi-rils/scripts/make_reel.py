"""Рилс по сценарию: озвучка -> чистка голоса -> тайминги слов -> сток по смыслу фраз -> монтаж 9:16 с субтитрами по словам
-> звуки из sfx/ -> ready/<дата>/<slug>/ (reel.mp4, post.txt, cover.jpg, scenario.json).

python make_reel.py scenario.json [--engine elevenlabs|piper] [--out ready]

scenario.json:
{"topic": "…", "slug": "latinica-bez-probelov",
 "lines": [{"text": "фраза как её произносить", "stock": ["laptop", "typing"], "keywords": ["слово"]}, …],
 "post": "текст поста", "hashtags": ["#нейросети", …]}
"""
import argparse, datetime, difflib, json, math, os, random, re, shutil, subprocess, sys
import numpy as np, cv2, soundfile as sf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "../../../.."))
sys.path.insert(0, HERE); import tts
ap = argparse.ArgumentParser(); ap.add_argument("scenario"); ap.add_argument("--engine"); ap.add_argument("--voice", help="своя запись голоса (голосовое из Telegram, mp3/m4a/ogg/wav) — по умолчанию"); ap.add_argument("--out", default=os.path.join(ROOT, "ready"))
A = ap.parse_args()
SC = json.load(open(A.scenario, encoding="utf-8"))
W, H, FPS, SR = 1080, 1920, 30, 48000
day = datetime.date.today().isoformat()
OUT = os.path.join(A.out, day, SC.get("slug") or "reel"); os.makedirs(OUT, exist_ok=True)
WK = os.path.join(OUT, "_work"); os.makedirs(WK, exist_ok=True)
log = lambda *a: print(*a, flush=True)
PY = sys.executable

# ---------- 1. озвучка ----------
raw = os.path.join(WK, "voice_raw.wav")
if A.voice:                                                   # голос пользователя (бесплатно: сам записывает)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A.voice, "-ac", "1", "-ar", "48000", raw], check=True); eng = "свой голос"
else:                                                         # черновой синтез — только для проверки системы
    text = " ".join(l["text"].strip() for l in SC["lines"])
    eng = tts.speak(text, raw, A.engine)
log("озвучка:", eng)

# ---------- 2. чистка: паузы по краям долой, голос чистый и громкий ----------
x, sr = sf.read(raw); x = x if x.ndim == 1 else x.mean(1)
a = np.abs(x); thr = a.max() * 0.03; nz = np.where(a > thr)[0]
x = x[max(0, nz[0] - int(0.06 * sr)): nz[-1] + int(0.15 * sr)]
trim = os.path.join(WK, "voice_trim.wav"); sf.write(trim, x, sr)
voice = os.path.join(WK, "voice.wav")
VP = os.path.join(ROOT, "video-tools/voice_pro.py")
subprocess.run([PY, VP, trim, voice, "--amount", "0.3"], check=True, capture_output=True)   # одобренная пользователем обработка (30 %)
v, _ = sf.read(voice); v = v if v.ndim == 1 else v.mean(1)
DUR = len(v) / SR + 0.6                                                          # хвост 0.6 с на финальный кадр
log(f"голос {len(v) / SR:.2f} с")

# ---------- 3. тайминги слов (faster-whisper) и привязка к тексту сценария ----------
from faster_whisper import WhisperModel
model = WhisperModel(os.environ.get("WHISPER_MODEL", "large-v3-turbo"), device="cpu", compute_type="int8",
                     download_root=os.path.expanduser("~/video-models/faster-whisper"))
segs, _ = model.transcribe(v.astype(np.float32) if SR == 16000 else np.interp(np.arange(int(len(v) * 16000 / SR)) * SR / 16000, np.arange(len(v)), v).astype(np.float32),
                           language="ru", word_timestamps=True, vad_filter=False, beam_size=5)
heard = [{"w": w.word.strip(), "t0": w.start, "t1": w.end} for s in segs for w in (s.words or [])]
norm = lambda s: re.sub(r"[^0-9a-zа-яё]", "", s.lower().replace("ё", "е"))
disp = []                                                                        # слова сценария: (слово, номер фразы)
for li, l in enumerate(SC["lines"]):
    for w in l["text"].split(): disp.append([w, li, None, None])
sm = difflib.SequenceMatcher(None, [norm(d[0]) for d in disp], [norm(h["w"]) for h in heard], autojunk=False)
for blk in sm.get_matching_blocks():
    for j in range(blk.size): disp[blk.a + j][2] = heard[blk.b + j]["t0"]; disp[blk.a + j][3] = heard[blk.b + j]["t1"]
if A.voice and heard:                                          # говорил своими словами — субтитры строго по речи
    owner = {}
    for blk in sm.get_matching_blocks():
        for j in range(blk.size): owner[blk.b + j] = disp[blk.a + j][1]
    li_, new = 0, []
    for k, h in enumerate(heard):
        li_ = max(li_, owner.get(k, li_)); new.append([h["w"], li_, h["t0"], h["t1"]])
    disp = new
known = [(i, d[2]) for i, d in enumerate(disp) if d[2] is not None] or [(0, 0.0)]
if known[0][0] != 0: known.insert(0, (0, 0.0))
if known[-1][0] != len(disp) - 1: known.append((len(disp) - 1, len(v) / SR - 0.3))
xs, ys = zip(*known); t0s = np.interp(range(len(disp)), xs, ys)
for i, d in enumerate(disp): d[2] = float(t0s[i])
for i, d in enumerate(disp): d[3] = d[3] if d[3] else (disp[i + 1][2] if i + 1 < len(disp) else len(v) / SR)
lines_t = []
for li in range(len(SC["lines"])):
    ws = [d for d in disp if d[1] == li]
    lines_t.append([ws[0][2], ws[-1][3]] if ws else [lines_t[-1][1] if lines_t else 0.0] * 2)
for i in range(len(lines_t) - 1): lines_t[i][1] = lines_t[i + 1][0]           # план держится до следующей фразы
lines_t[0][0] = 0.0; lines_t[-1][1] = DUR

# ---------- 4. сток по смыслу каждой фразы ----------
CAT = json.load(open(os.path.join(ROOT, "stock/catalog.json")))
used = set()
PEOPLE = re.compile(r"\b(friends?|people|customers?|team|crowd|group|family|man|men|guy|boy|person|students?|workers?|businessman|"
                    r"waiter|chef|tourists?|shoppers?|passengers?|pedestrians?|audience|fans|athlete|player|singer|actor|teenager|youth|adult|elderly|grandfather|face|portrait)\b")
def pick(tags):
    best, bs = None, -1
    for vid, e in CAT.items():
        if vid in used: continue
        title = e["title"].lower()
        if re.search(r"\b(woman|women|girl|girls|female|lady|her|she)\b", title): continue        # женщин нет вообще
        if PEOPLE.search(title) and not re.search(r"hand|silhouette", title): continue      # людей — только руки и силуэты
        s = sum(3 for t in tags if t in e["tags"]) + sum(1 for t in tags for w in t.split("-") if w in title) + random.random() * 0.5
        if s > bs: best, bs = vid, s
    used.add(best); return best
BLOCK = set(open(os.path.join(ROOT, "stock/blocked.txt")).read().split()) if os.path.exists(os.path.join(ROOT, "stock/blocked.txt")) else set()
used |= BLOCK                                          # ролики, где нашлись лица/женщины — в blocked.txt, больше не берём
def ok(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width", "-of", "csv=p=0", f], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() != ""
YUNET = os.path.join(HERE, "../models/yunet.onnx")
def has_faces(f):
    """Лица в кадре (правило пользователя: без лиц) — детектор YuNet на 5 кадрах клипа."""
    det = cv2.FaceDetectorYN.create(YUNET, "", (320, 320), 0.75)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout or 5)
    for k in range(5):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{d * (k + .5) / 5:.2f}", "-i", f, "-frames:v", "1", "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if img is None: continue
        det.setInputSize((img.shape[1], img.shape[0])); _, faces = det.detect(img)
        if faces is not None and any(fc[3] > img.shape[0] * 0.035 for fc in faces): return True
    return False
def fetch(vid):
    f = os.path.join(ROOT, "stock", f"{vid}.mp4")
    CK = os.path.join(ROOT, "stock/checked.txt"); checked = set(open(CK).read().split()) if os.path.exists(CK) else set()
    if os.path.exists(f) and ok(f):
        if vid in checked: return f
        if has_faces(f):
            open(os.path.join(ROOT, "stock/blocked.txt"), "a").write(f" {vid}"); os.remove(f); log(f"  {vid}: в кадре лица — пропускаю"); return None
        open(CK, "a").write(f" {vid}"); return f
    for q in ("1080", "720"):
        r = subprocess.run(["curl", "-sS", "-f", "-m", "300", "-o", f, f"https://assets.mixkit.co/videos/{vid}/{vid}-{q}.mp4"], capture_output=True)
        if r.returncode == 0 and ok(f):
            if has_faces(f):                                    # лица — в чёрный список, ролик удалить
                open(os.path.join(ROOT, "stock/blocked.txt"), "a").write(f" {vid}"); os.remove(f); log(f"  {vid}: в кадре лица — пропускаю"); return None
            open(os.path.join(ROOT, "stock/checked.txt"), "a").write(f" {vid}"); return f
    if os.path.exists(f): os.remove(f)
    return None
shots = []
NL = len(SC["lines"])
def look_of(li):                                             # kino — стопки слов поверх стока; flash — белая карточка-вспышка; title — размытый фон + крупный заголовок
    return SC["lines"][li].get("look") or ("flash" if (0 < li < NL - 1 and li % 3 == 2) else "kino")
for li, l in enumerate(SC["lines"]):
    a_, b_ = lines_t[li]
    for _ in range(5):                                       # битый/недоступный ролик — берём следующий подходящий
        vid = pick([t.lower() for t in l.get("stock", [])]); f = fetch(vid)
        if f: break
    n = max(1, round((b_ - a_) / 1.7))                       # динамичный монтаж: план 1.2–2 с
    for k in range(n):
        if k:
            for _ in range(5):
                vid = pick([t.lower() for t in l.get("stock", [])]); f = fetch(vid)
                if f: break
        t0_, t1_ = a_ + (b_ - a_) * k / n, a_ + (b_ - a_) * (k + 1) / n
        shots.append({"t0": t0_, "t1": t1_, "vid": vid, "file": f, "title": CAT[vid]["title"]})
        log(f"  {t0_:5.2f}–{t1_:5.2f}  {vid}  {CAT[vid]['title']}  ← «{l['text'][:40]}»")

shots = [s for s in shots if s["t1"] - s["t0"] > 0.05]                # фразу сценария пропустил в записи — плана нет
def decode(s):
    f = s["file"]; T = s["t1"] - s["t0"] + 0.4
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout.split()
    w, h = map(int, pr[0].split(",")); d = float(pr[1])
    sp = min(1.0, max(0.55, (d - 0.5) / T))                                       # короткий клип — замедлить, а не зациклить
    st = max(0.0, min(d - T * sp - 0.1, d * 0.2))
    vf = (f"crop={int(h * 9 / 16) // 2 * 2}:{h}," if w > h else "") + f"scale={W}:{H}:flags=lanczos,setpts=PTS/{sp:.3f},fps={FPS}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{st:.2f}", "-t", f"{T * sp + 0.2:.2f}", "-i", f, "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return fr

# ---------- 5. стиль «Apple»: текст рисует наш движок (engine/render.js + compose.py), как в референсах пользователя ----------
ENG = os.path.join(ROOT, ".claude/skills/montazh/engine")
KEYS = {norm(k) for l in SC["lines"] for k in l.get("keywords", [])}
BRAND = json.load(open(os.path.join(ROOT, "brand.json"))) if os.path.exists(os.path.join(ROOT, "brand.json")) else {"ig": "saidulaev.ai", "tg": ""}
def blocks_of(li):
    """Слова фразы -> блоки по ≤5 слов (разрыв на знаке препинания или паузе) со временем каждого слова."""
    ws = [d for d in disp if d[1] == li]; out, cur = [], []
    for i, d in enumerate(ws):
        cur.append(d)
        last = i + 1 == len(ws)
        if last or len(cur) >= 5 or d[0][-1:] in ".?!:;—" or (ws[i + 1][2] - d[3] > 0.35 and len(cur) >= 2) or (d[0][-1:] == "," and len(cur) >= 3):
            out.append(cur); cur = []
    return out
def stack(ws):
    """Подпись-стопка из референсов: мелкое слово сверху слева, КЛЮЧЕВОЕ крупно, мелкое снизу справа."""
    clean = lambda w: w.strip(" ,.;:—-!?«»")
    ki = next((i for i, d in enumerate(ws) if norm(d[0]) in KEYS), None)
    if ki is None: ki = max(range(len(ws)), key=lambda i: (len(clean(ws[i][0])) if len(clean(ws[i][0])) >= 4 else 0, i))
    kw = clean(ws[ki][0]); size = "hb" if len(kw) <= 8 else ("l" if len(kw) <= 11 else "m")
    L = []
    if ki: L.append({"size": "s", "align": "left", "words": [[clean(d[0]), d[2]] for d in ws[:ki]]})
    L.append({"size": size, "words": [[kw, ws[ki][2], "a"] if norm(ws[ki][0]) in KEYS else [kw, ws[ki][2]]]})
    if ki + 1 < len(ws): L.append({"size": "s", "align": "right", "words": [[clean(d[0]), d[2]] for d in ws[ki + 1:]]})
    return L
items = []
for li in range(NL):
    look, bl = look_of(li), blocks_of(li); lt0, lt1 = lines_t[li]
    if li == NL - 1:                                                     # призыв: подпишись (Instagram и Telegram)
        t_cta = next((d[2] for d in disp if d[1] == li and "подпиш" in norm(d[0])), lt0 + 1.0)
        items.append({"type": "cta", "t": round(t_cta, 2), "end": round(DUR, 2), "text": "Подпишись", "sub": "Instagram" + (" · Telegram" if BRAND.get("tg") else ""), "pos": [540, 980]})
        bl = [[d for d in b if d[2] < t_cta - 0.05] for b in bl]; bl = [b for b in bl if b]
    for bi, b in enumerate(bl):
        t0 = b[0][2]; nxt = bl[bi + 1][0][2] if bi + 1 < len(bl) else (lines_t[li + 1][0] if li + 1 < NL else DUR)
        end = round(min(nxt - 0.03, b[-1][3] + 0.55), 2)
        if end - t0 < 0.35: continue
        if look == "flash":
            txt = " ".join(d[0] for d in b).strip()
            items.append({"type": "flash", "t": round(t0, 2), "end": end, "bg": "#ffffff", "ink": "#12306b", "lines": [{"size": "m", "text": txt, "t": round(t0 + 0.04, 2)}]})
        else:
            items.append({"type": "words", "fx": "cinema", "t": round(t0, 2), "end": end, "pos": [540, 1060], "lines": stack(b)})
    if SC["lines"][li].get("title") and look == "title":                  # крупный заголовок на размытом фоне
        items.append({"type": "blur", "t": round(lt0, 2), "end": round(lt1, 2)}); items.append({"type": "title", "t": round(lt0 + 0.1, 2), "end": round(lt1, 2), "text": SC["lines"][li]["title"], "size": 150})
HOOK = SC.get("hook") or ""
if HOOK:                                                                 # хук на экране с первой секунды
    hw = HOOK.split(); k_ = max(1, len(hw) // 2)
    items.insert(0, {"type": "words", "fx": "cinema", "t": 0.1, "end": 2.7, "pos": [540, 430], "lines": [
        {"size": "m", "words": [[w, 0.1 + 0.12 * i] for i, w in enumerate(hw[:k_])]},
        {"size": "hb", "words": [[" ".join(hw[k_:]), 0.1 + 0.12 * k_, "a"]]}]})
items.append({"type": "mark", "t": 0, "end": round(DUR, 2), "name": "@" + BRAND["ig"], "sub": "нейросети простыми словами"})
cues = {"fps": FPS, "duration": round(DUR, 3), "anchor": None, "accent": "#4C8DFF", "textShadow": True, "items": items}
json.dump(cues, open(os.path.join(WK, "cues.json"), "w"), ensure_ascii=False, indent=1)

# ---------- 6. основа: сток, холодный грейд, мягкий наезд (без текста) ----------
GRAINS = [cv2.resize(np.random.default_rng(i).standard_normal((H // 3, W // 3)).astype(np.float32), (W, H)) for i in range(6)]
def grade_kino(img, n):
    l = (img[..., 0] * .11 + img[..., 1] * .59 + img[..., 2] * .30)[..., None]
    img = np.clip(0.5 + (img - 0.5) * 1.08, 0, 1)
    sh_, hi_ = (1 - l) ** 2, l ** 2
    img = img + np.concatenate([.050 * sh_ + .015 * hi_, .006 * sh_ + .002 * hi_, -.030 * sh_ - .012 * hi_], 2)   # синие тени, холодные света (гамма: белый + синий)
    return np.clip(img + GRAINS[n % 6][..., None] * (3.0 / 255), 0, 1)
N = int(math.ceil(DUR * FPS)); frames = {}
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", os.path.join(WK, "video.mp4")], stdin=subprocess.PIPE)
def shot_img(i, t):
    s = shots[i]
    if i not in frames: frames[i] = decode(s)
    fr = frames[i]; n = min(len(fr) - 1, max(0, int((t - s["t0"]) * FPS)))
    img = fr[n].astype(np.float32) / 255
    p = (t - s["t0"]) / max(0.1, s["t1"] - s["t0"]); z = 1.04 + 0.06 * p          # мягкий медленный наезд
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z); return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
for n in range(N):
    t = n / FPS; i = max(k for k, s_ in enumerate(shots) if s_["t0"] <= t + 1e-6)
    img = shot_img(i, t)
    if i > 0 and t - shots[i]["t0"] < 0.25:                                        # мягкий наплыв между планами
        k = (t - shots[i]["t0"]) / 0.25; img = shot_img(i - 1, t) * (1 - k) + img * k
    img = grade_kino(img, n)
    enc.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    for k in [k for k in frames if k < i - 1]: del frames[k]
enc.stdin.close(); enc.wait()

# ---------- 7. звук основы: голос + вжухи на склейках + размытые нашиды; остальные звуки (поп, печать) ставит движок по ролям пака ----------
SFXD = [os.path.join(ROOT, "sfx"), os.path.join(ENG, "sfx_local"), os.path.join(ENG, "sfx")]
def snd(*names):
    for d in SFXD:
        for nm in names:
            for ext in (".wav", ".mp3"):
                f = os.path.join(d, nm + ext)
                if os.path.exists(f):
                    r = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
                    y = np.frombuffer(r, np.float32).astype(np.float64); return y / (np.abs(y).max() + 1e-9)
    return None
L = int(DUR * SR); mix = np.zeros(L); mix[:len(v)] += v
VR = np.sqrt(np.mean(v[np.abs(v) > 1e-3] ** 2))
def put(y, t, db_):
    if y is None: return
    a0 = int(t * SR); e = min(L, a0 + len(y)); mix[a0:e] += y[:e - a0] * VR * 4 * 10 ** (db_ / 20)
wh = snd("sc_whoosh", "wbwhoosh", "whoosh", "swoosh")
for sh_ in shots[1:]: put(wh, max(0, sh_["t0"] - 0.12), -7)                 # вжух на каждой смене плана (динамика)
NASH = [os.path.join(ROOT, "nashid", f) for f in sorted(os.listdir(os.path.join(ROOT, "nashid"))) if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac"))] if os.path.isdir(os.path.join(ROOT, "nashid")) else []
if NASH:                                                                   # фон: размытые нашиды (только вокал; срез верха, реверберация, тихо)
    f_ = NASH[datetime.date.today().toordinal() % len(NASH)]
    y = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", f_, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
    st_ = random.randint(0, max(0, len(y) - L)) if len(y) > L else 0; y = y[st_:]
    while len(y) < L: y = np.concatenate([y, y])
    y = y[:L] / (np.sqrt(np.mean(y[:L] ** 2)) + 1e-9)                              # как есть, без обработки; выравниваем громкость треков
    fade = np.minimum(1, np.arange(L) / (1.5 * SR)) * np.minimum(1, (L - np.arange(L)) / (1.5 * SR))
    mix += y * VR * 0.05 * fade                                                    # громкость «5 из 100» = 5 % от голоса (−26 дБ)
    log("фон: нашид", os.path.basename(f_))
mx = os.path.join(WK, "mix.wav"); sf.write(mx, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")
base = os.path.join(WK, "base.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WK, "video.mp4"), "-i", mx, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", base], check=True)

# ---------- 7б. оверлей движка (стопки слов, вспышки, призыв) и сборка со звуками пака ----------
ov = os.path.join(WK, "ov")
subprocess.run(["node", os.path.join(ENG, "render.js"), os.path.join(WK, "cues.json"), ov], check=True, cwd=ENG, capture_output=True)
reel = os.path.join(OUT, "reel.mp4")
subprocess.run([PY, os.path.join(ENG, "compose.py"), base, ov, reel], check=True, capture_output=True, env={**os.environ, "GRADE": "0", "LOUDNORM": "1"})
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{min(1.6, DUR / 2):.2f}", "-i", reel, "-frames:v", "1", "-q:v", "2", os.path.join(OUT, "cover.jpg")], check=True)

# ---------- 8. пост, хэштеги, данные ----------
open(os.path.join(OUT, "post.txt"), "w", encoding="utf-8").write(SC.get("post", "").strip() + "\n\n" + " ".join(SC.get("hashtags", [])) + "\n")
json.dump({**SC, "voice": eng, "duration": round(DUR, 2), "shots": [{k: s[k] for k in ("t0", "t1", "vid", "title")} for s in shots]},
          open(os.path.join(OUT, "scenario.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"status": "draft", "created": datetime.datetime.now().isoformat(timespec="seconds")}, open(os.path.join(OUT, "status.json"), "w"))
shutil.rmtree(WK, ignore_errors=True)
log("ГОТОВО:", OUT)
