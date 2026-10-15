# 01 · Content Blueprint — Ide Konten & Struktur Naskah

Dua niche yang didukung mesin ini. Semua aturan di bawah mengubah "ide konten" menjadi parameter editing yang bisa dihitung.

## Dua niche, dua tone, dua tabel ritme

| | **Fakta Sejarah** | **Misteri Alam Semesta** |
|---|---|---|
| Tone (OpenMontage) | `wry` (sinis ringan, cepat) | `reverent` (kagum, lambung) |
| Hold dasar / shot | **2.0s** (min 1.2 / max 3.5) | **3.5s** (min 2.5 / max 6.0) |
| Shot per 60s | ~25–30 | ~15–18 |
| Palet | emas tua `#F2C879` + tembaga `#B5651D`, kertas/arsip | cyan `#6FE7FF` + ungu `#8A5CFF`, grid HUD |
| Metafora visual | arsip, cap stempel, kertas robek, peta kuno | peta bintang, orbit, skala jarak, HUD data |
| Musik | drone + perkusi ringan, 90–110 BPM | ambient swell, 70–95 BPM, tanpa perkusi tajam |
| Suara (edge-tts) | `id-ID-ArdiNeural` (tegas) | `id-ID-GadisNeural` / Ardi + prosodi pelan |

> Rumus hold: `hold = base`, lalu **total durasi harus tertutup ke target ±10%**: kelebihan dikurangi dari shot non-hero, kekurangan ditambah ke hero shot (hook, twist, outro). **Hero shot tidak pernah dikompresi.**

## Struktur naskah (wajib, 125–145 kata)

1. **HOOK** (2 kalimat, ≤25 kata) — fakta paling gila, tanpa basa-basi. Dilarang: "Tahu nggak", "Halo guys", "Pernah nggak lo".
2. **KONTEKS** (2–3 kalimat) — siapa/apa/kapan.
3. **BODY** (3 bagian eskalasi × 3–4 kalimat) — tiap bagian lebih gila dari sebelumnya, penuh angka konkret.
4. **RE-HOOK tengah** (1 kalimat) — "Tapi tunggu, bagian paling gila belum lo dengar."
5. **TWIST** (3–4 kalimat) — puncak.
6. **OUTRO** (2 kalimat) — pancing komentar + nyambung balik ke hook (dorong replay).

Panjang: 125–145 kata ≈ 48–56 detik pada 2.6 kata/detik. Hard cap 150 kata.

## Energy arc (porsi durasi)

| Segmen | Porsi | Energy | Apa yang terjadi secara visual |
|---|---|---|---|
| ① Hook | 8–12% | `high` | punch-in zoom, hook card 3s, flash 0.2s |
| ② Setup/konteks | 12–15% | `low→medium` | Ken Burns pelan, badge tema muncul |
| ③ Rantai fakta | 55–65% | `medium` ↔ `high` bergantian | callout tiap ~6.5s, 1 infografis wajib |
| ④ Penutup | 13–16% | `medium→low` | outro card 3s, logo, CTA, musik fade out |

Aturan: **naik-turun energi harus bergantian** di segmen ③ (fakta → napas → fakta → napas). Dua shot `high` berturut-turut = penonton lelah.

## Slot visual: deskripsi bukan kata kunci

Biar mesin pencari stok (Pexels) dan CLIP tidak meleset, tiap shot menulis **dua hal**:

```jsonc
{
  "description": "a stone dungeon corridor, torchlight flicker, damp texture, warm low-key light",
  "queries": ["stone dungeon corridor", "medieval torch light"]
}
```

- `description`: `<subject>, <action>, <environment>, <lighting>, <texture>` — kata benda + sifat, **tanpa kata emosi dan tanpa kata kerja niat**.
- `queries`: 2–3 query pendek (2–5 kata), bahasa Inggris, konkret. Dilarang "hyper-realistic / 8k / cinematic lighting".

## Bank ide konten (per niche)

**Fakta Sejarah** — wabah menari 1518 · peta bintang Portugis 1521 · Perpustakaan Alexandria · kode Navajo · jembatan manusia Roma · roti beracun Salem · prajurit-tertanam Pompeii · mata-mata wanita Soviet · surat-mati-cinta abad 17 · granat tangan pertama · kapal selam tahun 1600-an · kota yang hilang di hutan Amazon.

**Misteri Alam Semesta** — bintang yang "bernyanyi" · planet hujan besi · lubang hitam yang lebih tua dari galaksi · cahaya yang tertunda 13 miliar tahun · materi gelap 27% · pulsar bumerang · bulan yang menyusut · suara dari luar tata surya · gugusan bintang kembar · luas alam semesta yang tak teramati.

Tiap ide wajib punya minimal satu **angka yang bisa divisualisasikan** (tahun / persen / perbandingan / linimasa) — tanpa angka, tidak ada infografis, dan callout jatuh ke `keyword`.

## Hook style (pilih satu per video)

`angka mengejutkan` · `melawan logika` · `pertanyaan menusuk` · `"lo nggak bakal percaya"`.
Hook card memakai kata kerja gerak `slam` (lihat `05-kinetic-typography.md`), ukuran 96–190px, dan durasi 3 detik penuh.

## Yang bikin Shorts ini gagal (pantangan)

- Naskah tanpa angka → tidak ada infografis → visual jadi slide show.
- Semua callout menumpuk di 10 detik pertama.
- Transisi berbeda tiap 2 detik (terbaca sebagai "murah").
- Musik mengalahkan VO (lupa ducking / lupa −14 LUFS).
- Caption lebih dari 4 kata per baris atau font <96px.
