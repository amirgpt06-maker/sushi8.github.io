"""Наш стиль монтажа: собирает звуки эффектов из ВАШЕГО звукового пака (он не хранится в репозитории).

Использование: python pack_to_sfx.py "/путь/к/папке/с/паком" [out=engine/sfx_local]
Берёт файлы из sfx_map.json (роль -> имя файла), ищет их рекурсивно в папке пака,
обрезает, переводит в 48 кГц моно и сохраняет как <роль>.wav. Папка sfx_local игнорируется git.
Лицензия пака — на вас: звуки можно использовать в своих роликах по условиям пака, но не выкладывать файлами.
"""
import json
import os
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
pack = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "sfx_local"
out.mkdir(parents=True, exist_ok=True)
MAP = json.load(open(os.environ.get("SFX_MAP", HERE / "sfx_map.json"), encoding="utf-8"))   # SFX_MAP — другая таблица (набор)
index = {}
for root, _, files in os.walk(pack):
    for f in files:
        index.setdefault(f, os.path.join(root, f))
for role, m in MAP.items():
    if role.startswith("_"):
        continue
    src = index.get(m["file"])
    if not src:
        print(f"нет файла для «{role}»: {m['file']}")
        continue
    y, _ = librosa.load(src, sr=48000, mono=True, duration=m.get("max_s", 1.0))
    if len(y) == 0:
        print(f"пустой файл для «{role}»")
        continue
    full = librosa.get_duration(path=src)
    if full > m.get("max_s", 1.0) + 0.01:               # обрезали — плавный спад 60 мс, чтобы звук не обрывался
        n = min(len(y), int(0.06 * 48000))
        y[-n:] *= np.linspace(1, 0, n) ** 2
    act = y[np.abs(y) > 0.05 * np.abs(y).max()]          # громкость на слух: RMS звучащей части к одному уровню
    rms = np.sqrt(np.mean(act ** 2)) + 1e-9
    y = y * (10 ** (m.get("rms_db", -18) / 20) / rms)
    pk = np.abs(y).max()
    if pk > 0.9:
        y *= 0.9 / pk
    sf.write(str(out / f"{role}.wav"), y.astype(np.float32), 48000)
    print(f"{role:8s} <- {m['file']}  ({len(y)/48000:.2f} с)")
