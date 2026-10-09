import os
from moviepy import VideoFileClip

try:
    import numpy as np
except ImportError:
    np = None

BLACK_FRAME_THRESHOLD = 10.0   # rata-rata brightness 0-255; di bawah ini dianggap frame hitam
FREEZE_DIFF_THRESHOLD = 1.5    # rata-rata selisih piksel antar sampel; di bawah ini dianggap identik
FREEZE_RUN_MIN = 4             # berapa sampel berurutan identik baru dianggap "macet"


def _sample_frames(clip, duration, sample_count=12):
    """Ambil beberapa frame merata di sepanjang durasi untuk diperiksa."""
    if sample_count < 2 or duration <= 0:
        return []
    times = [duration * i / (sample_count - 1) for i in range(sample_count)]
    times = [min(t, max(duration - 0.05, 0)) for t in times]
    return [(t, clip.get_frame(t)) for t in times]


def detect_visual_defects(clip, duration, sample_count=12):
    """
    Deteksi cacat visual sederhana pada video hasil render:
    - Frame hitam (brightness rata-rata terlalu rendah) -> indikasi bg/overlay gagal muat.
    - Frame macet/freeze (beberapa sampel berurutan nyaris identik) -> indikasi render stuck.
    Return list string alasan (kosong = tidak ada cacat terdeteksi).
    """
    if np is None:
        return []  # numpy tidak ada -> lewati deteksi defect, QC dasar tetap jalan

    frames = _sample_frames(clip, duration, sample_count)
    if not frames:
        return []

    defects = []
    black_hits = []
    prev_arr = None
    freeze_run = 0
    max_freeze_run = 0

    for t, frame in frames:
        arr = np.asarray(frame, dtype=np.float32)
        brightness = float(arr.mean())
        if brightness < BLACK_FRAME_THRESHOLD:
            black_hits.append(round(t, 2))

        if prev_arr is not None and prev_arr.shape == arr.shape:
            diff = float(np.abs(arr - prev_arr).mean())
            if diff < FREEZE_DIFF_THRESHOLD:
                freeze_run += 1
                max_freeze_run = max(max_freeze_run, freeze_run)
            else:
                freeze_run = 0
        prev_arr = arr

    if len(black_hits) >= max(2, sample_count // 3):
        defects.append(f"Terdeteksi {len(black_hits)}/{len(frames)} sampel frame hitam (detik: {black_hits}).")

    if max_freeze_run >= FREEZE_RUN_MIN:
        defects.append(f"Terdeteksi indikasi frame macet/freeze ({max_freeze_run} sampel berurutan nyaris identik).")

    return defects


def inspect_video_quality(video_path, max_duration_sec=60.0, check_visual_defects=True):
    """
    ByteGuard (QC Inspector): Memeriksa kelayakan file video MP4 hasil render
    sebelum dikirim ke proses penerbitan.

    Pengecekan meliputi:
    1. Keberadaan file dan ukuran file (> 0.5 MB).
    2. Kesesuaian durasi (maksimal 60 detik untuk Shorts).
    3. Aspect ratio vertikal (tinggi > lebar / 9:16).
    4. Keberadaan track audio (mencegah video bisu).
    5. Cacat visual: frame hitam / frame macet (sampling, lihat detect_visual_defects).
    """
    print(f"🛡️ ByteGuard: Memulai inspeksi kualitas video '{os.path.basename(video_path)}'...")

    if not video_path or not os.path.exists(video_path):
        reason = f"File video tidak ditemukan di path: {video_path}"
        print(f"❌ ByteGuard QC Failed: {reason}")
        return {"passed": False, "reason": reason}

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb < 0.5:
        reason = f"Ukuran file video terlalu kecil ({file_size_mb:.2f} MB), indikasi file corrupt."
        print(f"❌ ByteGuard QC Failed: {reason}")
        return {"passed": False, "reason": reason}

    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        w, h = clip.size
        has_audio = clip.audio is not None
        clip.close()

        # 1. Cek Durasi Shorts
        if duration > max_duration_sec:
            reason = f"Durasi video ({duration:.1f} detik) melebihi batas YouTube Shorts (maksimal {max_duration_sec} detik)."
            print(f"❌ ByteGuard QC Failed: {reason}")
            return {"passed": False, "reason": reason}

        # 2. Cek Aspect Ratio Vertikal
        if h <= w:
            reason = f"Orientasi video bukan vertikal (Resolusi: {w}x{h}). Wajib format 9:16."
            print(f"❌ ByteGuard QC Failed: {reason}")
            return {"passed": False, "reason": reason}

        # 3. Cek Suara/Audio Track
        if not has_audio:
            reason = "Video tidak memiliki jalur audio (bisu)."
            print(f"❌ ByteGuard QC Failed: {reason}")
            return {"passed": False, "reason": reason}

        # 4. Cek cacat visual (frame hitam / macet)
        defects = []
        if check_visual_defects:
            clip2 = VideoFileClip(video_path)
            try:
                defects = detect_visual_defects(clip2, duration)
            finally:
                clip2.close()
            if defects:
                reason = "Cacat visual terdeteksi: " + " | ".join(defects)
                print(f"❌ ByteGuard QC Failed: {reason}")
                return {"passed": False, "reason": reason, "defects": defects}

        details = {
            "duration_sec": round(duration, 2),
            "resolution": f"{w}x{h}",
            "size_mb": round(file_size_mb, 2),
            "has_audio": has_audio,
            "defects": defects
        }

        print(f"✅ ByteGuard QC Passed! Video {w}x{h} ({duration:.1f}s, {file_size_mb:.2f}MB) siap dipublish.")
        return {
            "passed": True,
            "reason": "Video memenuhi seluruh standar kelayakan Shorts.",
            "details": details
        }

    except Exception as e:
        reason = f"Gagal membaca struktur file video: {str(e)}"
        print(f"💥 ByteGuard QC Exception: {reason}")
        return {"passed": False, "reason": reason}