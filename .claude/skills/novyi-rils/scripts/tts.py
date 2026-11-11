"""Озвучка текста голосом-клоном (ElevenLabs) или, для проверки, локальным Piper.
python tts.py "текст" out.wav [--engine elevenlabs|piper]

Ключи — из окружения или файла .env в корне репозитория:
    ELEVENLABS_API_KEY=...       (в облачной сессии можно не класть: ключ подставляет прокси, сохранённый через форму)
    ELEVENLABS_VOICE_ID=...      (id клонированного голоса)
    ELEVENLABS_MODEL=eleven_multilingual_v2
"""
import os, subprocess, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
def load_env():
    f = os.path.join(ROOT, ".env")
    if os.path.exists(f):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

def elevenlabs(text, out):
    import requests
    vid = os.environ.get("ELEVENLABS_VOICE_ID")
    if not vid: raise SystemExit("нет ELEVENLABS_VOICE_ID (id голоса-клона) в .env")
    key = os.environ.get("ELEVENLABS_API_KEY", "proxy-injects-key")       # в облаке ключ подставляет прокси
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_192",
                      headers={"xi-api-key": key, "Content-Type": "application/json"}, timeout=180,
                      json={"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
                            "voice_settings": {"stability": 0.45, "similarity_boost": 0.85, "style": 0.25, "use_speaker_boost": True}})
    if r.status_code != 200: raise SystemExit(f"ElevenLabs {r.status_code}: {r.text[:300]}")
    mp3 = out + ".mp3"; open(mp3, "wb").write(r.content)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "48000", out], check=True); os.remove(mp3)

def piper(text, out):
    model = os.path.expanduser("~/video-models/tts/ruslan/ru_RU-ruslan-medium.onnx")
    exe = "/root/venv-video/bin/piper" if os.path.exists("/root/venv-video/bin/piper") else "piper"
    subprocess.run([exe, "-m", model, "--length_scale", "1.0", "-f", out], input=text.encode(), check=True, capture_output=True)

def speak(text, out, engine=None):
    engine = engine or os.environ.get("TTS_ENGINE") or ("elevenlabs" if os.environ.get("ELEVENLABS_VOICE_ID") else "piper")
    (elevenlabs if engine == "elevenlabs" else piper)(text, out)
    return engine

if __name__ == "__main__":
    eng = sys.argv[sys.argv.index("--engine") + 1] if "--engine" in sys.argv else None
    print(speak(sys.argv[1], sys.argv[2], eng))
