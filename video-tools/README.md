# Монтаж роликов с Claude

Полностью «кодовый» монтаж: вы загружаете исходники, Claude режет, чистит звук, делает субтитры,
вертикаль и т.д. командами ffmpeg/Python. Без GUI-программ.

## Быстрый старт (в каждой новой облачной сессии)

```bash
./video-tools/setup.sh
```

## Что установлено и зачем

| Задача | Инструмент | Скрипт |
|---|---|---|
| Резка, склейка, кодирование, фильтры | **ffmpeg 6** (libx264, libass, vidstab, rnnoise, loudnorm) | все |
| Вырезать паузы / jump-cut | **auto-editor** | `cut_silence.sh` |
| Шумодав голоса | ffmpeg **arnndn** (нейросеть RNNoise) + `noisereduce` (Python) | `clean_audio.sh` |
| Громкость под YouTube/Reels (-14 LUFS), компрессор, де-эссер | ffmpeg `loudnorm`, `acompressor`, `deesser` | `clean_audio.sh` |
| Музыка с автоприглушением под голос | ffmpeg `sidechaincompress` | `music.sh` |
| Расшифровка речи → субтитры | **faster-whisper** (модели small/medium) | `transcribe.py` |
| Вшитые субтитры в стиле Shorts | ffmpeg `subtitles` + шрифт Montserrat ExtraBold (кириллица) | `burn_subs.sh` |
| Вертикаль 9:16 (crop или размытый фон) | ffmpeg | `vertical.sh` |
| Цветокоррекция / LUT (.cube) | ffmpeg `eq`, `lut3d`, `unsharp` | `color.sh` |
| Поиск склеек/сцен | **PySceneDetect** | `scenedetect -i in.mp4 detect-adaptive list-scenes` |
| Стабилизация | ffmpeg `vidstabdetect`/`vidstabtransform` | по запросу |
| Сложный монтаж кодом (титры, наложения, переходы) | **MoviePy 2**, OpenCV, Pillow | по запросу |
| Анализ звука | librosa, pyloudnorm, pydub | по запросу |

## Типичный конвейер

```bash
cd video-tools
./cut_silence.sh  raw.mp4    1_cut.mp4            # убрать паузы
./clean_audio.sh  1_cut.mp4  2_audio.mp4          # чистый громкий голос
./color.sh        2_audio.mp4 3_color.mp4         # цвет
./vertical.sh     3_color.mp4 4_vert.mp4 blur     # 9:16
~/venv-video/bin/python transcribe.py 4_vert.mp4  # -> 4_vert.srt (проверить текст!)
./burn_subs.sh    4_vert.mp4 4_vert.srt 5_subs.mp4
./music.sh        5_subs.mp4 track.mp3 final.mp4
```

## Как передавать мне видео

- Файлы до ~100 МБ можно загрузить прямо в чат/репозиторий; большие — ссылкой (Google Drive, Dropbox, YouTube)
  — но домен должен быть разрешён в сетевых настройках окружения.
- Напишите словами, что нужно: «убери паузы и эээ, субтитры жёлтым, вертикаль, музыка тихо».
- Я сделаю превью-кадры и покажу их, прежде чем рендерить финал.

## Ограничения

- **Нет GPU**: рендер и Whisper идут на CPU (4 ядра). 10 минут видео ≈ несколько минут рендера,
  Whisper medium ≈ 1–2× длительности ролика.
- **Я не вижу видео целиком** — я смотрю кадры и анализирую звук/текст. Решения «на вкус» (какой дубль лучше,
  где шутка) лучше подсказывать мне таймкодами.
- **huggingface.co** должен быть разрешён в настройках сети окружения, иначе Whisper-модели не скачаются.
- Контейнер временный: исходники и результаты нужно забирать, а `setup.sh` запускать заново.

## Альтернативные пути (если нужен GUI или другое)

- **DaVinci Resolve** (бесплатно, лучший цвет и Fairlight для звука) — на вашем компьютере; я могу готовить
  EDL/XML/субтитры для импорта.
- **CapCut** — быстро для Reels/TikTok, автосубтитры; я могу готовить сценарий и SRT.
- **Adobe Premiere + Audition / Podcast Enhance** — если есть подписка.
- **Descript** — монтаж текстом; похож на то, что делает этот набор скриптов.
- **Шумодав уровнем выше**: Adobe Podcast Enhance (онлайн), DeepFilterNet, Demucs (отделение голоса от музыки,
  нужен PyTorch).
- **Canva** подключён к этой сессии — можно делать обложки/превью.
