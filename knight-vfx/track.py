"""Трекинг человека: скелет (33 точки, 2D+3D), руки, поза головы, маски силуэта/одежды/кожи.

Использование: python track.py source.mp4 work_dir
Пишет: work/frames/%04d.png, work/masks/{person,clothes,skin,hair}_%04d.png, work/track.json
"""
import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

M = Path.home() / "video-models" / "mediapipe"


def main():
    src, work = sys.argv[1], Path(sys.argv[2])
    for d in ("frames", "masks"):
        (work / d).mkdir(parents=True, exist_ok=True)
    VM = vision.RunningMode.VIDEO
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(M / "pose_landmarker_heavy.task")), running_mode=VM,
        output_segmentation_masks=True, min_pose_detection_confidence=0.5, min_tracking_confidence=0.5))
    hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(M / "hand_landmarker.task")), running_mode=VM, num_hands=2))
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(M / "face_landmarker.task")), running_mode=VM,
        output_facial_transformation_matrixes=True, num_faces=1))
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(M / "selfie_multiclass_256x256.tflite")), running_mode=VM,
        output_category_mask=False, output_confidence_masks=True))

    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = {"fps": fps, "frames": []}
    i = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        h, w = bgr.shape[:2]
        cv2.imwrite(str(work / "frames" / f"{i:04d}.png"), bgr)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        ts = int(i * 1000 / fps)
        fr = {"i": i}
        r = pose.detect_for_video(img, ts)
        if r.pose_landmarks:
            fr["pose"] = [[p.x * w, p.y * h, p.z, p.visibility] for p in r.pose_landmarks[0]]
            fr["world"] = [[p.x, p.y, p.z] for p in r.pose_world_landmarks[0]]
            m = (r.segmentation_masks[0].numpy_view() * 255).astype(np.uint8)
            cv2.imwrite(str(work / "masks" / f"person_{i:04d}.png"), m)
        r = hands.detect_for_video(img, ts)
        fr["hands"] = [{"side": hd[0].category_name, "pts": [[p.x * w, p.y * h] for p in lm]}
                       for hd, lm in zip(r.handedness, r.hand_landmarks)]
        r = face.detect_for_video(img, ts)
        if r.face_landmarks:
            fr["face"] = [[p.x * w, p.y * h] for p in r.face_landmarks[0]]
            fr["face_mat"] = np.array(r.facial_transformation_matrixes[0]).tolist()
        r = seg.segment_for_video(img, ts)
        # классы: 0 фон, 1 волосы, 2 кожа тела, 3 кожа лица, 4 одежда, 5 прочее
        cm = [c.numpy_view() for c in r.confidence_masks]
        for name, idx in (("hair", [1]), ("skin", [2, 3]), ("clothes", [4, 5])):
            m = np.clip(sum(cm[k] for k in idx), 0, 1)
            cv2.imwrite(str(work / "masks" / f"{name}_{i:04d}.png"), (m * 255).astype(np.uint8))
        out["frames"].append(fr)
        i += 1
        if i % 50 == 0:
            print("кадр", i, flush=True)
    out["size"] = [w, h]
    json.dump(out, open(work / "track.json", "w"))
    print("готово, кадров:", i)


if __name__ == "__main__":
    main()
