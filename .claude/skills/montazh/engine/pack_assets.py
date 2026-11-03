"""Наш стиль монтажа: ставит шрифты и картинки iOS-интерфейса из пака пользователя в engine/local/ (папка в .gitignore).

Использование: python pack_assets.py "/папка/пака"   (рекурсивно; архивы .zip со шрифтами распаковываются)
  engine/local/fonts — SF Pro Display (для «белого Apple-экрана»; без них — Inter)
  engine/local/ui    — PNG/JPG интерфейса (батарея, Face ID, календарь, звонок, выделитель, клавиатура, иконки…);
                       в cues.json: "img": "@local/ui/Calendar small.png"
Лицензии шрифтов и картинок — на пользователе: использовать в своих роликах, не выкладывать файлами.
"""
import os
import shutil
import sys
import zipfile
from pathlib import Path

src = Path(sys.argv[1])
HERE = Path(__file__).resolve().parent
fonts, ui = HERE / "local" / "fonts", HERE / "local" / "ui"
fonts.mkdir(parents=True, exist_ok=True)
ui.mkdir(parents=True, exist_ok=True)
nf = ni = 0
for root, _, files in os.walk(src):
    for f in files:
        p = Path(root) / f
        low = f.lower()
        if low.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    b = os.path.basename(n)
                    if b.lower().endswith((".otf", ".ttf")) and not b.startswith("._"):
                        (fonts / b).write_bytes(z.read(n)); nf += 1
        elif low.endswith((".otf", ".ttf")):
            shutil.copy2(p, fonts / f); nf += 1
        elif low.endswith((".png", ".jpg", ".jpeg")):
            shutil.copy2(p, ui / f); ni += 1
print(f"шрифтов: {nf}, картинок: {ni} -> {HERE / 'local'}")
