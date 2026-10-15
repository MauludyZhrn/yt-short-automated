# 07 · Motion Graphics System — Tema, Lapisan, Maskot, Kuota

Menyatukan `MotionGraphics.tsx`, `Fx.tsx`, `GlowFx.tsx`, `Mascot.tsx` yang sudah ada dengan sistem desain ala **HyperFrames `frame.md`** ("atoms are sacred · composition is free · numbers come from the script").

## Struktur lapisan (z-index dari bawah)

```
0  Background slideshow   (Ken Burns per slot, crossfade 0.35s)
1  Color grade            (gradient atas/bawah + vignette)
2  Tema overlay           (grid/arsip HUD, badge niche)
3  Partikel / debu        (16 partikel, seed dari indeks)
4  Film grain             (noise halus, opacity 0.06–0.1)
5  Light leak + flash     (hanya saat pergantian shot)
6  Callout / infografis   (motion graphic utama)
7  Maskot                 (reaksi, samping kiri/kanan)
8  Caption                (karaoke, zona aman bawah)
9  Hook / outro card      (3 detik awal & akhir)
10 Watermark + progress bar
```

Aturan: **lapisan 6–9 tidak pernah saling menutupi**. Kalau callout muncul, caption turun 120px atau callout dipindah ke atas (jangan bertumpuk di tengah).

## Tema (token)

| Token | `history` | `space` | `cinematic` |
|---|---|---|---|
| primary | `#F2C879` emas | `#6FE7FF` cyan | `#E8C36C` gold |
| secondary | `#B5651D` tembaga | `#8A5CFF` ungu | `#8FE3FF` es |
| tint | `rgba(120,70,20,.35)` | `rgba(20,12,80,.38)` | `rgba(0,0,0,.45)` |
| badge | ARSIP SEJARAH | DATA KOSMIK | MODE SINEMATIK |
| font display | Anton | Anton | Space Grotesk |
| font aksen | Permanent Marker | Permanent Marker | Playfair Display |

Satu video = **satu tema**. Ganti tema hanya kalau niche berubah.

## Gerak kamera

| Nama | Rumus | Dipakai di |
|---|---|---|
| punch-in hook | `scale 1.16 → 1.0` dalam 22 frame, `ease out(cubic)` | 3 detik pertama |
| kenburns | `scale 1.0 → 1.05–1.08`, arah bergantian per slot | latar |
| drift | `sin(frame/40)*0.4deg` rotasi halus | panel info |
| shake | `sin(frame/23)*2.5px`, `cos(frame/29)*2.5px` | terus-menerus, amplitudo kecil |
| cue bump | `sin(d/26 * π) * 0.022` saat callout masuk (maks 26 frame) | reaksi callout |

Amplitudo shake **tidak pernah lebih dari 3px**; lebih dari itu terbaca sebagai gempa, bukan "hidup".

## Maskot

Pose: `utama` (menunjuk) · `wow` · `berfikir` · `bertanya` · `terkejut` · `wink`.
Aturan pakai:
- **Maks 1 pose per callout**, jangan ganti pose di tengah cue.
- Maskot tidak muncul selama hook card dan outro card (fokus ke teks).
- Tinggi 620 untuk callout biasa, 470 untuk panel infografis; `bottom` 560 / 500.
- Kalau LLM tidak memberi pose, `pickPose(cue, index)` memilih dari tipe cue + indeks (deterministik).

## Kuota dekorasi (anti "murah")

| Elemen | Kuota per video |
|---|---|
| Impact layar penuh (flash/getar) | ≤3, jarak ≥6s |
| Confetti / burst | ≤2 |
| Glitch RGB | ≤2 (hanya angka) |
| Lottie (rings/twinkle/scribble) | ≤1 jenis dipakai berulang, bukan semua jenis |
| Scribble/arrow (penunjuk) | ≤3 |
| Sweep ring | ≤2 |

> "Batch elemen masuk itu bagus kalau gerakannya yang bekerja, bukan kalau tiap elemen dinyalakan satu-satu." — satu teknik masuk per shot.

## Callout: 7 tipe × 3 gaya masuk

Masuk (pilih satu per shot, bergilir): `scale+blur slam` · `slide from side` · `flip 3D kecil (rotateY 8°)`.
Keluar: **selalu via transisi shot** (T4), bukan animasi keluar.

## Progress bar & watermark

- Progress bar di paling bawah zona aman (jangan di zona mati 320px).
- Watermark: opacity 0.55, pojok, ukuran 34–46px, tidak bergerak.

## Variasi antar video (penting untuk batch)

Kalau memproduksi banyak video, **jangan pakai kombinasi yang sama terus**:
- rotasi gaya masuk callout: `(videoIndex) % 3`
- rotasi sisi maskot: `(cueIndex) % 2`
- rotasi transisi: `cut` 60–70% dominan, 1–2 aksen per video
- `random(seed)` dengan seed `"<videoId>-<cueIndex>"`, bukan `Math.random()`

## Risiko "slide show" (dari OpenMontage)

Video dinyatakan berisiko bila:
- rata-rata durasi shot > 4.5s **dan** gerak kamera statis
- ≥60% shot memakai gambar latar yang sama atau nyaris sama
- tidak ada perubahan visual > 3 detik

`scripts/variation_check.py` menghitung skor 0–10; **≥4.0 = jangan render**, ganti/ tambah aset dulu.
