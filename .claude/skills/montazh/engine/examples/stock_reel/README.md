# Рилс из стока под озвучку («такси»)

Порядок (пути внутри скриптов — к рабочей папке; поменять `HERE`, `PACK`, `FONTS` под себя):

1. Голос: `python video-tools/voice_studio.py voice.mp3 work/voice_studio.wav T0 T1 --amount 1.0`
   (T0/T1 — начало и конец речи: паузы по краям срезаются), затем `python video-tools/words.py work/voice_studio.wav work/words2.json`.
2. Сток (Mixkit, 1080p) — в `src/{id}.mp4`; кадры еды для экранов — в `ui/img/*.jpg`; `ui/fonts` — ссылка на папку шрифтов SF Pro / Playfair.
3. Экраны: `node ui/render_ui.js <сцена> <длительность> work/ui/<сцена> <1=прозрачный фон>` для каждой сцены из `compose.py`.
4. Видео: `python compose.py work/video.mp4` (проверка кадров: `python compose.py work/prev/f --frames 10,200,900`).
5. Звук: `python audio.py` -> `work/mix.wav` (−14 LUFS). Склейка: `ffmpeg -i work/video.mp4 -i work/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -map_metadata -1 -movflags +faststart final.mp4`.
6. Обложка: `python cover.py`.

Стоковые ролики, кадры, шрифты и звуки пака в репозиторий не кладём.
