"""Кино-ролик с нуля по тексту: план (plan.json) -> нейроголос по предложениям -> 3D-сцены (three.js) -> кинотипографика
по словам -> звуковой дизайн -> video.mp4.  Использование: python t2v.py plan.json [этап: all|tts|render|compose|mix]

plan.json:
{ "voice": "ruslan", "speed": 1.1, "intro": 3.0, "outro": 6.0, "pause": 0.45,
  "title": {"top": "БИТВА ПРИ УХУДЕ · 625", "name": "МУСАБ ИБН УМЕЙР", "sub": "да будет доволен им Аллах", "scene": {spec}},
  "sentences": [ { "text": "что на экране", "say": "что произносить (если отличается)", "pause": 0.6,
                   "shots": [ {"frac": 0.5, "spec": {type, p, cam, exposure}}, ... ],
                   "accents": [ {"word": "восьмидесяти", "big": "80+", "sub": "УДАРОВ", "red": true, "sfx": "impact|thud|heart|bell|swish|none", "flash": true} ] } ],
  "ending": {"arabic": ["…", "…"], "lines": ["перевод…"], "ref": "КОРАН · 3:146", "scene": {spec}},
  "nick": "saidulaev.ai" }
"""
import json, os, subprocess, sys, math
import numpy as np, soundfile as sf

PY = "/root/venv-video/bin/python"
TOOLS = "/home/user/sushi8.github.io/video-tools/"
PLAN = os.path.abspath(sys.argv[1]); OUT = os.path.dirname(PLAN); STAGE = sys.argv[2] if len(sys.argv) > 2 else "all"
P = json.load(open(PLAN, encoding="utf-8")); SR = 48000; FPS = 30
HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda *a: os.path.join(OUT, *a)

# ---------------- 1. голос ----------------
def tts():
    voice = P.get("voice", "ruslan"); model = os.path.expanduser(f"~/video-models/tts/{voice}/ru_RU-{voice}-medium.onnx")
    parts, times, t = [], [], P.get("intro", 3.0)
    parts.append(np.zeros(int(t * SR)))
    for k, s in enumerate(P["sentences"]):
        wav = J(f"s{k:02d}.wav"); say = s.get("say") or s["text"]
        # 5 дублей, берём тот, который распознаётся ближе всего к тексту (нейроголос каждый раз читает чуть по-разному)
        import difflib, shutil
        nz_ = lambda q: "".join(c for c in q.lower().replace("ё", "е") if c.isalpha())
        best = (-1, None)
        for take in range(P.get("takes", 5)):
            tw = J(f"s{k:02d}_t{take}.wav")
            subprocess.run([PY.replace("python", "piper"), "-m", model, "--length_scale", str(P.get("speed", 1.1)),
                            "--noise_scale", str(P.get("noise", 0.6)), "--noise_w", str(P.get("noise_w", 0.7)), "-f", tw],
                           input=say.encode(), check=True, capture_output=True)
            subprocess.run([PY, TOOLS + "words.py", tw, tw + ".json"], check=True, capture_output=True)
            heard = " ".join(w["w"] for w in json.load(open(tw + ".json"))["words"])
            sc = difflib.SequenceMatcher(None, nz_(say), nz_(heard)).ratio()
            if sc > best[0]: best = (sc, tw, heard)
        shutil.copy(best[1], wav); print(f"  {k}: дубль {best[1][-6:-4]} совпадение {best[0]:.2f} | {best[2]}")
        x, sr = sf.read(wav); x = x if x.ndim == 1 else x.mean(1)
        if sr != SR:
            x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
        # срезаем тишину по краям, оставляем 40 мс
        a = np.abs(x); thr = a.max() * 0.02; nz = np.where(a > thr)[0]; x = x[max(0, nz[0] - int(.04 * SR)): nz[-1] + int(.08 * SR)]
        times.append([t, t + len(x) / SR]); parts.append(x); t += len(x) / SR
        gap = s.get("pause", P.get("pause", 0.45)); parts.append(np.zeros(int(gap * SR))); t += gap
    outro = P.get("outro", 6.0); parts.append(np.zeros(int(outro * SR))); t += outro
    raw = np.concatenate(parts); sf.write(J("voice_raw.wav"), raw.astype(np.float32), SR)
    # голос рассказчика: тёплый низ, разборчивость, плотность, лёгкая «комната»
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", J("voice_raw.wav"), "-af",
                    "highpass=f=70,equalizer=f=170:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=2,"
                    "acompressor=threshold=-22dB:ratio=2.5:attack=5:release=90:makeup=2,aecho=0.8:0.55:38|67:0.10|0.06,"
                    "alimiter=limit=0.9:level=disabled", "-ar", str(SR), J("voice.wav")], check=True)
    subprocess.run([PY, TOOLS + "words.py", J("voice.wav"), J("words.json")], check=True, capture_output=True)
    json.dump({"sent": times, "dur": t}, open(J("times.json"), "w"))
    print(f"голос: {len(times)} предложений, длина ролика {t:.2f} с")

# ---------------- 2. таймлайн 3D-сцен ----------------
def timeline():
    tm = json.load(open(J("times.json"))); S = tm["sent"]; dur = tm["dur"]; scenes = []
    scenes.append({"t0": 0.0, "t1": S[0][0], "spec": P["title"]["scene"]})
    for k, s in enumerate(P["sentences"]):
        a = S[k][0]; b = S[k + 1][0] if k + 1 < len(S) else S[k][1] + P["sentences"][k].get("pause", P.get("pause", .45))
        shots = s["shots"]; fr = [sh.get("frac", 1 / len(shots)) for sh in shots]; fr = np.cumsum(fr) / sum(fr)
        t = a
        for sh, f in zip(shots, fr):
            e = a + (b - a) * f; scenes.append({"t0": round(t, 3), "t1": round(e, 3), "spec": sh["spec"]}); t = e
    scenes.append({"t0": scenes[-1]["t1"], "t1": dur, "spec": P["ending"]["scene"]})
    json.dump({"fps": FPS, "scenes": scenes}, open(J("timeline.json"), "w"))
    return scenes, dur

def render():
    scenes, dur = timeline()
    subprocess.run(["node", os.path.join(HERE, "render3d.js"), J("timeline.json"), J("frames"), "0", str(dur)], check=True)

# ---------------- 3. типографика и эффекты ----------------
def accents_times():
    W_ = json.load(open(J("words.json")))["words"]; tm = json.load(open(J("times.json")))["sent"]
    norm = lambda w: "".join(c for c in w.lower().replace("ё", "е") if c.isalnum())
    import difflib
    acc = []
    for k, s in enumerate(P["sentences"]):
        a, b = tm[k][0] - 0.2, tm[k][1] + 0.2
        ws = [w for w in W_ if a <= w["t0"] <= b]
        for ac in s.get("accents", []):
            tgt = norm(ac["word"]); best = max(ws, key=lambda w: difflib.SequenceMatcher(None, norm(w["w"]), tgt).ratio(), default=None)
            if best: acc.append(dict(ac, t=best["t0"], k=k))
    return acc

def compose():
    import cv2
    from PIL import Image
    sys.path.insert(0, HERE); import typo
    tm = json.load(open(J("times.json"))); dur = tm["dur"]; S = tm["sent"]
    words = json.load(open(J("words.json")))["words"]; acc = accents_times(); json.dump(acc, open(J("accents.json"), "w"), ensure_ascii=False)
    scenes = json.load(open(J("timeline.json")))["scenes"]
    cuts = [s["t0"] for s in scenes[1:]]
    # субтитры: текст предложения (как на экране), время слов — из распознавания по порядку
    caps = typo.build_captions(P["sentences"], S, words, {a["word"] for a in acc if a.get("red", True)})
    W, H = 1080, 1920; N = int(dur * FPS)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-colorspace", "bt709", J("video.mp4")], stdin=subprocess.PIPE)
    vig = typo.vignette(W, H)
    for n in range(N):
        t = n / FPS
        f = cv2.imread(J("frames", f"{min(n, N - 1):05d}.jpg"))
        if f is None: f = np.zeros((H, W, 3), np.uint8)
        x = f.astype(np.float32) / 255
        # толчок камеры на ударах (2D), вспышки
        sh = sum(a.get("shake", 1) * 14 * math.exp(-(t - a["t"]) * 7) for a in acc if a.get("sfx") in ("impact", "thud") and 0 <= t - a["t"] < .7)
        if sh > .5:
            M = np.float32([[1.03, 0, -W * .015 + sh * math.sin(t * 90)], [0, 1.03, -H * .015 + sh * math.cos(t * 77)]]); x = cv2.warpAffine(x, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        x = typo.grade(x)
        for a in acc:
            if a.get("flash") and 0 <= t - a["t"] < .18: x = x + (1 - x) * (1 - (t - a["t"]) / .18) * .8
        # смазанный переход на смене сцен
        for c in cuts:
            if abs(t - c) < 0.05:
                k = 60; ker = np.ones((1, k), np.float32) / k; x = cv2.filter2D(x, -1, ker)
        x *= min(1, t / 0.6) * min(1, (dur - t) / 0.8)
        x *= vig
        img = Image.fromarray((np.clip(x[..., ::-1], 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        typo.draw(layer, t, P, S, caps, acc, dur)
        img.alpha_composite(layer)
        enc.stdin.write(np.ascontiguousarray(np.asarray(img.convert("RGB"))[..., ::-1]).tobytes())
        if n % 150 == 0: print(f"{t:.1f} с", flush=True)
    enc.stdin.close(); enc.wait(); print("видео собрано")

# ---------------- 4. звук ----------------
def mix():
    sys.path.insert(0, HERE); import sound
    tm = json.load(open(J("times.json"))); acc = json.load(open(J("accents.json"))); scenes = json.load(open(J("timeline.json")))["scenes"]
    sound.mix(J("voice.wav"), tm, acc, [s["t0"] for s in scenes[1:]], P, J("mix.wav"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", J("video.mp4"), "-i", J("mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-map_metadata", "-1", "-movflags", "+faststart", J("final.mp4")], check=True)
    print("готово:", J("final.mp4"))

if STAGE == "timeline": timeline()
if STAGE in ("all", "tts"): tts()
if STAGE in ("all", "render"): render()
if STAGE in ("all", "compose"): compose()
if STAGE in ("all", "mix"): mix()
