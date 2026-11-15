"""Пробный рилс в «стиле рилс»: раскладка под запись «нейросеть отвечает как скучный учебник» (68 слов).
python probnyi.py _work/words.json cues.json   — тайминги берутся из слов речи, тексты на экране — дословно по речи."""
import json, sys
wj, out = sys.argv[1:3]; D = json.load(open(wj, encoding="utf-8")); Wd = D["words"]; DUR = D["duration"]
T = lambda i: Wd[i][2]; E = lambda i: Wd[i][3]
BLUE = "#78AEFF"; items = []; ev = []   # акцент блога (синий), светлее базового #4C8DFF: читается на любом стоке
def ws(pairs): return [[w, T(i)] for w, i in pairs]
def stack(t0, t1, lines, y=1070, **k): items.append({"type": "stack", "t0": round(t0, 3), "t1": round(t1, 3), "y": y, "lines": lines, **k})
LVL = {"whoosh": -13, "whooshup": -16, "pop": -18, "switch": -22, "key": -26, "riser": -10, "click": -14}   # цели громкости по замеру референсов
def sfx(t, snd, kind, **k): ev.append({"t": round(max(0, t), 3), "snd": snd, "lvl": LVL[kind], **k})

items.append({"type": "mark", "t0": 0, "t1": DUR, "a": "saidulaev.ai", "b": "нейросети | боты | сайты", "y": 1650})
items.append({"type": "fx", "t0": 0, "t1": 0.32, "shape": "in", "blur": 24})

# --- хук: стопка «мелкое / КРУПНОЕ», потом «мелкое / курсив / крупное» ---
stack(max(0.04, T(0) - 0.06), T(3) - 0.02, [{"role": "small", "words": ws([("ты", 0), ("спрашиваешь", 1)]), "at": max(0.04, T(0) - 0.06)},
                                             {"role": "big", "text": "нейросеть", "at": T(2) - 0.04}])
stack(T(3) - 0.02, T(9) - 0.05, [{"role": "small", "words": ws([("а", 3), ("она", 4), ("отвечает", 5), ("как", 6)]), "at": T(3) - 0.02},
                                 {"role": "bigi", "text": "скучный", "at": T(7) - 0.04},
                                 {"role": "big", "text": "учебник", "at": T(8) - 0.04, "dx": 90, "color": BLUE}])

# --- чёрная карточка-вспышка: слова вразрядку появляются по речи ---
items.append({"type": "card", "t0": round(T(9) - 0.03, 3), "t1": round(T(13) - 0.03, 3), "bg": "#111111", "fg": "#ffffff",
              "lines": [{"role": "spaced", "words": ws([("дело", 9), ("не", 10), ("в", 11), ("ней", 12)]), "at": T(9) - 0.03, "gray": 0}]})

# --- абзац-караоке слева ---
items.append({"type": "para", "t0": round(T(13) - 0.03, 3), "t1": round(T(23) - 0.05, 3), "x": 150, "y": 1090,
              "lines": [{"role": "mid", "words": ws([("ты", 13), ("просто", 14), ("не", 15), ("сказал,", 16)])},
                        {"role": "mid", "words": ws([("кто", 17), ("ты", 18), ("и", 19), ("для", 20), ("кого", 21)])},
                        {"role": "mid", "words": ws([("текст", 22)])}]})

# --- «смотри» + стеклянная плашка: запрос печатается в такт речи ---
stack(T(23) - 0.03, T(24) - 0.1, [{"role": "midi", "text": "смотри", "at": T(23) - 0.03}], outd=0.16)
txt = "Напиши пост про кофе."
items.append({"type": "pill", "t0": round(T(24) - 0.14, 3), "t1": round(T(28) - 0.03, 3), "y": 1040, "avatar": "ai", "text": txt, "dim": 0.2, "blur": 5,
              "type0": round(T(24) - 0.02, 3), "marks": [[6, E(24)], [11, E(25)], [15, E(26)], [len(txt), E(27)]]})

# --- кремовая карточка: мелкое + крупное тёмным ---
items.append({"type": "card", "t0": round(T(28) - 0.03, 3), "t1": round(T(31) - 0.03, 3), "bg": "#F3F1E8", "fg": "#161616", "light": 1,
              "lines": [{"role": "small", "text": "получишь", "at": T(28) - 0.03}, {"role": "big", "text": "воду", "at": T(30) - 0.05}]})

# --- «а теперь / так» ---
stack(T(31) - 0.03, T(34) - 0.1, [{"role": "small", "words": ws([("а", 31), ("теперь", 32)]), "at": T(31) - 0.03}, {"role": "bigi", "text": "так", "at": T(33) - 0.04}], outd=0.18)

# --- вторая плашка: подробный запрос, печать по словам речи ---
seq = [("Я", 34), ("владелец", 35), ("кофейни", 36), ("в", 37), ("метро.", 38), ("Напиши", 39), ("пост", 40), ("для", 41), ("студентов,", 42), ("коротко", 43), ("и", 44), ("с", 45), ("юмором.", 46)]
txt = " ".join(w for w, _ in seq); marks = []; n = 0
for w, i in seq: n += len(w) + (1 if marks else 0); marks.append([n, E(i)])
items.append({"type": "pill", "t0": round(T(34) - 0.12, 3), "t1": round(T(47) - 0.06, 3), "y": 1040, "avatar": "ai", "text": txt, "dim": 0.3, "blur": 9,
              "type0": round(T(34), 3), "marks": marks})

# --- вывод: «и ответ сразу станет / ЖИВЫМ», «как будто писал / ты сам» ---
stack(T(47) - 0.03, T(52) - 0.03, [{"role": "small", "words": ws([("и", 47), ("ответ", 48), ("сразу", 49), ("станет", 50)]), "at": T(47) - 0.03},
                                   {"role": "big", "text": "живым", "at": T(51) - 0.04, "color": BLUE}])
stack(T(52) - 0.03, T(57) - 0.06, [{"role": "small", "words": ws([("как", 52), ("будто", 53), ("писал", 54)]), "at": T(52) - 0.03},
                                   {"role": "bigi", "words": ws([("ты", 55), ("сам", 56)]), "at": T(55) - 0.04, "dx": 40}])

# --- призыв: «сохрани [ чтобы не забыть ]», потом «подпишись» + кнопка с курсором ---
stack(T(57) - 0.03, T(61) - 0.03, [{"role": "big", "text": "сохрани", "at": T(57) - 0.03}, {"role": "br", "text": "[   чтобы не забыть   ]", "at": T(58) - 0.03, "from": "below"}])
stack(T(61) - 0.03, DUR + 1, [{"role": "bigi", "text": "подпишись", "at": T(62) - 0.04},
                              {"role": "small", "words": ws([("тут", 63), ("про", 64), ("нейросети", 65), ("простыми", 66), ("словами", 67)]), "at": T(63) - 0.05}], y=960)
b0 = T(62) + 0.35; ck = min(b0 + 1.35, DUR - 0.9)
items.append({"type": "button", "t0": round(b0, 3), "t1": DUR + 1, "y": 1250, "click": round(ck, 3)})

# --- звук: схема снята с 25 референсов. Звук стоит на появлении НОВОГО блока (вжух), вставке (поп, переключатель), ключевом слове (райзер),
#     кнопке (клик). На слова по одному, на караоке и на склейки стока звук не ставится. Всего 1 звук на 3–4 с. ---
sfx(0.02, "sr_whoosh1", "whoosh")                         # хук: первая стопка
sfx(T(8) - 0.04, "sr_pop2", "pop")                        # акцентное слово «учебник»
sfx(T(9) - 0.05, "sr_switch", "switch")                   # чёрная карточка
sfx(T(24) - 0.16, "sr_pop", "pop")                        # плашка 1 появилась
sfx(T(24), "sr_key1", "key"); sfx(T(26), "sr_key3", "key")
sfx(T(28) - 0.05, "sr_switch", "switch")                  # кремовая карточка
sfx(T(33) - 0.2, "sr_whoosh2", "whoosh")                  # «так»
sfx(T(34) - 0.14, "sr_pop3", "pop")                       # плашка 2 появилась
for snd_, i in (("sr_key2", 35), ("sr_key4", 39), ("sr_key1", 43), ("sr_key3", 46)): sfx(T(i), snd_, "key")
sfx(T(51) - 0.45, "sr_whoosh3", "whoosh")                 # ключевое слово «живым»: вжух подлиннее, пик на слове
sfx(T(57) - 0.2, "sr_whoosh1", "whoosh")                  # «сохрани»
sfx(T(62) - 0.62, "sr_whooshup", "whooshup")              # «подпишись»
sfx(ck, "sr_click", "click")                              # нажатие кнопки

json.dump({"fps": 30, "duration": DUR, "ig": "saidulaev.ai", "tg": "saidulaev_ai", "voice_rms": D.get("voice_rms"), "items": items, "events": ev},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("элементов:", len(items), "звуков:", len(ev))
