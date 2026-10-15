# 03 · Shot Craft — Aturan Potong, Ritme, Transisi

Nomor aturan dipakai di laporan QC: `R3 ✗ shot 4: hold 0.4s < 1.0s`. Jangan mengubah nomor, tambahkan yang baru di belakang.

Diadaptasi dari **video-shotcraft** (124 kartu resep shot + aturan R/Q/S/C/P).

## R · Ritme & durasi

**R1 — Hold dulu, efek belakangan.**
Setiap shot: `hold = holdSec - IN - OUT`. Anggarkan dulu `hold ≥ 30 frame` (1 detik) untuk shot yang memuat informasi kunci, dan `15 frame` diam di akhir gerakan massal. Sisa frame baru diisi animasi.
> Kalau habis diisi animasi baru cari sisa → hasilnya terasa "terburu-buru" dan tidak pernah ada momen diam.

**R2 — Hero shot tidak dikompresi.** Hook, twist, dan outro adalah hero. Saat total durasi harus dipotong, potong shot non-hero paling tengah.

**R3 — Dudukan minimum per tone (detik).**

| Tone | base | min | max | shot/60s |
|---|---|---|---|---|
| `wry` (Fakta Sejarah) | 2.0 | 1.2 | 3.5 | 25–30 |
| `reverent` (Misteri Alam Semesta) | 3.5 | 2.5 | 6.0 | 15–18 |
| `urgent` (bila naskah sangat padat) | 1.2 | 0.5 | 2.5 | ~50 |
| `elegiac` (bila tone sedih/heroik) | 4.0 | 2.5 | 7.0 | ~15 |

**R4 — Kuota impact layar penuh: ≤3 kali per video, jarak ≥6 detik.**
Kesalahan klasik: "setiap ketukan kick → layar bergetar". Itu terbaca sebagai gambar gemetar, bukan berenergi.
Catatan: kuota dihitung **per pemakaian teknik**, bukan per sub-event (mis. 3 ketukan dalam satu "beat pump" = 1 pemakaian).

**R5 — Napas (breath card).** Setiap 1–2 shot fakta, sisipkan 1 shot tanpa callout (`energy: low`) selama 1.5–2.0 detik. Total 2–4 kali per video. Ini yang bikin rantai fakta tidak melelahkan.

**R6 — Pergantian visual tiap 1–3 detik.** Tidak ada bidang statis > 3 detik tanpa gerak kamera (Ken Burns minimal `scale 1.0 → 1.05`).

**R7 — Jarak antar event berat ≥3 frame.** Dua elemen besar yang muncul bersamaan terbaca sebagai "berantakan"; <2 frame terbaca sebagai satu ketukan. Ideal 3–6 frame.

## T · Transisi

**T1 — Kosakata maksimal 4:** `cut` (default), `dissolve` (0.5–1.0s), `fade` (0.5–1.0s), `push` (0.3–0.5s).
Dilarang: wipe, glitch beruntun, zoom-blur, page-turn (menurunkan kesan).

**T2 — Pilih transisi dari selisih energi + makna sambungan**, bukan acak:

| Sambungan | Transisi | Durasi | Ease |
|---|---|---|---|
| Energi sama (fakta → fakta) | `cut` keras + flash 0.2s | — | — |
| Energi turun (klimaks → napas) | `dissolve` | 0.6–0.8s | `sine.inOut` |
| Energi naik (napas → klimaks) | `push` | 0.3–0.5s | `power2.out` |
| Ganti topik besar | `dissolve` + light leak | 0.7–1.0s | `sine.inOut` |
| Masuk/keluar kartu (hook/outro) | `fade` | 0.5s | `power1.inOut` |

**T3 — Satu sambungan satu teknik.** Tidak menumpuk push + glitch + flash di titik yang sama.

**T4 — Bukan exit animation.** Transisi **adalah** keluarnya shot lama. Jangan menulis `tl.to("#s1",{opacity:0})` lalu `tl.from("#s2")`. Yang benar: **dua arah di frame yang sama T**:

```tsx
const T = 90; // frame potong
tl.to("#s1", { yPercent: -100, filter: "blur(8px)", duration: 12, ease: "power3.in" }, T);
tl.fromTo("#s2", { yPercent: 100 }, { yPercent: 0, duration: 12, ease: "power3.out" }, T);
```

**T5 — Flash cut**: `from = titik potong - 5 frame`, panjang 10 frame, opacity 0.95 → 0 dalam 4 frame (≥6 frame berubah jadi soft dissolve).

## J · Jump cut & potongan cepat

**J1 — Tiga jeda nol-kompromi** (untuk momen "tunggu..."), tiap jeda `hold ≥ 35 frame`, jeda terakhir `≥ 45 frame`, rasio antar jeda minimal 1.5× (kalau <1.5× terbaca sebagai gambar bergetar, bukan jeda yang disengaja).

**J2 — Trailer bumper** (opsional, untuk teaser): 3 shot × 9 frame hard cut + 27–33 frame hitam total. Tiap shot internal `scale 1 → 1.04` supaya tidak mati.

**J3 — Hard cut = tanpa frame transisi.** Menambah 2 frame crossfade secara tidak sengaja sudah membatalkan hard cut.

## Q · Kualitas visual

**Q1 — Gerak kamera halus, bukan hentakan.** `cueBump` (dorongan saat callout masuk) maksimal `scale +0.022` dengan kurva `sin` penuh, bukan step.

**Q2 — Satu shot satu gagasan gerak.** Kalau dalam satu shot ada slam + wave + confetti + glitch, tidak ada yang terbaca.

**Q3 — Grain + vignette + color grade konsisten** sepanjang video; jangan ganti grade per shot (kecuali transisi topik besar).

**Q4 — Ken Burns**: `scale 1.0 → 1.05–1.08` selama shot, arah ganti bergantian (kiri/kanan/zoom-in/zoom-out) supaya tidak berpola.

**Q5 — Teks di atas gambar wajib punya scrim** (gradient gelap) — bukan shadow saja. Kontras teks ≥ 4.5:1 terhadap latar.

## S · Suara (ringkas; rinci di `04-beat-audio-sync.md`)

**S1** — BGM 0.15 saat VO bicara, 0.34 saat tidak ada VO (transisi/outro).
**S2** — SFX 0.2–0.6; impact terkeras 0.6 (bukan 1.0).
**S3** — Rentetan: dua sampel bergantian + volume menurun + interval makin rapat. Kalau tidak, terbaca sebagai "mesin senapan".
**S4** — Sampel > 5 detik wajib diberi `durationInFrames` eksplisit.
**S5** — Penutup tetap: `riser → +35 frame impact → +25 frame sparkle`.

## C · Copy di layar

**C1** — Maks 4 kata per callout, maks 3–4 kata per baris caption.
**C2** — Angka ditulis dengan digit (`1518`, `300 juta`), dan TTS mengeja lengkap (`kilometer`, bukan `km`).
**C3** — Jangan mengulang kata yang sama di caption dan callout dalam frame yang sama.

## P · Proses

**P1** — Storyboard disetujui dulu sebelum render (lihat `09-qc-checklist.md`).
**P2** — Semua angka frame berasal dari `wordF(i)` / `beatF(n)` / `SHOTS.x.from + offset`. Tidak ada angka telanjang.
**P3** — Render ulang harus menghasilkan frame yang identik (deterministik): seed dari indeks, bukan `Math.random()`.
