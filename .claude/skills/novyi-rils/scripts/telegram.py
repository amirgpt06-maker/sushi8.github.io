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
STATE = os.path.join(ROOT, "ready", "telegram_state.json")
state = json.load(open(STATE)) if os.path.exists(STATE) else {"offset": 0, "sent": {}}
save = lambda: json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
OK = {"ок", "ok", "окей", "да", "публикуй", "+", "👍"}

def call(m, **kw):
    r = requests.post(API + m, timeout=300, **kw); j = r.json()
    if not j.get("ok"): raise SystemExit(f"Telegram {m}: {j}")
    return j["result"]

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
    st = os.path.join(d, "status.json"); s = json.load(open(st)); s.update(status="sent", tg_message=msg["message_id"]); json.dump(s, open(st, "w"))
    print("отправлено:", msg["message_id"])
elif cmd == "script":
    sc_path = os.path.abspath(sys.argv[2]); sc = json.load(open(sc_path, encoding="utf-8"))
    txt = "\n".join(l["text"] for l in sc["lines"])
    msg = call("sendMessage", data={"chat_id": CHAT, "text": f"🎙 Тема дня: {sc.get('topic', '')}\n\n{txt}\n\n"
              "Запиши это голосовым (можно своими словами, ~30–40 с) и пришли ответом на это сообщение — смонтирую рилс."})
    state.setdefault("scripts", {})[str(msg["message_id"])] = sc_path; save(); print("сценарий отправлен:", msg["message_id"])
elif cmd == "check":
    ups = call("getUpdates", data={"offset": state["offset"] + 1, "timeout": 0})
    last_sent = max(state["sent"], key=int) if state["sent"] else None
    for u in ups:
        state["offset"] = max(state["offset"], u["update_id"])
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) != str(CHAT): continue
        media = m.get("voice") or m.get("audio") or m.get("video_note") or m.get("video") or m.get("document")
        if media:                                               # голосовое на сценарий -> скачать для монтажа
            scr = state.get("scripts", {}); ref_ = str((m.get("reply_to_message") or {}).get("message_id") or (max(scr, key=int) if scr else ""))
            sc_path = scr.get(ref_)
            if not sc_path: continue
            fp = call("getFile", data={"file_id": media["file_id"]})["file_path"]
            ext = os.path.splitext(fp)[1] or ".ogg"; outd = os.path.join(ROOT, "ready", "_voice"); os.makedirs(outd, exist_ok=True)
            dst = os.path.join(outd, f"{ref_}{ext}")
            open(dst, "wb").write(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}", timeout=300).content)
            call("sendMessage", data={"chat_id": CHAT, "text": "🎬 Получил голос, монтирую — пришлю на проверку.", "reply_to_message_id": m["message_id"]})
            print("VOICE", dst, sc_path); continue
        ref = str((m.get("reply_to_message") or {}).get("message_id") or last_sent or "")
        d = state["sent"].get(ref)
        if not d: continue
        st = os.path.join(ROOT, d, "status.json"); s = json.load(open(st)); txt = (m.get("text") or "").strip()
        if txt.lower().strip(" .!") in OK:
            s["status"] = "approved"; call("sendMessage", data={"chat_id": CHAT, "text": "✅ Принято. Опубликую, как только подключим Instagram API.", "reply_to_message_id": m["message_id"]})
        else:
            s.setdefault("comments", []).append(txt); s["status"] = "changes"
            call("sendMessage", data={"chat_id": CHAT, "text": "✍️ Записал правки, переделаю.", "reply_to_message_id": m["message_id"]})
        json.dump(s, open(st, "w"), ensure_ascii=False); print(d, "->", s["status"], txt)
    save()
