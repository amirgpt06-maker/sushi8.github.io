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
# чистые иконки приложений без подписи: «Logo and Text*.png» = иконка 240x240 сверху + подпись снизу
try:
    from PIL import Image
    names = {"Logo and Text (2).png": "photos", "Logo and Text-1.png": "calendar", "Logo and Text-2.png": "shortcuts",
             "Logo and Text-3.png": "mail", "Logo and Text-4.png": "podcasts", "Logo and Text-5.png": "appstore", "Logo and Text.png": "facetime"}
    for f, n in names.items():
        if (ui / f).exists():
            im = Image.open(ui / f).convert("RGBA"); w = im.size[0]
            im.crop((0, 0, w, w)).save(ui / f"icon_{n}.png")
except ImportError:
    pass
print(f"шрифтов: {nf}, картинок: {ni} -> {HERE / 'local'}")
