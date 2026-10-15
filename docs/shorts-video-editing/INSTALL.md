# Integrasi & Instalasi — Shorts Video Editing v2.0

Dokumen ini menjelaskan cara memasang skill ini dan menyambungkannya ke pipeline kamu yang sudah ada
(`modules/*.py` + `remotion-app/`). **Tidak ada yang harus dirombak** — skill ini bekerja
sebagai *lapisan tengah* (storyboard) di antara `script_gen.py` dan `remotion render`.

---

## 1. Instalasi skill

```bash
# salin ke folder skill global
cp -r video-editing-skill ~/.codebuddy/skills/shorts-video-editing

# atau pakai symlink kalau kamu masih ingin mengedit source-nya di /workspace
ln -s "$(pwd)/video-editing-skill" ~/.codebuddy/skills/shorts-video-editing
```

Struktur setelah terpasang:

```
shorts-video-editing/
├── SKILL.md                 # entry point (dibaca agent)
├── INSTALL.md               # dokumen ini
├── references/              # 10 dokumen metodologi
├── scripts/                 # 7 CLI Python
│   ├── shot_planner.py      # naskah+words+beats → STORYBOARD.json
│   ├── cue_planner.py       # STORYBOARD + callouts → jadwal callout final
│   ├── storyboard_compile.py# STORYBOARD → input_props.json (frame absolut)
│   ├── beat_detect.py       # BGM → beats.json (BPM + grid)
│   ├── audio_mix.py         # VO + BGM + SFX → mix −14 LUFS
│   ├── qc_check.py          # gate pra/pasca render
│   └── variation_check.py   # deteksi "slide show" & duplikasi
├── remotion/                # 6 komponen React siap salin ke src/
└── examples/                # 2 contoh niche yang sudah lolos QC
```

Dependensi Python (semuanya opsional kecuali yang pertama):

```bash
pip install numpy            # wajib untuk beat_detect.py saja
# sisanya: Python 3.9+ stdlib + ffmpeg di PATH
```

---

## 2. Pasang komponen Remotion

Salin 6 file ke project Remotion kamu:

```bash
cp video-editing-skill/remotion/*.tsx remotion-app/src/
```

Lalu daftarkan composition baru di `src/Root.tsx` — **jangan hapus `ShortsComposition`**,
karena `input_props.json` dari `storyboard_compile.py` tetap *backward compatible*:

```tsx
import { Composition } from "remotion";
import { ShortsVideo } from "./ShortsVideo";            // tetap ada (legacy)
import { StoryboardVideo } from "./StoryboardVideo";    // baru

export const RemotionRoot = () => (
  <>
    <Composition
      id="ShortsComposition"
      component={ShortsVideo}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ /* props lama kamu */ } as any}
    />
    <Composition
      id="StoryboardComposition"
      component={StoryboardVideo}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ storyboard: null, safeArea: null } as any}
    />
  </>
);
```

`StoryboardVideo` membaca field baru (`storyboard`, `beats`, `wordFrames`, `safeArea`,
`subtitleStyle`) bila ada, dan **jatuh kembali ke field lama** (`wordSubtitles`, `bgPaths`,
`durationInFrames`, `theme`, …) bila tidak ada. Jadi satu berkas props bisa dipakai dua
composition.

Dependensi npm yang dipakai komponen baru:

```bash
cd remotion-app
npm i @remotion/google-fonts @remotion/shapes
```

---

## 3. Sambungkan ke `remotion_bridge.py`

Tambahkan **satu fungsi baru** di samping `render_remotion_video()` yang sudah ada —
jangan ganti yang lama dulu, biar bisa A/B:

```python
# modules/remotion_bridge.py  (tambahan)

def render_storyboard_video(storyboard_path, words_path, audio_path, bg_paths,
                            beats_path=None, callouts_path=None,
                            output_filename="final_storyboard.mp4", fps=30,
                            keep_temp=False):
    """Render lewat jalur storyboard (skill v2). Butuh 3 langkah compile di Python."""
    import subprocess, uuid, shutil, os, json

    remotion_dir = os.path.abspath("./remotion-app")
    SKILL = os.path.expanduser("~/.codebuddy/skills/shorts-video-editing/scripts")

    run_id = uuid.uuid4().hex[:8]
    out_props = os.path.join(remotion_dir, "public", f"input_props_{run_id}.json")

    # 3a. STORYBOARD.json -> input_props.json (frame absolut)
    cmd = ["python", os.path.join(SKILL, "storyboard_compile.py"),
           storyboard_path, "--words", words_path,
           "--out", out_props]
    if beats_path:
        cmd += ["--beats", beats_path]
    subprocess.run(cmd, check=True)

    # 3b. (opsional) jadwalkan callout
    if callouts_path:
        subprocess.run(["python", os.path.join(SKILL, "cue_planner.py"),
                        "--storyboard", storyboard_path,
                        "--callouts", callouts_path,
                        "--words", words_path,
                        "--out", storyboard_path.replace("STORYBOARD", "callouts")],
                       check=True)

    # 3c. render
    total = json.load(open(out_props))["durationInFrames"]
    subprocess.run(["npx", "remotion", "render", "StoryboardComposition",
                    output_filename, "--props", out_props,
                    "--concurrency=4"], cwd=remotion_dir, check=True)
    return output_filename
```

Lalu di orkestrator (`main.py`), urutan lengkapnya:

```python
# 0-1. naskah (script_gen.py)  →  naskah.txt
# 2.  TTS (tts.py)             →  voice.mp3 + words.json
# 2b. beat grid (baru)
subprocess.run(["python", SKILL/"beat_detect.py", bgm_path, "--out", "beats.json"])
# 3.  storyboard (baru) — INI gerbang review-nya
subprocess.run(["python", SKILL/"shot_planner.py",
                "--script", "naskah.txt", "--words", "words.json",
                "--beats", "beats.json", "--niche", "sejarah",
                "--out", "STORYBOARD.json"])
subprocess.run(["python", SKILL/"cue_planner.py",
                "--storyboard", "STORYBOARD.json",
                "--callouts", "callouts.json",
                "--words", "words.json",
                "--out", "callouts.scheduled.json"])
# 3b. GATE: jangan lanjut kalau FAIL
subprocess.run(["python", SKILL/"qc_check.py", "--pre",
                "--storyboard", "STORYBOARD.json",
                "--words", "words.json"], check=True)
# 4.  assets (fetch_bg.py) + cek keberagaman
subprocess.run(["python", SKILL/"variation_check.py",
                "--storyboard", "STORYBOARD.json", "--images", *bg_paths])
# 6.  render (fungsi di atas)
# 7.  audio mix + QC akhir
subprocess.run(["python", SKILL/"audio_mix.py", "--vo", "voice.mp3",
                "--bgm", bgm_path, "--sfx", "sfx.json", "--out", "mix.mp3"])
subprocess.run(["python", SKILL/"qc_check.py", "final.mp4", "--post"], check=True)
```

---

## 4. Kontrak `words.json` (dari `tts.py`)

Semua skrip mengasumsikan format **edge-tts word boundary** (array datar):

```json
[
  { "word": "Tahun",  "start": 0.31, "end": 0.72 },
  { "word": "1518,",  "start": 0.72, "end": 1.30 }
]
```

Kalau TTS kamu menghasilkan *frasa* bukan kata (sering terjadi pada edge-tts bahasa
Indonesia), `shot_planner.py` dan `cue_planner.py` sudah menangani: frasa dipecah jadi kata
dengan waktu proporsional (`explode_words`), dan pencarian anchor callout memakai
pencocokan substring pada *joined stream*. Jadi tidak perlu mengubah `tts.py`.

---

## 5. Cek kesehatan pemasangan

```bash
cd ~/.codebuddy/skills/shorts-video-editing

# a. skrip bisa dipanggil
for f in scripts/*.py; do python "$f" --help >/dev/null 2>&1 && echo "ok  $f" || echo "??  $f"; done

# b. contoh storyboard lolos gate pra-render
python scripts/qc_check.py examples/storyboard.history.json --words examples/words.history.json --pre
python scripts/qc_check.py examples/storyboard.space.json   --words examples/words.space.json   --pre

# c. compile ke input_props.json
python scripts/storyboard_compile.py examples/storyboard.history.json \
       --words examples/words.history.json --out /tmp/ip.json

# d. cek keberagaman aset
python scripts/variation_check.py --storyboard examples/storyboard.history.json
```

Hasil yang diharapkan pada langkah (b): **0 FAIL, 0 WARN** untuk kedua contoh
(kepadatan callout ideal 0.8–1.0x). Catatan: argumen posisi yang berakhir `.json`
otomatis dianggap storyboard, jadi dua cara di atas dan `--storyboard` sama saja.

---

## 6. Catatan keamanan & batas

- Semua skrip **lokal**: tidak ada panggilan jaringan, tidak ada kunci API. Satu-satunya
  proses eksternal yang dipanggil adalah `ffmpeg`/`ffprobe` (dan `npx remotion` bila kamu
  memanggilnya sendiri dari orkestrator).
- Skrip **hanya menulis** ke jalur `--out` yang kamu berikan. `cue_planner.py` dapat
  menimpa STORYBOARD bila `--out` sama dengan masukannya — sengaja, tapi pakai berkas
  salinan kalau ragu.
- Tidak ada skrip yang menghapus berkas, menjalankan shell arbitrer, atau menyentuh
  `~/.codebuddy` selain saat kamu menyalin skill ini.
- Batas yang diketahui: `beat_detect.py` butuh `numpy`; `audio_mix.py` butuh `ffmpeg` dengan
  filter `sidechaincompress` dan `loudnorm`; `qc_check.py --post` butuh `ffprobe`.
