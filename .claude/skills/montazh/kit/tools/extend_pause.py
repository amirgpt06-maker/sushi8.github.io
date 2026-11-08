"""Удлинить паузу диктора (только если пользователь разрешил): вставить тишину в паузу голоса, слова не трогаются.
Использование: python extend_pause.py папка_проекта время_в_паузе секунд   (например 16.6 1.6)
Переписывает voice.wav и сдвигает времена в words.json после точки вставки."""
import json, sys
import numpy as np, soundfile as sf
P, at, gap = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
x, sr = sf.read(f"{P}/voice.wav")
i = int(round(at * sr))
win = x[max(0, i - sr // 20): i + sr // 20]
if np.abs(win).max() > 0.02:
    sys.exit(f"в точке {at} с не пауза (там звук) — выбери время внутри паузы")
sf.write(f"{P}/voice.wav", np.concatenate([x[:i], np.zeros(int(round(gap * sr)), x.dtype), x[i:]]), sr, subtype="PCM_16")
w = json.load(open(f"{P}/words.json"))
for k in ("words", "phrases"):
    for e in w.get(k, []):
        for t in ("t0", "t1"):
            if e[t] >= at: e[t] = round(e[t] + gap, 3)
json.dump(w, open(f"{P}/words.json", "w"), ensure_ascii=False)
print(f"вставлено {gap} с тишины в {at} с; новая длина {len(x) / sr + gap:.2f} с")
