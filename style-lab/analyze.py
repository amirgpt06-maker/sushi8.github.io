"""Анализ стиля монтажа референс-роликов: склейки, цвет, движение, звук, текст (OCR) -> style.json.

Использование: python analyze.py out_dir video1.mp4 [video2.mp4 ...]
Пишет out_dir/report.json и out_dir/<имя>/keyframes.png (кадры на склейках).
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import librosa
import numpy as np
from scenedetect import ContentDetector, detect
from sklearn.cluster import KMeans

OUT = Path(sys.argv[1])
VIDEOS = [Path(p) for p in sys.argv[2:]]


def ff(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def palette(frames, k=6):
    px = np.concatenate([cv2.resize(f, (48, 80)).reshape(-1, 3) for f in frames]).astype(np.float32)
    km = KMeans(k, n_init=3, random_state=0).fit(px[:: max(1, len(px) // 20000)])
    cnt = np.bincount(km.predict(px), minlength=k) / len(px)
    order = np.argsort(-cnt)
    return [{"hex": "#%02x%02x%02x" % tuple(int(c) for c in km.cluster_centers_[i][::-1]), "share": round(float(cnt[i]), 3)} for i in order]


def analyze(path):
    d = OUT / path.stem
    d.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(3)), int(cap.get(4))
    dur = n / fps
    rep = {"file": path.name, "size": [w, h], "fps": fps, "duration": round(dur, 2)}

    # --- склейки: два детектора (жёсткие и быстрые, в т.ч. «вспышки») ---
    scenes = detect(str(path), ContentDetector(threshold=18, min_scene_len=int(fps * 0.15)))
    cuts = [round(s[0].get_seconds(), 2) for s in scenes][1:]
    lens = np.diff([0] + cuts + [dur])
    rep["cuts"] = cuts
    rep["shots"] = {"count": len(lens), "avg_len": round(float(lens.mean()), 2), "median": round(float(np.median(lens)), 2),
                    "min": round(float(lens.min()), 2), "max": round(float(lens.max()), 2), "cuts_per_10s": round(len(cuts) / dur * 10, 1)}

    # --- покадровый анализ (каждый 2-й кадр): яркость/контраст/насыщенность, движение, зум ---
    lum, sat, motion, zoom, frames_small = [], [], [], [], []
    prev = None
    idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if idx % 2 == 0:
            sm = cv2.resize(bgr, (216, 384))
            g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV)
            lum.append(g.mean() / 255)
            sat.append(hsv[..., 1].mean() / 255)
            if prev is not None:
                fl = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 2, 15, 2, 5, 1.1, 0)
                motion.append(float(np.linalg.norm(fl, axis=2).mean()))
                # расходимость потока от центра: >0 — наезд, <0 — отъезд
                yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
                rx, ry = xx - g.shape[1] / 2, yy - g.shape[0] / 2
                zoom.append(float(((fl[..., 0] * rx + fl[..., 1] * ry) / (np.hypot(rx, ry) + 1)).mean()))
            else:
                motion.append(0.0)
                zoom.append(0.0)
            prev = g
            if idx % int(fps) == 0:
                frames_small.append(sm)
        idx += 1
    t = np.arange(len(lum)) * 2 / fps
    lum, sat, motion, zoom = map(np.array, (lum, sat, motion, zoom))
    sorted_l = np.sort(lum)
    rep["color"] = {"mean_luma": round(float(lum.mean()), 3), "luma_p10_p90": [round(float(np.percentile(lum, 10)), 3), round(float(np.percentile(lum, 90)), 3)],
                    "mean_saturation": round(float(sat.mean()), 3), "palette": palette(frames_small)}
    rep["motion"] = {"mean": round(float(motion.mean()), 3), "p90": round(float(np.percentile(motion, 90)), 3),
                     "punch_in_events": [round(float(x), 2) for x in t[zoom > np.percentile(zoom, 96)]][:12],
                     "flash_frames": [round(float(x), 2) for x in t[np.r_[0, np.diff(lum)] > 0.12]][:12]}

    # --- кадры на склейках (до/после) для просмотра ---
    pts = sorted(set([0.3] + [c + 0.05 for c in cuts] + [dur - 0.3]))
    tiles = []
    for p in pts[:24]:
        cap.set(cv2.CAP_PROP_POS_MSEC, p * 1000)
        ok, fr = cap.read()
        if ok:
            tiles.append(cv2.resize(fr, (216, 384)))
    if tiles:
        cols = 8
        while len(tiles) % cols:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(str(d / "keyframes.png"), np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]))

    # --- звук ---
    wav = d / "audio.wav"
    ff("-i", str(path), "-vn", "-ac", "1", "-ar", "22050", str(wav))
    y, sr = librosa.load(str(wav), sr=22050)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    ot = librosa.times_like(onset, sr=sr)
    rms = librosa.feature.rms(y=y)[0]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    # переходные пики (SFX-удары) рядом со склейками
    pk = np.where((onset > np.percentile(onset, 97)) & (onset == np.maximum.reduce([np.roll(onset, k) for k in range(-4, 5)])))[0]
    pk_t = ot[pk]
    near = [round(float(np.min(np.abs(np.array(cuts) - p))), 2) for p in pk_t] if cuts else []
    ebu = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = next((float(l.split("I:")[1].split("LUFS")[0]) for l in ebu.splitlines()[::-1] if "I:" in l and "LUFS" in l), None)
    rep["audio"] = {"lufs": lufs, "tempo_bpm": round(float(np.atleast_1d(tempo)[0]), 1), "mean_centroid_hz": int(cent.mean()),
                    "dynamic_range_db": round(float(20 * np.log10(np.percentile(rms, 95) / (np.percentile(rms, 10) + 1e-6))), 1),
                    "transient_hits": len(pk_t), "hits_within_0.12s_of_cut": int(sum(1 for x in near if x < 0.12)),
                    "speech_like_ratio": round(float(np.mean((rms > np.percentile(rms, 30)) & (cent < 3500))), 2)}

    # --- текст (OCR) раз в 0.5 с: слова и время появления ---
    texts = []
    for tt in np.arange(0.2, dur, 0.5):
        cap.set(cv2.CAP_PROP_POS_MSEC, tt * 1000)
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(g, 200, 255, cv2.THRESH_BINARY)       # светлый текст
        cv2.imwrite(str(d / "ocr_tmp.png"), cv2.bitwise_not(bw))
        out = subprocess.run(["tesseract", str(d / "ocr_tmp.png"), "-", "-l", "rus+eng", "--psm", "11"], capture_output=True, text=True).stdout
        words = [x for x in out.replace("\n", " ").split() if len(x) > 2 and sum(c.isalpha() for c in x) >= 3]
        if words:
            texts.append({"t": round(float(tt), 1), "text": " ".join(words)[:80]})
    (d / "ocr_tmp.png").unlink(missing_ok=True)
    rep["text_ocr"] = texts
    return rep


reports = [analyze(v) for v in VIDEOS]
json.dump(reports, open(OUT / "report.json", "w"), ensure_ascii=False, indent=1)
for r in reports:
    print(json.dumps({k: r[k] for k in ("file", "duration", "shots", "color", "motion", "audio")}, ensure_ascii=False))
