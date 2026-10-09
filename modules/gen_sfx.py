"""Generate SFX placeholder (whoosh / impact / pop) -> WAV 44.1kHz mono.
Pakai:  python gen_sfx.py remotion-app/public/sfx
Nanti file sfx asli tinggal timpa dengan nama sama (whoosh.wav, impact.wav, pop.wav).
"""
import os, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def save(path, x, peak=0.9):
    x = x / max(1e-9, np.max(np.abs(x))) * peak
    fade = int(SR * 0.004)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def whoosh(dur=0.6):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    a = 0.02 + 0.45 * t ** 2            # cutoff naik -> suara "swoosh"
    y = np.zeros(n)
    for i in range(1, n):
        y[i] = y[i - 1] + a[i] * (noise[i] - y[i - 1])
    env = np.sin(np.pi * t ** 1.4) ** 1.5
    return y * env


def impact(dur=0.9):
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 35 + 85 * np.exp(-t * 14)    # sub-bass jatuh 120 -> 35 Hz
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 4.5)
    burst = rng.standard_normal(n)
    for i in range(1, n):               # lowpass ringan
        burst[i] = burst[i - 1] + 0.25 * (burst[i] - burst[i - 1])
    burst *= np.exp(-t * 28) * 0.7
    return body + burst


def pop(dur=0.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 320 + 700 * np.exp(-t * 40)
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 22)
    click = rng.standard_normal(n) * np.exp(-t * 300) * 0.4
    return tone + click


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx"
    os.makedirs(out, exist_ok=True)
    for name, fn in (("whoosh", whoosh), ("impact", impact), ("pop", pop)):
        save(os.path.join(out, f"{name}.wav"), fn())
        print("ok", name)