"""Витрина звуков в стиле референса «Comment SFX» (таймлайн монтажки), нашими цветами: клипы с реальной волной звука
едут под плейхедом, на плейхеде звук звучит, сверху — его название. Сверху призыв «Напиши “ПАК”», снизу логотип."""
import json, os
import numpy as np, soundfile as sf
SFX = "/home/user/sushi8.github.io/.claude/skills/montazh/engine/sfx_local/"
OUT = os.path.dirname(os.path.abspath(__file__))
SR = 48000
cache = {}
def snd(r):
    if r not in cache:
        x, sr = sf.read(SFX + r + ".wav"); cache[r] = x if x.ndim == 1 else x.mean(1)
    return cache[r]
V, GAP, T0, G = 600, 0.50, 0.45, 0.9      # скорость ленты px/с, микропауза между звуками, старт, громкость
CLIPS = [("Печать", "aplkey1"), ("Поп", "wbpop"), ("Тег", "tagpop"), ("Вуш", "wbwhoosh"), ("Свайп", "wbslide"),
         ("Пружина", "wbbounce"), ("Клик", "wbclick"), ("Выделение", "wbselect"), ("Блеск", "wbshimmer"), ("Капля", "fx7"),
         ("Бип", "fx2"), ("Интерфейс", "chime2"), ("Разгон", "riser"), ("Удар", "flash")]   # каждый звук — ОДИН раз
def span(x):
    """Где звук реально слышен: начало/конец по порогу −50 дБ от пика (5-мс окна)."""
    h = SR // 200; env = np.array([np.abs(x[i:i + h]).max() for i in range(0, len(x), h)])
    db = 20 * np.log10(env / env.max() + 1e-12)
    on = int(np.argmax(db > -50)); off = len(db) - int(np.argmax(db[::-1] > -50))
    return on * h, min(len(x), off * h)
items, clips = [], []
peak = max(np.abs(snd(r)).max() for _, r in CLIPS) * G
ts = T0
for i, (name, r) in enumerate(CLIPS):
    x = snd(r) * G
    a, b = span(x); d = (b - a) / SR
    items.append({"type": "sfx", "t": round(ts - a / SR, 4), "s": r, "g": G})     # слышимое начало звука = левый край клипа на плейхеде
    nb = max(3, int(d * V / 9))
    seg = np.array_split(np.abs(x[a:b]), nb)
    bars = [round(float(c.max() / peak), 3) if len(c) else 0 for c in seg]       # настоящая громкость (пик в отрезке), без подгонки
    clips.append({"ts": round(ts, 4), "d": round(d, 4), "track": i % 2, "name": name, "bars": bars})
    ts += d + GAP
DUR = round(ts + 0.6, 3)
W = lambda *ws: [[w, t] for w, t in ws]
items = [{"type": "wb", "t": 0, "end": DUR + 1},
         {"type": "btext", "t": -1, "end": DUR + 1, "y": 300, "sfx": False, "exit": "cut",
          "lines": [{"words": W(("Напиши", -1), ("“ПАК”", -1)), "size": 118, "weight": 800, "ls": -0.04, "step": 0.0},
                    {"mode": "word", "words": W(("пришлю", -1), ("ссылку", -1), ("в", -1), ("директ", -1)), "size": 52, "weight": 400, "ls": -0.02, "y": 118}]},
         {"type": "sfxtl", "t": -1, "end": DUR + 1, "v": V, "x0": 540, "knobY": 790, "trackY": [885, 1030], "labelY": 640, "labelSize": 98, "clips": clips},
         {"type": "btext", "t": -1, "end": DUR + 1, "y": 1260, "sfx": False, "exit": "cut",
          "lines": [{"words": W(("saidulaev.ai", -1)), "size": 62, "weight": 800, "ls": 0.0, "step": 0.0},
                    {"mode": "word", "words": W(("—", -1), ("ИИ-МОНТАЖ", -1), ("—", -1)), "size": 22, "weight": 600, "ls": 0.3, "y": 64}]}] + items
x = np.zeros(int(DUR * SR), np.float32)
sf.write(os.path.join(OUT, "voice.wav"), x, SR, subtype="PCM_16")
cues = {"wbColor": "#3d7ef5", "wbPill": ["#6aa6ff", "#2f6df2"], "fps": 60, "mblur": 5, "shutter": 0.5, "typeEvery": 99, "duration": DUR,
        "anchor": None, "env": [0] * int(DUR * 60 + 2), "envFps": 60, "pauses": [], "items": items}
json.dump(cues, open(os.path.join(OUT, "cues.json"), "w"), ensure_ascii=False)
print(f"длина {DUR} с, клипов {len(clips)}, звуков {sum(1 for i in items if i['type'] == 'sfx')}")
