"""Разбор аккаунта Instagram: список рилсов с цифрами -> «залетевшие» -> топ-10 скачать и подготовить к разбору.

Использование:
    python akkaunt.py <ник> [--cookies reels/cookies.txt | --browser chrome] [--max 50] [--top 10] [--model large-v3-turbo]
    python akkaunt.py <ник> --list-only        # только список и цифры, без скачивания

Нужен вход: Instagram не отдаёт ленту профиля без него. Cookies запасного аккаунта — файлом cookies.txt (Netscape,
расширение «Get cookies.txt LOCALLY») или из браузера (--browser chrome — только когда скрипт запущен на компьютере с Chrome).

Результат:
    reports/<ник>/reels.json        — все рилсы: дата, просмотры, лайки, комментарии, длительность, подпись, «залетел»
    reports/<ник>/<shortcode>/      — для топ-10: кадры, контакт-листы, transcript.txt/json, data.json (видео удаляется)
Итоговый отчёт reports/<ник>.md пишет Claude по этим данным (см. SKILL.md).
"""
import argparse, json, os, random, shutil, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("nick")
ap.add_argument("--cookies"); ap.add_argument("--browser")
ap.add_argument("--max", type=int, default=50); ap.add_argument("--top", type=int, default=10)
ap.add_argument("--model", default="large-v3-turbo"); ap.add_argument("--list-only", action="store_true")
A = ap.parse_args()
A.max = min(A.max, 50)                                   # не больше 50 рилсов за раз — чтобы не заблокировали
nick = A.nick.lstrip("@").strip("/").split("/")[-1]
OUT = os.path.join("reports", nick); os.makedirs(OUT, exist_ok=True)
RAZBOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../razbor-rilsa/scripts/razbor.py")
log = lambda *a: print(*a, flush=True)
pause = lambda a=4, b=9: time.sleep(random.uniform(a, b))   # паузы между запросами

# ---------- вход по cookies ----------
import instaloader
from yt_dlp.cookies import extract_cookies_from_browser
from http.cookiejar import MozillaCookieJar
L = instaloader.Instaloader(quiet=True, sleep=True, download_pictures=False, download_videos=False, save_metadata=False,
                            max_connection_attempts=2, request_timeout=30)
if A.cookies:
    jar = MozillaCookieJar(A.cookies); jar.load(ignore_discard=True, ignore_expires=True); src = f"файл {A.cookies}"
elif A.browser:
    jar = extract_cookies_from_browser(A.browser); src = f"браузер {A.browser}"
else:
    log("ОШИБКА: нужен вход. Передай --cookies cookies.txt (запасной аккаунт) или --browser chrome."); sys.exit(2)
for c in jar:
    if "instagram.com" in c.domain: L.context._session.cookies.set_cookie(c)
me = L.test_login()
if not me:
    log(f"ОШИБКА: cookies ({src}) не дают вход в Instagram — выгрузи свежие."); sys.exit(3)
L.context.username = me
log(f"вход: @{me} ({src})")

# ---------- список рилсов ----------
prof = instaloader.Profile.from_username(L.context, nick)
log(f"@{prof.username}: {prof.followers} подписчиков, постов {prof.mediacount}")
rows = []
for post in prof.get_reels():
    if len(rows) >= A.max: break
    views = post.video_play_count or post.video_view_count
    rows.append({"shortcode": post.shortcode, "url": f"https://www.instagram.com/reel/{post.shortcode}/",
                 "date": post.date_utc.strftime("%Y-%m-%d"), "views": views, "likes": post.likes, "comments": post.comments,
                 "duration": round(post.video_duration or 0, 1), "caption": (post.caption or "")[:500]})
    log(f"  {len(rows):2d}. {rows[-1]['date']} {views} просм. {post.likes} лайков — {rows[-1]['caption'][:50]!r}")
    pause(2, 5)
vals = [r["views"] for r in rows if r["views"]]
avg = sum(vals) / len(vals) if vals else 0
for r in rows: r["viral"] = bool(r["views"] and avg and r["views"] >= 3 * avg); r["x_avg"] = round(r["views"] / avg, 2) if r["views"] and avg else None
rows.sort(key=lambda r: r["views"] or 0, reverse=True)
json.dump({"nick": prof.username, "followers": prof.followers, "avg_views": round(avg), "login": me, "reels": rows},
          open(os.path.join(OUT, "reels.json"), "w"), ensure_ascii=False, indent=1)
log(f"рилсов: {len(rows)}, в среднем {avg:.0f} просмотров, залетевших (≥3× среднего): {sum(r['viral'] for r in rows)}")
if A.list_only: sys.exit(0)

# ---------- топ: скачать, кадры, речь; видео удалить ----------
for k, r in enumerate(rows[:A.top], 1):
    d = os.path.join(OUT, r["shortcode"])
    if os.path.exists(os.path.join(d, "transcript.txt")): log(f"[{k}] {r['shortcode']} уже готов"); continue
    log(f"[{k}/{A.top}] {r['shortcode']} — {r['views']} просм.")
    cmd = [sys.executable, RAZBOR, r["url"], "--out", os.path.join(OUT, "_dl"), "--model", A.model]
    if A.cookies: cmd += ["--cookies", A.cookies]
    p = subprocess.run(cmd, capture_output=True, text=True)
    got = [l.split("ГОТОВО:", 1)[1].strip() for l in p.stdout.splitlines() if "ГОТОВО:" in l]
    if not got: log("   не скачалось:", (p.stdout + p.stderr).strip().splitlines()[-1:]); pause(); continue
    if os.path.exists(d): shutil.rmtree(d)
    shutil.move(got[0], d)
    v = os.path.join(d, "video.mp4")
    if os.path.exists(v): os.remove(v)                      # видео после разбора не храним — только кадры и отчёт
    pause()
shutil.rmtree(os.path.join(OUT, "_dl"), ignore_errors=True)
log("ГОТОВО:", OUT)
