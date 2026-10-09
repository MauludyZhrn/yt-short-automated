import os
import json
import shutil
import subprocess
from moviepy import AudioFileClip
from config.settings import OUTPUT_DIR

def render_remotion_video(word_subtitles, audio_path, bg_paths, output_filename="final_remotion.mp4",
                          title_text="", outro_text="", logo_path="", bg_music_path=None, fps=30,
                          theme="cinematic", motion_cues=None, bgm_volume=0.13):
    print("🚀 Menyiapkan asset & data untuk Remotion Engine...")

    remotion_dir = os.path.abspath("./remotion-app")
    public_temp_dir = os.path.join(remotion_dir, "public", "temp")
    os.makedirs(public_temp_dir, exist_ok=True)

    # 1. Hitung durasi presisi dari Voiceover
    voice_clip = AudioFileClip(audio_path)
    audio_duration = voice_clip.duration
    voice_clip.close()
    
    total_frames = int(audio_duration * fps)

    # 2. Salin Asset ke folder public/temp Remotion (mencegah error path Windows)
    def copy_to_public(src_path, prefix="file"):
        if src_path and os.path.exists(src_path):
            ext = os.path.splitext(src_path)[1]
            dest_name = f"{prefix}_{os.path.basename(src_path)}"
            dest_path = os.path.join(public_temp_dir, dest_name)
            shutil.copy(src_path, dest_path)
            
            # Format path web (forward slash)
            rel_path = f"temp/{dest_name}".replace("\\", "/")
            return rel_path
        return None

    # VO sudah dimaster (EQ + kompresor + loudnorm) oleh tts.py: salin apa adanya, jangan di-encode ulang.
    clean_audio_path = os.path.join(public_temp_dir, "voice_clean.mp3")
    shutil.copy(audio_path, clean_audio_path)
    rel_audio_path = "temp/voice_clean.mp3"
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

    props_file_path = os.path.join(remotion_dir, "public", "input_props.json")
    with open(props_file_path, "w", encoding="utf-8") as f:
        json.dump(remotion_props, f, indent=2, ensure_ascii=False)

    output_path = os.path.abspath(os.path.join(OUTPUT_DIR, output_filename))

    # Cek ketersediaan Browser lokal (Edge / Chrome)
    browser_path = None
    possible_browsers = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    for b in possible_browsers:
        if os.path.exists(b):
            browser_path = b
            break

    # 4. Eksekusi Remotion CLI
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    props_rel_path = "./public/input_props.json" # Gunakan path relatif dari cwd

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
    
    # Gunakan shell=False agar Windows tidak merusak penanganan spasi pada path
    result = subprocess.run(cmd, cwd=remotion_dir, shell=False)

    if result.returncode == 0:
        print(f"✨ SUCCESS! Video Remotion berhasil dibuat di: {output_path}")
        return output_path
    else:
        raise RuntimeError("❌ Gagal merender video di Remotion!")