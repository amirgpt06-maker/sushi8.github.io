"""Скачать звуки пользователя с Google Drive (папка с паком) и разложить по ролям в engine/sfx_local; то же — для нашидов.
python fetch_assets.py            # пак звуков (DRIVE_SFX_FOLDER) -> .claude/skills/montazh/engine/sfx_local
python fetch_assets.py nashid     # нашиды (DRIVE_NASHID_FOLDER, если задана) -> nashid/
Папки: assets.json в корне репозитория (id папок Drive, не секрет: доступ по ссылке). Файлы в git не попадают."""
import html, json, os, re, subprocess, sys, urllib.parse
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
cfg = json.load(open(os.path.join(ROOT, "assets.json"))); kind = sys.argv[1] if len(sys.argv) > 1 else "sfx"
folder = cfg[kind]; AUDIO = (".mp3", ".wav", ".m4a", ".ogg", ".flac")
dst = os.path.join(ROOT, "_assets", kind); os.makedirs(dst, exist_ok=True)
page = subprocess.run(["curl", "-sS", "-m", "60", f"https://drive.google.com/embeddedfolderview?id={folder}"], capture_output=True, text=True).stdout
files = re.findall(r'id="entry-([A-Za-z0-9_-]+)".*?flip-entry-title">([^<]*)', page, re.S)
n = 0
for fid, name in files:
    name = html.unescape(name)
    if not name.lower().endswith(AUDIO): continue
    f = os.path.join(dst, name)
    if os.path.exists(f) and os.path.getsize(f) > 1000: continue
    r = subprocess.run(["curl", "-sS", "-f", "-L", "-m", "300", "-o", f, f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"], capture_output=True)
    if r.returncode != 0 or os.path.getsize(f) < 1000:
        if os.path.exists(f): os.remove(f)
        print("не скачалось:", name); continue
    n += 1
print(f"{kind}: {len(os.listdir(dst))} файлов в {dst} (новых {n})")
if kind == "sfx":
    py = sys.executable; eng = os.path.join(ROOT, ".claude/skills/montazh/engine")
    subprocess.run([py, os.path.join(eng, "pack_to_sfx.py"), dst], check=True)
elif kind == "nashid":
    nd = os.path.join(ROOT, "nashid"); os.makedirs(nd, exist_ok=True)
    for f in os.listdir(dst): subprocess.run(["cp", "-n", os.path.join(dst, f), nd])
