#!/usr/bin/env python3
"""
beat_detect.py — deteksi BPM & grid ketukan dari BGM (tanpa librosa; cukup numpy + ffmpeg)

Keluaran beats.json:
  {"bpm":96.0,"beat0":0.224,"interval":0.625,"beatTimes":[...],"beatStrengths":[...],
   "lowTimes":[...],   # kandidat kick (40-160 Hz) -> cocok untuk impact
   "bpmConfidence":0.82,"duration":52.4}

Dipakai untuk:
  * menempelkan potongan gambar ke ketukan (toleransi <= 3 frame)
  * memilih momen impact (pakai lowTimes / kekuatan >= 0.5)
  * `start: {"ref":"beat:8"}` di storyboard

Pemakaian:
  python beat_detect.py bgm.mp3 --out beats.json
  python beat_detect.py bgm.mp3 --min-bpm 70 --max-bpm 140
"""
import argparse
import json
import subprocess
import sys

import numpy as np

SR = 44100
HOP = 512                 # 11.6 ms
MIN_BPM, MAX_BPM = 60.0, 180.0


def decode(path, sr=SR):
    cmd = ["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(sr),
           "-f", "s16le", "-acodec", "pcm_s16le", "-"]
    try:
        raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    except FileNotFoundError:
        sys.exit("❌ ffmpeg tidak ditemukan.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"❌ ffmpeg gagal membaca {path}: {e}")
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return x


def envelope(x, sr=SR, hop=HOP):
    """RMS + onset (selisih positif dari log-energy) + pita rendah (kick)."""
    n = (len(x) // hop) * hop
    frames = x[:n].reshape(-1, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    log_e = np.log(rms + 1e-9)
    onset = np.maximum(0.0, np.diff(log_e, prepend=log_e[0]))

    # pita rendah 40-160 Hz (kick) memakai FFT per 4 hop
    win = 2048
    step = hop
    idx = np.arange(0, max(1, len(x) - win), step)
    low = np.zeros(len(idx))
    spec = np.zeros((len(idx), win // 2 + 1), dtype=np.float32)
    hann = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    band = (freqs >= 40) & (freqs <= 160)
    for k, i in enumerate(idx):
        seg = x[i:i + win] * hann
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        s = np.abs(np.fft.rfft(seg))
        spec[k] = s
        low[k] = s[band].mean()
    return rms, onset, low, idx / float(sr)


def tempo(onset, sr=SR, hop=HOP, lo=MIN_BPM, hi=MAX_BPM):
    """Autocorrelation onset -> BPM + confidence."""
    o = onset - onset.mean()
    if o.std() < 1e-6:
        return 120.0, 0.0
    fps_env = sr / float(hop)
    min_lag = int(fps_env * 60.0 / hi)
    max_lag = int(fps_env * 60.0 / lo)
    max_lag = min(max_lag, len(o) - 1)
    if max_lag <= min_lag:
        return 120.0, 0.0
    ac = np.correlate(o, o, mode="full")[len(o) - 1:]
    ac = ac[: max_lag + 1]
    seg = ac[min_lag:max_lag + 1]
    if seg.size == 0 or seg.max() <= 0:
        return 120.0, 0.0
    lag = int(np.argmax(seg)) + min_lag
    bpm = 60.0 * fps_env / lag
    # cek ambiguitas 0.5x / 2x: pilih yang skor normalnya tertinggi
    cands = []
    for mult in (0.5, 1.0, 2.0):
        b = bpm * mult
        if not (lo <= b <= hi):
            continue
        l = int(round(60.0 * fps_env / b))
        if 0 < l < len(ac):
            cands.append((ac[l] / (l ** 0.5), b))
    if not cands:
        return bpm, float(seg.max() / (ac.max() + 1e-9))
    cands.sort(reverse=True)
    best_bpm = cands[0][1]
    conf = float(min(1.0, cands[0][0] / (max(c[0] for c in cands) + 1e-9) * 0.6 +
                     0.4 * (cands[0][0] / (np.abs(o).mean() * len(o) + 1e-9))))
    return round(best_bpm, 2), round(min(1.0, max(0.0, conf)), 2)


def grid(onset, bpm, sr=SR, hop=HOP):
    """Cari fase terbaik lalu kembalikan waktu & kekuatan tiap ketukan."""
    fps_env = sr / float(hop)
    interval = 60.0 / bpm
    period = int(round(interval * fps_env))
    if period < 2:
        return [], []
    best_phase, best_score = 0, -1e18
    for ph in range(period):
        idxs = np.arange(ph, len(onset), period)
        score = float(onset[idxs].sum())
        if score > best_score:
            best_score, best_phase = score, ph
    idxs = np.arange(best_phase, len(onset), period)
    times = (idxs / fps_env).tolist()
    vals = onset[idxs]
    if vals.max() > 0:
        strengths = (vals / vals.max()).clip(0, 1)
    else:
        strengths = np.ones_like(vals) * 0.5
    return [round(t, 3) for t in times], [round(float(s), 3) for s in strengths]


def kick_times(low, low_t, fps_env=SR / HOP, top=24):
    """Kandidat kick: puncak lokal pita rendah."""
    if len(low) < 3:
        return []
    d = np.maximum(0.0, np.diff(low, prepend=low[0]))
    thr = d.mean() + 1.5 * d.std()
    idxs = np.where(d > thr)[0]
    if len(idxs) == 0:
        return []
    # jarak minimum 0.25 detik
    out, last = [], -10.0
    order = idxs[np.argsort(-d[idxs])][: top * 3]
    for i in sorted(order):
        t = float(low_t[min(i, len(low_t) - 1)])
        if t - last >= 0.25:
            out.append(round(t, 3))
            last = t
        if len(out) >= top:
            break
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description="Deteksi BPM & grid ketukan BGM")
    ap.add_argument("audio")
    ap.add_argument("--out", default="beats.json")
    ap.add_argument("--min-bpm", type=float, default=MIN_BPM)
    ap.add_argument("--max-bpm", type=float, default=MAX_BPM)
    args = ap.parse_args()

    x = decode(args.audio)
    dur = len(x) / float(SR)
    rms, onset, low, low_t = envelope(x)
    bpm, conf = tempo(onset, lo=args.min_bpm, hi=args.max_bpm)
    times, strengths = grid(onset, bpm)
    kicks = kick_times(low, low_t)

    data = {
        "source": args.audio,
        "duration": round(dur, 2),
        "bpm": bpm,
        "interval": round(60.0 / bpm, 5),
        "beat0": times[0] if times else 0.0,
        "beatTimes": times,
        "beatStrengths": strengths,
        "lowTimes": kicks,
        "bpmConfidence": conf,
        "fpsEnv": round(SR / float(HOP), 2),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"✅ {args.out}: BPM {bpm} (conf {conf}), {len(times)} ketukan, "
          f"{len(kicks)} kandidat kick, durasi {dur:.1f}s")


if __name__ == "__main__":
    main()
