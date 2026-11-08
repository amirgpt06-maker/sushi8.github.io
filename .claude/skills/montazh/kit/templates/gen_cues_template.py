"""Сценарий ролика под голос — шаблон. Скопируй в папку проекта как gen_cues.py (рядом voice.wav и words.json).

Порядок работы:
  1) bash prep_voice.sh запись.mp3 проект      -> voice.wav, words.json и список слов с паузами
  2) раздели речь на смысловые сцены (6–9 на 30–40 с), для каждой выбери сцену из библиотеки (см. PROMPT.md, раздел «Смысл -> сцена»)
  3) заполни SCENES ниже, времена бери через at("слово") — не руками
  4) FROM=… TO=… bash make_video.sh проект     -> быстрый просмотр куска;  bash make_video.sh проект -> весь ролик
Если сцены не заполнены (AUTO = True) — получится черновик: каждая фраза заголовком по словам.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SKILL_TEMPLATES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skill.ai", "templates")))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from scenes import *   # noqa: E402,F403

load(os.path.dirname(os.path.abspath(__file__)))
AUTO = True

if AUTO:
    auto_scenes()
else:
    pass
    # ---------- 1. Открытие ----------
    # scene_intro([("Этот", at("этот")), ("ролик", at("ролик"))], end=at("монтажер") - 0.05,
    #             pill_text="смонтировал", pill_t=at("смонтировал"), small_words=[("не", at("не")), ("человек", at("человек"))])
    # ---------- 2. … ----------

save()
