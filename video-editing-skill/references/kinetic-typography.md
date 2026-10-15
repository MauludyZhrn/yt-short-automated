# 05 · Kinetic Typography — Kata Kerja Gerak & Resepnya

Gabungan **HyperFrames** (`kinetic-type-beats.md`, 49 aturan atomik) dan **video-shotcraft** (kartu `typography/*`), disesuaikan dengan `Kinetic.tsx` yang sudah ada di proyek.

## Prinsip utama: sebutkan kata kerjanya

> "Kalau lo tidak bisa menyebut kata kerja untuk sebuah elemen teks, elemen itu belum selesai didesain."

Jadi LLM **tidak** menulis parameter animasi. LLM menulis:
```jsonc
{"text": "400 ORANG MENARI", "verb": "slam", "emphasis": [0]}
```
dan tabel di bawah menerjemahkannya ke parameter.

## Tabel kata kerja → parameter (Remotion)

| Kata kerja | Kapan dipakai | Parameter kunci | Komponen |
|---|---|---|---|
| `slam` | hook, tahun, angka kejutan | `spring({damping:11,stiffness:210,mass:0.6})`, `scale 2.8→1`, `blur 12→0`, stagger 2 frame/huruf | `KineticText variant="slam"` |
| `wave` | pertanyaan, CTA, outro | `spring({damping:9,stiffness:160,mass:0.7})` + `sin(frame/6)*7` | `variant="wave"` |
| `mask` | teks editorial / kutipan | huruf naik dari `translateY(118%)` dengan `overflow:hidden`, `damping:20` | `variant="mask"` |
| `type` | kalimat misteri, kode, pesan | mesin tik + kursor `|` kedip tiap 8 frame | `variant="type"` |
| `pop` | kata penekanan di caption | `spring overshoot {damping:8,stiffness:220}`, `scale 0.6→1.08→1` | `KineticType verb="pop"` |
| `countup` | angka statistik | `tabular-nums`, easing `out(cubic)` 20–26 frame, + pulse 3 frame saat mendarat | `InfographicAnim` |
| `draw` | garis/underline/scribble | `strokeDashoffset` penuh→0 dalam 12–18 frame | `Fx.tsx` `WigglyArrow` |
| `glitch` | angka yang "menghantam", kontras fakta | RGB-split ±34px memudar dalam 14 frame + `clipPath` slice acak | `GlitchText` |
| `wipe` | marker/stabilo pada kata penting | `scaleX 0→1 skewX(-8deg)` dari kiri, 14 frame, `ease out(cubic)` | `markerWord` di `KineticText` |
| `float` | teks lain (badge, sumber) | drift `sin` amplitudo 4–7px, tanpa masuk/keluar | — |

## Paket waktu (envelope) untuk teks

```
IN_BASE   = 0.35s   (huruf masuk, stagger ≤ 2 frame/huruf, maks total 0.6s)
HOLD      = sisa    (minimal 0.8s; teks yang perlu dibaca minimal 1.2s)
OUT_BASE  = 0.25s   (keluar lewat transisi, BUKAN animasi keluar sendiri — lihat T4)
```

Aturan: **teks 3–6 kata butuh minimal 1.2 detik tampil**. Kalau shot-nya cuma 1 detik, teksnya dipotong jadi ≤3 kata atau Shot-nya dipanjangkan.

## Hirarki ukuran (1080×1920)

| Peran | Ukuran | Keterangan |
|---|---|---|
| Hook card | 96–190px | `KineticText`, `font-size` dihitung dari kata terpanjang |
| Angka tahun / stat | 150–210px | `tabular-nums`, extrude 7 lapis |
| Judul infografis (kicker) | 40px | stiker miring −3°, shadow keras |
| Caption utama | **≥96px** | ≥5% tinggi frame; jangan di bawah ini |
| Sub-caption / satuan | 58–72px | ≥3% tinggi frame |
| Badge / watermark | 34–46px | opacity 0.5–0.7 |

Rumus ukuran hook (dari `HookScene` yang sudah ada, pertahankan):
```ts
const size = Math.max(96, Math.min(190, Math.min(940 / (maxWord * 0.52), 3400 / Math.sqrt(total * 18))));
```

## Ekstrusi & outline (identitas visual)

```ts
// extrude: bayangan bertumpuk (CapCut-like)
export const extrude = (color: string, depth = 8, step = 1.6) =>
  Array.from({length: depth}, (_, i) =>
    `${((i+1)*step*0.6).toFixed(1)}px ${((i+1)*step).toFixed(1)}px 0 ${color}`).join(", ");
// outline: -webkit-text-stroke 6-10px + paintOrder:"stroke fill"
```

Pakai **salah satu** per elemen: extrude (berat, untuk hook) **atau** outline+ring sticker (untuk callout). Keduanya bersamaan = teks tidak terbaca.

## Warna & penekanan

- Kata penekanan (`emphasis`) = warna aksen tema, **maks 1–2 kata per baris**.
- Marker/stabilo: `#FFE600`, teks di atasnya `#0A0A0A`, miring −8°.
- Warna tema: `history` emas `#F2C879`, `space` cyan `#6FE7FF`, `cinematic` gold+ice.
- Teks di atas foto wajib scrim gradient; jangan mengandalkan shadow saja (Q5).

## Karaoke caption (paling penting untuk retensi)

Lihat `04-beat-audio-sync.md` → pola gradient `WebkitBackgroundClip: text`.
Aturan tambahan:
- 3–4 kata per halaman, 2 baris maksimal.
- Muncul **0.15s sebelum** kata pertama diucapkan (`PRE_ROLL`).
- Kata aktif: warna aksen + garis bawah 8px. Kata belum diucapkan: putih 0.85 opacity.
- Jangan mewarnai lebih dari 1 kata sekaligus (mata tidak sempat).

## Kesalahan yang sering terjadi

1. **Stagger terlalu besar** — 6 frame/huruf × 20 huruf = 4 detik hanya untuk masuk. Maks 2 frame/huruf, total masuk ≤0.6s.
2. **Animasi keluar sendiri** — melanggar T4; keluarkan lewat transisi shot.
3. **Font tidak ke-load** → teks jatuh ke fallback dan layout melompat. Load via `@remotion/google-fonts` di level modul, jangan di dalam komponen.
4. **Huruf gemetar** saat count-up → pakai `font-variant-numeric: tabular-nums` dan lebar tetap.
5. **Teks terlalu lama** — penonton Shorts membaca ~2.5 kata/detik. 6 kata butuh 2.4 detik, bukan 1 detik.
