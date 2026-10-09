import os
import random
import re

import requests

from config.settings import PEXELS_API_KEY, BG_DIR

API = "https://api.pexels.com/v1/search"
PER_PROMPT = 1                      # foto per kata kunci (visual utama kini motion graphic/infografis)
MAX_BG = int(os.environ.get("BG_MAX", "3"))   # batas total foto latar; ubah via .env BG_MAX
FALLBACK_QUERIES = ["ancient ruins", "old map", "galaxy", "night sky", "dark history", "vintage library"]
STOP_WORDS = {"hyper-realistic", "hyperrealistic", "8k", "4k", "hd", "cinematic", "lighting",
              "detailed", "resolution", "realistic"}


def clean_search_query(query):
    """Membersihkan prompt dari kata-kata sampah AI agar ramah pencarian Pexels."""
    words = re.sub(r"[^a-zA-Z0-9\s]", "", str(query)).split()
    return " ".join([w for w in words if w.lower() not in STOP_WORDS][:3])   # maks 3 kata -> spesifik


def _search(query, per_page):
    """Return list foto Pexels ([] jika gagal). Query di-encode lewat params=."""
    res = requests.get(API, headers={"Authorization": PEXELS_API_KEY},
                       params={"query": query, "orientation": "portrait", "per_page": per_page}, timeout=15)
    if res.status_code != 200:
        print(f"  ❌ Pexels API Error {res.status_code}")
        return []
    return res.json().get("photos", [])


def _download(photo, path):
    img = requests.get(photo["src"]["large2x"], timeout=20)
    img.raise_for_status()
    with open(path, "wb") as f:
        f.write(img.content)
    return path


def fetch_pexels_photo(query, filename):
    """Download sampai PER_PROMPT foto. Return list path (kosong bila semuanya gagal)."""
    clean_q = clean_search_query(query)
    print(f"🔍 Searching Pexels for: '{clean_q}'...")
    try:
        photos = _search(clean_q, 3) if clean_q else []
    except Exception as e:
        print(f"  ❌ Error fetching photo: {e}")
        photos = []
    if not photos:
        fb = random.choice(FALLBACK_QUERIES)
        print(f"  ⚠️ Tidak ada foto untuk '{clean_q}'. Fallback: '{fb}'")
        return fetch_fallback_photo(fb, filename)

    saved = []
    for idx, photo in enumerate(photos[:PER_PROMPT]):
        try:
            saved.append(_download(photo, os.path.join(BG_DIR, f"{idx}_{filename}")))
        except Exception as e:
            print(f"  ⚠️ Gagal unduh foto {idx}: {e}")
    print(f"  ✅ Saved {len(saved)} images for: {clean_q}")
    return saved or fetch_fallback_photo(random.choice(FALLBACK_QUERIES), filename)


def fetch_fallback_photo(fallback_query, filename):
    """Pencarian cadangan. Return list berisi 1 path, atau []."""
    try:
        photos = _search(fallback_query, 10)
        if photos:
            path = _download(random.choice(photos), os.path.join(BG_DIR, filename))
            print(f"  ✅ Fallback saved: {filename}")
            return [path]
    except Exception as e:
        print(f"  ❌ Fallback gagal: {e}")
    return []


def download_multiple_backgrounds(prompts):
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY belum diisi (Settings → API Keys, atau file .env).")
    os.makedirs(BG_DIR, exist_ok=True)
    print("🖼️ Fetching stock photos from Pexels API...")
    paths = []
    prompts = list(prompts)[:MAX_BG]               # kurangi jumlah download
    for i, prompt in enumerate(prompts):
        paths.extend(fetch_pexels_photo(prompt, f"bg_{i+1}.jpg"))
    if not paths:
        raise RuntimeError("Tidak ada background yang berhasil diunduh dari Pexels (cek internet / API key).")
    return paths
