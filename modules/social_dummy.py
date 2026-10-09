"""
modules/social_dummy.py
=======================
Konektor multi-platform DUMMY untuk TikTok, Instagram Reels, dan Facebook Reels.

* Tidak ada request ke API asli — upload hanya disimulasikan (progress + URL palsu).
* Status koneksi akun disimpan di  social_accounts.json
* Riwayat publish disimpan di      publish_log.json
* YouTube tetap memakai modules/youtube_uploader.py (asli); di sini hanya dicatat
  sebagai metadata platform supaya UI punya satu daftar platform yang seragam.

Saat API asli sudah siap, cukup ganti isi fungsi `_upload_<platform>` dan ubah
`"dummy": False` pada PLATFORMS — server/UI tidak perlu diubah.
"""
import json
import os
import random
import re
import string
import threading
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "social_accounts.json")
PUBLISH_LOG_FILE = os.path.join(BASE_DIR, "publish_log.json")
_lock = threading.Lock()

PLATFORMS = {
    "youtube": {
        "label": "YouTube Shorts", "icon": "fi-brands-youtube", "color": "#FF0000",
        "dummy": False, "caption_max": 5000, "hashtag_max": 15,
    },
    "tiktok": {
        "label": "TikTok", "icon": "fi-brands-tik-tok", "color": "#111317",
        "dummy": True, "caption_max": 2200, "hashtag_max": 5,
    },
    "instagram": {
        "label": "Instagram Reels", "icon": "fi-brands-instagram", "color": "#E1306C",
        "dummy": True, "caption_max": 2200, "hashtag_max": 10,
    },
    "facebook": {
        "label": "Facebook Reels", "icon": "fi-brands-facebook", "color": "#1877F2",
        "dummy": True, "caption_max": 63206, "hashtag_max": 5,
    },
}
DUMMY_IDS = [k for k, v in PLATFORMS.items() if v["dummy"]]


# ------------------------------------------------------------------ storage
def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ------------------------------------------------------------------ akun
def get_accounts():
    with _lock:
        return _load(ACCOUNTS_FILE, {})


def is_connected(pid):
    return pid in get_accounts()


def connect(pid, username):
    if pid not in DUMMY_IDS:
        raise ValueError(f"Platform '{pid}' tidak dikenal atau bukan platform dummy.")
    username = re.sub(r"^@+", "", (username or "").strip())
    if not re.fullmatch(r"[A-Za-z0-9._]{2,30}", username):
        raise ValueError("Username 2–30 karakter (huruf, angka, titik, underscore).")
    with _lock:
        acc = _load(ACCOUNTS_FILE, {})
        acc[pid] = {"username": username, "connected_at": time.strftime("%Y-%m-%d %H:%M:%S"), "dummy": True}
        _save(ACCOUNTS_FILE, acc)
    return acc[pid]


def disconnect(pid):
    with _lock:
        acc = _load(ACCOUNTS_FILE, {})
        if pid not in acc:
            raise ValueError("Akun belum terhubung.")
        acc.pop(pid)
        _save(ACCOUNTS_FILE, acc)


# ------------------------------------------------------------------ caption
def _hashtags(tags, limit):
    out = []
    for t in tags:
        h = re.sub(r"[^0-9A-Za-zÀ-ÿ_]", "", str(t))
        if h and f"#{h.lower()}" not in [x.lower() for x in out]:
            out.append(f"#{h}")
        if len(out) >= limit:
            break
    return out


def build_caption(pid, title, description, tags):
    """Sesuaikan judul/deskripsi YouTube menjadi caption per platform."""
    spec = PLATFORMS[pid]
    title, description = (title or "").strip(), (description or "").strip()
    tags = list(tags or [])
    desc_plain = "\n".join(l for l in description.splitlines() if not l.strip().startswith("#")).strip()
    # hashtag: yang sudah ada di deskripsi + dari tag, tanpa duplikat
    found = re.findall(r"#\w+", description)
    merged = []
    for h in found + _hashtags(tags, 30):
        if h.lower() not in [x.lower() for x in merged]:
            merged.append(h)
    tagline = " ".join(merged[: spec["hashtag_max"]])

    if pid == "tiktok":
        body = f"{title}\n\n{tagline}"          # TikTok: pendek, hashtag sedikit
    elif pid == "instagram":
        first = desc_plain.split("\n\n")[0] if desc_plain else ""
        body = f"{title}\n\n{first}\n\n{tagline}".replace("\n\n\n", "\n\n")
    else:                                       # facebook & lainnya
        body = f"{title}\n\n{desc_plain}\n\n{tagline}"
    body = body.strip()
    return body[: spec["caption_max"]]


# ------------------------------------------------------------------ upload dummy
def _rand(n, alphabet=string.digits):
    return "".join(random.choice(alphabet) for _ in range(n))


def _fake_url(pid, username):
    if pid == "tiktok":
        return f"https://www.tiktok.com/@{username}/video/{_rand(19)}"
    if pid == "instagram":
        return f"https://www.instagram.com/reel/{_rand(11, string.ascii_letters + string.digits)}/"
    return f"https://www.facebook.com/reel/{_rand(15)}"


def upload(pid, video_path, caption, privacy="public", publish_at=None, progress_callback=None):
    """Simulasi upload. Return dict {id, url, dummy, caption_len}. Raise Exception jika gagal."""
    if pid not in DUMMY_IDS:
        raise ValueError(f"Platform '{pid}' tidak didukung oleh konektor dummy.")
    acc = get_accounts().get(pid)
    if not acc:
        raise RuntimeError(f"Akun {PLATFORMS[pid]['label']} belum terhubung (menu Akun).")
    if not video_path or not os.path.isfile(video_path):
        raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")
    if not (caption or "").strip():
        raise ValueError("Caption kosong.")
    # Uji jalur error: set env SOCIAL_DUMMY_FAIL=tiktok,instagram
    if pid in os.environ.get("SOCIAL_DUMMY_FAIL", "").lower().split(","):
        raise RuntimeError(f"[DUMMY] {PLATFORMS[pid]['label']} menolak upload (SOCIAL_DUMMY_FAIL).")

    print(f"🧪 [DUMMY] Upload ke {PLATFORMS[pid]['label']} (@{acc['username']}) — simulasi, tidak ada data terkirim.")
    steps = 10
    for i in range(1, steps + 1):
        time.sleep(random.uniform(0.15, 0.35))
        if progress_callback:
            progress_callback(int(i / steps * 100))
    vid = _rand(12)
    return {"id": vid, "url": _fake_url(pid, acc["username"]), "dummy": True,
            "caption_len": len(caption), "scheduled": publish_at is not None,
            "privacy": privacy}


# ------------------------------------------------------------------ riwayat
def log_publish(row_id, pid, info):
    """Catat hasil publish per baris & platform (sukses/gagal)."""
    entry = {"platform": pid, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
             "dummy": PLATFORMS.get(pid, {}).get("dummy", False), **info}
    with _lock:
        data = _load(PUBLISH_LOG_FILE, {})
        data.setdefault(str(row_id), []).append(entry)
        data[str(row_id)] = data[str(row_id)][-40:]
        _save(PUBLISH_LOG_FILE, data)


def get_publish_log(row_id):
    with _lock:
        return _load(PUBLISH_LOG_FILE, {}).get(str(row_id), [])