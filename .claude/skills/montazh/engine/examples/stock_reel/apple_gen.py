"""Белые Apple-сцены рилса «такси» для движка montazh (engine.html): времена — время ролика (паузы по краям уже срезаны).
Три белых блока: 9.36–14.78 («А нейросетями…», промпты), 21.90–35.70 («Адрес для ИИ», шаги 1-2-3), 38.90–41.70 («Подпишись»)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
LT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../local/taxi/")   # картинки сцены (engine/local, в git не кладём)
items = []; add = items.append
def sfx(t, s, g=0.7): add({"type": "sfx", "t": round(t, 3), "s": s, "g": g})
def typing(text, t0, t1, g=0.55):
    """щелчок на начало слова и дальше раз в 3 буквы (правило пользователя), время буквы — равномерно на [t0, t1]"""
    n = len(text); j = k = 0
    for i, ch in enumerate(text):
        if not ch.isalnum(): j = 0; continue
        if j % 3 == 0: sfx(t0 + (t1 - t0) * i / max(1, n - 1), "aplkey" + str(1 + k % 4), g); k += 1
        j += 1
def num_tile(n, t, end, y=330, exit_="circle"):
    add({"type": "tile", "t": t, "end": end, "pos": [540, y], "w": 190, "fit": "full", "bg": "#1d1d1f", "exit": exit_, "exitDur": 0.4, "sfx": False,
         "html": f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:SF;font-weight:800;font-size:128px;color:#FFD60A;letter-spacing:-4px">{n}</div>'})
def photo(name): return f'<div style="width:100%;height:100%;background:url(file://{LT}{name}) center/cover"></div>'
PIN = ('<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center"><svg width="104" height="132" viewBox="0 0 24 31">'
       '<path d="M12 1a10 10 0 0 0-10 10c0 7.5 10 19 10 19s10-11.5 10-19A10 10 0 0 0 12 1z" fill="#FFD60A"/><circle cx="12" cy="11" r="4" fill="#1d1d1f"/></svg></div>')
SPARK = '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:SF;font-size:96px;color:#FFD60A">✦</div>'

# ===================== Блок 1: «А нейросетями так пользуются почти все» =====================
add({"type": "wb", "t": 9.36, "end": 14.79})
add({"type": "wave", "t": 9.36, "end": 12.42, "rise": 0.9, "fall": 0.4, "h": 420, "sfx": False})
add({"type": "group", "id": "b1", "t": 9.36, "end": 12.42, "origin": [540, 820], "keys": [[9.36, {"s": 0.12}], [10.08, {"s": 1}]]})
add({"type": "btext", "g": "b1", "t": 9.39, "end": 12.42, "y": 470, "exit": "drop", "exitDur": 0.4, "sfx": False, "lines": [
    {"words": [["А", 9.39], ["нейросетями", 9.52]], "size": 100, "weight": 700, "ls": -0.04, "step": 0.034},
    {"mode": "word", "words": [["так", 10.36], ["пользуются", 10.56]], "size": 62, "weight": 400, "ls": -0.02, "y": 122}]})
add({"type": "reels", "g": "b1", "t": 10.40, "end": 12.42, "pos": [540, 1030], "cw": 250, "ch": 445, "gap": 30, "exit": "drop", "exitDur": 0.4,
     "items": [{"img": f"file://{LT}chat{i}.png", "t": t} for i, t in enumerate([10.42, 10.62, 10.82])]})
add({"type": "pill", "g": "b1", "t": 11.20, "end": 12.42, "text": "почти все", "size": 66, "pos": [540, 1390], "exit": "drop", "exitDur": 0.4, "sfx": False})
sfx(9.36, "wbwhoosh", 0.8); sfx(9.39, "aplkey1", 0.6); sfx(10.36, "aplkey2", 0.45)
for t in (10.42, 10.62, 10.82): sfx(t, "wbbounce", 0.45)
sfx(11.20, "wbpop", 0.85); sfx(12.20, "wbslide", 0.55)

# ---- промпты: «Сделай сайт. Сделай монтаж» ----
add({"type": "wave", "t": 12.32, "end": 14.79, "from": "top", "rise": 0.5, "fall": 0.3, "h": 250, "sfx": False})
add({"type": "tile", "t": 12.40, "end": 14.79, "pos": [540, 560], "w": 170, "fit": "full", "bg": "#1d1d1f", "html": SPARK, "exit": "cut", "sfx": False})
add({"type": "prompt", "t": 12.40, "end": 13.64, "pos": [540, 900], "w": 900, "h": 300, "size": 60, "placeholder": "Сообщение…", "color": "#1d1d1f",
     "text": "Сделай сайт", "typeT": 12.49, "typeEnd": 13.30, "sendT": 13.45, "exit": "up", "exitDur": 0.3})
add({"type": "prompt", "t": 13.64, "end": 14.79, "pos": [540, 900], "w": 900, "h": 300, "size": 60, "placeholder": "Сообщение…", "color": "#1d1d1f",
     "text": "Сделай монтаж", "typeT": 13.68, "typeEnd": 14.40, "sendT": 14.50, "exit": "cut"})
sfx(12.32, "wbslide", 0.5); sfx(12.40, "wbbounce", 0.6); typing("Сделай сайт", 12.49, 13.30); sfx(13.45, "wbclick", 0.85); sfx(13.50, "wbpop", 0.55)
sfx(13.62, "wbslide", 0.45); sfx(13.64, "wbbounce", 0.5); typing("Сделай монтаж", 13.68, 14.40); sfx(14.50, "wbclick", 0.85); sfx(14.55, "wbpop", 0.55)

# ===================== Блок 2: «Адрес для ИИ — это…», шаги 1-2-3 =====================
add({"type": "wb", "t": 21.90, "end": 35.71})
# --- «Адрес для ИИ это» ---
add({"type": "wave", "t": 21.90, "end": 23.80, "rise": 0.9, "fall": 0.4, "h": 400, "sfx": False})
add({"type": "group", "id": "f1", "t": 21.90, "end": 23.82, "origin": [540, 860], "keys": [[21.90, {"s": 0.12}], [22.62, {"s": 1}]]})
add({"type": "tile", "g": "f1", "t": 21.90, "end": 23.82, "pos": [540, 450], "w": 210, "fit": "full", "bg": "#1d1d1f", "html": PIN, "exit": "cut", "sfx": False})
add({"type": "select", "g": "f1", "t": 21.94, "end": 23.82, "text": "Адрес", "size": 150, "step": 0.08, "pos": [540, 760], "exit": "cut", "sfx": False})
add({"type": "btext", "g": "f1", "t": 22.46, "end": 23.82, "y": 930, "exit": "cut", "sfx": False, "lines": [
    {"words": [["для", 22.46], ["ИИ", 22.70]], "size": 130, "weight": 800, "ls": -0.04, "step": 0.04}]})
add({"type": "btext", "g": "f1", "t": 23.26, "end": 23.82, "y": 1135, "exit": "cut", "sfx": False, "lines": [
    {"mode": "word", "words": [["это", 23.26]], "size": 66, "weight": 400, "ls": -0.02}]})
# стеклянная капля: выныривает под фразой, мутнеет, белеет и раздувается на весь экран — внутри проявляется шаг 1
add({"type": "ball", "pop": True, "t": 23.34, "end": 24.18, "pos": [540, 880], "r": 250, "rise": 70, "frostAt": 23.62, "whiteAt": 23.80,
     "grow": 1550, "whiteMax": 0.8, "fadeOut": 0.24, "sfx": False})
add({"type": "circle", "t": 23.80, "end": 24.25, "pos": [540, 880], "r0": 200, "dur": 0.42, "sfx": False})
sfx(21.90, "wbwhoosh", 0.8); sfx(21.94, "wbselect", 0.85); typing("Адрес", 22.04, 22.36, 0.5); sfx(22.46, "aplkey2", 0.6); sfx(23.26, "aplkey3", 0.45)
sfx(23.30, "wbwhoosh", 0.6); sfx(23.36, "fx7", 0.55); sfx(23.62, "wbshimmer", 0.7)

# --- шаг 1: «Первое — для кого. Сайт для общепита» ---
num_tile(1, 23.92, 27.12)
add({"type": "btext", "t": 23.96, "end": 27.12, "y": 465, "exit": "drop", "exitDur": 0.4, "sfx": False, "lines": [
    {"mode": "word", "words": [["Первое —", 23.96]], "size": 64, "weight": 500, "ls": -0.02, "color": "#6e6e73"}]})
add({"type": "select", "t": 24.40, "end": 27.12, "text": "для кого", "size": 110, "step": 0.075, "pos": [540, 640], "exit": "drop", "exitDur": 0.4, "sfx": False})
add({"type": "btext", "t": 25.64, "end": 27.12, "y": 800, "exit": "drop", "exitDur": 0.4, "sfx": False, "lines": [
    {"words": [["Сайт", 25.64], ["для", 26.00], ["общепита", 26.20]], "size": 92, "weight": 700, "ls": -0.04, "step": 0.034}]})
add({"type": "tile", "t": 25.64, "end": 27.12, "pos": [540, 1290], "w": 560, "fit": "full", "html": photo("grill.jpg"), "exit": "circle", "exitDur": 0.4, "sfx": False,
     "swap": [[26.05, photo("latte.jpg")], [26.55, photo("dish.jpg")]]})
sfx(23.96, "aplkey1", 0.5); sfx(24.40, "wbselect", 0.85); typing("для кого", 24.50, 25.02, 0.5)
sfx(25.64, "wbbounce", 0.7); sfx(26.05, "wbclick", 0.6); sfx(26.55, "wbclick", 0.6); sfx(26.92, "wbslide", 0.55)

# --- шаг 2: «Второе — что должно получиться. Чтобы люди заказывали онлайн» ---
add({"type": "wave", "t": 27.00, "end": 28.20, "from": "top", "rise": 0.5, "fall": 0.45, "h": 380, "sfx": False})
num_tile(2, 27.12, 31.97, exit_="left")
add({"type": "btext", "t": 27.18, "end": 31.97, "y": 465, "enter": "tilt", "exit": "left", "exitDur": 0.45, "sfx": False, "lines": [
    {"mode": "word", "words": [["Второе —", 27.18]], "size": 64, "weight": 500, "ls": -0.02, "color": "#6e6e73"}]})
add({"type": "select", "t": 27.58, "end": 31.97, "text": "что должно получиться", "size": 74, "step": 0.062, "pos": [540, 630], "exit": "left", "exitDur": 0.45, "sfx": False})
add({"type": "btext", "t": 29.45, "end": 31.97, "y": 790, "exit": "left", "exitDur": 0.45, "sfx": False, "lines": [
    {"words": [["Чтобы", 29.45], ["люди", 29.86]], "size": 92, "weight": 700, "ls": -0.04, "step": 0.034},
    {"mode": "word", "words": [["заказывали", 30.18], ["онлайн", 30.94]], "size": 62, "weight": 400, "ls": -0.02, "y": 118}]})
add({"type": "dock2", "t": 29.80, "end": 31.97, "pos": [540, 1290], "img": "@local/taxi/bag.png", "words": [["Заказать", 29.92]],
     "swap": {"t": 30.94, "words": [["Заказ", 30.94], ["принят ✓", 31.04]], "color": "#30D158"}, "scale": 1.45, "exit": "left", "exitDur": 0.45})
sfx(27.00, "wbslide", 0.5); sfx(27.18, "aplkey2", 0.5); sfx(27.58, "wbselect", 0.85); typing("что должно получиться", 27.68, 28.92, 0.5)
sfx(29.45, "aplkey1", 0.6); sfx(29.80, "wbbounce", 0.65); sfx(30.94, "wbclick", 0.85); sfx(31.00, "tagpop", 0.7); sfx(31.75, "wbslide", 0.55)

# --- шаг 3: «Третье — пример. Вот сайт, который мне нравится» ---
add({"type": "wave", "t": 31.85, "end": 35.71, "rise": 0.6, "fall": 0.3, "h": 300, "sfx": False})
num_tile(3, 31.97, 35.71, exit_="cut")
add({"type": "btext", "t": 32.05, "end": 35.71, "y": 465, "enter": "tilt", "exit": "cut", "sfx": False, "lines": [
    {"mode": "word", "words": [["Третье —", 32.05]], "size": 64, "weight": 500, "ls": -0.02, "color": "#6e6e73"}]})
add({"type": "select", "t": 32.48, "end": 35.71, "text": "пример", "size": 110, "step": 0.07, "pos": [540, 640], "exit": "cut", "sfx": False})
add({"type": "btext", "t": 33.36, "end": 35.71, "y": 790, "exit": "cut", "sfx": False, "lines": [
    {"words": [["Вот", 33.36], ["сайт,", 33.68]], "size": 92, "weight": 700, "ls": -0.04, "step": 0.034},
    {"mode": "word", "words": [["который", 34.08], ["мне", 34.48], ["нравится", 34.72]], "size": 60, "weight": 400, "ls": -0.02, "y": 116}]})
add({"type": "reels", "t": 33.62, "end": 35.71, "pos": [540, 1320], "cw": 250, "ch": 445, "gap": 30, "exit": "cut",
     "items": [{"img": f"file://{LT}site{i}.png", "t": t} for i, t in enumerate([33.68, 34.08, 34.48])]})
sfx(31.97, "wbbounce", 0.5); sfx(32.05, "aplkey3", 0.5); sfx(32.48, "wbselect", 0.85); typing("пример", 32.58, 32.95, 0.5)
sfx(33.36, "aplkey1", 0.6)
for t in (33.68, 34.08, 34.48): sfx(t, "wbbounce", 0.45)

# ===================== Блок 3: «Подпишись — тут про искусственный интеллект» =====================
add({"type": "wb", "t": 38.90, "end": 41.71})
add({"type": "wave", "t": 38.90, "end": 41.71, "rise": 0.8, "fall": 0.3, "h": 380, "sfx": False})
add({"type": "group", "id": "h", "t": 38.90, "end": 41.71, "origin": [540, 820], "keys": [[38.90, {"s": 0.12}], [39.58, {"s": 1}]]})
add({"type": "select", "g": "h", "t": 38.96, "end": 41.71, "text": "Подпишись", "size": 120, "step": 0.07, "pos": [540, 430], "exit": "cut", "sfx": False})
add({"type": "follow", "g": "h", "t": 39.20, "end": 41.71, "pos": [540, 900], "w": 600, "avatarEmoji": "👤", "name": "saidulaev.ai", "sub": "Амирхан | Вайбкодинг",
     "btnT": 39.30, "cardT": 39.62, "pressT": 40.96, "exit": "cut"})
add({"type": "btext", "g": "h", "t": 40.11, "end": 41.71, "y": 1330, "exit": "cut", "sfx": False, "lines": [
    {"mode": "word", "words": [["тут", 40.11], ["про", 40.16]], "size": 62, "weight": 400, "ls": -0.02},
    {"mode": "word", "words": [["искусственный\u00a0", 40.36], ["интеллект", 41.12]], "size": 62, "weight": 600, "ls": -0.02, "y": 84}]})
sfx(38.90, "wbwhoosh", 0.8); sfx(38.96, "wbselect", 0.85); typing("Подпишись", 39.06, 39.62, 0.5); sfx(39.20, "wbbounce", 0.55); sfx(39.30, "wbpop", 0.5)
sfx(39.62, "wbbounce", 0.45); sfx(40.96, "wbclick", 0.9); sfx(41.02, "wbpop", 0.6)

cues = {"wbColor": "#FFC21A", "wbPill": ["#FFE27A", "#FFC21A"], "wbPillText": "#1d1d1f", "wbSel": ["rgba(255, 214, 10, .55)", "#E0A400"],
        "fps": 30, "mblur": 5, "shutter": 0.5, "duration": 42.3, "anchor": None, "typeEvery": 99, "pauses": [], "items": items}
os.makedirs(HERE + "/work/apple", exist_ok=True)
json.dump(cues, open(HERE + "/work/apple/cues.json", "w"), ensure_ascii=False)
print("элементов", len(items), "звуков", sum(1 for i in items if i["type"] == "sfx"))
