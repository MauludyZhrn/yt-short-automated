---
name: shorts-video-editing
description: "Skill editing video untuk YouTube Shorts otomatis (niche Fakta Sejarah / Misteri Alam Semesta, Bahasa Indonesia). Mengubah naskah+voiceover menjadi storyboard, motion graphic, kinetic typography, infographic animation, dan render Remotion 1080x1920. Dipakai saat user minta: buat/edit/upgrade video shorts, motion graphic, kinetic typography, infographic animation, remotion composition, pacing/cutting, beat sync, QC video. 视频剪辑/短视频/动态图形/字幕动画技能"
version: "2.0.0"
author: "CodeBuddy AI"
created: "2026-10-14"
updated: "2026-10-14"
---

# Shorts Video Editing — Editing, Motion Graphic & Typography

> **Tujuan**: satu skill yang menutup seluruh rantai *naskah → audio → storyboard → motion graphic → render Remotion → QC*.
> Semua keputusan editing ditulis sebagai **aturan bernomor dengan angka ambang**, bukan selera.

## Kapan dipakai

- User minta membuat / memperbaiki / meng-upgrade video Shorts (≤60 detik, 1080×1920).
- User menyebut: motion graphic, kinetic typography, infographic animation, callout, lower third, caption karaoke.
- User menyebut: pacing, cutting, jump cut, transisi, beat sync, ducking, audio mix, loudness.
- User memakai Remotion (`remotion render`, `Composition`, `Sequence`, `spring()`).

**Jangan** dipakai untuk: video landscape panjang (>3 menit), editing manual di Premiere/CapCut, atau pembuatan aset 3D.

## Filosofi (3 baris yang tidak bisa ditawar)

1. **Satu sumber kebenaran untuk waktu.** Semua bingkai, teks, dan SFX diturunkan dari tabel kata voiceover (`wordF(i)`) atau grid musik (`beatF(n)`). Tidak ada angka frame absolut yang diketik dua kali.
2. **Anggarkan hold dulu, baru efek.** Setiap shot dipotong `hold/rest` (diam) dulu, sisanya baru diisi animasi. Kalau diisi efek dulu, hasilnya "terburu-buru" dan tidak pernah punya momen diam.
3. **Deterministik.** Dilarang `Date.now()`, `Math.random()`, dan permintaan jaringan saat render. Semua acak memakai seed dari indeks (`random("key")`).

## Pipa kerja 8 tahap

| # | Tahap | Masukan → Keluaran | Alat |
|---|---|---|---|
| 0 | **Ideation** | niche + topik → `BRIEF` (tone, durasi, energy arc) | `references/content-blueprint.md` |
| 1 | **Script** | BRIEF → naskah + `hook_text` + `slots` (deskripsi visual) + `callouts` (dengan kata kerja gerak) | `script_gen.py` (existing) + aturan di `references/storyboard-schema.md` |
| 2 | **Audio** | naskah → `voice.mp3` + `words.json` (timestamp per kata) + BGM + `beats.json` | `tts.py`, `scripts/beat_detect.py` |
| 3 | **Storyboard** | naskah + words + beats → `STORYBOARD.json` (shot, hold, transisi, callout, caption) | `scripts/shot_planner.py`, `scripts/cue_planner.py` |
| 4 | **Assets** | `slots` → gambar/video Pexels + cek keberagaman & risiko "slide show" | `fetch_bg.py`, `scripts/variation_check.py` |
| 5 | **Edit plan** | STORYBOARD → jadwal final (potong di beat, kuota impact, jadwal SFX) | `references/shot-craft-rules.md` |
| 6 | **Compose** | STORYBOARD → `input_props.json` → `remotion render` | `scripts/storyboard_compile.py`, `remotion/*.tsx` |
| 7 | **Audio mix + QC** | VO + BGM + SFX → mix −14 LUFS; lalu cek durasi/black frame/loudness | `scripts/audio_mix.py`, `scripts/qc_check.py` |

**Gerbang wajib**: tahap 3 (storyboard) adalah *human/agent review gate* — jangan render sebelum `STORYBOARD.json` disetujui (atau sebelum `qc_check --pre` lolos).

## Aturan keras (pelanggaran = render ditolak)

**Format & durasi**
- 1080×1920, 30fps, **maks 59.5 detik** (batas Shorts 60.0; target naskah 125–145 kata ≈ 48–56 detik).
- Safe area 900×1400 terpusat; **300–320px bawah adalah zona mati** (caption/UI platform).
- Nada bicara 180–200 WPM; tidak ada potongan kata di tengah suku kata.

**Teks**
- Caption utama **≥96px** (≥5% tinggi frame 1920), teks bantu **≥58px** (≥3%). Tidak ada "setengah terbaca".
- Maks 3–4 kata per baris caption, 2 baris.
- Angka pakai `font-variant-numeric: tabular-nums` (biar tidak bergetar saat count-up).

**Gerak**
- Hold minimum: informasi kunci diam **≥30 frame (1 detik)** setelah animasinya selesai; gerakan massal diakhiri **15 frame diam**.
- Kuota impact layar penuh: **≤3 kali per video**, jarak antar impact **≥6 detik** (atau ≥16 ketukan bila musik mendominasi).
- Transisi: kosakata **maks 4** (`cut`, `dissolve 0.5–1.0s`, `fade`, `push`). Dilarang wipe/glitch/zoom-blur beruntun.
- Callout/infografis: **1 per ~6.5 detik**, tidak menumpuk di awal, tidak masuk 3.4s pertama dan 3.2s terakhir.

**Audio**
- `amix` selalu `normalize=0`. Loudness akhir `loudnorm=I=-14:LRA=11:TP=-1.5` (YouTube/TikTok/Reels).
- Ducking: `sidechaincompress=threshold=0.02:ratio=9:attack=200ms:release=500ms`, BGM saat bicara ≈ 0.15 (≈ −12 dB).
- SFX 0.2–0.6; rentetan pakai **dua sampel bergantian + volume menurun (0.40/0.37/0.34/…)** + interval makin rapat.

**Determinisme**
- Tidak ada `Date.now()`, `Math.random()`, fetch jaringan, atau font yang diunduh saat render (font di-load lewat `@remotion/google-fonts` lalu di-inline).

## Cara pakai (routing cepat)

```
"buat video shorts tentang X"            → jalankan tahap 0→7 penuh
"upgrade motion graphic-nya"             → references/motion-graphics-system.md + remotion/KineticType.tsx
"teksnya kurang hidup / kinetic"         → references/kinetic-typography.md + remotion/KineticType.tsx
"tambah infografis / data"               → references/infographic-animation.md + remotion/InfographicAnim.tsx
"potongannya berantakan / ngebut"        → references/shot-craft-rules.md + scripts/shot_planner.py
"kurang karuan sama musik"               → references/beat-audio-sync.md + scripts/beat_detect.py
"caption karaoke-nya meleset"            → references/beat-audio-sync.md + remotion/Captions.tsx
"cek sebelum publish"                    → scripts/qc_check.py + references/qc-checklist.md
"Remotion error / lambat"                → references/remotion-patterns.md
```

## Kontrak data (ringkas)

`STORYBOARD.json` — lapisan tengah yang bisa diedit manusia (diadaptasi dari HyperFrames):

```jsonc
{
  "meta": { "niche": "sejarah", "tone": "wry", "fps": 30, "durationSec": 52.4 },
  "shots": [
    {
      "id": "hook",
      "start": { "ref": "abs", "offset": 0 },        // atau {"ref":"hook","offset":-0.4} = overlap
      "holdSec": 3.0,
      "energy": "high",                              // low | medium | high
      "voWords": [0, 11],                            // rentang indeks kata VO
      "visual": { "type": "bg", "slot": 0, "motion": "kenburns" },
      "caption": { "style": "karaoke", "emphasis": [3] },
      "callout": { "type": "year", "verb": "slam", "text": "1518", "sub": "Strasbourg" },
      "transitionIn": "cut"
    }
  ],
  "callouts": [],   // hasil cue_planner (detik absolut, tidak tumpang tindih)
  "captions": []    // hasil buildPages (frasa 3–4 kata)
}
```

Kompilasi ke Remotion: `python scripts/storyboard_compile.py STORYBOARD.json --words words.json --beats beats.json --out input_props.json`
(mengubah `start.ref/offset` relatif → frame absolut; semua angka lain diturunkan darinya).

## Isi paket

- `INSTALL.md` — cara memasang & menyambungkan ke pipeline yang sudah ada (remotion_bridge.py, Root.tsx).
- `references/` — 10 dokumen metodologi (aturan bernomor + ambang angka + contoh).
- `scripts/` — 7 skrip CLI Python (lokal, tanpa API wajib).
- `remotion/` — komponen React/Remotion siap salin ke `remotion-app/src/`.
- `examples/` — storyboard contoh untuk 2 niche (sudah lolos QC 0 FAIL / 0 WARN).

## Sumber pengetahuan

Diadaptasi dari: **HyperFrames** (HeyGen) — storyboard Markdown + `data-*` timing deklaratif + komponen bervariabel;
**video-shotcraft** — 124 kartu resep shot, aturan R/Q/S/C/P, `beatF(n)`, anggaran hold, voice-locked typography;
**OpenMontage** — pipeline agentik 8 stage, CLIP/描述 slot, tone→hold table, rantai audio ffmpeg, self-review pasca-render.
Rincian pemetaan ada di `references/upstream-sources.md`.
