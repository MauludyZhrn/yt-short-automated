"""
modules/row_platforms.py
========================
Satu sumber kebenaran untuk "tempat publish" tiap baris Content Planner.

Masalah yang dipecahkan:
  Sebelumnya target publish hanya ada di Settings (`default_platforms`) — semantics-nya
  global: semua baris dipublish ke tempat yang sama. Padahal tiap ide konten bisa punya
  tempat terbaik sendiri (mis. fakta sejarah cocok ke YouTube Shorts, tantangan ringan
  cocok ke TikTok). Modul ini menyimpan pemetaan  baris -> daftar platform  dan dipakai
  bersama oleh:
    * Content Planner  (UI web: klik kolom Platform di tabel)
    * NexaTrend        (riset tren per-platform, langsung menandai ide hasil riset)
    * CrossByte        (multi_publisher: publish per baris sesuai targetnya)
    * main.py          (mode auto: publish ke platform milik baris itu)

Prioritas resolusi platform sebuah baris:
    1. nilai yang datang dari Google Sheets (kolom "Platform", dibaca sheets_manager)
    2. override lokal di row_platforms.json (yang diedit dari UI / ditulis NexaTrend)
    3. default_platforms dari Settings
    4. ["youtube"]

Kenapa override disimpan lokal & bukan langsung ke Sheets?
  Penulisan balik ke Sheets butuh fungsi khusus di modules/sheets_manager.py yang belum
  tentu ada di semua instalasi. Modul ini tetap MENCOBA sinkronisasi bila fungsi
  `update_row_platforms()` tersedia; kalau tidak ada, nilai tetap tersimpan lokal dan
  ketahuan di UI (tanpa pernah merusak baris Sheets).
"""
import json
import os
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_FILE = os.path.join(BASE_DIR, "row_platforms.json")

DEFAULT_SHEET = "Shorts Content Planner"
DEFAULT_PLATFORMS = ["youtube"]

# Urutan tetap supaya tampilan UI konsisten
KNOWN_PLATFORMS = ("youtube", "tiktok", "instagram", "facebook")

# Nama alternatif yang biasa muncul di Sheets / input user
ALIASES = {
    "yt": "youtube", "youtube shorts": "youtube", "shorts": "youtube", "yt shorts": "youtube",
    "yt short": "youtube", "youtube short": "youtube",
    "tik tok": "tiktok", "tiktok": "tiktok", "tt": "tiktok",
    "ig": "instagram", "ig reels": "instagram", "ig reel": "instagram", "insta": "instagram",
    "instagram reels": "instagram", "instagram reel": "instagram", "reels": "instagram", "reel": "instagram",
    "fb": "facebook", "fb reels": "facebook", "fb reel": "facebook", "facebook reels": "facebook",
    "facebook reel": "facebook", "meta": "facebook",
}

_lock = threading.Lock()


# ------------------------------------------------------------------ parsing
def normalize_pid(pid):
    """'IG Reels' -> 'instagram'. None bila tidak dikenal."""
    if pid is None:
        return None
    s = str(pid).strip().lower().replace("_", " ")
    s = " ".join(s.split())
    if s in ALIASES:
        return ALIASES[s]
    return s if s in KNOWN_PLATFORMS else None


def parse_platforms(value, fallback=None):
    """Terima list / string 'youtube, tiktok' / 'youtube|tiktok' -> list platform valid.

    Nilai yang tidak dikenal dibuang (bukan bikin error), hasil diurutkan sesuai
    KNOWN_PLATFORMS dan tanpa duplikat. Kosong -> fallback.
    """
    if value is None:
        items = []
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        s = str(value).strip()
        if not s:
            items = []
        else:
            items = [p for chunk in s.replace("|", ",").replace(";", ",").replace("/", ",").split(",") for p in [chunk]]
    out = []
    for raw in items:
        pid = normalize_pid(raw)
        if pid and pid not in out:
            out.append(pid)
    out.sort(key=lambda p: KNOWN_PLATFORMS.index(p) if p in KNOWN_PLATFORMS else 99)
    if out:
        return out
    return list(fallback) if fallback else list(DEFAULT_PLATFORMS)


def format_platforms(platforms):
    """Kebalikan parse_platforms: list -> 'youtube, tiktok' (untuk kolom Sheets)."""
    return ", ".join(parse_platforms(platforms, []))


# ------------------------------------------------------------------ storage
def load_overrides():
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): parse_platforms(v, None) for k, v in data.items() if v}
    except (OSError, ValueError):
        pass
    return {}


def _save_overrides(data):
    tmp = STORE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STORE_FILE)


def get_row_platforms(row_id):
    """Platform tersimpan untuk satu baris, None bila belum pernah diatur."""
    if row_id is None or str(row_id).strip() == "":
        return None
    return load_overrides().get(str(row_id).strip())


def set_row_platforms(row_id, platforms, sync_sheet=True, sheet_name=DEFAULT_SHEET):
    """Simpan target platform satu baris. Return list final yang tersimpan."""
    plats = parse_platforms(platforms)
    key = str(row_id).strip()
    with _lock:
        data = load_overrides()
        data[key] = plats
        _save_overrides(data)
    if sync_sheet:
        sync_to_sheet(row_id, plats, sheet_name)
    return plats


def set_many(pairs, sheet_name=DEFAULT_SHEET):
    """Bulk: pairs = iterable of (row_id, platforms). Dipakai NexaTrend & bulk edit UI."""
    with _lock:
        data = load_overrides()
        for row_id, platforms in pairs:
            if row_id is None or str(row_id).strip() == "":
                continue
            data[str(row_id).strip()] = parse_platforms(platforms)
        _save_overrides(data)
    return dict(data)


def sync_to_sheet(row_id, platforms, sheet_name=DEFAULT_SHEET):
    """Tulis balik ke Google Sheets — upaya terbaik (best effort).

    Hanya jalan kalau modules/sheets_manager.py punya `update_row_platforms(row_id, platforms, ...)`.
    Kalau tidak ada (atau gagal), diam saja: nilai sudah aman di row_platforms.json.
    Return True bila Sheets ikut terupdate.
    """
    try:
        from modules import sheets_manager as sheets
    except Exception:
        return False
    fn = getattr(sheets, "update_row_platforms", None)
    if not callable(fn):
        return False
    try:
        fn(row_id, format_platforms(platforms), sheet_name=sheet_name)
        return True
    except TypeError:                      # signature lama: (row_id, platforms)
        try:
            fn(row_id, format_platforms(platforms))
            return True
        except Exception as exc:
            print(f"⚠️ row_platforms: sinkronisasi Sheets gagal ({exc}) — nilai tetap tersimpan lokal.")
            return False
    except Exception as exc:
        print(f"⚠️ row_platforms: sinkronisasi Sheets gagal ({exc}) — nilai tetap tersimpan lokal.")
        return False


# ------------------------------------------------------------------ resolusi
def resolve(row_id=None, row_platforms=None, default=None):
    """Tentukan platform sebuah baris mengikuti urutan prioritas di atas."""
    for cand in (row_platforms, get_row_platforms(row_id) if row_id is not None else None, default):
        plats = parse_platforms(cand, None) if cand else None
        if plats:
            return plats
    return list(DEFAULT_PLATFORMS)


def attach(rows, default=None):
    """Isi field 'platforms' di setiap baris (dipakai server sebelum dikirim ke UI)."""
    overrides = load_overrides()
    out = []
    for r in rows or []:
        r = dict(r)
        rid = str(r.get("id", "")).strip()
        r["platforms"] = resolve(rid, r.get("platforms") or r.get("platform"),
                                 overrides.get(rid) or default)
        out.append(r)
    return out


def summary(rows):
    """Hitung jumlah baris per platform — untuk badge ringkas di UI."""
    out = {p: 0 for p in KNOWN_PLATFORMS}
    for r in rows or []:
        for p in parse_platforms(r.get("platforms"), DEFAULT_PLATFORMS):
            if p in out:
                out[p] += 1
    return {k: v for k, v in out.items() if v}
