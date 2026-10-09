import os
import random

def get_local_bgm(niche):
    """
    Mengambil 1 file BGM secara acak dari folder lokal berdasarkan Niche.
    Folder target:
    - assets/bgm/fakta_sejarah
    - assets/bgm/misteri_alam_semesta
    """
    niche_lower = str(niche).lower()
    
    # 1. Tentukan sub-folder berdasarkan kata kunci Niche
    if "sejarah" in niche_lower or "history" in niche_lower:
        sub_folder = "fakta_sejarah"
    elif "misteri" in niche_lower or "alam" in niche_lower or "kosmik" in niche_lower or "space" in niche_lower:
        sub_folder = "misteri_alam_semesta"
    else:
        # Default fallback
        sub_folder = "misteri_alam_semesta"

    bgm_dir = os.path.abspath(os.path.join("assets", "bgm", sub_folder))
    
    # 2. Cek keberadaan folder
    if not os.path.exists(bgm_dir):
        print(f"⚠️ Warning: Folder BGM '{bgm_dir}' tidak ditemukan!")
        return None

    # 3. Ambil semua file audio (.mp3, .wav, .m4a)
    audio_files = [f for f in os.listdir(bgm_dir) if f.lower().endswith(('.mp3', '.wav', '.m4a'))]

    if not audio_files:
        print(f"⚠️ Warning: Tidak ada file audio di folder '{bgm_dir}'!")
        return None

    # 4. Pilih 1 file secara acak
    selected_file = random.choice(audio_files)
    full_path = os.path.join(bgm_dir, selected_file)
    
    print(f"🎵 [Local BGM] Menggunakan backsound ({sub_folder}): {selected_file}")
    return full_path