"""Маска человека по кадрам (MediaPipe selfie multiclass) — для «текста за спиной», силуэта и замены фона.

Использование: python matte.py source.mp4 out_dir [шаг=1]
Пишет out_dir/NNNNN.png (8 бит, 540x960, 255 = человек). Уже готовые кадры не пересчитывает.
"""
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

src, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
MODEL = str(Path.home() / "video-models/mediapipe/selfie_multiclass_256x256.tflite")
opts = mp.tasks.vision.ImageSegmenterOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=MODEL),
    running_mode=mp.tasks.vision.RunningMode.VIDEO, output_confidence_masks=True)
seg = mp.tasks.vision.ImageSegmenter.create_from_options(opts)
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
prev = None
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    f = out / f"{i:05d}.png"
    if not f.exists():
        small = cv2.resize(fr, (540, 960))
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        r = seg.segment_for_video(img, int(i * 1000 / fps))
        bg = r.confidence_masks[0].numpy_view()          # класс 0 — фон, всё остальное — человек
        m = np.clip(1 - bg, 0, 1).astype(np.float32)
        m = cv2.GaussianBlur(m, (0, 0), 1.2)
        if prev is not None:                              # сглаживание только там, где маска почти не изменилась:
            w = 0.35 * (np.abs(m - prev) < 0.25)          # край не дрожит, а у движущихся рук нет «хвоста»
            m = m * (1 - w) + prev * w
        prev = m
        cv2.imwrite(str(f), (m * 255 + 0.5).astype(np.uint8))
    i += 1
print("кадров:", i)
