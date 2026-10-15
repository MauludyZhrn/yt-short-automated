# 09 · QC Checklist — Gerbang Sebelum Publish

Format laporan wajib menyertakan **nomor frame** sebagai bukti: `R4 ✗ f340: impact ke-4 dalam 12 detik`.
Jangan mengubah nomor aturan; tambahkan yang baru di belakang.

> Aturan proses: **pemeriksaan pertama tidak pernah diserahkan ke user.** Jalankan sub-agent/AI lain yang tidak ikut membuat video untuk memeriksa ulang dengan daftar ini.

## A · Pra-render (jalankan `scripts/qc_check.py --pre`)

| # | Cek | Ambang |
|---|---|---|
| A1 | Durasi total | ≤ 59.5 detik (batas Shorts 60.0) |
| A2 | Naskah | 110–150 kata |
| A3 | Jumlah shot | sesuai tabel tone (`sejarah` 25–30/60s, `semesta` 15–18/60s) |
| A4 | `hold` tiap shot | ≥ 1.0s untuk shot ber-info, ≥ 0.5s untuk shot napas |
| A5 | Callout | 1 per ~6.5s, tidak di 3.4s awal & 3.2s akhir, jarak ≥ 0.5s |
| A6 | Infografis | ≥ 1 bila naskah punya angka; semua `items` valid (compare ≥2, timeline ≥2) |
| A7 | Anchor | setiap anchor ketemu di `words.json` (kalau tidak → callout dibuang) |
| A8 | Variasi aset | skor "slide show" < 4.0 (`variation_check.py`) |
| A9 | Font | semua font di-load di level modul |
| A10 | Determinisme | tidak ada `Math.random()` / `Date.now()` / fetch di `src/` |

## B · Pasca-render (jalankan `scripts/qc_check.py out.mp4`)

| # | Cek | Ambang |
|---|---|---|
| B1 | Durasi file vs rencana | simpang ≤ 2% |
| B2 | Frame hitam | sampling 10/35/65/90% → tidak ada PNG < 2 KB |
| B3 | Loudness | −14 LUFS ±1, true peak ≤ −1 dBTP |
| B4 | Bisu / clipping | `mean_volume > −60 dB`, `max_volume < −0.5 dB` |
| B5 | Ada trek audio | ffprobe menunjukkan stream audio |
| B6 | Resolusi/rasio | 1080×1920, 30fps |
| B7 | Caption sinkron | simpangan ≤ 3 frame terhadap `words.json` |
| B8 | Zona aman | tidak ada elemen penting di 320px bawah & 260px atas |

## C · Visual (frame-by-frame oleh reviewer)

| # | Cek |
|---|---|
| C1 | Hook 3 detik pertama langsung "kena" (tidak ada basa-basi) |
| C2 | Teks terbaca dalam 0.4 detik pertama kemunculannya |
| C3 | Tidak ada dua elemen besar muncul di frame yang sama (R7) |
| C4 | Transisi konsisten (≤4 kosakata) |
| C5 | Tidak ada "gambar gemetar" (shake > 3px) |
| C6 | Maskot tidak menutupi teks |
| C7 | Infografis angkanya sempat dibaca (≥0.8s setelah mendarat) |
| C8 | Outro punya ajakan + benang balik ke hook |
| C9 | Watermark & progress bar tidak mengganggu |
| C10 | Warna konsisten dengan tema niche |

## D · Audio (dengarkan)

| # | Cek |
|---|---|
| D1 | VO selalu di atas musik (tidak ada kalimat yang tenggelam) |
| D2 | Tidak ada "mesin senapan" pada rentetan SFX |
| D3 | Musik fade out sebelum video habis (0.5–1.0s) |
| D4 | Tidak ada potongan napas yang terasa salah (potong di batas kata) |
| D5 | Tidak ada kata yang terpotong di tengah suku kata |

## Cara menjalankan

```bash
# pra-render
python scripts/qc_check.py --pre --storyboard STORYBOARD.json --words words.json

# pasca-render
python scripts/qc_check.py out.mp4 --words words.json --beats beats.json --storyboard STORYBOARD.json

# audio saja
ffmpeg -i out.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

Keluaran skrip: tabel `PASS/WARN/FAIL` per butir + daftar frame bermasalah.
**Gagal (FAIL) = jangan publish**, perbaiki dan render ulang.

## Urutan perbaikan yang efisien

1. Semua `FAIL` di grup **A** (murah, tidak perlu render ulang).
2. Render draft (`--quality draft` / `--scale 0.5`) → periksa **C**.
3. Baru render final → periksa **B** dan **D**.
Jangan langsung render final sebelum A bersih.
