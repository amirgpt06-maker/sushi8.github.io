"""Сценарий ролика «под голос» в стиле белого Apple-экрана (референс пользователя «монтаж Apple за 3 шага»).
Все времена — по записи (как распознано), из них вычитается OFF (убранная пауза в начале)."""
import json
import numpy as np
import soundfile as sf

OFF = 1.86
D = "/tmp/claude-0/-home-user-sushi8-github-io/e45a17fa-f666-558d-8135-60ef79d3ed2c/scratchpad/apple"
x, sr = sf.read(f"{D}/white/voice_trim.wav")
DUR = len(x) / sr
hop = sr // 60
rms = np.sqrt(np.convolve(x ** 2, np.ones(hop * 2) / (hop * 2), "same"))[::hop]
env = np.clip(rms / np.percentile(rms, 99), 0, 1.2)
T = lambda v: round(v - OFF, 3)                      # время записи -> время ролика
W = lambda *ws: [[w, T(t)] for w, t in ws]           # слова с временами
UI = "@local/ui/"
items = []
add = items.append
def sfx(t, s, g=0.7): add({"type": "sfx", "t": T(t), "s": s, "g": g})

add({"type": "wb", "t": 0, "end": DUR + 1})

# ---------- 1. «Этот ролик смонтировал не человек» — вход «камерой», волна снизу; выход — белый круг ----------
add({"type": "wave", "t": 0, "end": T(4.63), "rise": 1.0, "fall": 0.01, "h": 520, "sfx": False})
add({"type": "group", "id": "intro", "t": 0, "end": T(4.63), "origin": [540, 800], "keys": [[0, {"s": 0.12}], [0.75, {"s": 1}]]})
add({"type": "tile", "g": "intro", "t": 0, "end": T(4.63), "img": UI + "icon_shortcuts.png", "fit": "full", "w": 170, "pos": [540, 600], "exit": "cut", "sfx": False})
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
add({"type": "numcard", "t": T(6.80), "end": T(10.22), "pos": [540, 905], "w": 600, "label": "МОНТАЖЁР", "num": "5 000 ₽", "numT": T(6.82), "step": 0.06,
     "strikeT": T(8.45), "strikeDur": 0.45, "swapT": T(9.43), "num2": "0 ₽", "size": 104, "size2": 170, "exit": "circle", "exitDur": 0.45})
add({"type": "btext", "t": T(8.20), "end": T(10.10), "y": 1265, "exit": "blur", "exitDur": 0.33, "sfx": False, "lines": [
    {"mode": "word", "words": W(("Я", 8.20), ("заплатил", 8.40)), "size": 66, "weight": 400, "ls": -0.02}]})
sfx(4.68, "aplkey1", 0.6); sfx(6.80, "wbbounce", 0.7); sfx(7.16, "wbclick", 0.7); sfx(8.45, "wbslide", 0.55); sfx(9.43, "tagpop", 0.75); sfx(9.77, "wbwhoosh", 0.8)

# ---------- 3. «Вот эта анимация — ИИ» — формы слетаются и собираются в объект ----------
add({"type": "btext", "t": T(10.43), "end": T(13.03), "y": 760, "move": [[T(10.55), 330, 0.5]], "exit": "drop", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": W(("Вот", 10.43), ("эта", 10.67), ("анимация", 10.99)), "size": 100, "weight": 700, "ls": -0.04, "step": 0.04}]})
add({"type": "assemble", "t": T(10.95), "end": T(13.03), "pos": [540, 920], "w": 600, "pulseT": T(12.12), "exit": "drop", "exitDur": 0.45, "shapes": [
    {"t": T(11.05), "w": 340, "h": 124, "r": 62, "bg": "#0c0c0e", "from": [-560, 80, -35, 0.6], "to": [0, 0]},
    {"t": T(11.30), "w": 92, "bg": "#34c759", "from": [-110, -470, 0, 0.4], "to": [-102, 0], "css": "box-shadow:0 0 30px rgba(52,199,89,.7)"},
    {"t": T(11.48), "w": 40, "bg": "#ffffff", "from": [-102, 0, 0, 0], "to": [-102, 0]},
    {"t": T(11.55), "w": 18, "bg": "#0c0c0e", "from": [-102, 0, 0, 0], "to": [-102, 0]},
    {"t": T(11.40), "w": 120, "h": 16, "r": 8, "bg": "#ffffff", "from": [520, -60, 25, 0.5], "to": [38, -18]},
    {"t": T(11.52), "w": 80, "h": 16, "r": 8, "bg": "#8e8e93", "from": [520, 90, -25, 0.5], "to": [18, 20]}]})
add({"type": "pill", "t": T(12.12), "end": T(13.03), "text": "ИИ", "size": 64, "pos": [540, 1260], "exit": "drop", "exitDur": 0.45, "sfx": False})
sfx(10.43, "aplkey1", 0.6); sfx(10.95, "wbbounce", 0.6); sfx(12.12, "wbpop", 0.85); sfx(12.58, "wbwhoosh", 0.7)

# ---------- 4. «Этот переход — ИИ» — стеклянный шар прямо на фразе, на «ИИ» он растворяется в «ИИ» ----------
add({"type": "wave", "t": T(13.24), "end": T(14.66), "from": "top", "rise": 0.5, "fall": 0.01, "h": 420, "sfx": False})
add({"type": "btext", "t": T(13.32), "end": T(14.66), "y": 760, "enter": "tilt", "exit": "cut", "sfx": False, "lines": [
    {"words": W(("Этот", 13.32), ("переход", 13.68)), "size": 120, "weight": 700, "ls": -0.04, "step": 0.04}]})
add({"type": "ball", "t": T(13.78), "end": T(14.84), "fadeOut": 0.18, "x0": 1040, "x1": 540, "y": 830, "frostAt": T(14.27), "r0": 150, "r1": 1320, "sfx": False})
add({"type": "btext", "t": T(14.69), "end": T(15.38), "y": 690, "exit": "up", "exitDur": 0.33, "sfx": False, "lines": [
    {"words": W(("ИИ", 14.69)), "size": 300, "weight": 800, "ls": -0.03, "step": 0.08}]})
sfx(13.24, "wbslide", 0.55); sfx(13.78, "wbwhoosh", 0.8); sfx(14.27, "wbshimmer", 0.7); sfx(14.69, "wbpop", 0.9); sfx(15.05, "wbslide", 0.55)

# ---------- 5. «Даже звук, который ты сейчас слышишь — это ИИ» — плитка-звук, всплеск ровно на «звук» ----------
add({"type": "btext", "t": T(15.71), "end": T(20.30), "y": 760, "move": [[T(15.85), 330, 0.55]], "exit": "left", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": W(("Даже", 15.71), ("звук,", 16.19)), "size": 116, "weight": 700, "ls": -0.04, "step": 0.045},
    {"mode": "word", "words": W(("который", 16.63), ("ты", 17.03), ("сейчас", 17.23), ("слышишь —", 17.63)), "size": 58, "weight": 400, "ls": -0.02, "y": 128}]})
add({"type": "eqtile", "t": T(16.19), "end": T(20.30), "pos": [540, 935], "w": 600, "burstT": T(16.19), "exit": "left", "exitDur": 0.45})
add({"type": "btext", "t": T(19.14), "end": T(20.30), "y": 1270, "exit": "left", "exitDur": 0.45, "sfx": False, "lines": [
    {"mode": "word", "words": W(("это", 19.14)), "size": 66, "weight": 400, "ls": -0.02}]})
add({"type": "pill", "t": T(19.50), "end": T(20.30), "text": "ИИ", "size": 64, "pos": [540, 1360], "exit": "left", "exitDur": 0.45, "sfx": False})
sfx(15.71, "aplkey1", 0.6); sfx(16.19, "tagpop", 0.8); sfx(19.50, "wbpop", 0.85); sfx(19.85, "wbwhoosh", 0.8)

# ---------- 6. «Единственное, что здесь моё — голос» — тишина, затем волна точно по голосу ----------
add({"type": "btext", "t": T(21.00), "end": T(24.49), "y": 330, "exit": "drop", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": W(("Единственное,", 21.00)), "size": 100, "weight": 700, "ls": -0.04, "step": 0.035},
    {"mode": "word", "words": W(("что", 22.15), ("здесь", 22.28), ("моё —", 22.68)), "size": 64, "weight": 400, "ls": -0.02, "y": 118}]})
add({"type": "vcard", "t": T(20.90), "end": T(24.49), "pos": [540, 910], "w": 900, "h": 320, "exit": "drop", "exitDur": 0.45})
add({"type": "select", "t": T(23.46), "end": T(24.49), "text": "голос", "size": 100, "step": 0.06, "pos": [540, 1270], "exit": "drop", "exitDur": 0.45, "sfx": False})
sfx(21.00, "aplkey1", 0.6); sfx(20.90, "wbbounce", 0.45); sfx(23.46, "wbselect", 0.85); sfx(24.04, "wbwhoosh", 0.75)

# ---------- 7. «Всё это — один промпт…» — смена виджета на каждом ударном слоге ----------
cuts = [24.80, 25.08, 25.67, 26.13, 27.13, 27.74, 28.34, 29.00, 29.80, 30.10, 30.33, 31.02, 31.85, 32.22]
pics = [("Weather Large.png", "linear-gradient(160deg,#ffffff,#d8e6ff 55%,#8fb4ff)"),
        ("icon_photos.png|46", "linear-gradient(160deg,#ffffff,#ffe6ef 55%,#ffc2d6)"),
        ("Calendar small.png", "linear-gradient(160deg,#ffffff,#ffe8e6 55%,#ffbdb6)"),
        ("icon_shortcuts.png|46", "linear-gradient(160deg,#ffffff,#e9e4ff 55%,#c2b4ff)"),
        ("MusicPlayer.jpg", "linear-gradient(160deg,#ffffff,#ece9f6 55%,#cfc6ea)"),
        ("FaceID3.png", "linear-gradient(160deg,#ffffff,#ecebef 60%,#d3cddd)"),
        ("On.png", "linear-gradient(160deg,#ffffff,#e3f8e8 55%,#a8e8b8)"),
        ("Battery10.png", "linear-gradient(160deg,#ffffff,#e3f8e8 55%,#a8e8b8)"),
        ("icon_appstore.png|46", "linear-gradient(160deg,#ffffff,#dde9ff 55%,#9cc0ff)"),
        ("Keyboard1.png", "linear-gradient(160deg,#ffffff,#eeeef3 60%,#d4d4dc)"),
        ("icon_facetime.png|46", "linear-gradient(160deg,#ffffff,#e3f8e8 55%,#a8e8b8)"),
        ("Photos Large.png", "linear-gradient(160deg,#ffffff,#fff0e0 55%,#ffd2a6)"),
        ("Volume.jpg", "linear-gradient(160deg,#ffffff,#ffe6ef 55%,#f5c4d4)"),
        ("icon_calendar.png|46", "linear-gradient(160deg,#ffffff,#ffe8e6 55%,#ffbdb6)")]
add({"type": "wave", "t": T(24.75), "end": T(33.06), "rise": 0.9, "fall": 0.45, "h": 340, "sfx": False})
add({"type": "tile", "t": T(cuts[0]), "end": T(33.06), "pos": [540, 985], "w": 600, "img": UI + pics[0][0], "bg": pics[0][1],
     "swap": [[T(c), UI + p, bg] for c, (p, bg) in zip(cuts[1:], pics[1:])], "exit": "circle", "exitDur": 0.45, "sfx": False})
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
sfx(24.80, "wbbounce", 0.65); sfx(26.04, "wbpop", 0.85); sfx(31.70, "wbselect", 0.75); sfx(32.61, "wbwhoosh", 0.8)

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

pauses = [[T(a), T(b)] for a, b in [(12.58, 13.32), (18.09, 19.14), (19.85, 21.00), (24.04, 24.80), (37.41, OFF + DUR)]]
cues = {"fps": 60, "mblur": 5, "shutter": 0.5, "duration": round(DUR, 4), "anchor": None, "typeEvery": 99,
        "env": [round(float(v), 3) for v in env], "envFps": 60, "pauses": pauses, "items": items}
json.dump(cues, open(f"{D}/white/cues.json", "w"), ensure_ascii=False)
print(f"длина {DUR:.3f} с, элементов {len(items)}, звуков {sum(1 for i in items if i['type'] == 'sfx')}")
