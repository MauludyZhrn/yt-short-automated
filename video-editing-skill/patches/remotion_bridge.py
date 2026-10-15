import os
import json
import shutil
import subprocess
import uuid
from moviepy import AudioFileClip
from config.settings import OUTPUT_DIR

# Folder skrip skill v2. Bisa di-override lewat env kalau skill dipasang di tempat lain.
SKILL_SCRIPTS = os.environ.get(
    "VIDEO_SKILL_SCRIPTS",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "video_skill")),
)


def find_browser():
    """Cari browser lokal lintas OS. Urutan: env REMOTION_BROWSER, PATH, jalur umum.

    Return None bila tidak ketemu: Remotion lalu mengunduh Chrome Headless sendiri.
    """
    env = os.environ.get("REMOTION_BROWSER")
    if env and os.path.exists(env):
        return env

    for name in ("msedge", "chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        # Windows
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _py():
    """Interpreter Python yang sama dengan yang menjalankan proses ini."""
    return os.environ.get("PYTHON", "python")


def render_remotion_video(word_subtitles, audio_path, bg_paths, output_filename="final_remotion.mp4",
                          title_text="", outro_text="", logo_path="", bg_music_path=None, fps=30,
                          theme="cinematic", motion_cues=None, bgm_volume=0.13, keep_temp=False):
    print("🚀 Menyiapkan asset & data untuk Remotion Engine...")

    remotion_dir = os.path.abspath("./remotion-app")

    # Tiap render punya folder & props sendiri: dua render paralel tidak saling menimpa.
    run_id = uuid.uuid4().hex[:8]
    run_rel_dir = f"temp/{run_id}"
    run_dir = os.path.join(remotion_dir, "public", "temp", run_id)
    os.makedirs(run_dir, exist_ok=True)

    # 1. Hitung durasi presisi dari Voiceover
    voice_clip = AudioFileClip(audio_path)
    audio_duration = voice_clip.duration
    voice_clip.close()

    total_frames = int(audio_duration * fps)

    # 2. Salin Asset ke public/temp/<run_id> Remotion (mencegah error path Windows)
    def copy_to_public(src_path, prefix="file"):
        if src_path and os.path.exists(src_path):
            dest_name = f"{prefix}_{os.path.basename(src_path)}"
            shutil.copy(src_path, os.path.join(run_dir, dest_name))
            return f"{run_rel_dir}/{dest_name}"      # path web (forward slash)
        return None

    props_file_path = os.path.join(remotion_dir, "public", f"input_props_{run_id}.json")

    try:
        # VO sudah dimaster (EQ + kompresor + loudnorm) oleh tts.py: salin apa adanya, jangan di-encode ulang.
        shutil.copy(audio_path, os.path.join(run_dir, "voice_clean.mp3"))
        rel_audio_path = f"{run_rel_dir}/voice_clean.mp3"
        rel_bgm_path = copy_to_public(bg_music_path, "bgm") if bg_music_path else None
        rel_logo_path = copy_to_public(logo_path, "logo") if logo_path else None
        rel_bg_paths = [copy_to_public(p, f"bg_{i}") for i, p in enumerate(bg_paths) if p]

        # 3. Susun Props JSON
        remotion_props = {
            "audioPath": rel_audio_path,
            "bgMusicPath": rel_bgm_path,
            "bgImages": rel_bg_paths,
            "titleText": title_text,
            "outroText": outro_text,
            "logoPath": rel_logo_path,
            "subtitles": word_subtitles,
            "durationInFrames": total_frames,
            "fps": fps,
            "theme": theme,
            "motionCues": motion_cues or [],
            "bgmVolume": bgm_volume
        }

        with open(props_file_path, "w", encoding="utf-8") as f:
            json.dump(remotion_props, f, indent=2, ensure_ascii=False)

        output_path = os.path.abspath(os.path.join(OUTPUT_DIR, output_filename))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        browser_path = find_browser()

        # 4. Eksekusi Remotion CLI
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        props_rel_path = f"./public/input_props_{run_id}.json"   # path relatif dari cwd

        cmd = [
            npx_cmd, "remotion", "render",
            "ShortsComposition",
            output_path,
            f"--props={props_rel_path}",
            f"--duration-in-frames={total_frames}",
            f"--fps={fps}",
            "--concurrency=4"
        ]

        if browser_path:
            cmd.append(f"--browser-executable={browser_path}")

        print(f"🎬 Merender {total_frames} frame ({audio_duration:.1f} detik) via Remotion...")

        # shell=False agar Windows tidak merusak penanganan spasi pada path
        result = subprocess.run(cmd, cwd=remotion_dir, shell=False)

        if result.returncode == 0:
            print(f"✨ SUCCESS! Video Remotion berhasil dibuat di: {output_path}")
            return output_path
        raise RuntimeError("❌ Gagal merender video di Remotion!")
    finally:
        # Bersihkan aset sementara run ini (set keep_temp=True untuk debugging).
        if not keep_temp:
            shutil.rmtree(run_dir, ignore_errors=True)
            try:
                os.remove(props_file_path)
            except OSError:
                pass


# ===========================================================================
# SKILL v2 — render lewat jalur storyboard (ShotPlanner -> CuePlanner -> Compile)
# ===========================================================================
def _run_skill(script_name, *args):
    """Panggil skrip skill v2 sebagai subprocess; raise bila gagal."""
    path = os.path.join(SKILL_SCRIPTS, script_name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Skrip skill v2 tidak ada: {path}. Salin dulu scripts/*.py dari "
            "video-editing-skill ke modules/video_skill/, atau set VIDEO_SKILL_SCRIPTS."
        )
    subprocess.run([_py(), path, *args], check=True)


def render_storyboard_video(script_data, audio_path, word_subtitles, bg_paths,
                            bg_music_path=None, logo_path="", niche="Fakta Sejarah",
                            output_filename="final_storyboard.mp4", fps=30,
                            bgm_volume=0.13, keep_temp=False):
    """Render lewat jalur storyboard (skill v2).

    Urutan:
      1. Salin asset (VO/BGM/BG/logo) ke public/temp/<run_id> Remotion.
      2. shot_planner  -> STORYBOARD.json   (naskah + words [+ beats])
      3. cue_planner   -> jadwal callout (ditulis balik ke STORYBOARD.json)
      4. storyboard_compile -> input_props.json (frame absolut + asset relatif)
      5. (gate) qc_check --pre  ->  raise bila FAIL
      6. npx remotion render StoryboardComposition
    Semua file kerja ditaruh di run-dir agar dua render paralel tidak saling menimpa.
    """
    remotion_dir = os.path.abspath("./remotion-app")
    run_id = uuid.uuid4().hex[:8]
    run_rel_dir = f"temp/{run_id}"
    run_dir = os.path.join(remotion_dir, "public", "temp", run_id)
    os.makedirs(run_dir, exist_ok=True)

    # ---- 1. Salin asset ke public/temp/<run_id> ---------------------------
    def copy_to_public(src, prefix):
        if src and os.path.exists(src):
            dst = f"{prefix}_{os.path.basename(src)}"
            shutil.copy(src, os.path.join(run_dir, dst))
            return f"{run_rel_dir}/{dst}"
        return None

    rel_audio = copy_to_public(audio_path, "voice")
    rel_bgm = copy_to_public(bg_music_path, "bgm")
    rel_logo = copy_to_public(logo_path, "logo")
    rel_bgs = [copy_to_public(p, f"bg_{i}") for i, p in enumerate(bg_paths) if p]

    # words.json dipakai shot_planner & cue_planner (absolute path, lokal — bukan public).
    words_path = os.path.join(run_dir, "words.json")
    with open(words_path, "w", encoding="utf-8") as f:
        json.dump(word_subtitles, f, ensure_ascii=False)

    # Naskah disalin ke file karena shot_planner butuh --script <file>.
    script_path = os.path.join(run_dir, "naskah.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_data["script"])

    # callouts mentah dari LLM (boleh kosong — cue_planner ada auto-cue cadangan).
    callouts_path = os.path.join(run_dir, "callouts.json")
    with open(callouts_path, "w", encoding="utf-8") as f:
        json.dump(script_data.get("callouts", []), f, ensure_ascii=False)

    # beats.json: baca dari BGM lokal bila ada (numpy opsional; gagal -> None).
    beats_path = os.path.join(run_dir, "beats.json")
    if bg_music_path:
        try:
            _run_skill("beat_detect.py", bg_music_path, "--out", beats_path)
        except Exception as exc:
            print(f"⚠️ beat_detect gagal ({exc}); lanjut tanpa beat grid.")
            beats_path = None
    else:
        beats_path = None

    # ---- 2. shot_planner --------------------------------------------------
    sb_path = os.path.join(run_dir, "STORYBOARD.json")
    niche_arg = "sejarah" if "sejarah" in niche.lower() else "semesta"
    shot_cmd = [
        "--script", script_path, "--words", words_path,
        "--niche", niche_arg,
        "--hook", script_data.get("hook_text", "")[:80],
        "--out", sb_path,
    ]
    if beats_path:
        shot_cmd += ["--beats", beats_path]
    _run_skill("shot_planner.py", *shot_cmd)

    # ---- 3. cue_planner (jadwal callout, tulis balik ke STORYBOARD) -------
    cue_cmd = ["--storyboard", sb_path, "--callouts", callouts_path,
               "--words", words_path, "--out", callouts_path]
    if beats_path:
        cue_cmd += ["--beats", beats_path]
    _run_skill("cue_planner.py", *cue_cmd)

    # ---- 4. storyboard_compile -> input_props.json ------------------------
    props_path = os.path.join(remotion_dir, "public", f"input_props_{run_id}.json")
    compile_cmd = [
        sb_path, "--words", words_path,
        "--audio", rel_audio or "",
        "--bgm", rel_bgm or "",
        "--bg", *rel_bgs,
        "--bgm-volume", str(bgm_volume),
        "--out", props_path,
    ]
    if rel_logo:
        compile_cmd += ["--logo", rel_logo]
    if beats_path:
        compile_cmd += ["--beats", beats_path]
    _run_skill("storyboard_compile.py", *compile_cmd)

    # ---- 5. gate QC pra-render (FAIL -> raise, jangan boros waktu render) -
    qc_cmd = ["--pre", "--storyboard", sb_path, "--words", words_path]
    if beats_path:
        qc_cmd += ["--beats", beats_path]
    _run_skill("qc_check.py", *qc_cmd)

    # ---- 6. render --------------------------------------------------------
    with open(props_path, "r", encoding="utf-8") as f:
        total = json.load(f).get("durationInFrames", 1800)

    output_path = os.path.abspath(os.path.join(OUTPUT_DIR, output_filename))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    props_rel = f"./public/input_props_{run_id}.json"   # relatif dari cwd=remotion_dir
    render_cmd = [
        npx_cmd, "remotion", "render",
        "StoryboardComposition",
        output_path,
        f"--props={props_rel}",
        f"--duration-in-frames={int(total)}",
        f"--fps={fps}",
        "--concurrency=4",
    ]
    browser_path = find_browser()
    if browser_path:
        render_cmd.append(f"--browser-executable={browser_path}")

    print(f"🎬 Skill v2: merender {int(total)} frame via StoryboardComposition...")
    try:
        result = subprocess.run(render_cmd, cwd=remotion_dir, shell=False)
        if result.returncode != 0:
            raise RuntimeError("❌ Gagal merender StoryboardComposition di Remotion.")
        print(f"✨ SUCCESS! Video skill v2 jadi di: {output_path}")
        return output_path
    finally:
        if not keep_temp:
            shutil.rmtree(run_dir, ignore_errors=True)
            try:
                os.remove(props_path)
            except OSError:
                pass
