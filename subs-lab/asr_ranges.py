"""Распознать заданные отрезки: python asr_ranges.py audio16k.wav lang "t0-t1,t0-t1,..." """
import sys
from pathlib import Path

import sherpa_onnx
import soundfile as sf

M = Path.home() / "video-models" / "asr" / "sherpa-onnx-whisper-turbo"
x, sr = sf.read(sys.argv[1], dtype="float32")
r = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=str(M / "turbo-encoder.int8.onnx"), decoder=str(M / "turbo-decoder.int8.onnx"),
                                               tokens=str(M / "turbo-tokens.txt"), language=sys.argv[2], task="transcribe", num_threads=4, tail_paddings=800)
for rg in sys.argv[3].split(","):
    a, b = map(float, rg.split("-"))
    st = r.create_stream()
    st.accept_waveform(sr, x[int(a * sr):int(b * sr)])
    r.decode_stream(st)
    print(f"{a:6.2f}-{b:6.2f} [{sys.argv[2]}] {st.result.text.strip()}", flush=True)
