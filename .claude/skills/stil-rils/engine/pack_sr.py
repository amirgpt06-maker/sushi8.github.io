"""Звуки «стиля рилс» из пака пользователя (Drive, подпапка «isla pac») -> роли sr_* в montazh/engine/sfx_local.
python pack_sr.py            # скачивает нужные файлы пака (если их нет в _assets/isla) и режет роли
Роли и куски выбраны по разбору звука 25 референсов: какие классы звуков там стоят и какие файлы пака на них похожи."""
import html, json, os, re, subprocess, sys
import numpy as np, soundfile as sf
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
SRC = os.path.join(ROOT, "_assets", "isla"); DST = os.path.join(ROOT, ".claude/skills/montazh/engine/sfx_local"); SR = 48000
ROLES = {   # роль: (файл пака, начало с, длина с)
    "sr_whoosh1": ("Whooshes_ODC-0002-506.wav", 2.47, 0.46), "sr_whoosh2": ("Whooshes_ODC-0002-506.wav", 2.98, 0.48), "sr_whoosh3": ("Whooshes_ODC-0002-506.wav", 3.55, 0.40),
    "sr_whooshup": ("mixkit-air-woosh-1489.wav", 0.08, 0.95), "sr_switch": ("переключатель.mp3", 0.12, 0.30), "sr_click": ("clickbutton.mp3", 0.03, 0.22),
    "sr_pop": ("ES_Pops, Wobble, Bloop, Pops - Epidemic Sound.mp3", 0.0, 0.25), "sr_riser": ("1. Riser.mp3", 0.05, 1.15),
    "sr_key1": ("эпл печатание.mp3", 0.25, 0.09), "sr_key2": ("эпл печатание.mp3", 0.42, 0.10), "sr_key3": ("эпл печатание.mp3", 0.69, 0.09), "sr_key4": ("эпл печатание.mp3", 0.95, 0.09),
}
os.makedirs(SRC, exist_ok=True); os.makedirs(DST, exist_ok=True)
need = sorted({v[0] for v in ROLES.values()})
if any(not os.path.exists(os.path.join(SRC, n)) for n in need):
    folder = json.load(open(os.path.join(ROOT, "assets.json")))["isla"]
    page = subprocess.run(["curl", "-sS", "-L", "-m", "60", f"https://drive.google.com/embeddedfolderview?id={folder}"], capture_output=True, text=True).stdout
    ids = {html.unescape(t): i for i, t in re.findall(r'id="entry-([A-Za-z0-9_-]+)".*?flip-entry-title">([^<]*)', page, re.S)}
    for n in need:
        f = os.path.join(SRC, n)
        if os.path.exists(f) or n not in ids: continue
        subprocess.run(["curl", "-sS", "-f", "-L", "-m", "300", "-o", f, f"https://drive.usercontent.google.com/download?id={ids[n]}&export=download&confirm=t"])
for role, (name, st, du) in ROLES.items():
    f = os.path.join(SRC, name)
    if not os.path.exists(f): print("нет файла пака:", name); continue
    y = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-ss", str(st), "-t", str(du), "-i", f, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout, np.float32).astype(np.float64)
    n = len(y); fi, fo = int(0.004 * SR), int(min(0.06, du / 3) * SR)
    y[:fi] *= np.linspace(0, 1, fi); y[n - fo:] *= np.linspace(1, 0, fo)
    sf.write(os.path.join(DST, role + ".wav"), (y / (np.abs(y).max() + 1e-9) * 0.9).astype(np.float32), SR)
print("роли:", ", ".join(sorted(ROLES)))
