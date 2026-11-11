"""«Блюр» нашида: слов не разобрать, остаётся только тёплый размытый фон. Спектр сглаживается по времени (≈0.4 с) со случайной фазой
(как расфокус по звуку), срез верха, без чёткой атаки. Использование: nashid_blur(y, sr) -> тот же массив, нормированный по RMS."""
import numpy as np
from scipy.signal import butter, sosfilt, stft, istft

def nashid_blur(y, sr, smooth_s=0.4, lp=900):
    y = sosfilt(butter(4, lp, "lp", fs=sr, output="sos"), y)
    n, hop = 4096, 1024
    f, t, Z = stft(y, sr, nperseg=n, noverlap=n - hop)
    mag = np.abs(Z); k = max(3, int(smooth_s * sr / hop))
    ker = np.hanning(k * 2 + 1); ker /= ker.sum()
    sm = np.apply_along_axis(lambda r: np.convolve(r, ker, "same"), 1, mag)           # сглаживание по времени — слова расплываются
    sm = np.apply_along_axis(lambda c: np.convolve(c, np.ones(5) / 5, "same"), 0, sm)  # и по частоте — нет различимых гласных
    ph = np.exp(1j * np.random.default_rng(3).uniform(0, 2 * np.pi, sm.shape))
    _, out = istft(sm * ph, sr, nperseg=n, noverlap=n - hop)
    out = np.resize(out, len(y)) if len(out) < len(y) else out[:len(y)]
    return out / (np.sqrt(np.mean(out ** 2)) + 1e-9)
