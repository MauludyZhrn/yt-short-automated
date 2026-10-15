# 02 · Storyboard Schema — Lapisan Tengah yang Bisa Diedit

Diadaptasi dari **HyperFrames** (HeyGen): jangan pernah membiarkan LLM menulis JSX atau frame absolut langsung.
LLM menulis **storyboard**; compiler mengubahnya menjadi frame.

## Kenapa pakai lapisan tengah

| Tanpa storyboard | Dengan storyboard |
|---|---|
| LLM menulis JSX + angka detik | LLM menulis deskripsi + referensi relatif |
| Ubah satu shot → semua timing geser | Ubah satu shot → sisanya mengikuti otomatis |
| Sulit di-review manusia | Bisa dikomentari per baris, di-diff, di-edit tangan |
| Render ulang = hasil beda | Render ulang = identik (deterministik) |

## Format: JSON (mesin) atau Markdown (manusia)

`STORYBOARD.json` dipakai compiler. `STORYBOARD.md` dipakai saat review manual (satu baris per shot).
Isi keduanya harus sama; `storyboard_compile.py` menerima keduanya (`.md` diparse dari tabel).

## Skema lengkap

```jsonc
{
  "meta": {
    "niche": "sejarah",           // sejarah | semesta
    "tone": "wry",                // wry | reverent | elegiac | urgent
    "fps": 30,
    "width": 1080, "height": 1920,
    "durationSec": 52.4,          // dihitung dari VO, bukan ditebak
    "energyArc": [                // porsi 4 segmen (hook/setup/chain/closer)
      {"id": "hook",   "share": 0.10, "energy": "high"},
      {"id": "setup",  "share": 0.14, "energy": "medium"},
      {"id": "chain",  "share": 0.60, "energy": "medium"},
      {"id": "closer", "share": 0.16, "energy": "low"}
    ]
  },

  "shots": [
    {
      "id": "hook",                            // unik, dipakai sebagai ref
      "start": {"ref": "abs", "offset": 0},    // lihat "Timing relatif"
      "holdSec": 3.0,                          // durasi total shot (include hold)
      "energy": "high",                        // low | medium | high
      "hero": true,                            // tidak boleh dikompresi
      "voWords": [0, 11],                      // indeks inklusif ke words.json
      "visual": {
        "type": "bg",                          // bg | infographic | card | mascot
        "slot": 0,                             // indeks ke bgImages
        "motion": "kenburns",                  // kenburns | static | punch | drift
        "description": "stone dungeon corridor, torch flicker, warm low-key",
        "queries": ["stone dungeon corridor"]
      },
      "caption": {"style": "karaoke", "emphasis": [3]},
      "callout": {"type": "year", "verb": "slam", "text": "1518", "sub": "Strasbourg", "pose": "wow"},
      "transitionIn": "cut",                   // cut | dissolve | fade | push
      "transitionSec": 0.35,
      "sfx": [{"name": "impact", "at": "start+0", "volume": 0.6}]
    }
  ],

  // turunan (diisi oleh scripts/shot_planner.py & cue_planner.py, jangan ditulis manual)
  "callouts": [{"type":"year","text":"1518","sub":"Strasbourg","start":3.6,"end":6.4,"pose":"wow","verb":"slam"}],
  "captions": [{"text":"Pada 1518, kota","start":0.0,"end":2.18,"words":[0,1,2]}],
  "beats": {"bpm": 96.0, "beat0": 0.224, "beatTimes": [0.224, 0.849, ...]}
}
```

## Timing relatif (inti dari HyperFrames)

```jsonc
"start": {"ref": "abs",   "offset": 0}      // absolut: detik 0
"start": {"ref": "hook",  "offset": 0}      // persis setelah shot "hook" selesai
"start": {"ref": "hook",  "offset": 0.5}    // 0.5s setelah hook selesai (napas)
"start": {"ref": "hook",  "offset": -0.4}   // overlap 0.4s (cross dissolve / whip)
"start": {"ref": "word:12", "offset": -0.15}// 0.15s sebelum kata ke-12 diucapkan
"start": {"ref": "beat:8", "offset": 0}     // pada ketukan ke-8 BGM
```

Aturan resolver (`storyboard_compile.py`):
1. `ref` menunjuk **waktu selesai** shot yang direferensikan (bukan waktu mulai), kecuali `word:`/`beat:` yang menunjuk **waktu mulai** momen itu.
2. Referensi hanya boleh mundur (tidak boleh siklus). Kalau siklus → error, jangan ditebak.
3. `offset` negatif = overlap; compiler tidak boleh menghasilkan `start < 0`.
4. Hasil akhir dibulatkan **hanya sekali** di langkah terakhir (`Math.round(sec * fps)`), tidak di tengah proses — pembulatan dini membuat galat menumpuk.

## Visibilitas = interval setengah terbuka `[start, start+hold)`

Konsekuensi penting: **animasi harus selesai sebelum `holdSec` habis**. Kalau animasi masuk butuh 0.6s dan shot cuma 0.5s, frame terakhir tidak pernah kelihatan. Aturan praktis:

```
IN_BASE  = 0.35s   (untuk callout kecil)
HOLD     = max(0.8, holdSec - IN_BASE - OUT_BASE)
OUT_BASE = 0.25s
```
Kalau `HOLD < 0.8s`, shot terlalu pendek → **panjangi shot atau buang callout**. Compiler akan memperingatkan.

## Status shot (untuk proses iteratif)

`outline` → `built` (visual ada) → `animated` (gerak ada) → `approved`.
Render hanya boleh dijalankan kalau semua shot `approved` atau `--force` diberikan.

## Markdown equivalent (untuk review manusia)

```markdown
| # | id | start | hold | energy | vo | visual | callout | trans | status |
|---|----|-------|------|--------|----|--------|---------|-------|--------|
| 1 | hook | abs 0 | 3.0 | high | 0-11 | bg#0 kenburns | year 1518 slam | cut | animated |
| 2 | ctx1 | hook +0 | 5.2 | medium | 12-30 | bg#1 drift | - | dissolve 0.6 | built |
```

## Kontrak dengan Remotion

`storyboard_compile.py` menghasilkan `input_props.json` yang **kompatibel mundur** dengan `ShortsVideo.tsx` yang sudah ada
(field lama `subtitles`, `motionCues`, `bgImages`, `titleText`, `outroText`, `theme`, `bgmVolume` tetap ada),
ditambah field baru:

```jsonc
{
  "storyboard": { "shots": [ {"id":"hook","from":0,"durationFrames":90, ...} ] },
  "beats": {...}, "wordFrames": [[0,20],[20,65], ...],
  "safeArea": {"top": 260, "bottom": 320}
}
```

Jadi Remotion lama tetap jalan; `StoryboardVideo.tsx` (baru) membaca field tambahan ini.
