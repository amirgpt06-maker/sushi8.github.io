"""Витрина звуков в стиле референса «Comment SFX» (таймлайн монтажки), нашими цветами: клипы с реальной волной звука
едут под плейхедом, на плейхеде звук звучит, сверху — его название. Сверху призыв «Напиши “ПАК”», снизу логотип."""
import json, os
import numpy as np, soundfile as sf
SFX = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/sfx_local/"
OUT = os.path.dirname(os.path.abspath(__file__))
SR = 48000
CLIPS = [  # название, [(роль, сдвиг, громкость)], длительность показа
    ("Печать",    [("aplkey1", 0, .8), ("aplkey2", .2, .75), ("aplkey3", .4, .8), ("aplkey4", .58, .85)], 1.5),
    ("Поп",       [("wbpop", 0, .9), ("wbpop", .42, .75)], 1.5),
    ("Тег",       [("tagpop", 0, .9)], 1.5),
    ("Вуш",       [("wbwhoosh", 0, .95)], 1.5),
    ("Свайп",     [("wbslide", 0, .9), ("wbslide", .48, .75)], 1.5),
    ("Пружина",   [("wbbounce", 0, .95)], 1.5),
    ("Клик",      [("wbclick", 0, .95), ("wbclick", .38, .75)], 1.5),
    ("Выделение", [("wbselect", 0, .9), ("wbselect", .3, .7)], 1.5),
    ("Блеск",     [("wbshimmer", 0, .9)], 1.5),
    ("Капля",     [("fx7", 0, .95), ("fx7", .32, .75)], 1.5),
    ("Бип-бип",   [("fx2", 0, .85), ("fx1", .14, .75), ("fx5", .28, .85), ("fx3", .42, .8)], 1.5),
    ("Интерфейс", [("chime2", 0, .9)], 1.5),
    ("Разгон",    [("riser", 0, 1.05)], 1.75),
    ("Удар",      [("flash", 0, 1.3), ("chime5", 0, .75)], 1.6),
]
STEP, T0 = 1.15, 0.30
cache = {}
def snd(r):
    if r not in cache:
        x, sr = sf.read(SFX + r + ".wav"); cache[r] = x if x.ndim == 1 else x.mean(1)
    return cache[r]
items, clips = [], []
rng = np.random.default_rng(7)
for i, (name, hits, d) in enumerate(CLIPS):
    ts = round(T0 + i * STEP, 3)
    buf = np.zeros(int(d * SR))
    for r, off, g in hits:
        s = snd(r) * g; a = int(off * SR); n = min(len(s), len(buf) - a)
        if n > 0: buf[a:a + n] += s[:n]
        items.append({"type": "sfx", "t": round(ts + off, 3), "s": r, "g": g})
    nb = int((d * 290 - 44) / 11)
    env = np.array([np.abs(c).max() if len(c) else 0 for c in np.array_split(buf, nb)])
    env = np.maximum(env, np.convolve(env, [0.5, 0.8, 1, 0.8, 0.5], "same") / 3)   # хвосты звука шире, волна плотнее
    env = (env / (env.max() + 1e-9)) ** 0.45
    tex = rng.uniform(0.55, 1.0, nb) * (0.75 + 0.25 * np.abs(np.sin(np.arange(nb) * 1.3)))
    bars = np.clip((0.26 + 0.74 * env) * tex, 0.12, 1)
    clips.append({"ts": ts, "d": d, "track": i % 2, "name": name, "bars": [round(float(b), 3) for b in bars]})
DUR = round(T0 + len(CLIPS) * STEP + 0.75, 3)
W = lambda *ws: [[w, t] for w, t in ws]
items = [{"type": "wb", "t": 0, "end": DUR + 1},
         {"type": "btext", "t": -1, "end": DUR + 1, "y": 300, "sfx": False, "exit": "cut",
          "lines": [{"words": W(("Напиши", -1), ("“ПАК”", -1)), "size": 118, "weight": 800, "ls": -0.04, "step": 0.0},
                    {"mode": "word", "words": W(("пришлю", -1), ("ссылку", -1), ("в", -1), ("директ", -1)), "size": 52, "weight": 400, "ls": -0.02, "y": 118}]},
         {"type": "sfxtl", "t": -1, "end": DUR + 1, "v": 290, "x0": 540, "knobY": 790, "trackY": [885, 1030], "labelY": 640, "labelSize": 98, "clips": clips},
         {"type": "btext", "t": -1, "end": DUR + 1, "y": 1260, "sfx": False, "exit": "cut",
          "lines": [{"words": W(("saidulaev.ai", -1)), "size": 92, "weight": 800, "ls": 0.0, "step": 0.0},
                    {"mode": "word", "words": W(("—", -1), ("ИИ-МОНТАЖ", -1), ("—", -1)), "size": 30, "weight": 600, "ls": 0.3, "y": 92}]}] + items
x = np.zeros(int(DUR * SR), np.float32)
sf.write(os.path.join(OUT, "voice.wav"), x, SR, subtype="PCM_16")
cues = {"wbColor": "#3d7ef5", "wbPill": ["#6aa6ff", "#2f6df2"], "fps": 60, "mblur": 5, "shutter": 0.5, "typeEvery": 99, "duration": DUR,
        "anchor": None, "env": [0] * int(DUR * 60 + 2), "envFps": 60, "pauses": [], "items": items}
json.dump(cues, open(os.path.join(OUT, "cues.json"), "w"), ensure_ascii=False)
print(f"длина {DUR} с, клипов {len(clips)}, звуков {sum(1 for i in items if i['type'] == 'sfx')}")
