"""Telegram-бот «Рилс дня». Состояние хранит сам Telegram (git из облачных запусков не пишет):
    telegram.py daily                       — прислать сценарий на сегодня (из scenarios/pool, по дате) файлом scenario.json + текстом
    telegram.py check                       — обработать входящие и подтвердить их (offset): строки результата:
        VOICE <файл голоса> <scenario.json>   — владелец ответил голосовым на сценарий -> собрать рилс (make_reel.py … --voice …)
        APPROVED <папка рилса>                — «ок» на рилс; EDIT <папка> <текст> — правки владельца
        KEYWORD <слово>                       — подписчик написал ключевое слово, бот ответил материалом
        QUESTION <chat> <msg> <текст>         — вопрос подписчика: отвечаю сам (telegram.py answer)
    telegram.py send ready/<дата>/<slug>    — отправить рилс + текст поста на проверку (в подписи метка [reel:<папка>])
    telegram.py notify "текст"              — написать владельцу (например, что сборка не удалась)
    telegram.py answer <chat> <msg> "текст" — ответить подписчику;  telegram.py whoami — chat_id
Ключи: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (.env или окружение).
"""
import datetime, glob, json, os, re, sys, tempfile
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tts   # подгружает .env
ROOT = tts.ROOT
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN"); CHAT = os.environ.get("TELEGRAM_CHAT_ID")
if not TOKEN: raise SystemExit("нет TELEGRAM_BOT_TOKEN в .env")
API = f"https://api.telegram.org/bot{TOKEN}/"
OK = {"ок", "ok", "окей", "да", "публикуй", "+", "👍"}
START = datetime.date(2026, 11, 11)                     # день 0 пула сценариев: сегодняшний запуск шлёт первый
KW_FILE = os.path.join(ROOT, "keywords.json")

def call(m, **kw):
    r = requests.post(API + m, timeout=300, **kw); j = r.json()
    if not j.get("ok"): raise SystemExit(f"Telegram {m}: {j}")
    return j["result"]
def say(text, **kw): return call("sendMessage", data={"chat_id": CHAT, "text": text, **kw})

def handle_subscriber(m):
    txt = (m.get("text") or "").strip(); chat = m["chat"]["id"]
    if not txt: return
    kw = json.load(open(KW_FILE, encoding="utf-8")) if os.path.exists(KW_FILE) else {}
    low = re.sub(r"[^\w\s]", " ", txt.lower().replace("ё", "е"))
    for word, rep in kw.get("keywords", {}).items():
        if re.search(rf"(?<!\w){re.escape(word.lower().replace('ё', 'е'))}(?!\w)", low):
            body = rep["text"] + (f"\n\n{rep['link']}" if rep.get("link") else "")
            call("sendMessage", data={"chat_id": chat, "text": body, "reply_to_message_id": m["message_id"]}); print("KEYWORD", word); return
    if txt.startswith("/start"):
        call("sendMessage", data={"chat_id": chat, "text": kw.get("welcome", "Привет! Напиши ключевое слово из рилса — пришлю материал.")}); return
    print("QUESTION", chat, m["message_id"], txt.replace("\n", " ")[:500])
    if kw.get("ack"): call("sendMessage", data={"chat_id": chat, "text": kw["ack"], "reply_to_message_id": m["message_id"]})

def download(file_id, dst):
    fp = call("getFile", data={"file_id": file_id})["file_path"]
    open(dst, "wb").write(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}", timeout=300).content)

cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
if cmd == "whoami":
    for u in call("getUpdates"):
        m = u.get("message") or {}; print(m.get("chat", {}).get("id"), (m.get("chat") or {}).get("username"), m.get("text"))
elif cmd == "daily":
    pool = sorted(glob.glob(os.path.join(ROOT, "scenarios", "pool", "*.json")))
    if not pool: raise SystemExit("пул сценариев пуст (scenarios/pool)")
    f = pool[max(0, (datetime.date.today() - START).days) % len(pool)]; sc = json.load(open(f, encoding="utf-8"))
    txt = "\n".join(l["text"] for l in sc["lines"])
    with open(f, "rb") as fh:
        call("sendDocument", data={"chat_id": CHAT, "caption": f"🎙 Тема дня: {sc.get('topic', '')}\n\nЗапиши это голосовым (можно своими словами, 30–40 с) и ответь на это сообщение — смонтирую рилс.\nКлючевое слово: {sc.get('keyword', '')}\n\n{txt}"[:1000]},
             files={"document": (os.path.basename(f), fh, "application/json")})
    print("сценарий отправлен:", os.path.basename(f))
elif cmd == "send":
    d = os.path.abspath(sys.argv[2]); post = open(os.path.join(d, "post.txt"), encoding="utf-8").read().strip()
    sc = json.load(open(os.path.join(d, "scenario.json"), encoding="utf-8"))
    cap = f"🎬 Рилс на проверку: {sc.get('topic', '')}\n\n{post}"[:880] + f"\n\nОтветь «ок» — одобрю. Или напиши, что поправить.\n[reel:{os.path.relpath(d, ROOT)}]"
    with open(os.path.join(d, "reel.mp4"), "rb") as f:
        msg = call("sendVideo", data={"chat_id": CHAT, "caption": cap, "supports_streaming": "true", "width": 1080, "height": 1920}, files={"video": f})
    print("отправлено:", msg["message_id"])
elif cmd == "notify": say(sys.argv[2])
elif cmd == "answer": call("sendMessage", data={"chat_id": sys.argv[2], "text": sys.argv[4], "reply_to_message_id": sys.argv[3]}); print("ответ отправлен")
elif cmd == "check":
    ups = call("getUpdates", data={"timeout": 0}); last = 0
    for u in ups:
        last = max(last, u["update_id"]); m = u.get("message") or {}
        if not m: continue
        if str(m.get("chat", {}).get("id")) != str(CHAT): handle_subscriber(m); continue
        rep = m.get("reply_to_message") or {}
        media = m.get("voice") or m.get("audio") or m.get("video_note") or m.get("video")
        if media:                                                      # голосовое -> нужен сценарий из документа, на который ответили
            doc = rep.get("document")
            if not doc: say("Ответь голосовым именно на сообщение со сценарием — тогда я пойму, про какую тему рилс."); continue
            td = tempfile.mkdtemp(); sc_path = os.path.join(td, doc.get("file_name", "scenario.json")); download(doc["file_id"], sc_path)
            vp = os.path.join(td, "voice" + os.path.splitext(call("getFile", data={"file_id": media["file_id"]})["file_path"])[1]); download(media["file_id"], vp)
            say("🎬 Получил голос, монтирую — пришлю на проверку (около 10 минут).", reply_to_message_id=m["message_id"]); print("VOICE", vp, sc_path); continue
        mm = re.search(r"\[reel:([^\]]+)\]", rep.get("caption") or "")
        if mm:
            txt = (m.get("text") or "").strip()
            if txt.lower().strip(" .!") in OK:
                say("✅ Принято. Опубликую, как только подключим Instagram API.", reply_to_message_id=m["message_id"]); print("APPROVED", mm.group(1))
            elif txt:
                say("✍️ Записал правки. Пришли голос заново ответом на сообщение со сценарием — пересоберу с учётом правок.", reply_to_message_id=m["message_id"]); print("EDIT", mm.group(1), txt.replace("\n", " ")[:400])
    if last: call("getUpdates", data={"offset": last + 1, "timeout": 0})     # подтверждаем обработанное: Telegram сам хранит очередь
