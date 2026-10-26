# Рыцарь против Ти-Рекса: план и промпты

Исходник: 9,5 с, 1920×1080, 30 fps, человек в комнате имитирует бой, камера в руках.
Подготовлено: `source-h264.mp4` (тот же ролик в H.264, его принимают все сервисы), `ref-frame.jpg` (опорный кадр).

## Чем делать

Реалистичная замена костюма и добавление динозавра с сохранением движений — это задача генеративного
видео-в-видео (video-to-video). Лучше всего сейчас подходят:

| Сервис | Что использовать | Почему |
|---|---|---|
| **Runway** (runwayml.com) | Gen-4 **Aleph** — редактирование видео по тексту | Меняет одежду, окружение и добавляет объекты, сохраняя движения и камеру. Лучший вариант для этого ролика |
| **Kling** (klingai.com) | Video Edit / Elements | Сильный реализм, хорошие существа |
| **Luma** (lumalabs.ai) | Modify Video | Сохраняет хореографию, меняет внешний вид |
| **Wan 2.x VACE** (через fal.ai) | video-to-video с маской | Можно запустить по API |

Длина одной генерации обычно 5–10 с, поэтому ролик удобно делать двумя кусками: 0–5 с и 5–9,5 с.

## Промпты (английский — сервисы понимают его лучше)

**Шаг 1. Рыцарь** (весь ролик):

> Transform the man into a medieval knight in full realistic steel plate armor with chainmail, a weathered red tabard and a battle-worn open-face helmet. He holds a long wooden spear with a steel tip in both hands, following his exact movements. Replace the living room with a misty prehistoric forest clearing at golden hour, ferns, giant trees, volumetric light. Photorealistic, cinematic, 35mm film, shallow depth of field, natural motion blur. Keep the original camera movement and body motion exactly.

**Шаг 2. Динозавр** (на результат шага 1):

> Add a massive photorealistic Tyrannosaurus rex fighting the knight, attacking from the right side of the frame, roaring and snapping its jaws. The knight dodges and thrusts the spear. Realistic scaly skin, scars, heavy footsteps shaking the ground, dust and debris. Cinematic, photorealistic, consistent lighting.

**Шаг 3. Ранение** (финальные 2–3 с):

> The knight drives the spear deep into the Tyrannosaurus rex's shoulder. The dinosaur recoils and roars in pain, staggering back, dust flying. Dramatic slow motion, cinematic lighting, photorealistic.

Если сервис просит один промпт — объединить шаги 1 и 2.

## Что сделаю я после генерации

Пришлите полученные куски — я:
- склею их, выровняю цвет между кусками и сделаю киношную цветокоррекцию;
- добавлю звук: рёв, тяжёлые шаги, звон доспехов, удар копья, атмосферу леса;
- сделаю замедление в момент удара, тряску камеры, финальный титр;
- выдам версии 16:9 и 9:16 для Reels/Shorts.
