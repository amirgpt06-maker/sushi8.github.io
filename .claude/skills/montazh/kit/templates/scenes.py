"""Библиотека сцен стиля «белый Apple-экран под голос» (skill.ai).

Все времена — секунды ГОТОВОГО голоса (voice.wav, words.json). Каждая функция добавляет элементы в общий список
и ставит звуки. В конце save() пишет cues.json для engine/render.js.

Быстрый старт (в gen_cues.py папки проекта):
    import sys; sys.path.insert(0, "<путь>/skill.ai/templates")
    from scenes import *
    load(".")                      # читает voice.wav и words.json
    t = at("этот"); ...            # время слова (n-е вхождение: at("это", 2); после времени: at("это", after=12.0))
    heading([("Этот", at("этот")), ("ролик", at("ролик"))], end=4.5)
    save()

Правила стиля (кратко, подробно в PROMPT.md):
  * каждое слово появляется РОВНО когда звучит (время из words.json), никогда раньше;
  * смена сцены — в паузе диктора, выход старой сцены 0.3–0.45 с, новая входит на первом слове;
  * один главный виджет на сцену, он появляется в момент, когда о нём говорят;
  * цвет акцента — синий (#3d7ef5), фон #fbfbfb, шрифт SF Pro; без музыки; без зерна.
"""
import json
import math
import os
import re

import numpy as np
import soundfile as sf

ITEMS = []
CFG = {"wbColor": "#3d7ef5", "wbPill": ["#6aa6ff", "#2f6df2"], "fps": 60, "mblur": 5, "shutter": 0.5, "typeEvery": 99}
P = {"dir": ".", "dur": 0.0, "words": [], "env": [], "pauses": []}


def add(item):
    ITEMS.append(item)
    return item


def r3(v):
    return round(float(v), 3)


def sfx(t, role, g=0.7):
    """Звук роли `role` (см. engine/sfx_map.json) в момент t; g — громкость относительно голоса (0.4 тихо … 1.0 акцент)."""
    add({"type": "sfx", "t": r3(t), "s": role, "g": g})


def _norm(s):
    return re.sub(r"[^а-яёa-z0-9]", "", s.lower().replace("ё", "е"))


def load(project_dir="."):
    """Читает voice.wav (длина ролика = длина голоса) и words.json; считает огибающую голоса и паузы."""
    P["dir"] = project_dir
    x, sr = sf.read(os.path.join(project_dir, "voice.wav"))
    x = x if x.ndim == 1 else x.mean(1)
    P["dur"] = len(x) / sr
    hop = sr // 60
    rms = np.sqrt(np.convolve(x ** 2, np.ones(hop * 2) / (hop * 2), "same"))[::hop]
    P["env"] = [round(float(v), 3) for v in np.clip(rms / (np.percentile(rms, 99) + 1e-9), 0, 1.2)]
    P["words"] = json.load(open(os.path.join(project_dir, "words.json"), encoding="utf-8"))["words"]
    ws = P["words"]
    P["pauses"] = [[r3(a["t1"]), r3(b["t0"])] for a, b in zip(ws, ws[1:]) if b["t0"] - a["t1"] >= 0.7]
    if ws and P["dur"] - ws[-1]["t1"] > 0.3:
        P["pauses"].append([r3(ws[-1]["t1"]), r3(P["dur"])])
    add({"type": "wb", "t": 0, "end": r3(P["dur"] + 1)})
    return P


def at(word, n=1, after=None):
    """Время начала слова по words.json: n-е вхождение (с 1) или первое после `after` секунд.
    Сначала точное совпадение (без регистра/знаков, ё=е), если его нет — ближайшее похожее (ошибки распознавания: «промт», «эпл»)."""
    import difflib
    if isinstance(word, (list, tuple)):              # варианты написания: at(("ии", "и"), after=…) — берём самое раннее найденное
        found = []
        for v in word:
            try:
                found.append(at(v, n, after))
            except KeyError:
                pass
        if not found:
            raise KeyError(f"ни один вариант {word} не найден в words.json")
        return min(found)
    k = _norm(word)
    pool = [w for w in P["words"] if after is None or w["t0"] > after]
    hits = [w for w in pool if _norm(w["w"]) == k]
    if not hits:
        hits = [w for w in pool if abs(len(_norm(w["w"])) - len(k)) <= 3 and difflib.SequenceMatcher(None, _norm(w["w"]), k).ratio() >= 0.75]
    if after is not None:
        n = 1
    if len(hits) < n:
        raise KeyError(f"слово «{word}» (№{n}{'' if after is None else f', после {after}'}) не найдено в words.json — проверь распознавание")
    return r3(hits[n - 1]["t0"])


def end_of(word, n=1, after=None):
    """Время конца слова."""
    t0 = at(word, n, after)
    return r3(next(w["t1"] for w in P["words"] if abs(w["t0"] - t0) < 1e-3))


def W(*pairs):
    """Слова с временами для строк: W(("Этот", 2.02), ("ролик", 2.38))."""
    return [[w, r3(t)] for w, t in pairs]


# ---------------------------------------------------------------- базовые элементы
def heading(words, end, y=760, size=110, weight=700, move=None, exit="up", exitDur=0.33, enter=None, step=0.04, lines_extra=(), g=None, key_sfx=True):
    """Крупный заголовок: буквы выпрыгивают по одной ровно на словах. move=(t, y_new) — подняться, освобождая место виджету."""
    it = {"type": "btext", "t": r3(words[0][1]), "end": r3(end), "y": y, "exit": exit, "exitDur": exitDur, "sfx": False,
          "lines": [{"words": W(*words), "size": size, "weight": weight, "ls": -0.04, "step": step}] + list(lines_extra)}
    if move:
        it["move"] = [[r3(move[0]), move[1], move[2] if len(move) > 2 else 0.5]]
    if enter:
        it["enter"] = enter
    if g:
        it["g"] = g
    add(it)
    if key_sfx:
        sfx(words[0][1], "aplkey1", 0.6)
    return it


def subline(words, dy=118, size=62):
    """Вторая строка заголовка (мелко, по словам) — передаётся в heading(..., lines_extra=[subline(...)])."""
    return {"mode": "word", "words": W(*words), "size": size, "weight": 400, "ls": -0.02, "y": dy}


def text_line(words, end, y=1265, size=66, weight=400, exit="blur", exitDur=0.33, g=None):
    """Отдельная строка текста (под виджетом), слова появляются по одному."""
    it = {"type": "btext", "t": r3(words[0][1]), "end": r3(end), "y": y, "exit": exit, "exitDur": exitDur, "sfx": False,
          "lines": [{"mode": "word", "words": W(*words), "size": size, "weight": weight, "ls": -0.02}]}
    if g:
        it["g"] = g
    return add(it)


def big_word(word, t, end, y=690, size=300, exit="up"):
    """Одно огромное слово по центру (как «ИИ» после перехода)."""
    return add({"type": "btext", "t": r3(t), "end": r3(end), "y": y, "exit": exit, "exitDur": 0.33, "sfx": False,
                "lines": [{"words": W((word, t)), "size": size, "weight": 800, "ls": -0.03, "step": 0.08}]})


def pill(text, t, end, pos=(540, 1260), size=64, exit="drop", g=None, s="wbpop", gain=0.8):
    """Синяя плашка-тег (ключевое слово) — прилетает с поворотом и встаёт пружиной."""
    it = {"type": "pill", "t": r3(t), "end": r3(end), "text": text, "size": size, "pos": list(pos), "exit": exit, "exitDur": 0.45, "sfx": False}
    if g:
        it["g"] = g
    add(it)
    if s:
        sfx(t, s, gain)
    return it


def select(text, t, end, pos=(540, 1270), size=100, exit="drop"):
    """iOS-выделение слова синим (ручки по краям) — для главного слова фразы."""
    add({"type": "select", "t": r3(t), "end": r3(end), "text": text, "size": size, "step": 0.06, "pos": list(pos), "exit": exit, "exitDur": 0.45, "sfx": False})
    sfx(t, "wbselect", 0.85)


def wave(t, end, frm="bottom", h=380, rise=0.9, fall=0.45):
    """Размытая синяя волна снизу (frm="bottom") или сверху ("top") — подложка-настроение сцены."""
    it = {"type": "wave", "t": r3(t), "end": r3(end), "rise": rise, "fall": fall, "h": h, "sfx": False}
    if frm == "top":
        it["from"] = "top"
    return add(it)


def circle_wipe(t, pos=(540, 2100), dur=0.46, end=None, r0=None):
    """Белый круг-шторка: растёт из точки и закрывает экран (смена сцены)."""
    it = {"type": "circle", "t": r3(t), "end": r3(end if end is not None else t + dur + 0.3), "pos": list(pos), "dur": dur, "sfx": False}
    if r0:
        it["r0"] = r0
    add(it)
    sfx(t, "wbwhoosh", 0.8)


# ---------------------------------------------------------------- готовые сцены
def spark_svg(size=170, rays=12):
    """Иконка-«искра» Claude (белые лучи) для плитки на терракотовом фоне."""
    c = size / 2
    out = []
    for k in range(rays):
        a = math.radians(k * 360 / rays + 8)
        L = size * (0.33 if k % 2 else 0.27) * (1 + 0.06 * math.sin(k * 2.3))
        out.append(f'<line x1="{c:.1f}" y1="{c:.1f}" x2="{c + L * math.cos(a):.1f}" y2="{c + L * math.sin(a):.1f}" '
                   f'stroke="#fff" stroke-width="{size * 0.075:.1f}" stroke-linecap="round"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">' + "".join(out) + "</svg>"


def scene_intro(title_words, end, icon_html=None, icon_img=None, icon_bg="#d97757", pill_text=None, pill_t=None, small_words=None):
    """Открытие: камера «въезжает» (группа из масштаба 0.12 в 1), иконка-плитка сверху, крупный заголовок, плашка, мелкая строка,
    снизу поднимается волна; уходит белым кругом снизу. Звук: печать на заголовке, поп на плашке, клик на мелкой строке."""
    wave(0, end, h=520, rise=1.0, fall=0.01)
    add({"type": "group", "id": "intro", "t": 0, "end": r3(end), "origin": [540, 800], "keys": [[0, {"s": 0.12}], [0.75, {"s": 1}]]})
    tile = {"type": "tile", "g": "intro", "t": 0, "end": r3(end), "bg": icon_bg, "fit": "full", "w": 170, "pos": [540, 600], "exit": "cut", "sfx": False}
    if icon_img:
        tile["img"] = icon_img
    else:
        tile["html"] = icon_html or spark_svg()
    add(tile)
    add({"type": "btext", "g": "intro", "t": r3(title_words[0][1]), "end": r3(end), "y": 700, "exit": "cut", "sfx": False,
         "lines": [{"words": W(*title_words), "size": 124, "weight": 700, "ls": -0.04, "step": 0.045}]})
    sfx(title_words[0][1], "aplkey1", 0.6)
    if pill_text:
        add({"type": "pill", "g": "intro", "t": r3(pill_t), "end": r3(end), "text": pill_text, "size": 42, "pos": [540, 850], "exit": "cut", "sfx": False})
        sfx(pill_t, "wbpop", 0.8)
    if small_words:
        add({"type": "btext", "g": "intro", "t": r3(small_words[0][1]), "end": r3(end), "y": 935, "exit": "cut", "sfx": False,
             "lines": [{"mode": "word", "words": W(*small_words), "size": 66, "weight": 400, "ls": -0.02}]})
        sfx(small_words[0][1], "wbclick", 0.55)
    circle_wipe(end - 0.46, pos=(540, 2100), dur=0.46, end=end + 0.27)


def scene_number(label, num, t_card, end, num2=None, t_strike=None, t_swap=None, pos=(540, 905)):
    """Виджет с числом (цена/сроки/метрика): цифры печатаются, линия зачёркивает (t_strike), число сменяется на num2 (t_swap)."""
    wave(t_card, end, h=380)
    it = {"type": "numcard", "t": r3(t_card), "end": r3(end), "pos": list(pos), "w": 600, "label": label, "labelColor": "#2f6df2",
          "strikeColor": "#2f6df2", "num": num, "numT": r3(t_card + 0.02), "step": 0.06, "size": 104, "exit": "circle", "exitDur": 0.45}
    if t_strike:
        it.update({"strikeT": r3(t_strike), "strikeDur": 0.45})
        sfx(t_strike, "wbslide", 0.55)
    if num2:
        it.update({"swapT": r3(t_swap), "num2": num2, "size2": 170})
        sfx(t_swap, "tagpop", 0.75)
    add(it)
    sfx(t_card, "wbbounce", 0.7)


def scene_follow(t, end, t_btn, t_card, t_press, name, sub, pos=(540, 920)):
    """Подписка как в Instagram: кнопка «Подписаться» -> карточка профиля (аватар 👤, ник, подпись) -> нажатие «Вы подписаны ✓»."""
    add({"type": "follow", "t": r3(t), "end": r3(end), "pos": list(pos), "w": 600, "avatarEmoji": "👤", "name": name, "sub": sub,
         "btnT": r3(t_btn), "cardT": r3(t_card), "pressT": r3(t_press), "exit": "drop", "exitDur": 0.45})
    sfx(t, "wbbounce", 0.6); sfx(t_btn, "wbpop", 0.5); sfx(t_card, "wbbounce", 0.45); sfx(t_press, "wbclick", 0.9); sfx(t_press + 0.06, "wbpop", 0.6)


def scene_drop(t_start, t_next_word, pos=(540, 825), r=245):
    """Переход «стеклянная капля» (как в референсе): капля выныривает под фразой, надувается с пружиной, живая как резина,
    внутри увеличение + зеркальная полоса у обода, мутнеет в голубо-сиреневое «яйцо», белеет и раздувается на весь экран;
    слово t_next_word проявляется внутри неё.
    t_start — когда буквы ключевого слова фразы уже появились (≈ начало слова + 0.2 с), НЕ конец слова.
    Лучше всего 0.75–1.0 с от t_start до следующего слова; меньше 0.6 с — капля не успеет (будет предупреждение)."""
    span = t_next_word - t_start
    if span < 0.6:
        print(f"!! капле мало времени: {span:.2f} с (нужно ≥0.75) — начни раньше (на ключевом слове) или удлини паузу")
    frost = t_start + (0.40 if span >= 0.75 else 0.5 * span)
    white = t_next_word - 0.14 if span >= 0.75 else t_start + 0.8 * span
    t_end = t_next_word + 0.43
    add({"type": "ball", "pop": True, "t": r3(t_start), "end": r3(t_end), "pos": list(pos), "r": r, "rise": 70,
         "frostAt": r3(frost), "whiteAt": r3(white), "grow": 1550, "whiteMax": 0.8, "fadeOut": 0.24, "sfx": False})
    add({"type": "circle", "t": r3(t_next_word + 0.03), "end": r3(t_end + 0.3), "pos": list(pos), "r0": 200, "dur": 0.42, "sfx": False})
    sfx(t_start - 0.04, "wbwhoosh", 0.6); sfx(t_start + 0.02, "fx7", 0.55); sfx(frost, "wbshimmer", 0.7)


def scene_sound_show(p0, p1, end, pos=(540, 930), w=600):
    """«Звуковое шоу» в паузе диктора [p0, p1] (p0 — конец фразы про звук, p1 — следующее слово): пульт 3×3, каждая подушечка
    нажимается ровно на своём звуке; ритм UI-звуков -> разгон (riser + ускоряющаяся дробь) -> удар (все разом) -> тишина.
    Нужна пауза ≥ 2.4 с (если короче — удлини паузу tools/extend_pause.py, с разрешения пользователя)."""
    L = p1 - p0
    if L < 2.4:
        print(f"!! пауза для звукового шоу {L:.2f} с — мало, удлини до ~2.6 с (tools/extend_pause.py)")
    k = max(0.55, min(1.0, (L - 0.25) / 2.38))      # сжатие схемы под длину паузы
    groove = [(0.22, "fx2", 0, 1.7), (0.33, "fx1", 4, 1.5), (0.44, "fx7", 8, 1.7), (0.66, "fx5", 2, 1.6), (0.77, "fx3", 6, 1.6),
              (0.88, "fx6", 1, 1.6), (0.99, "fx8", 3, 1.4), (1.10, "chime2", 5, 1.5)]
    order = [0, 1, 2, 5, 8, 7, 6, 3, 4, 0, 2, 8, 6, 4]
    roll, tt, dt = [], 1.22, 0.14
    while tt < 2.30:
        roll.append(tt); tt += dt; dt = max(0.05, dt * 0.86)
    imp = p0 + 2.38 * k
    hits = [[r3(p0 + a * k), i, 1] for a, _, i, _ in groove] + [[r3(p0 + a * k), order[j % len(order)], 0.8] for j, a in enumerate(roll)] + [[r3(imp), -1, 1]]
    add({"type": "pads", "t": r3(p0 + 0.01), "end": r3(end), "pos": list(pos), "w": w, "exit": "left", "exitDur": 0.45,
         "rise": [r3(p0 + 1.15 * k), r3(imp)], "hits": hits})
    sfx(p0 + 0.01, "wbpop", 1.1)
    for a, s, _, g in groove:
        sfx(p0 + a * k, s, g)
    sfx(p0 + 1.12 * k, "riser", 1.05)
    for j, a in enumerate(roll):
        sfx(p0 + a * k, "tick" if j % 2 else "fx1", round(0.55 + 0.55 * j / max(1, len(roll) - 1), 2))
    sfx(imp, "flash", 1.35); sfx(imp, "chime5", 0.85); sfx(imp + 0.02, "wbbounce", 0.5)


def scene_voice_card(t, end, pos=(540, 910)):
    """Карточка «голос»: тонкая волна строго по громкости голоса + синяя точка записи и таймер."""
    add({"type": "vcard", "t": r3(t), "end": r3(end), "pos": list(pos), "w": 900, "h": 320, "dot": "#2f6df2", "exit": "drop", "exitDur": 0.45})
    sfx(t, "wbbounce", 0.45)


def scene_prompt(text, t, end, t_type, t_type_end, t_send, chips=(), pos=(540, 840)):
    """Поле промпта: текст печатается (t_type..t_type_end), синяя кнопка «отправить» (t_send), ниже чипы с галочками.
    chips: [(текст, t_появления, t_галочки), …]."""
    add({"type": "prompt", "t": r3(t), "end": r3(end), "pos": list(pos), "w": 900, "h": 300, "size": 44, "text": text,
         "typeT": r3(t_type), "typeEnd": r3(t_type_end), "sendT": r3(t_send), "exit": "up", "exitDur": 0.35,
         "chips": [{"text": c, "t": r3(a), "checkT": r3(b)} for c, a, b in chips]})
    sfx(t, "wbbounce", 0.65); sfx(t_send, "wbclick", 0.85); sfx(t_send + 0.06, "wbpop", 0.6)
    for _, a, b in chips:
        sfx(a, "fx1", 0.45); sfx(b, "fx5", 0.5)


def scene_reels(items, end, pos=(540, 1000)):
    """Ряд вертикальных превью-роликов, вылетают по очереди. items: [(путь_к_картинке, t), …] — превью делай tools/make_thumbs.sh."""
    add({"type": "reels", "t": r3(items[0][1] - 0.04), "end": r3(end), "pos": list(pos), "exit": "left", "exitDur": 0.45,
         "items": [{"img": "file://" + os.path.abspath(p), "t": r3(t)} for p, t in items]})
    for _, t in items:
        sfx(t, "wbbounce", 0.45)


def scene_cta(top_word, big, t_big, bottom_words, end, t_arrow, dock_words, swap_words=None, dock_img="@local/ui/photo_2025-08-02_14-36-27-Photoroom.png"):
    """Призыв: «Напиши» / ОГРОМНОЕ слово / «в комментариях», стрелка вниз, тёмная кнопка-док с подписью по словам,
    которая меняется на синюю кнопку (swap_words). top_word=(текст, t); bottom_words/dock_words/swap_words=[(слово, t), …]."""
    add({"type": "btext", "t": r3(top_word[1]), "end": r3(end), "y": 420, "exit": "blur", "exitDur": 0.5, "sfx": False, "lines": [
        {"mode": "word", "words": W(top_word), "size": 66, "weight": 400, "ls": -0.02},
        {"words": W((big, t_big)), "size": 240, "weight": 800, "ls": -0.03, "step": 0.07, "y": 80},
        {"mode": "word", "words": W(*bottom_words), "size": 66, "weight": 400, "ls": -0.02, "y": 360}]})
    add({"type": "arrow", "t": r3(t_arrow), "end": r3(end), "pos": [540, 980], "exit": "blur", "exitDur": 0.5})
    d = {"type": "dock2", "t": r3(dock_words[0][1]), "end": r3(end), "pos": [540, 1250], "img": dock_img, "words": W(*dock_words),
         "scale": 1.5, "exit": "blur", "exitDur": 0.5}
    if swap_words:
        d["swap"] = {"t": r3(swap_words[0][1]), "words": W(*swap_words), "color": "#1f6ef5"}
        sfx(swap_words[0][1], "wbclick", 0.8)
    add(d)
    sfx(top_word[1], "aplkey1", 0.55); sfx(t_big, "tagpop", 0.9); sfx(dock_words[0][1], "wbbounce", 0.65)


# ---------------------------------------------------------------- авто-режим и сохранение
def auto_scenes(max_words=4):
    """Черновик без ручной раскладки: каждая фраза (между паузами ≥0.7 с) — заголовок по словам по центру,
    длинные фразы — заголовок + мелкая строка; на смене фраз — короткий вуш. Для проверки конвейера и как основа."""
    ws = P["words"]
    groups, cur = [], []
    for w in ws:
        if cur and w["t0"] - cur[-1]["t1"] >= 0.7:
            groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    for gi, g in enumerate(groups):
        nxt = groups[gi + 1][0]["t0"] if gi + 1 < len(groups) else P["dur"]
        end = min(nxt - 0.05, g[-1]["t1"] + 1.2) if gi + 1 < len(groups) else P["dur"] - 0.1
        top = [(w["w"], w["t0"]) for w in g[:max_words]]
        rest = [(w["w"], w["t0"]) for w in g[max_words:]]
        heading(top, end, y=760, size=104 if len(" ".join(x for x, _ in top)) < 18 else 80,
                lines_extra=[subline(rest)] if rest else [], exit="blur")
        if gi + 1 < len(groups):
            sfx(end - 0.2, "wbslide", 0.5)


def save(path=None):
    """Пишет cues.json (рядом с voice.wav)."""
    cues = dict(CFG, duration=round(P["dur"], 4), anchor=None, env=P["env"], envFps=60, pauses=P["pauses"], items=ITEMS)
    path = path or os.path.join(P["dir"], "cues.json")
    json.dump(cues, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"cues.json: длина {P['dur']:.2f} с, элементов {len(ITEMS)}, звуков {sum(1 for i in ITEMS if i['type'] == 'sfx')}")
