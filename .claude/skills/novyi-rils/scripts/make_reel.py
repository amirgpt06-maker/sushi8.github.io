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
        if PEOPLE.search(title) and "hand" not in title: continue      # без лиц: людей — только руки (правило пользователя)
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
for li, l in enumerate(SC["lines"]):
    for _ in range(5):                                       # битый/недоступный ролик — берём следующий подходящий
        vid = pick([t.lower() for t in l.get("stock", [])]); f = fetch(vid)
        if f: break
    a_, b_ = lines_t[li]; n = max(1, math.ceil((b_ - a_) / 3.0))          # длинная фраза — несколько планов по 2–3 с
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

# ---------- 5. субтитры по словам: 1–3 слова, ключевые жёлтым ----------
FONT = next((p for p in ["/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf", "/usr/share/fonts/opentype/montserrat/Montserrat-ExtraBold.otf",
             os.path.join(ROOT, ".claude/skills/montazh/engine/local/fonts/SF-Pro-Display-Bold.otf"), "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(p)), None)
KEYS = {norm(k) for l in SC["lines"] for k in l.get("keywords", [])}
groups, cur = [], []                                  # куски фразы до знака препинания делим ровно: 4 слова -> 2+2, 5 -> 3+2
for i, d in enumerate(disp):
    cur.append(d)
    if d[0][-1:] in ".,!?:—…" or i + 1 == len(disp) or disp[i + 1][1] != d[1]:
        n = len(cur); k = math.ceil(n / 3)
        while k < n and any(sum(len(w[0]) for w in cur[j * n // k:(j + 1) * n // k]) > 18 for j in range(k)): k += 1
        groups += [cur[j * n // k:(j + 1) * n // k] for j in range(k)]; cur = []
_cache = {}
def sprite(words):
    key = tuple(w for w, *_ in words)
    if key in _cache: return _cache[key]
    for size in range(92, 60, -4):
        fo = ImageFont.truetype(FONT, size); txt = " ".join(key)
        if fo.getlength(txt) <= 900: break
    pad = 60; tw = int(fo.getlength(" ".join(key))) + 2 * pad; asc, desc = fo.getmetrics(); th = asc + desc + 2 * pad
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); x0 = pad
    for w in key:
        col = (255, 214, 10, 255) if norm(w) in KEYS else (255, 255, 255, 255)
        dr.text((x0, pad), w, font=fo, fill=col, stroke_width=3, stroke_fill=(0, 0, 0, 255)); x0 += fo.getlength(w + " ")
    a = np.array(im.getchannel("A")).astype(np.float32) / 255
    sh = np.roll(cv2.GaussianBlur(a, (0, 0), 10), 6, 0) * 0.75
    rgb = np.array(im.convert("RGB")).astype(np.float32)[..., ::-1] / 255
    A_ = a + sh * (1 - a); C = rgb * a[..., None] / np.maximum(A_[..., None], 1e-4)
    _cache[key] = (C, A_); return _cache[key]
def draw_subs(img, t):
    for gi, g in enumerate(groups):
        a, b = g[0][2], (groups[gi + 1][0][2] if gi + 1 < len(groups) else g[-1][3] + 0.4)
        if not (a - 0.02 <= t < b): continue
        C, A_ = sprite(g); k = min(1, (t - a) / 0.14); s = 0.85 + 0.15 * (1 - (1 - k) ** 3) + 0.04 * math.sin(math.pi * k)
        h, w = A_.shape; M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s); C2 = cv2.warpAffine(C, M, (w, h)); A2 = cv2.warpAffine(A_, M, (w, h)) * min(1, (t - a) / 0.06 + 0.001)
        x0, y0 = int(W / 2 - w / 2), int(H * 0.70 - h / 2)
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
        al = A2[ya - y0:yb - y0, xa - x0:xb - x0, None]
        img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - al) + C2[ya - y0:yb - y0, xa - x0:xb - x0] * al

# ---------- 6. видео ----------
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
    t = n / FPS; i = max(k for k, s in enumerate(shots) if s["t0"] <= t + 1e-6)
    img = shot_img(i, t)
    if i > 0 and t - shots[i]["t0"] < 0.25:                                        # мягкий наплыв между планами
        k = (t - shots[i]["t0"]) / 0.25; img = shot_img(i - 1, t) * (1 - k) + img * k
    img = np.clip(0.5 + (img - 0.5) * 1.05, 0, 1)
    if n == 0: pass
    draw_subs(img, t)
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    if abs(t - min(1.5, DUR / 2)) < 0.5 / FPS: cv2.imwrite(os.path.join(OUT, "cover.jpg"), out)
    enc.stdin.write(out.tobytes())
    for k in [k for k in frames if k < i - 1]: del frames[k]
enc.stdin.close(); enc.wait()

# ---------- 7. звуки (из sfx/, иначе синтез из skill montazh) и сведение ----------
SFXD = [os.path.join(ROOT, "sfx"), os.path.join(ROOT, ".claude/skills/montazh/engine/sfx")]
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
wh, pop, ding = snd("whoosh", "swoosh"), snd("pop", "tagpop", "linepop"), snd("ding", "chime", "tink")
for s in shots[1:]: put(wh, max(0, s["t0"] - 0.12), -10)
for g in groups:
    if any(norm(w) in KEYS for w, *_ in g): put(pop, g[0][2], -9)
put(ding, max(0, len(v) / SR - 1.2), -8)
mx = os.path.join(WK, "mix.wav"); sf.write(mx, np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")
reel = os.path.join(OUT, "reel.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(WK, "video.mp4"), "-i", mx, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000", "-c:a", "aac", "-b:a", "256k", "-shortest", "-map_metadata", "-1",
                "-movflags", "+faststart", reel], check=True)

# ---------- 8. пост, хэштеги, данные ----------
open(os.path.join(OUT, "post.txt"), "w", encoding="utf-8").write(SC.get("post", "").strip() + "\n\n" + " ".join(SC.get("hashtags", [])) + "\n")
json.dump({**SC, "voice": eng, "duration": round(DUR, 2), "shots": [{k: s[k] for k in ("t0", "t1", "vid", "title")} for s in shots]},
          open(os.path.join(OUT, "scenario.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"status": "draft", "created": datetime.datetime.now().isoformat(timespec="seconds")}, open(os.path.join(OUT, "status.json"), "w"))
shutil.rmtree(WK, ignore_errors=True)
log("ГОТОВО:", OUT)
