# 04 · Beat & Audio Sync — Nada, Ketukan, dan Rantai Audio ffmpeg

Gabungan **video-shotcraft** (`music-beat-sync.md`, `sound-design.md`) dan **OpenMontage** (`audio_mixer.py`, `subtitle-sync.md`).

## Waktu: dua sumber kebenaran

```ts
// voiceover-driven (wajib kalau ada narasi)
export const wordF = (words: {start:number;end:number}[], i: number, fps = 30) =>
  ({ from: Math.round(words[i].start * fps), dur: Math.round((words[i].end - words[i].start) * fps) });

// music-driven (untuk potongan tanpa narasi / transisi)
export const beatT = (n: number, beat0: number, interval: number, offsetSec = 0) =>
  beat0 + offsetSec + n * interval;
export const beatF = (n: number, beat0: number, interval: number, fps = 30, offsetSec = 0) =>
  Math.round(beatT(n, beat0, interval, offsetSec) * fps);
```

**Aturan P2**: semua `Sequence from` ditulis `wordF(words,i).from`, `beatF(n,…)`, atau `SHOTS.x.from + offset`. Detik → frame hanya di langkah terakhir.

## Kompensasi offset audio (hard rule)

Remotion 4.x + AAC 48kHz punya priming encoder ≈ 2048 sampel = **1.28 frame @30fps**. Tanpa kompensasi, pukulan terkeras datang **0.27 detik terlambat**.

```
Sequence.from = frame target − lag sumber (frame) − OUTPUT_AUDIO_OFFSET_F
OUTPUT_AUDIO_OFFSET_F = 1.28
```

Cara ukur ulang (bila ganti codec): render 2 detik test tone → `ffmpeg -i out.mp4 -af astats` → bandingkan posisi puncak.

## Deteksi ketukan

```bash
python scripts/beat_detect.py bgm.mp3 --out beats.json
# → {"bpm":96.0,"beat0":0.224,"beatTimes":[...],"beatStrengths":[...],"bpmConfidence":0.82}
```

- Algoritma: RMS onset → autocorrelation untuk BPM → grid `beat0 + n*interval` → kekuatan tiap ketukan (0–1).
- **Cek ambiguitas**: hitung coverage pada 0.5×, 1×, 2× BPM; pilih yang coverage-nya tertinggi.
- Klasifikasi transient (untuk memilih efek):
  - **kick** 40–160 Hz → slam / impact layar
  - **snare** 150–500 Hz + 1–3 kHz → flash cut / pergantian gambar
  - **hi-hat** 6–14 kHz → gerakan mikro / partikel
- Hasil di-cache ke `beats/<nama>.json`; jangan menganalisis ulang tiap render.

**Ambang mutu grid**: `match ≥ 98%`, `mean_abs_ms < 10ms`, `drift < 5ms`, residu `≤ ±15ms`.
**Ambang potongan ke ketukan**: `≤3 frame` lolos, `≤1.5 frame` ideal, `>3 frame` wajib diperbaiki.

## Menempelkan potongan ke ketukan

1. Tentukan titik potong natural dari VO (akhir kalimat / akhir kata ke-i).
2. Cari ketukan terdekat dengan kekuatan ≥ 0.5.
3. Geser potongan ke ketukan itu **hanya bila |Δ| ≤ 3 frame**. Kalau lebih, biarkan di titik VO (narasi lebih penting dari musik).
4. Jangan pernah memotong di tengah kata: geser ke batas kata terdekat lebih dulu.

## Rantai audio ffmpeg (OpenMontage, sudah teruji)

```bash
# 1) VO sudah dimaster di tts.py (EQ + kompresor + loudnorm). Jangan di-encode ulang.

# 2) Campur VO + BGM dengan ducking + limiter
ffmpeg -y -i voice.mp3 -i bgm.mp3 -filter_complex "\
[1:a]sidechaincompress=threshold=0.02:ratio=9:attack=200:release=500:level_sc=1:mix=0.9[ducked];\
[ducked]volume=0.45[music];\
[0:a][music]amix=inputs=2:duration=longest:normalize=0[mixed];\
[mixed]loudnorm=I=-14:LRA=11:TP=-1.5,aresample=48000[out]" \
-map "[out]" -c:a aac -b:a 192k -ar 48000 -ac 2 mix.m4a
```

Tiga jebakan yang wajib diingat:
1. **`amix` wajib `normalize=0`** — tanpa itu N track dibagi N (VO sendirian saja sudah −3 dB, dua track −6 dB) dan musik menang.
2. **Ducking = sidechaincompress, bukan menurunkan volume statis.** Setelah ditekan, BGM perlu kompensasi `volume = music_vol * 3`.
3. **Loudness akhir −14 LUFS / −1 dBTP** untuk YouTube/TikTok/Reels (−16 LUFS untuk podcast). Tanpa `loudnorm`, pakai minimal `alimiter=limit=1:level=0`.

**BGM per segmen** (hanya terdengar di bagian tertentu, mis. hook dan outro, senyap saat twist):

```bash
ffmpeg -y -i video_noaudio.mp4 -stream_loop -1 -i bgm.mp3 -filter_complex "\
[1:a]volume='if(lt(t,3),0,if(lt(t,4),0.15*(t-3)/1,if(lt(t,48),0.15,if(lt(t,52),0.15*(52-t)/1,0))))':eval=frame[bg];\
[0:a][bg]amix=inputs=2:duration=first:normalize=0[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k out.mp4
```

## Voice-locked typography (caption mengikuti suara)

Dari `type-rhythm-sync` (shotcraft), bentuk B = **karaoke fill sync** — paling cocok untuk Shorts narasi:

```tsx
const p = interpolate(frame, [word.start * fps, word.end * fps], [0, 1],
  { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const edge = p * (100 + FEATHER * 2) - FEATHER;      // FEATHER = 6 (%)
style = {
  backgroundImage: `linear-gradient(90deg, ${ACTIVE_COLOR} ${edge - 4}%, ${IDLE_COLOR} ${edge + 4}%)`,
  WebkitBackgroundClip: "text",
  color: "transparent",
};
```

Parameter yang sudah terkalibrasi:
- Kata aktif dapat **4–10 frame** jeda napas sebelum kata berikutnya.
- Kata panjang dapat jendela baca lebih panjang; membagi rata (seragam) terbaca sebagai "mesin membaca".
- Garis bawah kata aktif: tinggi 8px, radius 4px.
- Satu halaman caption = **3–4 kata, 2 baris**, muncul 0.15s sebelum kata pertama diucapkan.

## Self-check pasca render (tertutup loop)

```bash
ffmpeg -i out.mp4 -vn -acodec pcm_s16le -f wav /tmp/audio.wav
python scripts/qc_check.py out.mp4 --words words.json --beats beats.json
# → tabel: durasi | frame hitam | mean/max volume | drift caption
```

Ambang: durasi menyimpang >25% → alarm; tidak ada trek audio → alarm;
`mean_volume < -60 dB` → bisu; `max_volume > -0.5 dB` → clipping;
simpangan caption vs puncak suara >3 frame → daftar frame yang perlu diperbaiki.
