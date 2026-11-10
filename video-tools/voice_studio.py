"""Голос «вплотную к хорошему студийному микрофону»: обрезка пауз по краям -> match-EQ к кривой большой мембраны вблизи
(эффект близости, плотная середина, присутствие, воздух) -> гармоники -> тёплая сатурация -> де-эссер -> компрессия -> лимитер.
python voice_studio.py in out.wav T0 T1 [--amount 0.85]"""
import subprocess, sys, tempfile
import numpy as np, soundfile as sf
from scipy.signal import firwin2, fftconvolve, butter, sosfiltfilt
src, dst, T0, T1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
AM = float(sys.argv[sys.argv.index("--amount") + 1]) if "--amount" in sys.argv else 0.85
SR = 48000
x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).astype(np.float64)
x = x[int(T0 * SR):int(T1 * SR)]
x = sosfiltfilt(butter(4, 55, "hp", fs=SR, output="sos"), x)
N, hop = 4096, 1024
fr = np.lib.stride_tricks.sliding_window_view(x, N)[::hop] * np.hanning(N)
lv = 10 * np.log10((fr ** 2).mean(1) + 1e-14); sp = lv > np.percentile(lv, 50)
f = np.fft.rfftfreq(N, 1 / SR)
S = 10 * np.log10((np.abs(np.fft.rfft(fr[sp], axis=1)) ** 2).mean(0) + 1e-20)
def smooth(d, oct_=1 / 3):
    o = np.empty_like(d)
    for i, fi in enumerate(f):
        m = (f >= fi / 2 ** (oct_ / 2)) & (f <= fi * 2 ** (oct_ / 2)); o[i] = d[m].mean() if m.any() else d[i]
    return o
S = smooth(S); cur = S - S[(f > 250) & (f < 500)].mean()
# эталон: мужской голос, крупная мембрана в 5–8 см (эффект близости +2…3 дБ на 120–200 Гц), ровная середина, присутствие 3–5 кГц
TF = [20, 50, 80, 120, 180, 250, 400, 630, 1000, 1600, 2500, 3500, 5000, 6300, 8000, 10000, 12500, 16000, 20000]
TD = [-30, -12, -3, 1.5, 2.5, 1, 0, -2.5, -5.5, -8.5, -10.5, -11.5, -12.5, -14.5, -17, -20, -23, -28, -38]
tgt = np.interp(np.log10(np.maximum(f, 20)), np.log10(TF), TD)
top = f[np.where(cur > -70)[0].max()]
corr = np.clip((tgt - cur) * AM, -8, 26); corr[f < 50] = 0
corr[f > top * .97] = corr[np.argmin(np.abs(f - top * .9))]
corr = smooth(smooth(corr, 1 / 2), 1 / 3)
fir = firwin2(8191, f / (SR / 2), 10 ** (corr / 20), fs=2)
y = fftconvolve(x, fir, "full")[4095:4095 + len(x)]
# воздух: выпрямленные гармоники полосы 5–9 кГц -> 10–18 кГц
band = sosfiltfilt(butter(4, [5000, min(9000, top * .95)], "bp", fs=SR, output="sos"), y)
harm = sosfiltfilt(butter(4, 9300, "hp", fs=SR, output="sos"), np.abs(band))
y = y + harm * np.sqrt((y ** 2).mean()) / (np.sqrt((harm ** 2).mean()) + 1e-12) * 10 ** (-19 / 20)
# тёплая «ламповая» сатурация в параллель (120–900 Гц), даёт плотность и богатство
y = y / (np.abs(y).max() + 1e-9) * .5
lowmid = sosfiltfilt(butter(2, [120, 900], "bp", fs=SR, output="sos"), y)
y = y + .22 * (np.tanh(lowmid * 3.2) / 3.2 - lowmid * .55)
y = y / (np.abs(y).max() + 1e-9) * .5
tmp = tempfile.mkdtemp(); sf.write(f"{tmp}/a.wav", y.astype(np.float32), SR, subtype="FLOAT")
chain = ("deesser=i=0.45:m=0.5:f=0.5:s=o,"
         "acompressor=threshold=-24dB:ratio=3.2:attack=3:release=60:knee=4:makeup=1,"
         "acompressor=threshold=-16dB:ratio=2:attack=18:release=220:knee=6:makeup=1,"
         "equalizer=f=7200:t=q:w=2:g=-1.5,"
         "alimiter=limit=0.84:attack=3:release=40:level=disabled,loudnorm=I=-15:TP=-1.5:LRA=6,aresample=48000")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{tmp}/a.wav", "-af", chain, "-ac", "1", "-c:a", "pcm_f32le", f"{tmp}/b.wav"], check=True)
z, _ = sf.read(f"{tmp}/b.wav")
# паузы исходника остаются тихими (вдохи остаются), щелчки/фон между фразами -30 дБ
h = SR // 100; env = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(h) / h, "same") + 1e-20))
loud = env > env.max() - 52; pad = int(.09 * SR)
loud = np.convolve(loud.astype(float), np.ones(2 * pad + 1), "same") > 0
g = np.where(loud, 1, 10 ** (-30 / 20)); r = np.hanning(int(.03 * SR)); g = np.convolve(g, r / r.sum(), "same")
g = np.concatenate([np.ones(141), g])[:len(z)]
z = z[:len(g)] * g
f8 = int(.012 * SR); z[:f8] *= np.linspace(0, 1, f8); z[-int(.08 * SR):] *= np.linspace(1, 0, int(.08 * SR))
sf.write(dst, z.astype(np.float32), SR, subtype="FLOAT")
Z = np.lib.stride_tricks.sliding_window_view(z, N)[::hop] * np.hanning(N)
lz = 10 * np.log10((Z ** 2).mean(1) + 1e-14); Sz = smooth(10 * np.log10((np.abs(np.fft.rfft(Z[lz > np.percentile(lz, 50)], axis=1)) ** 2).mean(0) + 1e-20))
Sz -= Sz[(f > 250) & (f < 500)].mean()
for a, b in [(80, 150), (150, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 12000), (12000, 16000)]:
    m = (f >= a) & (f < b); print(f"{a:5d}-{b:5d}: было {cur[m].mean():6.1f}  стало {Sz[m].mean():6.1f}  эталон {tgt[m].mean():6.1f}")
