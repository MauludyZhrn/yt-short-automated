# 10 · Sumber Hulu & Pemetaan Ide

Skill ini adalah **sintesis**, bukan salinan. Tiga repo hulu memberi kerangka; angka ambangnya disesuaikan untuk
Shorts 1080×1920 berbahasa Indonesia (narasi TTS, 2 niche).

## HyperFrames (heygen-com/hyperframes) — "Write HTML. Render video."

| Yang diambil | Jadi di sini |
|---|---|
| Lapisan tengah `STORYBOARD.md` dengan status `outline → built → animated` | `STORYBOARD.json` + `status` per shot (`02`) |
| Timing deklaratif `data-start="intro - 0.5"` (referensi ke **waktu selesai**) | `start: {ref, offset}` + resolver di `storyboard_compile.py` |
| Visibilitas interval setengah terbuka `[start, start+duration)` | aturan "animasi harus selesai sebelum hold habis" |
| Larangan animasi keluar; transisi = dua arah di frame T | aturan **T4** |
| Komponen bervariabel + envelope `IN_BASE / HOLD / OUT_BASE` | envelope callout & count-up (`06`) |
| `tabular-nums` untuk angka berhitung | aturan keterbacaan (`06`) |
| Katalog 30+ transisi CSS dikelompokkan energi | tabel transisi energi (**T2**) |
| Determinisme: larang `Date.now()` / `Math.random()` / jaringan saat render | aturan keras + **A9/A10** |
| `frame.md` — desain sistem dengan token | tabel token tema (`07`) |
| Beat detection (`beatTimes`, `beatStrengths`) + VO carve per pita frekuensi | `beat_detect.py` + ducking (`04`) |

## video-shotcraft (Vincentwei1021/video-shotcraft) — 124 kartu resep shot

| Yang diambil | Jadi di sini |
|---|---|
| `SHOTS` sebagai satu sumber kebenaran; `from` selalu relatif | `SHOTS` di `Timeline.tsx`, aturan **P2** |
| Anggarkan `hold/rest` dulu, baru efek (R1/R3) | aturan **R1** |
| Hold ≥30f untuk info kunci, 15f di akhir gerakan massal | **R1** |
| Kuota impact ≤3, jarak ≥16 ketukan; "kick bukan pemicu" | **R4** (diadaptasi ke ≥6 detik untuk video narasi) |
| Napas: 1 kartu tiap 1–2 shot fakta, 50–55 frame | **R5** |
| Tiga jeda jump cut; rasio antar jeda ≥1.5× | **J1** |
| `beatF(n)`, toleransi ≤3 frame, offset encoder 1.28 frame | `04` + `Timeline.tsx` |
| Hanya 4 kosakata transisi; larang wipe/glitch beruntun | **T1/T2** |
| Voice-locked typography: karaoke fill sync, 4–10 frame napas antar kata | `04` + `Captions.tsx` |
| BGM 0.34 / SFX 0.2–0.6 / dua sampel bergantian + volume menurun | **S1–S3** |
| Checklist bernomor dengan bukti frame | `09` |
| Sub-agent review independen (pembuat punya bias konfirmasi) | catatan di `09` |

## OpenMontage (calesthio/OpenMontage) — pipeline agentik 8 stage

| Yang diambil | Jadi di sini |
|---|---|
| Slot = **deskripsi** (bukan kata kunci) + query pendek | `visual.description` + `queries` (`01`, `02`) |
| Tabel `tone → hold` (elegiac 4.0 / reverent 3.5 / wry 2.0 / urgent 1.2) | tabel **R3** untuk 2 niche |
| Hero shot tidak dikompresi; total ±10% | **R2** + rumus penutupan durasi (`01`) |
| MMR / diversitas untuk hindari shot kembar | `variation_check.py` |
| Skor risiko "slide show" (≥4.0 = jangan render) | **A8** |
| `amix normalize=0` + `sidechaincompress` + `loudnorm −14 LUFS` | `04`, `audio_mix.py` |
| BGM per segmen dengan `volume='if(lt(t,…))'` | `04` |
| Self-review pasca render: durasi, frame hitam, volumedetect | `qc_check.py`, **B1–B5** |
| Media profile `youtube_shorts` (1080×1920, crf 20, ≤60s) | aturan keras format |
| Zona aman 900×1400 + 300–320px mati bawah; font ≥42px@1080p | aturan teks (diskalakan ke ≥96px @1920 tinggi) |
| 8 stage `research→proposal→script→scene_plan→assets→edit→compose→publish` | pipa 8 tahap di `SKILL.md` |

## Yang **tidak** diambil (dan alasannya)

- **BMTS-Lite (OpenMontage)**: engine "satu musik + banyak klip → montase otomatis". Dokumentasinya sendiri menyatakan
  *not good for "narrated composition"* — tidak cocok untuk Shorts yang digerakkan narasi.
- **Remotion maps / Cesium / MapTiler** (dari bundle `remotion-best-practices`): tidak relevan untuk fakta sejarah/antariksa
  kecuali topiknya geografis; biarkan di `.agents/skills/` dan aktifkan hanya bila topik butuh peta.
- **HyperFrames runtime HTML/GSAP**: proyek ini sudah berinvestasi di Remotion/React. Yang dipinjam adalah
  *model mentalnya* (storyboard + timing relatif + komponen bervariabel), bukan runtime-nya.

## Cara memakai repo hulu lagi nanti

```bash
# bila ingin menarik pembaruan
git -C repos/hyperframes pull
grep -rn "hold" repos/video-shotcraft/references/shots/rhythm/ | head
grep -rn "sidechaincompress" repos/OpenMontage/tools/audio/
```
Perubahan upstream yang menyentuh angka ambang harus ditulis ulang ke `03` dan `09` (bukan sekadar ditautkan).
