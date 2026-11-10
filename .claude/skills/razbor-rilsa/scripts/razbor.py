"""Разбор рилса: скачать -> кадры -> склейки -> речь с таймкодами -> контакт-листы для просмотра.

Использование:
    python razbor.py <ссылка на рилс> [--out reels] [--model large-v3-turbo|small] [--cookies файл.txt]

Результат: reels/<ГГГГ-ММ-ДД>/<id>/
    video.mp4, info.json                 — видео и данные поста (подпись, лайки, просмотры, если отдались)
    frames/hook_0.0.jpg … hook_2.5.jpg   — первые 3 с, кадр каждые 0.5 с
    frames/t_003.jpg …                   — дальше 1 кадр в секунду
    hook.jpg, sheet_*.jpg                — контакт-листы (их смотрит Claude)
    transcript.json / transcript.txt     — речь по фразам и словам с таймкодами (faster-whisper, ru)
    data.json                            — длительность, склейки (средняя длина плана), громкость, доля речи
"""
import argparse, datetime, glob, json, math, os, re, shutil, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("--out", default="reels")
ap.add_argument("--model", default="large-v3-turbo")
ap.add_argument("--lang", default="auto", help="ru | en | auto (по умолчанию определяется сам: чужие рилсы часто на английском)")
ap.add_argument("--cookies", default=None, help="cookies.txt (Netscape) — если Instagram требует вход")
A = ap.parse_args()

MODELS = os.path.expanduser("~/video-models/faster-whisper")
FONT = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/local/fonts/SF-Pro-Display-Bold.otf"
YTDLP = shutil.which("yt-dlp") or "yt-dlp"
log = lambda *a: print(*a, flush=True)

# ---------- 1. скачивание ----------
day = datetime.date.today().isoformat()
tmp = os.path.join(A.out, day, "_tmp")
os.makedirs(tmp, exist_ok=True)
base = [YTDLP, "--no-playlist", "--no-progress", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
        "--write-info-json", "-o", os.path.join(tmp, "%(id)s.%(ext)s"), A.url]
tries = [("без входа", [])]
if A.cookies: tries.append((f"cookies из файла {A.cookies}", ["--cookies", A.cookies]))
tries.append(("cookies из браузера Chrome (--cookies-from-browser chrome)", ["--cookies-from-browser", "chrome"]))
used, err = None, ""
for name, extra in tries:
    r = subprocess.run(base[:1] + extra + base[1:], capture_output=True, text=True)
    vids = [f for f in glob.glob(os.path.join(tmp, "*.mp4"))]
    if r.returncode == 0 and vids:
        used = name; break
    err = (r.stderr or r.stdout).strip().splitlines()[-3:]
    log(f"не скачалось ({name}):", " | ".join(err))
if not used:
    log("ОШИБКА: рилс не скачался ни одним способом."); sys.exit(2)
log("скачано:", used)
vid = sorted(glob.glob(os.path.join(tmp, "*.mp4")), key=os.path.getmtime)[-1]
rid = os.path.splitext(os.path.basename(vid))[0]
D = os.path.join(A.out, day, rid)
if os.path.exists(D): shutil.rmtree(D)
os.makedirs(D)
shutil.move(vid, os.path.join(D, "video.mp4"))
for f in glob.glob(os.path.join(tmp, rid + "*.info.json")): shutil.move(f, os.path.join(D, "info.json"))
shutil.rmtree(tmp, ignore_errors=True)
V = os.path.join(D, "video.mp4")

# ---------- 2. параметры видео ----------
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate",
                                "-of", "json", V], capture_output=True, text=True).stdout)
dur = float(pr["format"]["duration"])
vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
W, H = vs["width"], vs["height"]; fr = vs["r_frame_rate"].split("/"); fps = float(fr[0]) / float(fr[1])
has_audio = any(s["codec_type"] == "audio" for s in pr["streams"])

# ---------- 3. кадры: первые 3 с каждые 0.5 с, дальше 1 в секунду ----------
F = os.path.join(D, "frames"); os.makedirs(F)
def grab(t, name):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", V, "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3",
                    os.path.join(F, name)], check=False)
hook_t = [x * 0.5 for x in range(6) if x * 0.5 < dur]
for t in hook_t: grab(t, f"hook_{t:.1f}.jpg")
sec_t = list(range(3, int(math.floor(dur)) + 1))
for t in sec_t:
    if t < dur - 0.05: grab(t, f"t_{t:03d}.jpg")

# ---------- 4. склейки (смена плана) ----------
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", V, "-vf", "select='gt(scene,0.2)',showinfo", "-an", "-f", "null", "-"],
                   capture_output=True, text=True)
cuts = [round(float(m), 2) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
shots = [b - a for a, b in zip([0] + cuts, cuts + [dur]) if b - a > 0.05]

# ---------- 5. громкость ----------
lufs = None
if has_audio:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", V, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[0-9.]+) LUFS", r.stderr); lufs = float(m[-1]) if m else None

# ---------- 6. речь с таймкодами (faster-whisper, русский) ----------
segs = []; lang_ = None
if has_audio:
    from faster_whisper import WhisperModel
    model = WhisperModel(A.model, device="cpu", compute_type="int8", download_root=MODELS)
    import numpy as np                                   # звук декодирует ffmpeg (PyAV в окружении несовместим с faster-whisper)
    pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", V, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                       capture_output=True, check=True).stdout, np.float32)
    it, info = model.transcribe(pcm, language=None if A.lang == "auto" else A.lang, word_timestamps=True, vad_filter=True, beam_size=5)
    lang_ = getattr(info, "language", None)
    BAD = ("субтитры сделал", "субтитры создавал", "продолжение следует", "редактор субтитров", "подписывайтесь на канал")
    for s in it:
        tx = s.text.strip(); low = tx.lower()
        if any(b in low for b in BAD) or re.search(r"(.{1,3})\1{8,}", low) or s.no_speech_prob > 0.6: continue   # галлюцинации на музыке
        segs.append({"t0": round(s.start, 2), "t1": round(s.end, 2), "text": s.text.strip(),
                     "words": [{"w": w.word.strip(), "t0": round(w.start, 2), "t1": round(w.end, 2)} for w in (s.words or [])]})
json.dump(segs, open(os.path.join(D, "transcript.json"), "w"), ensure_ascii=False, indent=1)
# короткие фразы по словам: новая строка на паузе > 0.3 с, после точки/вопроса или каждые ~8 слов — удобно для разбора «по секундам»
phr, cur = [], []
for w in [w for s in segs for w in s["words"]]:
    if cur and (w["t0"] - cur[-1]["t1"] > 0.3 or len(cur) >= 8 or cur[-1]["w"][-1:] in ".?!"):
        phr.append(cur); cur = []
    cur.append(w)
if cur: phr.append(cur)
with open(os.path.join(D, "transcript.txt"), "w") as f:
    for p_ in phr: f.write(f"[{p_[0]['t0']:6.2f} – {p_[-1]['t1']:6.2f}] {' '.join(w['w'] for w in p_)}\n")
speech = sum(s["t1"] - s["t0"] for s in segs)

# ---------- 7. контакт-листы (подпись: секунда; красная рамка — в эту секунду была склейка) ----------
from PIL import Image, ImageDraw, ImageFont
try: fo = ImageFont.truetype(FONT, 26)
except Exception: fo = ImageFont.load_default()
def sheet(files, out, cols, labels, marks):
    ims = [Image.open(f).convert("RGB") for f in files]
    if not ims: return
    w = 270; h = int(ims[0].height * w / ims[0].width); rows = math.ceil(len(ims) / cols)
    S = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + 6) + 6), (20, 20, 22)); d = ImageDraw.Draw(S)
    for i, (im, lab, mk) in enumerate(zip(ims, labels, marks)):
        x, y = 6 + (i % cols) * (w + 6), 6 + (i // cols) * (h + 6)
        S.paste(im.resize((w, h)), (x, y))
        if mk: d.rectangle([x, y, x + w - 1, y + h - 1], outline=(255, 60, 60), width=5)
        d.rectangle([x, y, x + 92, y + 36], fill=(0, 0, 0)); d.text((x + 8, y + 4), lab, font=fo, fill=(255, 214, 10))
    S.save(out, quality=88)
hf = [os.path.join(F, f"hook_{t:.1f}.jpg") for t in hook_t]
sheet(hf, os.path.join(D, "hook.jpg"), 6, [f"{t:.1f}с" for t in hook_t], [any(t <= c < t + 0.5 for c in cuts) for t in hook_t])
tf = [os.path.join(F, f"t_{t:03d}.jpg") for t in sec_t if os.path.exists(os.path.join(F, f"t_{t:03d}.jpg"))]
ts = [int(os.path.basename(f)[2:5]) for f in tf]
for k in range(0, len(tf), 24):
    sheet(tf[k:k + 24], os.path.join(D, f"sheet_{k // 24 + 1}.jpg"), 6, [f"{t}с" for t in ts[k:k + 24]], [any(t - 1 < c <= t for c in cuts) for t in ts[k:k + 24]])

# ---------- 8. сводка ----------
info = json.load(open(os.path.join(D, "info.json"))) if os.path.exists(os.path.join(D, "info.json")) else {}
data = {"url": A.url, "id": rid, "download": used, "duration": round(dur, 2), "size": [W, H], "fps": round(fps, 2),
        "cuts": cuts, "cuts_count": len(cuts), "avg_shot_s": round(sum(shots) / len(shots), 2) if shots else None,
        "cuts_first_3s": sum(1 for c in cuts if c < 3), "lufs": lufs, "speech_s": round(speech, 1), "lang": lang_,
        "speech_share": round(speech / dur, 2) if dur else None, "words": sum(len(s["words"]) for s in segs),
        "words_per_s": round(sum(len(s["words"]) for s in segs) / speech, 2) if speech else None,
        "author": info.get("uploader") or info.get("channel"), "caption": info.get("description"),
        "views": info.get("view_count"), "likes": info.get("like_count"), "comments": info.get("comment_count"),
        "upload_date": info.get("upload_date"), "music": info.get("track") or info.get("artist")}
json.dump(data, open(os.path.join(D, "data.json"), "w"), ensure_ascii=False, indent=1)
log("ГОТОВО:", D)
log(json.dumps({k: v for k, v in data.items() if k not in ("cuts", "caption")}, ensure_ascii=False))
