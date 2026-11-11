"""Публикация рилсов и ответы на комментарии через официальный Instagram Graph API (бесплатно).
    python instagram.py publish ready/<дата>/<slug>   — опубликовать ОДОБРЕННЫЙ рилс (после «ок» в Telegram): видео, обложка, описание
    python instagram.py comments                      — комментарии к последним рилсам: ключевое слово -> ответ + материал в личку (private reply);
                                                        вопросы печатаются строкой COMMENT_QUESTION <comment_id> <username> <текст> — отвечаю сам: reply <comment_id> "текст"
    python instagram.py reply <comment_id> "текст"    — ответить на комментарий
Нужно (.env или переменные окружения): INSTAGRAM_ACCESS_TOKEN (долгоживущий токен), INSTAGRAM_USER_ID (id профессионального аккаунта).
Права приложения Meta: instagram_content_publish, instagram_manage_comments, instagram_manage_messages (для личных ответов), pages_show_list.
Видео грузится прямо с сервера (resumable upload), публичный хостинг не нужен. Обложка — кадр из видео (thumb_offset). Не проверено на боевом аккаунте."""
import json, os, re, sys, time
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tts          # подгружает .env
ROOT = tts.ROOT
TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN"); UID = os.environ.get("INSTAGRAM_USER_ID")
if not TOKEN or not UID: raise SystemExit("нет INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_USER_ID")
G = "https://graph.facebook.com/v21.0"
STATE_F = os.path.join(ROOT, "scenarios", "instagram_state.json")
state = json.load(open(STATE_F)) if os.path.exists(STATE_F) else {"published": {}, "handled": []}
save = lambda: json.dump(state, open(STATE_F, "w"), ensure_ascii=False, indent=1)
def api(method, path, **kw):
    r = requests.request(method, f"{G}/{path}", params={"access_token": TOKEN, **kw.pop("params", {})}, timeout=300, **kw); j = r.json()
    if "error" in j: raise SystemExit(f"Instagram API {path}: {j['error'].get('message')}")
    return j

def tg_status(rel):
    s = json.load(open(os.path.join(ROOT, "scenarios", "telegram_state.json"))).get("status", {}).get(rel, {})
    return s.get("status")

def publish(d):
    d = os.path.abspath(d); rel = os.path.relpath(d, ROOT)
    if tg_status(rel) != "approved": raise SystemExit(f"{rel}: нет «ок» от владельца в Telegram — не публикую")
    if rel in state["published"]: raise SystemExit(f"{rel}: уже опубликован")
    cap = open(os.path.join(d, "post.txt"), encoding="utf-8").read().strip()
    mp4 = os.path.join(d, "reel.mp4"); size = os.path.getsize(mp4)
    c = api("POST", f"{UID}/media", data={"media_type": "REELS", "upload_type": "resumable", "caption": cap, "share_to_feed": "true", "thumb_offset": "1600"})
    with open(mp4, "rb") as f:
        r = requests.post(c["uri"], headers={"Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(size)}, data=f, timeout=900)
    if r.status_code != 200: raise SystemExit(f"загрузка видео: {r.status_code} {r.text[:200]}")
    for _ in range(60):                                              # ждём обработку видео
        st = api("GET", c["id"], params={"fields": "status_code"})["status_code"]
        if st == "FINISHED": break
        if st == "ERROR": raise SystemExit("Instagram не принял видео (ERROR)")
        time.sleep(10)
    m = api("POST", f"{UID}/media_publish", data={"creation_id": c["id"]})
    state["published"][rel] = {"media_id": m["id"], "at": time.strftime("%Y-%m-%dT%H:%M:%S")}; save()
    print("ОПУБЛИКОВАНО", m["id"])

def comments():
    kw = json.load(open(os.path.join(ROOT, "keywords.json"), encoding="utf-8"))["keywords"]
    media = api("GET", f"{UID}/media", params={"fields": "id,timestamp,media_product_type", "limit": 10})["data"]
    for m in media:
        for c in api("GET", f"{m['id']}/comments", params={"fields": "id,text,username,timestamp", "limit": 50}).get("data", []):
            if c["id"] in state["handled"] or c.get("username") == os.environ.get("INSTAGRAM_USERNAME", "saidulaev.ai"): continue
            low = re.sub(r"[^\w\s]", " ", c["text"].lower().replace("ё", "е")); hit = None
            for w, rep in kw.items():
                if re.search(rf"(?<!\w){re.escape(w.lower().replace('ё', 'е'))}(?!\w)", low): hit = (w, rep); break
            if hit:
                api("POST", f"{c['id']}/replies", data={"message": "Отправил в личные сообщения 🙌"})
                try: api("POST", f"{UID}/messages", data={"recipient": json.dumps({"comment_id": c["id"]}), "message": json.dumps({"text": hit[1]["text"] + (f"\n\n{hit[1]['link']}" if hit[1].get("link") else "")})})
                except SystemExit as e: print("личное сообщение не ушло:", e)
                print("KEYWORD", hit[0], c["username"])
            else:
                print("COMMENT_QUESTION", c["id"], c["username"], c["text"].replace("\n", " ")[:400]); continue     # остаётся необработанным до ответа
            state["handled"].append(c["id"])
    save()

cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "publish": publish(sys.argv[2])
elif cmd == "comments": comments()
elif cmd == "reply":
    api("POST", f"{sys.argv[2]}/replies", data={"message": sys.argv[3]}); state["handled"].append(sys.argv[2]); save(); print("ответ отправлен")
else: print(__doc__)
