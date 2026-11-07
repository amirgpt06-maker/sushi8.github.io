"""Сценарий ролика «под голос» в стиле белого Apple-экрана (референс пользователя «монтаж Apple за 3 шага»).
Все времена — по записи (как распознано), из них вычитается OFF (убранная пауза в начале)."""
import json
import numpy as np
import soundfile as sf

OFF = 1.86
D = "/tmp/claude-0/-home-user-sushi8-github-io/e45a17fa-f666-558d-8135-60ef79d3ed2c/scratchpad/apple"
x, sr = sf.read(f"{D}/white/voice_trim2.wav")      # в паузе после «слышишь» вставлено GAP с тишины (просьба пользователя)
DUR = len(x) / sr
hop = sr // 60
rms = np.sqrt(np.convolve(x ** 2, np.ones(hop * 2) / (hop * 2), "same"))[::hop]
env = np.clip(rms / np.percentile(rms, 99), 0, 1.2)
SPLIT, GAP = 18.50, 1.6                              # пауза после «слышишь —» удлинена на GAP: место для звуков
T = lambda v: round(v - OFF + (GAP if v >= SPLIT else 0), 3)   # время записи -> время ролика
W = lambda *ws: [[w, T(t)] for w, t in ws]           # слова с временами
UI = "@local/ui/"
items = []
add = items.append
def sfx(t, s, g=0.7): add({"type": "sfx", "t": T(t), "s": s, "g": g})

add({"type": "wb", "t": 0, "end": DUR + 1})

# ---------- 1. «Этот ролик смонтировал не человек» — вход «камерой», волна снизу; выход — белый круг ----------
add({"type": "wave", "t": 0, "end": T(4.63), "rise": 1.0, "fall": 0.01, "h": 520, "sfx": False})
add({"type": "group", "id": "intro", "t": 0, "end": T(4.63), "origin": [540, 800], "keys": [[0, {"s": 0.12}], [0.75, {"s": 1}]]})
import math
def spark(size=170, rays=12):
    c = size / 2; out = []
    for k in range(rays):
        a = math.radians(k * 360 / rays + 8); L = size * (0.33 if k % 2 else 0.27) * (1 + 0.06 * math.sin(k * 2.3))
        out.append(f'<line x1="{c:.1f}" y1="{c:.1f}" x2="{c + L * math.cos(a):.1f}" y2="{c + L * math.sin(a):.1f}" stroke="#fff" stroke-width="{size * 0.075:.1f}" stroke-linecap="round"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">' + "".join(out) + "</svg>"
add({"type": "tile", "g": "intro", "t": 0, "end": T(4.63), "html": spark(), "bg": "#d97757", "fit": "full", "w": 170, "pos": [540, 600], "exit": "cut", "sfx": False})
add({"type": "btext", "g": "intro", "t": T(2.02), "end": T(4.63), "y": 700, "exit": "cut", "sfx": False, "lines": [
    {"words": W(("Этот", 2.02), ("ролик", 2.38)), "size": 124, "weight": 700, "ls": -0.04, "step": 0.045}]})
add({"type": "pill", "g": "intro", "t": T(2.74), "end": T(4.63), "text": "смонтировал", "size": 42, "pos": [540, 850], "exit": "cut", "sfx": False})
add({"type": "btext", "g": "intro", "t": T(3.46), "end": T(4.63), "y": 935, "exit": "cut", "sfx": False, "lines": [
    {"mode": "word", "words": W(("не", 3.46), ("человек", 3.66)), "size": 66, "weight": 400, "ls": -0.02}]})
add({"type": "circle", "t": T(4.17), "end": T(4.90), "pos": [540, 2100], "dur": 0.46, "sfx": False})
sfx(2.02, "aplkey1", 0.6); sfx(2.74, "wbpop", 0.8); sfx(3.46, "wbclick", 0.55); sfx(4.17, "wbwhoosh", 0.8)

# ---------- 2. «Монтажёр взял бы за такое от пяти тысяч. Я заплатил ноль» — виджет с числом ----------
add({"type": "btext", "t": T(4.68), "end": T(10.10), "y": 760, "move": [[T(6.25), 330, 0.7]], "exit": "up", "exitDur": 0.33, "sfx": False, "lines": [
    {"words": W(("Монтажёр", 4.68), ("взял", 5.44), ("бы", 5.76)), "size": 104, "weight": 700, "ls": -0.04, "step": 0.04},
    {"mode": "word", "words": W(("за", 5.96), ("такое", 6.12), ("от", 6.60), ("пяти", 6.80), ("тысяч", 7.16)), "size": 60, "weight": 400, "ls": -0.02, "y": 118}]})
add({"type": "wave", "t": T(6.80), "end": T(10.22), "rise": 0.9, "fall": 0.45, "h": 380, "sfx": False})
add({"type": "numcard", "t": T(6.80), "end": T(10.22), "pos": [540, 905], "w": 600, "label": "МОНТАЖЁР", "labelColor": "#2f6df2", "strikeColor": "#2f6df2", "num": "5 000 ₽", "numT": T(6.82), "step": 0.06,
     "strikeT": T(8.45), "strikeDur": 0.45, "swapT": T(9.43), "num2": "0 ₽", "size": 104, "size2": 170, "exit": "circle", "exitDur": 0.45})
add({"type": "btext", "t": T(8.20), "end": T(10.10), "y": 1265, "exit": "blur", "exitDur": 0.33, "sfx": False, "lines": [
    {"mode": "word", "words": W(("Я", 8.20), ("заплатил", 8.40)), "size": 66, "weight": 400, "ls": -0.02}]})
sfx(4.68, "aplkey1", 0.6); sfx(6.80, "wbbounce", 0.7); sfx(7.16, "wbclick", 0.7); sfx(8.45, "wbslide", 0.55); sfx(9.43, "tagpop", 0.75); sfx(9.77, "wbwhoosh", 0.8)

# ---------- 3. «Вот эта анимация — ИИ» — формы слетаются и собираются в объект ----------
add({"type": "btext", "t": T(10.43), "end": T(13.03), "y": 760, "move": [[T(10.55), 330, 0.5]], "exit": "drop", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": W(("Вот", 10.43), ("эта", 10.67), ("анимация", 10.99)), "size": 100, "weight": 700, "ls": -0.04, "step": 0.04}]})
add({"type": "follow", "t": T(10.95), "end": T(13.03), "pos": [540, 920], "w": 600, "avatarEmoji": "👤",
     "name": "saidulaev.vibe", "sub": "Амирхан | Вайбкодинг", "btnT": T(11.05), "cardT": T(11.40), "pressT": T(12.12), "exit": "drop", "exitDur": 0.45})
add({"type": "pill", "t": T(12.12), "end": T(13.03), "text": "ИИ", "size": 64, "pos": [540, 1260], "exit": "drop", "exitDur": 0.45, "sfx": False})
sfx(10.43, "aplkey1", 0.6); sfx(10.95, "wbbounce", 0.6); sfx(11.05, "wbpop", 0.5); sfx(11.40, "wbbounce", 0.45); sfx(12.12, "wbclick", 0.9); sfx(12.18, "wbpop", 0.6); sfx(12.58, "wbwhoosh", 0.7)

# ---------- 4. «Этот переход — ИИ» — стеклянный шар прямо на фразе, на «ИИ» он растворяется в «ИИ» ----------
add({"type": "wave", "t": T(13.24), "end": T(14.80), "from": "top", "rise": 0.5, "fall": 0.3, "h": 420, "sfx": False})
add({"type": "btext", "t": T(13.32), "end": T(14.72), "y": 760, "enter": "tilt", "exit": "blur", "exitDur": 0.32, "sfx": False, "lines": [
    {"words": W(("Этот", 13.32), ("переход", 13.68)), "size": 120, "weight": 700, "ls": -0.04, "step": 0.04}]})
# стеклянная капля как в референсе: выныривает точкой под фразой, с пружиной надувается и всплывает к центру, форма живая
# (резина: сплющивается, по краю волнится, донышко приплюснуто), внутри — увеличение и зеркальная полоса у обода,
# мутнеет в голубо-сиреневое «яйцо», белеет и раздувается на весь экран — «ИИ» проявляется внутри неё
add({"type": "ball", "pop": True, "t": T(13.90), "end": T(15.12), "pos": [540, 825], "r": 245, "rise": 70, "frostAt": T(14.30),
     "whiteAt": T(14.55), "grow": 1550, "whiteMax": 0.8, "fadeOut": 0.24, "sfx": False})
add({"type": "circle", "t": T(14.72), "end": T(15.40), "pos": [540, 825], "r0": 200, "dur": 0.42, "sfx": False})
add({"type": "btext", "t": T(14.69), "end": T(15.38), "y": 690, "exit": "up", "exitDur": 0.33, "sfx": False, "lines": [
    {"words": W(("ИИ", 14.69)), "size": 300, "weight": 800, "ls": -0.03, "step": 0.08}]})
sfx(13.24, "wbslide", 0.55); sfx(13.86, "wbwhoosh", 0.6); sfx(13.92, "fx7", 0.55); sfx(14.30, "wbshimmer", 0.7); sfx(14.69, "wbpop", 0.9); sfx(15.05, "wbslide", 0.55)

# ---------- 5. «Даже звук, который ты сейчас слышишь — это ИИ» — плитка-звук, всплеск ровно на «звук» ----------
add({"type": "btext", "t": T(15.71), "end": T(20.30), "y": 760, "move": [[T(17.90), 330, 0.5]], "exit": "left", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": W(("Даже", 15.71), ("звук,", 16.19)), "size": 116, "weight": 700, "ls": -0.04, "step": 0.045},
    {"mode": "word", "words": W(("который", 16.63), ("ты", 17.03), ("сейчас", 17.23), ("слышишь —", 17.63)), "size": 58, "weight": 400, "ls": -0.02, "y": 128}]})
# пауза диктора удлинена: ~2.6 с «звукового шоу» — пульт 3×3, каждая подушечка нажимается ровно на своём звуке:
# ритмичная фраза из UI-звуков -> разгон (riser + ускоряющаяся дробь по кругу, плитка подрастает и светится) -> удар (все разом)
# -> короткая тишина -> «это ИИ»
def sfxm(t, s_, g): add({"type": "sfx", "t": round(t, 3), "s": s_, "g": g})
P0 = T(18.05)                                        # конец «слышишь»
groove = [(0.22, "fx2", 0, .85), (0.33, "fx1", 4, .75), (0.44, "fx7", 8, .85), (0.66, "fx5", 2, .8), (0.77, "fx3", 6, .8),
          (0.88, "fx6", 1, .8), (0.99, "fx8", 3, .7), (1.10, "chime2", 5, .75)]
roll, tt, dt = [], 1.22, 0.14
order = [0, 1, 2, 5, 8, 7, 6, 3, 4, 0, 2, 8, 6, 4]
while tt < 2.30:
    roll.append(tt); tt += dt; dt = max(0.05, dt * 0.86)
IMP = P0 + 2.38
hits = [[round(P0 + a, 3), i_, 1] for a, _, i_, _ in groove] + [[round(P0 + a, 3), order[k % len(order)], 0.8] for k, a in enumerate(roll)] + [[round(IMP, 3), -1, 1]]
add({"type": "pads", "t": round(P0 + 0.01, 3), "end": T(20.30), "pos": [540, 930], "w": 600, "exit": "left", "exitDur": 0.45,
     "rise": [round(P0 + 1.15, 3), round(IMP, 3)], "hits": hits})
sfxm(P0 + 0.01, "wbpop", 0.8)
for a, s_, _, g in groove: sfxm(P0 + a, s_, g)
sfxm(P0 + 1.12, "riser", 0.75)
for k, a in enumerate(roll): sfxm(P0 + a, "tick" if k % 2 else "fx1", round(0.35 + 0.35 * k / max(1, len(roll) - 1), 2))
sfxm(IMP, "flash", 0.95); sfxm(IMP, "chime5", 0.6); sfxm(IMP + 0.02, "wbbounce", 0.5)
add({"type": "btext", "t": T(19.14), "end": T(20.30), "y": 1270, "exit": "left", "exitDur": 0.45, "sfx": False, "lines": [
    {"mode": "word", "words": W(("это", 19.14)), "size": 66, "weight": 400, "ls": -0.02}]})
add({"type": "pill", "t": T(19.50), "end": T(20.30), "text": "ИИ", "size": 64, "pos": [540, 1360], "exit": "left", "exitDur": 0.45, "sfx": False})
sfx(15.71, "aplkey1", 0.6); sfx(16.19, "tagpop", 0.5); sfx(19.50, "wbpop", 0.85); sfx(19.85, "wbwhoosh", 0.8)

# ---------- 6. «Единственное, что здесь моё — голос» — тишина, затем волна точно по голосу ----------
add({"type": "btext", "t": T(21.00), "end": T(24.49), "y": 330, "exit": "drop", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": W(("Единственное,", 21.00)), "size": 100, "weight": 700, "ls": -0.04, "step": 0.035},
    {"mode": "word", "words": W(("что", 22.15), ("здесь", 22.28), ("моё —", 22.68)), "size": 64, "weight": 400, "ls": -0.02, "y": 118}]})
add({"type": "vcard", "t": T(20.90), "end": T(24.49), "pos": [540, 910], "w": 900, "h": 320, "dot": "#2f6df2", "exit": "drop", "exitDur": 0.45})
add({"type": "select", "t": T(23.46), "end": T(24.49), "text": "голос", "size": 100, "step": 0.06, "pos": [540, 1270], "exit": "drop", "exitDur": 0.45, "sfx": False})
sfx(21.00, "aplkey1", 0.6); sfx(20.90, "wbbounce", 0.45); sfx(23.46, "wbselect", 0.85); sfx(24.04, "wbwhoosh", 0.75)

# ---------- 7. «Всё это — один промпт…» — смена виджета на каждом ударном слоге ----------
add({"type": "wave", "t": T(24.75), "end": T(33.06), "rise": 0.9, "fall": 0.45, "h": 300, "sfx": False})
add({"type": "prompt", "t": T(24.85), "end": T(29.80), "pos": [540, 840], "w": 900, "h": 300, "size": 44,
     "text": "Смонтируй ролик под мой голос в стиле Apple: текст по словам, переходы, звуки",
     "typeT": T(24.95), "typeEnd": T(26.00), "sendT": T(26.04), "exit": "up", "exitDur": 0.35,
     "chips": [{"text": "голос", "t": T(27.04), "checkT": T(28.40)}, {"text": "стиль", "t": T(27.25), "checkT": T(28.58)},
               {"text": "звуки", "t": T(27.50), "checkT": T(28.76)}, {"text": "переходы", "t": T(27.75), "checkT": T(28.94)}]})
TH = "file://" + D + "/white/thumbs/"
add({"type": "reels", "t": T(29.90), "end": T(33.06), "pos": [540, 1000], "exit": "left", "exitDur": 0.45,
     "items": [{"img": TH + f"r{i}.jpg", "t": T(t)} for i, t in enumerate([29.94, 30.34, 30.62, 31.02])]})
add({"type": "btext", "t": T(24.80), "end": T(26.95), "y": 330, "exit": "blur", "exitDur": 0.25, "sfx": False, "lines": [
    {"words": W(("Всё", 24.80), ("это —", 25.12), ("один", 25.64)), "size": 96, "weight": 700, "ls": -0.04, "step": 0.04}]})
add({"type": "pill", "t": T(26.04), "end": T(26.95), "text": "промпт", "size": 54, "pos": [540, 452], "exit": "blur", "exitDur": 0.25, "sfx": False})
add({"type": "btext", "t": T(27.04), "end": T(28.25), "y": 330, "exit": "blur", "exitDur": 0.2, "sfx": False, "lines": [
    {"words": W(("Я", 27.04), ("его", 27.20), ("собрал,", 27.52)), "size": 96, "weight": 700, "ls": -0.04, "step": 0.04}]})
add({"type": "btext", "t": T(28.30), "end": T(29.40), "y": 330, "exit": "blur", "exitDur": 0.2, "sfx": False, "lines": [
    {"words": W(("протестировал,", 28.30)), "size": 96, "weight": 700, "ls": -0.04, "step": 0.035}]})
add({"type": "btext", "t": T(29.45), "end": T(31.70), "y": 300, "exit": "blur", "exitDur": 0.2, "sfx": False, "lines": [
    {"words": W(("и", 29.45), ("теперь", 29.54), ("делаю", 29.94), ("так", 30.34)), "size": 84, "weight": 700, "ls": -0.04, "step": 0.035},
    {"words": W(("любые", 30.62), ("ролики.", 31.02)), "size": 84, "weight": 700, "ls": -0.04, "step": 0.035, "y": 100}]})
add({"type": "select", "t": T(31.70), "end": T(33.06), "text": "Хочешь так же?", "size": 82, "step": 0.045, "pos": [540, 380], "exit": "erase", "eraseDur": 0.4, "sfx": False})
sfx(24.85, "wbbounce", 0.65); sfx(26.04, "wbclick", 0.85); sfx(26.10, "wbpop", 0.6)
for t in (27.04, 27.25, 27.50, 27.75): sfx(t, "fx1", 0.45)
for t in (28.40, 28.58, 28.76, 28.94): sfx(t, "fx5", 0.5)
sfx(29.45, "wbslide", 0.5)
for t in (29.94, 30.34, 30.62, 31.02): sfx(t, "wbbounce", 0.45)
sfx(31.70, "wbselect", 0.75); sfx(32.61, "wbwhoosh", 0.8)

# ---------- 8. «Напиши ЭППЛ в комментариях — я пришлю тебе, как это повторить» ----------
add({"type": "btext", "t": T(33.08), "end": T(37.91), "y": 420, "exit": "blur", "exitDur": 0.5, "sfx": False, "lines": [
    {"mode": "word", "words": W(("Напиши", 33.08)), "size": 66, "weight": 400, "ls": -0.02},
    {"words": W(("ЭППЛ", 33.56)), "size": 240, "weight": 800, "ls": -0.03, "step": 0.07, "y": 80},
    {"mode": "word", "words": W(("в", 33.92), ("комментариях", 34.04)), "size": 66, "weight": 400, "ls": -0.02, "y": 360}]})
add({"type": "arrow", "t": T(34.55), "end": T(37.91), "pos": [540, 980], "exit": "blur", "exitDur": 0.5})
add({"type": "dock2", "t": T(35.13), "end": T(37.91), "pos": [540, 1250], "img": UI + "photo_2025-08-02_14-36-27-Photoroom.png",
     "words": W(("я", 35.13), ("пришлю", 35.29), ("тебе,", 35.77)),
     "swap": {"t": T(36.37), "words": W(("как", 36.37), ("это", 36.65), ("повторить", 36.89)), "color": "#1f6ef5"}, "scale": 1.5, "exit": "blur", "exitDur": 0.5})
sfx(33.08, "aplkey1", 0.55); sfx(33.56, "tagpop", 0.9); sfx(35.13, "wbbounce", 0.65); sfx(36.37, "wbclick", 0.8); sfx(37.41, "wbslide", 0.5)

pauses = [[T(a), T(b)] for a, b in [(12.58, 13.32), (19.85, 21.00), (24.04, 24.80), (37.41, OFF + DUR)]]
cues = {"wbColor": "#3d7ef5", "wbPill": ["#6aa6ff", "#2f6df2"], "fps": 60, "mblur": 5, "shutter": 0.5, "duration": round(DUR, 4), "anchor": None, "typeEvery": 99,
        "env": [round(float(v), 3) for v in env], "envFps": 60, "pauses": pauses, "items": items}
json.dump(cues, open(f"{D}/white/cues.json", "w"), ensure_ascii=False)
print(f"длина {DUR:.3f} с, элементов {len(items)}, звуков {sum(1 for i in items if i['type'] == 'sfx')}")
