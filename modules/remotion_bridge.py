import os
import json
import shutil
import subprocess
import uuid
from moviepy import AudioFileClip
from config.settings import OUTPUT_DIR


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