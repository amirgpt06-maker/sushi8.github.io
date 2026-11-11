"""Каталог стока (Mixkit, бесплатная лицензия, можно в соцсети): stock/catalog.json — id, название, теги.
Сами ролики качаются по запросу в stock/ (в git не попадают). Без женщин и крупных лиц (правило пользователя) — фильтр по названию.
python build_catalog.py [тег …]"""
import html, json, os, re, subprocess, sys, time
TAGS = sys.argv[1:] or ["laptop", "smartphone", "typing", "computer", "technology", "code", "programming", "office", "business",
        "city", "night", "traffic", "neon", "abstract", "digital", "data", "network", "internet", "screen", "keyboard", "desk",
        "money", "coffee", "notebook", "writing", "clock", "time", "camera", "video", "studio", "light", "lights", "sky", "clouds",
        "space", "robot", "hands", "work", "startup", "success", "time-lapse", "car", "road", "rain", "food", "restaurant", "shop",
        "phone", "social-media", "creative", "design", "drawing", "paper", "books", "school", "fire", "water", "nature", "sunset"]
BAD = re.compile(r"\b(woman|women|girl|girls|female|lady|ladies|her|she|mother|bride|couple|portrait|face|selfie|smiling|model|kiss|dancing|dancer|child|baby|kids?)\b", re.I)
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../stock/catalog.json")
cat = json.load(open(P)) if os.path.exists(P) else {}
for tag in TAGS:
    for page in (1, 2):
        u = f"https://mixkit.co/free-stock-video/{tag}/" + (f"?page={page}" if page > 1 else "")
        r = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", u], capture_output=True, text=True).stdout
        found = 0
        for m in re.finditer(r'item-id-value="(\d+)".*?overlay-video-title">\s*(.*?)\s*</span>', r, re.S):
            vid, title = m.group(1), html.unescape(m.group(2)); found += 1
            if BAD.search(title): continue
            e = cat.setdefault(vid, {"title": title, "tags": []})
            if tag not in e["tags"]: e["tags"].append(tag)
        print(tag, page, found, flush=True)
        time.sleep(2.5)
        if not found: break
json.dump(cat, open(P, "w"), ensure_ascii=False, indent=0)
print("в каталоге:", len(cat))
