# 08 · Remotion Patterns — Implementasi yang Aman & Cepat

Ringkasan praktis untuk proyek `remotion-app` (1080×1920, 30fps). Dokumen resmi lengkap tetap di `.agents/skills/remotion-best-practices/`.

## 1. Satu sumber kebenaran untuk waktu

```tsx
// Timeline.tsx
export const sec2f = (s: number, fps = 30) => Math.round(s * fps);

export const wordF = (w: { start: number; end: number }, fps = 30) => ({
  from: Math.round(w.start * fps),
  dur: Math.max(1, Math.round((w.end - w.start) * fps)),
});

export const SHOTS = {
  hook:  { from: 0,   duration: 90 },
  ctx:   { from: 90,  duration: 156 },
  twist: { from: 246, duration: 180 },
} as const;
```
Semua `Sequence from` ditulis `SHOTS.twist.from + offset` atau `wordF(words[i]).from`.
**Tidak ada angka telanjang** selain di dalam `SHOTS`.

## 2. Deterministik (syarat mutlak agar render ulang identik)

| Dilarang | Ganti dengan |
|---|---|
| `Math.random()` | `random("<videoId>-<idx>")` dari `remotion` |
| `Date.now()` / `new Date()` | konstanta di props |
| fetch/gambar jarak jauh saat render | `staticFile()` + aset di `public/` |
| font diunduh saat render | `@remotion/google-fonts` di-load di level modul |
| `key={Math.random()}` | `key={id}` |

## 3. `Sequence` dan durasi

- `durationInFrames` wajib eksplisit untuk `Audio` yang sampelnya > 5 detik, kalau tidak audionya akan dipotong/loop.
- Interval `Sequence` **setengah terbuka** `[from, from+duration)`: frame `from+duration` sudah tidak dirender.
- Karena itu: **animasi harus selesai sebelum `duration` habis**, kalau tidak frame puncak tidak pernah kelihatan.
- `layout="none"` untuk `Sequence` yang hanya berisi `Audio` (hemat layout).

## 4. Kapabilitas Remotion yang relevan (dan kapan dipakai)

| Fitur | Dokumen | Dipakai untuk |
|---|---|---|
| `<Audio volume={(f)=>…}>` | `remotion-markup/audio.md` | BGM fade in/out, ducking manual |
| `<Audio>` + `sequence` | `audio.md` | SFX berulang |
| `@remotion/google-fonts` | `google-fonts.md` | Anton, Permanent Marker, Space Grotesk |
| `spring()` / `interpolate()` | `effects.md` | hampir semua gerak |
| `random(seed)` | `effects.md` | partikel, glitch |
| `@remotion/shapes` (Circle/Pie/Star) | `remotion-markup/3d.md` | donut persen, bintang pemenang |
| Lottie | `lottie.md` | burst/rings/confetti (file di `public/lottie`) |
| `<Img>` + `staticFile` | `images.md` | latar, maskot, dekorasi |
| Light leak / glow | `light-leaks.md` | flash transisi |
| Multi-scene | `multi-scene-video.md` | menggabung shot |
| `calculateMetadata` | `calculate-metadata.md` | durasi dari panjang audio |
| Captions (SRT/transcribe) | `remotion-captions/` | caption dari SRT bila VO punya subtitle |
| Tailwind | `remotion-create/tailwind.md` | (opsional) styling cepat |

## 5. Performa render

- `--concurrency=4` (sudah dipakai `remotion_bridge.py`); naikkan hanya kalau RAM > 16GB.
- Kompresi per-shot dengan `useMemo` di level komposisi (contoh `buildPages(subtitles)` sudah benar).
- Hindari `filter: blur()` besar di lebih dari 2 lapisan sekaligus (mahal).
- Partikel: maks 16–24 elemen, pakai transform (bukan `top/left`).
- Jangan buat komponen baru di dalam render (`() => <X/>` inline) — bikin komponen terpisah.

## 6. Integrasi dengan pipeline Python (yang sudah ada)

`remotion_bridge.py` menulis `public/input_props_<run_id>.json` lalu menjalankan:
```bash
npx remotion render ShortsComposition out.mp4 --props=./public/input_props_<id>.json \
  --duration-in-frames=<N> --fps=30 --concurrency=4 [--browser-executable=<path>]
```

Yang ditingkatkan di versi 2:
- props sekarang juga berisi `storyboard`, `beats`, `wordFrames`, `safeArea` (lihat `02`).
- `storyboard_compile.py` menghasilkan props itu dari `STORYBOARD.json` (relatif → absolut).
- Tetap **kompatibel mundur**: field lama dipertahankan, jadi `ShortsVideo.tsx` lama tidak rusak.

## 7. Komposisi baru (opsional, bertahap)

```
src/
  Timeline.tsx         (helper waktu; salin dari remotion/Timeline.tsx)
  Transitions.tsx      (5 transisi energi; salin)
  KineticType.tsx      (kata kerja gerak; salin)
  InfographicAnim.tsx  (countup/compare/timeline/percent; salin)
  Captions.tsx         (karaoke + zona aman; salin)
  StoryboardVideo.tsx  (komposisi baru yang membaca storyboard)
  ShortsVideo.tsx      (TETAP ADA — fallback bila storyboard kosong)
```

Daftarkan dua komposisi di `Root.tsx`:
```tsx
<Composition id="ShortsComposition" component={ShortsVideo} … />      // lama
<Composition id="StoryboardComposition" component={StoryboardVideo} … /> // baru
```
Lalu tinggal ganti argumen `render` di `remotion_bridge.py`.

## 8. Kesalahan umum & obatnya

| Gejala | Penyebab | Obat |
|---|---|---|
| Teks tampil sebentar lalu hilang | animasi selesai setelah `duration` | pakai envelope IN/HOLD/OUT (lihat 05) |
| Hasil render beda tiap kali | `Math.random()` | `random(seed)` |
| Audio BGM dipotong | sampel panjang tanpa `durationInFrames` | set eksplisit |
| Font melompat | font belum ke-load saat frame pertama | load di level modul |
| Frame hitam di awal | gambar latar belum ke-decode | pakai `staticFile` + `delayRender` bila perlu |
| Render lambat | blur besar / partikel banyak | kurangi, pakai transform |
| Caption meleset | offset encoder | kompensasi `OUTPUT_AUDIO_OFFSET_F = 1.28` |
