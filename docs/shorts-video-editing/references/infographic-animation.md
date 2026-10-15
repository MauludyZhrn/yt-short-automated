# 06 · Infographic Animation — Data yang Bergerak

Sumber: **HyperFrames** (`count-up`, `animated-bar-chart`, `conic-progress-ring`, `bar-chart-race`) + `Infographic.tsx` yang sudah ada di proyek + kuota callout dari `motion_cues.py`.

## Empat tipe yang didukung

| Tipe | Data | Kapan dipakai | Durasi |
|---|---|---|---|
| `percent` | angka 0–100 | "73% permukaan bumi" | 3.4s |
| `compare` | 2–3 `{label,value}` | perbandingan ukuran/jarak/jumlah | 4.0s |
| `timeline` | 2–4 `{year,label}` | urutan peristiwa | 4.4s |
| `year` / `stat` | angka tunggal | tahun, jarak, jumlah | 2.8s / 3.0s |
| `keyword` / `question` | teks pendek | istilah kunci, pertanyaan pancing | 2.4s / 2.6s |

Aturan `cue_planner.py`: tanpa data yang valid, `percent/compare/timeline` **turun kelas** jadi `keyword` (lebih baik teks biasa daripada grafik kosong).

## Envelope waktu (sama untuk semua tipe)

```
IN_BASE   = 0.35s  panel masuk + counting mulai
COUNT     = 0.6–0.9s (ease out(cubic), bukan linear — linear terbaca "robot")
LAND_PULSE= 0.10s  skala 1 → 1.04 → 1 saat angka mendarat
HOLD      = sisa   minimal 0.8s (angka harus sempat dibaca)
OUT_BASE  = 0.25s
```

`countup` untuk angka besar: **jangan** mulai dari 0 bila nilainya 13.8 miliar (terlalu lama). Mulai dari `value * 0.6` atau pakai "rolling digits" 3 digit terakhir saja.

## Aturan per tipe

**percent (donut)**
- Lingkaran `Pie` dengan `strokeLinecap="round"`, mulai dari −90°.
- Angka di tengah memakai `tabular-nums`; tanda `%` berukuran 0.53× angka utama.
- `sub` (keterangan) di bawah, maks 4 kata, font marker.
- Warna: `primary` untuk isi, `rgba(255,255,255,0.12)` untuk relung.

**compare (batang horizontal)**
- Maks 3 baris. Baris pemenang = warna aksen + bintang berputar di ujung batang.
- Lebar batang = `value / max * BAR_W * spring` — **spring, bukan linear**.
- Stagger antar baris 9 frame (bukan bersamaan) supaya mata mengikuti urutan.
- Satuan (`sub`) ditulis kecil di belakang angka, bukan di judul.

**timeline (garis waktu)**
- Garis tumbuh kiri→kanan (`ease out(cubic)`, 6 → 14 + n*12 frame).
- Titik muncul stagger 12 frame; label bergantian atas/bawah supaya tidak bertabrakan.
- Maks 4 titik. Tahun 92px, label 34px — kalau label >4 kata, potong (tulis ulang di naskah).

**year / stat**
- `GlitchText` saat menghantam (14 frame) lalu diam. Tahun = angka saja, tanpa kata "tahun".
- Untuk `stat`: angka + satuan lengkap yang dieja TTS-nya (`384.400 KILOMETER`).

## Panel & dekorasi

- `InfoPanel`: kaca gelap + grid, border 5px warna tema, selotip kuning miring −9°, drop shadow ganda.
- Dekorasi `scrap`: `paper_photo` (untuk compare) / `paper_text` (untuk percent). **Maks 1 dekorasi per panel.**
- Maskot muncul di samping panel dengan pose sesuai cue (`pickPose`), tinggi 470 untuk panel info.

## Keterbacaan (wajib)

- Angka utama ≥ 150px di frame 1080 lebar.
- `font-variant-numeric: tabular-nums` di semua angka yang berhitung.
- Kontras teks terhadap panel ≥ 4.5:1.
- Jangan menaruh infografis di **zona mati bawah (300–320px)** atau terlalu dekat dengan caption.

## Penempatan & kuota

- Callout/infografis **1 per ~6.5 detik** (`CUE_PER_SECONDS = 6.5`), maks `total // 6.5`.
- Tidak masuk ke 3.4 detik pertama (hook card) dan 3.2 detik terakhir (outro card).
- Jarak antar callout minimal 0.5 detik; tidak ada dua infografis berurutan tanpa shot napas di antaranya (R5).
- Minimal **1 infografis per video** bila naskah memuat angka/urutan/perbandingan.
- Posisi kiri/kanan (`side`) bergantian supaya tidak monoton.

## Anchor ke naskah

Tiap callout punya `anchor` (1–3 kata persis seperti di naskah) → `cue_planner.py` mencari indeks kata di `words.json` → `start = words[idx].start − 0.15` (PRE_ROLL).
Kalau anchor tidak ketemu: coba kata pertama saja; kalau tetap tidak ada, **buang callout** (jangan ditebak posisinya).

## Contoh JSON callout siap render

```json
[
  {"type":"year","verb":"slam","text":"1518","sub":"Strasbourg","start":3.62,"end":6.42,"pose":"wow"},
  {"type":"percent","verb":"countup","text":"73%","sub":"Permukaan bumi","start":11.2,"end":14.6},
  {"type":"compare","verb":"grow","text":"UKURAN","sub":"km","start":21.0,"end":25.0,
   "items":[{"label":"Bumi","value":12742},{"label":"Bulan","value":3474}]},
  {"type":"timeline","verb":"draw","text":"LINIMASA","start":31.5,"end":35.9,
   "items":[{"year":"1518","label":"Wabah mulai"},{"year":"1519","label":"Mereda"}]}
]
```
