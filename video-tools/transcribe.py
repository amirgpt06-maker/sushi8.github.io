"""Расшифровка речи (Whisper) -> .srt субтитры и .txt текст.

Использование: python transcribe.py input.mp4 [--model medium] [--lang ru] [--max-words 4]
--max-words: сколько слов в одной строке субтитров (коротко = стиль Reels/Shorts).
"""
import argparse
import os
from pathlib import Path

from faster_whisper import WhisperModel


def ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--max-words", type=int, default=4)
    a = ap.parse_args()

    os.environ.setdefault("HF_HUB_CACHE", str(Path.home() / "video-models" / "whisper"))
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(a.input, language=a.lang, word_timestamps=True, vad_filter=True)

    words, text = [], []
    for seg in segments:
        text.append(seg.text.strip())
        words.extend(seg.words)

    base = Path(a.input).with_suffix("")
    with open(f"{base}.srt", "w", encoding="utf-8") as f:
        for i in range(0, len(words), a.max_words):
            chunk = words[i : i + a.max_words]
            line = "".join(w.word for w in chunk).strip()
            f.write(f"{i // a.max_words + 1}\n{ts(chunk[0].start)} --> {ts(chunk[-1].end)}\n{line}\n\n")
    Path(f"{base}.txt").write_text("\n".join(text), encoding="utf-8")
    print(f"{base}.srt", f"{base}.txt")


if __name__ == "__main__":
    main()
