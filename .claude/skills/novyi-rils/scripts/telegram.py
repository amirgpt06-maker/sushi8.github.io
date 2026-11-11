"""Telegram-бот для проверки рилсов.
    python telegram.py script scenario.json         — прислать сценарий: пользователь отвечает голосовым (своя запись, бесплатно)
    python telegram.py send ready/<дата>/<slug>     — отправить рилс + текст поста на проверку
    python telegram.py check                        — ответы: голосовое -> скачать в ready/…/voice.* (VOICE <путь> <scenario>),
                                                      «ок» на рилс -> status approved, другой текст -> правки
    python telegram.py whoami                       — узнать chat_id (сначала напиши боту /start)

Ключи (.env в корне или окружение): TELEGRAM_BOT_TOKEN=123:ABC…, TELEGRAM_CHAT_ID=…
Публикация в Instagram — позже (Instagram API); сейчас «ок» только помечает рилс как одобренный (status.json).
"""
import glob, json, os, sys
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tts   # подгружает .env
ROOT = tts.ROOT
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN"); CHAT = os.environ.get("TELEGRAM_CHAT_ID")
if not TOKEN: raise SystemExit("нет TELEGRAM_BOT_TOKEN в .env")
API = f"https://api.telegram.org/bot{TOKEN}/"
STATE = os.path.join(ROOT, "scenarios", "telegram_state.json")      # в git: переживает новые облачные сессии (секретов нет)
state = json.load(open(STATE)) if os.path.exists(STATE) else {"offset": 0, "sent": {}}
save = lambda: json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
OK = {"ок", "ok", "окей", "да", "публикуй", "+", "👍"}

def call(m, **kw):
    r = requests.post(API + m, timeout=300, **kw); j = r.json()
    if not j.get("ok"): raise SystemExit(f"Telegram {m}: {j}")
    return j["result"]

KW_FILE = os.path.join(ROOT, "keywords.json")
def handle_subscriber(m):
    """Ключевое слово из keywords.json -> текст и ссылка; незнакомый вопрос -> печатаем QUESTION для ответа (текст не сохраняем: репозиторий)."""
    import re
    txt = (m.get("text") or "").strip(); chat = m["chat"]["id"]
    if not txt: return
    kw = json.load(open(KW_FILE, encoding="utf-8")) if os.path.exists(KW_FILE) else {}
    low = re.sub(r"[^\w\s]", " ", txt.lower().replace("ё", "е"))
    for word, rep in kw.get("keywords", {}).items():
        if re.search(rf"(?<!\w){re.escape(word.lower().replace('ё', 'е'))}(?!\w)", low):
            body = rep["text"] + (f"\n\n{rep['link']}" if rep.get("link") else "")
            call("sendMessage", data={"chat_id": chat, "text": body, "reply_to_message_id": m["message_id"], "disable_web_page_preview": "false"})
            print("KEYWORD", word, "->", chat); return
    if txt.startswith("/start"):
        call("sendMessage", data={"chat_id": chat, "text": kw.get("welcome", "Привет! Напиши ключевое слово из рилса — пришлю материал. Или задай вопрос.")}); return
    print("QUESTION", chat, m["message_id"], txt.replace("\n", " ")[:500])
    if kw.get("ack"): call("sendMessage", data={"chat_id": chat, "text": kw["ack"], "reply_to_message_id": m["message_id"]})
cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
if cmd == "whoami":
    for u in call("getUpdates"):
        m = u.get("message") or {}; c = m.get("chat", {})
        print(c.get("id"), c.get("username"), m.get("text"))
elif cmd == "send":
    d = os.path.abspath(sys.argv[2]); post = open(os.path.join(d, "post.txt"), encoding="utf-8").read().strip()
    sc = json.load(open(os.path.join(d, "scenario.json"), encoding="utf-8"))
    cap = f"🎬 Рилс на проверку: {sc.get('topic', '')}\n\n{post}"[:1000] + "\n\nОтветь на это сообщение «ок» — опубликую. Или напиши, что поправить."
    with open(os.path.join(d, "reel.mp4"), "rb") as f:
        msg = call("sendVideo", data={"chat_id": CHAT, "caption": cap, "supports_streaming": "true", "width": 1080, "height": 1920}, files={"video": f})
    state["sent"][str(msg["message_id"])] = os.path.relpath(d, ROOT); save()
    state.setdefault("status", {})[os.path.relpath(d, ROOT)] = {"status": "sent", "tg_message": msg["message_id"]}; save()
    print("отправлено:", msg["message_id"])
elif cmd == "answer":                                  # telegram.py answer <chat_id> <message_id> "текст"
    call("sendMessage", data={"chat_id": sys.argv[2], "text": sys.argv[4], "reply_to_message_id": sys.argv[3]}); print("ответ отправлен")
elif cmd == "script":
    sc_path = os.path.abspath(sys.argv[2]); sc = json.load(open(sc_path, encoding="utf-8"))
    txt = "\n".join(l["text"] for l in sc["lines"])
    msg = call("sendMessage", data={"chat_id": CHAT, "text": f"🎙 Тема дня: {sc.get('topic', '')}\n\n{txt}\n\n"
              "Запиши это голосовым (можно своими словами, ~30–40 с) и пришли ответом на это сообщение — смонтирую рилс."})
    state.setdefault("scripts", {})[str(msg["message_id"])] = os.path.relpath(sc_path, ROOT); save(); print("сценарий отправлен:", msg["message_id"])
elif cmd == "check":
    ups = call("getUpdates", data={"offset": state["offset"] + 1, "timeout": 0})
    last_sent = max(state["sent"], key=int) if state["sent"] else None
    for u in ups:
        state["offset"] = max(state["offset"], u["update_id"])
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) != str(CHAT):          # пишет не владелец — подписчик: ключевое слово -> ссылка, иначе вопрос на ответ
            handle_subscriber(m); continue
        media = m.get("voice") or m.get("audio") or m.get("video_note") or m.get("video") or m.get("document")
        if media:                                               # голосовое на сценарий -> скачать для монтажа
            scr = state.get("scripts", {}); ref_ = str((m.get("reply_to_message") or {}).get("message_id") or (max(scr, key=int) if scr else ""))
            sc_path = scr.get(ref_)
            if not sc_path: continue
            sc_path = os.path.join(ROOT, sc_path) if not os.path.isabs(sc_path) else sc_path
            fp = call("getFile", data={"file_id": media["file_id"]})["file_path"]
            ext = os.path.splitext(fp)[1] or ".ogg"; outd = os.path.join(ROOT, "ready", "_voice"); os.makedirs(outd, exist_ok=True)
            dst = os.path.join(outd, f"{ref_}{ext}")
            open(dst, "wb").write(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}", timeout=300).content)
            call("sendMessage", data={"chat_id": CHAT, "text": "🎬 Получил голос, монтирую — пришлю на проверку.", "reply_to_message_id": m["message_id"]})
            print("VOICE", dst, sc_path); continue
        ref = str((m.get("reply_to_message") or {}).get("message_id") or last_sent or "")
        d = state["sent"].get(ref)
        if not d: continue
        s = state.setdefault("status", {}).setdefault(d, {"status": "sent"}); txt = (m.get("text") or "").strip()
        if txt.lower().strip(" .!") in OK:
            s["status"] = "approved"; call("sendMessage", data={"chat_id": CHAT, "text": "✅ Принято. Опубликую, как только подключим Instagram API.", "reply_to_message_id": m["message_id"]})
        else:
            s.setdefault("comments", []).append(txt); s["status"] = "changes"
            call("sendMessage", data={"chat_id": CHAT, "text": "✍️ Записал правки, переделаю.", "reply_to_message_id": m["message_id"]})
        print(d, "->", s["status"], txt)
    save()
