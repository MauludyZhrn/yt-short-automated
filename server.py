import sys
import os
import json
import time
import re
import queue
import calendar
import datetime
import threading
import subprocess
import traceback
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv, set_key, unset_key
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
import asyncio

import office_bus
from office_bus import notify_office  # noqa: F401

# Konsol Windows (cp1252) crash saat print emoji -> paksa UTF-8
for _st in (sys.__stdout__, sys.__stderr__):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# PATH & KONFIGURASI DASAR
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Modul SEO/copywriting YouTube
try:
    from modules import youtube_uploader as yt_seo
except Exception as _exc:
    yt_seo = None
    print(f"⚠️ Modul youtube_uploader tidak bisa dimuat: {_exc}")

# Konektor multi-platform ASLI (TikTok / Instagram Reels / Facebook Reels)
try:
    from modules import social_real as social
except Exception as _exc:
    social = None
    print(f"⚠️ Modul social_real tidak bisa dimuat: {_exc}")

# Agen Ke-3: CrossByte Multi-Publisher Agent
try:
    from modules import multi_publisher
except Exception as _exc:
    multi_publisher = None
    print(f"⚠️ Modul multi_publisher tidak bisa dimuat: {_exc}")

# Agen Metrix: Data Analyst (laporan performa, bias engagement untuk tab Analytics)
try:
    from modules.data_analyst import MetrixDataAnalyst, load_bias, REPORTS_DIR as METRIX_REPORTS_DIR
except Exception as _exc:
    MetrixDataAnalyst = None
    METRIX_REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    def load_bias():
        return {}
    print(f"⚠️ Modul data_analyst (Metrix) tidak bisa dimuat: {_exc}")

PLATFORM_META = dict(social.PLATFORMS) if social else {
    "youtube": {"label": "YouTube Shorts", "icon": "fi-brands-youtube", "color": "#FF0000",
                "dummy": False, "caption_max": 5000, "hashtag_max": 15}}

CATEGORY_CHOICES = dict(yt_seo.CATEGORIES) if yt_seo else {"Education": "27"}
DEFAULT_CATEGORY = yt_seo.DEFAULT_CATEGORY_NAME if yt_seo else "Education"
DEFAULT_CHANNEL_NAME = yt_seo.CHANNEL_NAME if yt_seo else "MorbMyth"
TITLE_MAX = getattr(yt_seo, "TITLE_MAX", 100)
DESC_MAX_BYTES = getattr(yt_seo, "DESC_MAX_BYTES", 5000)
TAGS_MAX_CHARS = getattr(yt_seo, "TAGS_MAX_CHARS", 500)

PRIVACY_CHOICES = {
    "Public": "public",
    "Unlisted": "unlisted",
    "Private": "private",
    "Jadwalkan": "scheduled",
}

ENV_FILE = os.path.join(BASE_DIR, ".env")
SETTINGS_FILE = os.path.join(BASE_DIR, "gui_settings.json") # Tetap dipertahankan namanya
HISTORY_FILE = os.path.join(BASE_DIR, "gui_history.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TEMP_DIR = os.path.join(BASE_DIR, "remotion-app", "public", "temp")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")

load_dotenv(ENV_FILE)

APP_VERSION = "2.4.0 Pro (Server Edition)"
SHEET_NAME = "Shorts Content Planner"
ROWS_CACHE_TTL = 15

UPLOAD_MODES = {
    "Draft / Edit Dulu (Manual Publish)": "draft",
    "Langsung Publish (Full Auto)": "auto",
}

DEFAULT_SETTINGS = {
    "upload_mode": "Draft / Edit Dulu (Manual Publish)",
    "interval": 30,
    "retries": 3,
    "output_folder": "",
    "log_level": "Info",
    "notifications": True,
    "autostart": False,
    "sidebar_collapsed": False,
    "channel_name": DEFAULT_CHANNEL_NAME,
    "default_platforms": ["youtube"],   # target publish untuk mode Auto & pilihan awal di Video Studio
}

MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]

# ============================================================
# SKEMA WARNA & STYLE (Dipertahankan untuk referensi UI/Frontend Web)
# ============================================================
YELLOW        = "#FFD027"
YELLOW_HOVER  = "#E6BC22"
YELLOW_SOFT   = "#FEF3C7"
YELLOW_FAINT  = "#FFFBEB"
SIDEBAR       = "#121316"
SIDEBAR_HOVER = "#1E2024"
SIDEBAR_CARD  = "#191B20"
SIDEBAR_LINE  = "#26282F"
SIDEBAR_TEXT  = "#A6ABB7"
SIDEBAR_FAINT = "#6B7280"
SURFACE       = "#F5F6FA"
CARD          = "#FFFFFF"
BORDER        = "#E8EAED"
GRAY_100      = "#F3F4F6"
GRAY_200      = "#E5E7EB"
TEXT          = "#111317"
TEXT_MUTED    = "#6B7280"
TEXT_FAINT    = "#9CA3AF"
EMERALD       = "#10B981"
EMERALD_DARK  = "#047857"
EMERALD_BG    = "#D1FAE5"
AMBER_DARK    = "#B45309"
AMBER_BG      = "#FEF3C7"
SKY_DARK      = "#0369A1"
SKY_BG        = "#E0F2FE"
ROSE          = "#E5484D"
ROSE_DARK     = "#BE123C"
ROSE_BG       = "#FFE4E6"
TERMINAL_BG   = "#141518"

LOG_COLORS = {"info": "#D1D5DB", "ok": "#34D399", "warn": "#FBBF24", "err": "#FB7185"}

STATUS_STYLE = {
    "ready":            (AMBER_DARK,   AMBER_BG,   "ready"),
    "processing":       (SKY_DARK,     SKY_BG,     "processing"),
    "ready for review": ("#111317",    YELLOW,     "review"),
    "done":             (EMERALD_DARK, EMERALD_BG, "done"),
    "failed":           (ROSE_DARK,    ROSE_BG,    "failed"),
}

STOPWORDS_ID = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "dalam", "ini", "itu", "adalah",
    "atau", "akan", "oleh", "sebuah", "satu", "para", "juga", "saat", "bisa", "tidak", "detik",
    "the", "and", "of", "with",
}

# ============================================================
# HELPER SEO
# ============================================================
def seo_keywords(title, limit=4):
    out = []
    for w in re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", title.lower()):
        if w in STOPWORDS_ID or w in out:
            continue
        out.append(w)
        if len(out) >= limit:
            break
    return out

def seo_analyze(title, description, tags):
    checks, score = [], 0
    t, d = title.strip(), description.strip()
    n = len(t)

    if 30 <= n <= 70:
        score += 20
        checks.append((True, f"Judul {n} karakter (ideal 30–70)"))
    elif 15 <= n < 30 or 70 < n <= 100:
        score += 10
        checks.append((None, f"Judul {n} karakter — ideal 30–70, maks 100"))
    else:
        checks.append((False, f"Judul {n} karakter — ideal 30–70, maks 100"))

    hashtags = re.findall(r"#\w+", d)
    if any(h.lower() == "#shorts" for h in hashtags) or "#shorts" in t.lower():
        score += 10
        checks.append((True, "Ada #Shorts"))
    else:
        checks.append((False, "Tambahkan #Shorts di deskripsi"))

    dn = len(d)
    if dn >= 100:
        score += 15
        checks.append((True, f"Deskripsi {dn} karakter"))
    elif dn >= 50:
        score += 8
        checks.append((None, f"Deskripsi {dn} karakter — sebaiknya ≥ 100"))
    else:
        checks.append((False, f"Deskripsi {dn} karakter — terlalu pendek (≥ 100)"))

    kws = seo_keywords(t)
    hit = [k for k in kws if k in d[:150].lower()]
    if hit:
        score += 15
        checks.append((True, f"Keyword '{hit[0]}' ada di awal deskripsi"))
    elif kws:
        checks.append((False, f"Masukkan keyword '{kws[0]}' di 150 karakter pertama deskripsi"))
    else:
        checks.append((False, "Judul belum punya keyword yang jelas"))

    hn = len(hashtags)
    if 3 <= hn <= 5:
        score += 10
        checks.append((True, f"{hn} hashtag di deskripsi (ideal 3–5)"))
    elif 1 <= hn <= 2 or 6 <= hn <= 15:
        score += 5
        checks.append((None, f"{hn} hashtag — ideal 3–5"))
    else:
        checks.append((False, "Hashtag tidak ada / lebih dari 15 (YouTube mengabaikan semuanya)"))

    tn = len(tags)
    if 5 <= tn <= 12:
        score += 15
        checks.append((True, f"{tn} tag (ideal 5–12)"))
    elif 3 <= tn <= 4 or 13 <= tn <= 15:
        score += 8
        checks.append((None, f"{tn} tag — ideal 5–12"))
    else:
        checks.append((False, f"{tn} tag — ideal 5–12"))

    chars = sum(len(x) for x in tags) + max(0, tn - 1)
    if tn and chars <= 500:
        score += 5
        checks.append((True, f"Total tag {chars}/500 karakter"))
    else:
        checks.append((False, f"Total tag {chars}/500 karakter" if tn else "Belum ada tag"))

    if kws and any(k in " ".join(tags).lower() for k in kws):
        score += 10
        checks.append((True, "Tag memuat keyword judul"))
    else:
        checks.append((False, "Tambahkan tag yang memuat keyword judul"))

    return score, checks

def local_report(title, description, tags, topic=""):
    score, checks = seo_analyze(title, description, tags)
    mapped = [("ok" if ok is True else "warn" if ok is None else "err", text) for ok, text in checks]
    errors = []
    if not title.strip():
        errors.append("Judul kosong")
    elif len(title.strip()) > TITLE_MAX:
        errors.append(f"Judul lebih dari {TITLE_MAX} karakter")
    return {
        "score": score,
        "counts": {"title": len(title.strip()), "desc_bytes": len(description.encode("utf-8")),
                   "tags": sum(len(t) for t in tags)},
        "checks": mapped,
        "errors": errors,
        "warnings": [t for st, t in mapped if st != "ok"],
    }

TITLE_TEMPLATES = ["{topic}", "Fakta Unik: {topic}", "Tahukah Kamu? {topic}",
                   "{topic} — Ini Penjelasannya", "Rahasia di Balik {topic}", "Jarang Diketahui: {topic}"]

def local_seo_metadata(topic, niche, hook, channel, variant=0, disclose_ai=True):
    """Fallback bila modules/youtube_uploader.py tidak termuat / error — fitur Generate SEO tetap jalan."""
    topic = (topic or "").strip() or "Fakta Unik"
    niche = (niche or "").strip()
    v = variant % len(TITLE_TEMPLATES)
    title = TITLE_TEMPLATES[v].format(topic=topic)
    if len(title) > TITLE_MAX:
        title = title[: TITLE_MAX - 1].rstrip() + "…"
    lead = (hook or "").strip() or f"Simak fakta menarik tentang {topic}."
    parts = [f"{lead} {topic} — fakta singkat seputar {niche or 'topik ini'} dalam hitungan detik.",
             f"Suka konten seperti ini? Like, Comment & Subscribe {channel}!"]
    if disclose_ai:
        parts.append("Video ini dibuat dengan bantuan AI.")
    clean_niche = re.sub(r"[^0-9A-Za-z_]+", "", niche) or "Fakta"
    parts.append(f"#Shorts #{clean_niche} #FaktaUnik")
    tags = []
    for w in seo_keywords(topic, 6) + ([niche.lower()] if niche else []) + ["shorts", "fakta unik"]:
        if w and w not in tags:
            tags.append(w)
    return {"title": title, "description": "\n\n".join(parts), "tags": tags, "variant": v}

def _analyze(title, description, tags, topic=""):
    if yt_seo is not None:
        try:
            return yt_seo.analyze_metadata(title, description, tags, topic)
        except Exception as exc:
            print(f"⚠️ analyze_metadata gagal ({exc}) — memakai analisis lokal.")
    return local_report(title, description, tags, topic)

def _parse_schedule(text):
    if yt_seo is not None and hasattr(yt_seo, "parse_schedule"):
        return yt_seo.parse_schedule(text)
    dt = datetime.datetime.strptime((text or "").strip(), "%Y-%m-%d %H:%M")
    if dt <= datetime.datetime.now():
        raise ValueError("Jadwal harus di masa depan.")
    return dt.astimezone().isoformat()

# ============================================================
# HELPER DATA
# ============================================================
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_settings():
    data = dict(DEFAULT_SETTINGS)
    data.update(load_json(SETTINGS_FILE, {}))
    return data

def normalize_row(raw):
    row = dict(raw)
    for key in ("niche", "topic", "hook", "status", "output"):
        value = row.get(key)
        row[key] = "" if value is None else str(value)
    row.setdefault("id", "-")
    row["is_url"] = is_url(row["output"])
    row["exists"] = row["is_url"] or (bool(row["output"]) and os.path.exists(os.path.abspath(row["output"])))
    return row

def status_key(row):
    return str(row.get("status", "")).strip().lower()

def status_style(key):
    return STATUS_STYLE.get(key, (TEXT_MUTED, GRAY_200, "ready"))

def id_sort_key(row):
    try:
        return int(str(row.get("id", 0)))
    except (ValueError, TypeError):
        return 0

def is_url(value):
    return str(value).lower().startswith(("http://", "https://"))

def shorten(text, limit):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

def short_date(d):
    return f"{d.day} {MONTHS_ID[d.month - 1][:3]}"

# ============================================================
# REDIRECTOR STDOUT -> QUEUE (Thread-Safe untuk Web API Logs)
# ============================================================
class APITextRedirector:
    def __init__(self, log_queue):
        self.log_queue = log_queue
        self.terminal = sys.__stdout__

    def write(self, text):
        # Tulis ke terminal asli (abaikan jika error)
        if self.terminal:
            try:
                self.terminal.write(text)
                self.terminal.flush()
            except:
                pass
            
        clean_text = text.strip()
        if clean_text:
            level = self._classify_log(clean_text)
            if level == "debug" and str(getattr(state, "settings", {}).get("log_level", "Info")).lower() != "debug":
                return
            try:
                import time # Pastikan modul time tersedia
                self.log_queue.put_nowait({
                    "time": time.strftime("%H:%M:%S"), 
                    "level": level, 
                    "text": clean_text
                })
            except Exception: # Tangkap semua jenis error agar bot tidak macet
                pass

    def flush(self):
        if self.terminal:
            try:
                self.terminal.flush()
            except:
                pass

    def isatty(self):
        return False
        
    @staticmethod
    def _classify_log(text):
        if text.startswith("[DEBUG]"):
            return "debug"
        if any(m in text for m in ("❌", "Error", "Traceback", "Exception")):
            return "err"
        if "⚠️" in text or "Warning" in text:
            return "warn"
        if any(m in text for m in ("✅", "✨", "🎉", "⏹️", "🚀", "📤", "🎯")):
            return "ok"
        return "info"

# ============================================================
# SERVER STATE (Pengganti Class GUI app_gui.py)
# ============================================================
class ServerState:
    def __init__(self):
        self.settings = load_settings()
        self.history = load_json(HISTORY_FILE, {})
        self.log_queue = queue.Queue(maxsize=1500) # Batas buffer log
        
        self.is_running = False
        self.rows = None
        self._rows_ts = 0.0
        self._rows_loading = False
        self._review_count = None
        self._generating = False
        self._metrix_generating = False
        self.waiting_for_user = False
        self.rows_lock = threading.Lock()
        self.thread = None
        self.countdown = 0
        self.pub = {"busy": False, "progress": 0, "message": "", "error": None, "url": None,
                    "partial": False, "row_id": None, "items": {}}

state = ServerState()
os.environ["LOG_LEVEL"] = str(state.settings.get("log_level", "Info"))
sys.stdout = APITextRedirector(state.log_queue)

# ============================================================
# FASTAPI APPLICATION & ENDPOINTS
# ============================================================
@asynccontextmanager
async def lifespan(_app):
    office_bus.set_loop(asyncio.get_running_loop())
    if state.settings.get("autostart"):
        _start_automation()
    yield

app = FastAPI(title="YouTube Shorts Automation Server", version=APP_VERSION, lifespan=lifespan)

@app.websocket("/ws/office")
async def websocket_office(ws: WebSocket):
    await office_bus.register(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        office_bus.connections.discard(ws)


@app.get("/api/office/config")
def office_config():
    """Info untuk tab Office 3D: URL Hermes3D, status adapter & Ollama."""
    import urllib.request
    base = os.getenv("HERMES3D_URL", f"http://127.0.0.1:{os.getenv('HERMES3D_PORT', '3000')}").rstrip("/")
    adapter = office_bus.ADAPTER_URL

    def _up(url):
        try:
            urllib.request.urlopen(url, timeout=1.5).read(64)
            return True
        except Exception:
            return False
    return {"hermes3d_url": base, "hermes3d_up": _up(base + "/"),
            "adapter_url": adapter, "adapter_up": _up(adapter + "/health")}


@app.get("/api/ollama/status")
def ollama_status():
    from modules import ollama_client
    return ollama_client.status()


class ChatIn(BaseModel):
    message: str


@app.post("/api/office/chat")
def office_chat(req: ChatIn):
    """Ngobrol dengan Hermes (CEO) via Ollama; bisa memicu start/stop/generate."""
    from modules import ollama_client as oc
    rows = state.rows or []
    ctx = {"automation_berjalan": state.is_running, "baris_ready": sum(status_key(r) == "ready" for r in rows),
           "siap_review": sum(status_key(r) == "ready for review" for r in rows), "total_baris": len(rows)}
    try:
        out = oc.hermes_chat(req.message.strip()[:500], ctx)
    except Exception as exc:
        raise HTTPException(503, f"Ollama tidak merespons ({exc}). Jalankan 'ollama serve' & 'ollama pull {oc.MODEL}'.")
    act = out["action"]
    if act == "start":
        _start_automation()
    elif act == "stop":
        state.is_running = False
        state.waiting_for_user = False
    elif act == "generate" and not state._generating:
        def _gen():
            state._generating = True
            try:
                from modules.sheets_manager import generate_content_ideas_to_sheet
                generate_content_ideas_to_sheet(count=5)
                state._rows_ts = 0.0
            except Exception as exc:
                print(f"❌ Gagal generate ide: {exc}")
            finally:
                state._generating = False
        threading.Thread(target=_gen, daemon=True).start()
    return out


class SEORequest(BaseModel):
    title: str
    description: str
    tags: list[str]
    topic: str = ""
    niche: str = ""
    hook: str = ""
    variant: int = 0
    disclose_ai: bool = True

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "version": APP_VERSION,
        "is_running": state.is_running,
        "generating_ideas": state._generating,
        "countdown": state.countdown,
        "stopping": (not state.is_running) and bool(state.thread and state.thread.is_alive()),
        "publish": state.pub,
        "waiting_for_user": getattr(state, "waiting_for_user", False)
    }

@app.get("/api/settings")
def get_settings():
    keys = {"groq": bool(os.getenv("GROQ_API_KEY")), "pexels": bool(os.getenv("PEXELS_API_KEY")),
            "magick": bool(os.getenv("IMAGEMAGICK_PATH"))}
    return {**state.settings, "keys_set": keys}

@app.get("/api/rows")
def get_rows(force: bool = False):
    """Menarik data Planner dari Google Sheets"""
    if not force and state.rows is not None and time.time() - state._rows_ts < ROWS_CACHE_TTL:
        return {"rows": state.rows, "cached": True}
    if not state.rows_lock.acquire(blocking=False):
        return {"rows": state.rows or [], "cached": True, "loading": True}
    try:
        from modules.sheets_manager import fetch_all_planner_rows
        raw_rows = fetch_all_planner_rows(SHEET_NAME) or []
        state.rows = [normalize_row(r) for r in raw_rows]
        state._rows_ts = time.time()
    except Exception as exc:
        print(f"❌ Gagal mengambil data Google Sheets: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        state.rows_lock.release()
    return {"rows": state.rows, "cached": False}

@app.post("/api/planner/generate")
def generate_ideas(background_tasks: BackgroundTasks):
    """Generate ide konten via AI (Background Task)"""
    if state._generating:
        return {"status": "processing", "message": "Proses generate sedang berjalan."}
        
    def _generate_task():
        state._generating = True
        try:
            from modules.sheets_manager import generate_content_ideas_to_sheet
            print("\n✨ Meminta AI membuat ide baru...")
            generate_content_ideas_to_sheet(count=5)
            print("✅ 5 ide baru ditambahkan ke Google Sheets.")
            state._rows_ts = 0.0   # paksa tarik ulang data agar tabel ikut terbarui
        except Exception as exc:
            print(f"❌ Gagal generate ide: {str(exc)}")
        finally:
            state._generating = False
            
    background_tasks.add_task(_generate_task)
    return {"status": "started", "message": "Generasi 5 ide konten dimulai di background."}

# ============================================================
# METRIX (Agent Data Analyst) — tab Analytics, laporan performa & export
# ============================================================
METRIX_FILE_RE = re.compile(r"^metrix_report_\d{8}_\d{6}\.json$")

def _metrix_list_files():
    if not os.path.isdir(METRIX_REPORTS_DIR):
        return []
    files = [f for f in os.listdir(METRIX_REPORTS_DIR) if METRIX_FILE_RE.match(f)]
    return sorted(files, reverse=True)  # nama file berisi timestamp -> urut terbaru dulu

def _metrix_summary(filename):
    path = os.path.join(METRIX_REPORTS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    agg = d.get("aggregate_stats", {})
    top = d.get("top_performer")
    return {
        "file": filename,
        "generated_at": d.get("generated_at"),
        "total_videos_analyzed": d.get("total_videos_analyzed", 0),
        "total_views": agg.get("total_views", 0),
        "total_likes": agg.get("total_likes", 0),
        "avg_engagement_rate": agg.get("avg_engagement_rate", 0),
        "avg_score": round(sum(r.get("score", 0) for r in d.get("detailed_metrics", [])) /
                            max(1, len(d.get("detailed_metrics", []))), 1),
        "top_topic": top.get("topic") if top else None,
    }

@app.get("/api/metrix/reports")
def metrix_reports():
    """Daftar semua laporan Metrix (terbaru dulu) + ringkasan tiap laporan, untuk dropdown riwayat tab Analytics."""
    items = [s for s in (_metrix_summary(f) for f in _metrix_list_files()) if s]
    return {"reports": items, "generating": state._metrix_generating}

@app.get("/api/metrix/reports/{filename}")
def metrix_report_detail(filename: str):
    """Isi lengkap satu laporan (detailed_metrics) — dipakai tabel & export di tab Analytics."""
    if not METRIX_FILE_RE.match(filename):
        raise HTTPException(400, "Nama file laporan tidak valid.")
    path = os.path.join(METRIX_REPORTS_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Laporan tidak ditemukan.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/metrix/bias")
def metrix_bias():
    """Bias engagement terakhir (niche/hook/keyword pemenang, mode boost EchoBee) — dipakai kartu insight Analytics."""
    return load_bias()

@app.post("/api/metrix/run")
def metrix_run(background_tasks: BackgroundTasks):
    """Jalankan Metrix manual dari tab Analytics (tombol Refresh Laporan)."""
    if MetrixDataAnalyst is None:
        raise HTTPException(503, "Modul data_analyst (Metrix) tidak termuat di server ini.")
    if state._metrix_generating:
        return {"status": "processing", "message": "Metrix sedang menyusun laporan."}

    def _run_task():
        state._metrix_generating = True
        try:
            print("\n📈 Metrix: menyusun laporan performa (dipicu manual dari tab Analytics)...")
            MetrixDataAnalyst().generate_ceo_report()
        except Exception as exc:
            print(f"❌ Metrix gagal menyusun laporan: {exc}")
        finally:
            state._metrix_generating = False

    background_tasks.add_task(_run_task)
    return {"status": "started", "message": "Metrix sedang menyusun laporan performa terbaru."}

@app.post("/api/seo/analyze")
def analyze_seo(req: SEORequest):
    """Fallback ke analisis lokal jika modul YT tidak ada / error."""
    return _analyze(req.title, req.description, req.tags, req.topic)

@app.post("/api/seo/generate")
def generate_seo(req: SEORequest):
    """Generate SEO berdasarkan niche, topik, dan hook (fallback lokal bila modul YT bermasalah)."""
    channel = state.settings.get("channel_name", DEFAULT_CHANNEL_NAME)
    meta = None
    if yt_seo is not None:
        try:
            meta = yt_seo.build_seo_metadata(req.topic, req.niche, req.hook, channel_name=channel,
                                             variant=req.variant, disclose_ai=req.disclose_ai)
        except Exception as exc:
            print(f"⚠️ build_seo_metadata gagal ({exc}) — memakai generator lokal.")
    if meta is None:
        meta = local_seo_metadata(req.topic, req.niche, req.hook, channel, req.variant, req.disclose_ai)
    meta = dict(meta)
    meta.setdefault("variant", req.variant)
    return meta

@app.get("/api/logs")
def get_logs():
    """Mengambil semua log stdout sejak hit terakhir."""
    logs = []
    while not state.log_queue.empty():
        try:
            logs.append(state.log_queue.get_nowait())
        except queue.Empty:
            break
    return {"logs": logs}

# --- Analitik Internal Backend ---
def _bump_analytics(kind, n=1):
    key = datetime.date.today().isoformat()
    day = state.history.setdefault(key, {"rendered": 0, "uploaded": 0})
    day[kind] = int(day.get(kind, 0)) + n
    for old in sorted(state.history)[:-180]:
        state.history.pop(old, None)
    try:
        save_json(HISTORY_FILE, state.history)
    except OSError:
        pass

# ============================================================
# KONTROL AUTOMATION (pengganti run_automation_loop di app_gui.py)
# main.py dijalankan di thread background; web hanya membaca status via REST.
# ============================================================
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

state.thread = None
state.countdown = 0
state.pub = {"busy": False, "progress": 0, "message": "", "error": None, "url": None,
             "partial": False, "row_id": None, "items": {}}


def _sleep(seconds):
    for remaining in range(int(seconds), 0, -1):
        if not state.is_running:
            break
        state.countdown = remaining
        time.sleep(1)
    state.countdown = 0


def _automation_loop():
    try:
        from main import main as run_single_task
    except Exception as exc:
        print(f"❌ Gagal mengimpor main.py: {exc}")
        state.is_running = False
        return

    while state.is_running:
        cfg = dict(state.settings)
        mode = UPLOAD_MODES.get(cfg.get("upload_mode"), "draft")
        interval = max(5, int(cfg.get("interval", 30)))
        retries = max(1, int(cfg.get("retries", 3)))
        platforms = [p for p in cfg.get("default_platforms", ["youtube"]) if p in PLATFORM_META] or ["youtube"]
        os.environ["LOG_LEVEL"] = str(cfg.get("log_level", "Info"))

        print(f"\n🚀 Mengecek Google Sheets (mode: {mode})...")
        hasil = False

        # Retry render per-baris ada di main.py (argumen `retries`).
        # Loop ini hanya mengulang jika terjadi error tak terduga (mis. gagal baca Google Sheets).
        for attempt in range(1, retries + 1):
            if not state.is_running:
                break
            try:
                hasil = run_single_task(mode=mode, retries=retries, platforms=platforms,
                                        should_stop=lambda: not state.is_running,
                                        channel_name=cfg.get("channel_name"))
                break
            except Exception as exc:
                print(f"❌ Execution Error (percobaan {attempt}/{retries}): {exc}")
                if str(cfg.get("log_level")).lower() == "debug":
                    print("[DEBUG] " + traceback.format_exc())
                if attempt < retries:
                    _sleep(min(5 * attempt, 20))

        state._rows_ts = 0.0
        if hasil:
            _bump_analytics("rendered")
            if isinstance(hasil, dict) and hasil.get("uploaded"):
                _bump_analytics("uploaded")
        if not state.is_running:
            break

        # Jeda loop dan tunggu perintah dari web UI
        if hasil:
            print("⏸️ Video selesai! Menunggu konfirmasi dari web UI...")
            state.waiting_for_user = True
            while state.waiting_for_user and state.is_running:
                time.sleep(1)  # menunggu tombol Lanjut / Berhenti di web
            if not state.is_running:
                break
            continue  # lanjut tanpa jeda interval

        print(f"💤 Menunggu {interval} detik sebelum pengecekan berikutnya...")
        _sleep(interval)

    print("⏹️ Automation loop berhenti.")
    state.countdown = 0
    state.waiting_for_user = False


def _start_automation():
    if state.thread and state.thread.is_alive():
        return False  # loop lama masih menyelesaikan tugas
    state.is_running = True
    state.thread = threading.Thread(target=_automation_loop, daemon=True)
    state.thread.start()
    return True


@app.post("/api/automation/start")
def automation_start():
    if state.is_running:
        return {"status": "already_running"}
    if not _start_automation():
        raise HTTPException(409, "Loop sebelumnya masih menyelesaikan tugas terakhir.")
    return {"status": "started"}


@app.post("/api/automation/stop")
def automation_stop():
    state.is_running = False
    state.waiting_for_user = False   # lepas gembok jika sedang menunggu modal konfirmasi
    print("⏹️ Automation berhenti setelah tugas yang sedang berjalan selesai...")
    return {"status": "stopping"}

@app.post("/api/automation/resume")
def automation_resume():
    state.waiting_for_user = False
    return {"status": "resumed"}


# ============================================================
# META, ANALITIK, SETTINGS
# ============================================================
@app.get("/api/meta")
def get_meta():
    return {"upload_modes": list(UPLOAD_MODES), "privacy": list(PRIVACY_CHOICES),
            "categories": list(CATEGORY_CHOICES), "default_category": DEFAULT_CATEGORY,
            "title_max": TITLE_MAX, "desc_max_bytes": DESC_MAX_BYTES, "tags_max_chars": TAGS_MAX_CHARS}


@app.get("/api/analytics")
def analytics(days: int = 14):
    out = []
    for i in range(days - 1, -1, -1):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        v = state.history.get(d, {})
        out.append({"date": d, "rendered": v.get("rendered", 0), "uploaded": v.get("uploaded", 0)})
    return {"days": out}


class SettingsIn(BaseModel):
    upload_mode: str
    interval: int = 30
    retries: int = 3
    output_folder: str = ""
    log_level: str = "Info"
    notifications: bool = True
    autostart: bool = False
    channel_name: str = ""
    groq_api_key: str = ""
    pexels_api_key: str = ""
    imagemagick_path: str = ""
    default_platforms: list[str] = ["youtube"]


@app.put("/api/settings")
def save_settings(req: SettingsIn):
    if req.interval < 5:
        raise HTTPException(400, "Interval minimal 5 detik.")
    if not 1 <= req.retries <= 10:
        raise HTTPException(400, "Percobaan ulang harus 1–10.")
    if req.upload_mode not in UPLOAD_MODES:
        raise HTTPException(400, "Mode upload tidak dikenal.")
    if req.log_level not in ("Info", "Debug"):
        raise HTTPException(400, "Log level harus Info atau Debug.")
    plats = [p for p in dict.fromkeys(req.default_platforms) if p in PLATFORM_META]
    if not plats:
        raise HTTPException(400, "Pilih minimal satu platform default.")
    out = req.output_folder.strip()
    env_values = {"GROQ_API_KEY": req.groq_api_key.strip(), "PEXELS_API_KEY": req.pexels_api_key.strip(),
                  "IMAGEMAGICK_PATH": req.imagemagick_path.strip()}
    if out:
        env_values["OUTPUT_DIR"] = out
    try:
        if not os.path.exists(ENV_FILE):
            open(ENV_FILE, "w", encoding="utf-8").close()
        for key, value in env_values.items():
            if value:  # kosong = biarkan nilai lama (web tidak menampilkan key)
                set_key(ENV_FILE, key, value)
                os.environ[key] = value
        if not out and os.environ.get("OUTPUT_DIR"):   # folder dikosongkan -> kembali ke default
            unset_key(ENV_FILE, "OUTPUT_DIR")
            os.environ.pop("OUTPUT_DIR", None)
        state.settings.update({
            "upload_mode": req.upload_mode, "interval": req.interval, "retries": req.retries,
            "output_folder": out, "log_level": req.log_level, "notifications": req.notifications,
            "autostart": req.autostart, "channel_name": req.channel_name.strip() or DEFAULT_CHANNEL_NAME,
            "default_platforms": plats})
        os.environ["LOG_LEVEL"] = req.log_level
        save_json(SETTINGS_FILE, state.settings)
    except OSError as exc:
        raise HTTPException(500, f"Tidak bisa menulis file pengaturan: {exc}")
    return state.settings


@app.post("/api/settings/reset")
def reset_settings():
    state.settings = dict(DEFAULT_SETTINGS)
    os.environ["LOG_LEVEL"] = state.settings["log_level"]
    save_json(SETTINGS_FILE, state.settings)
    return state.settings


@app.post("/api/cache/clear")
def clear_cache():
    if not os.path.isdir(TEMP_DIR):
        raise HTTPException(404, f"Folder cache belum ada: {TEMP_DIR}")
    removed = failed = 0
    for name in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed += 1
            except OSError:
                failed += 1
    return {"message": f"{removed} file cache dihapus." + (f" {failed} gagal (sedang dipakai)." if failed else "")}


# ============================================================
# AKUN, VIDEO, PUBLISH
# ============================================================
def _youtube_state():
    if os.path.exists(TOKEN_FILE):
        return "connected", "Token tersimpan (token.pickle) — siap upload."
    if os.path.exists(CLIENT_SECRET_FILE):
        return "login", "Belum login. Browser server akan terbuka saat upload pertama."
    return "missing", "client_secret.json tidak ditemukan di folder project."


def _platform_list():
    accounts = social.get_accounts() if social else {}
    out = []
    for pid, spec in PLATFORM_META.items():
        item = {"id": pid, **spec}
        if pid == "youtube":
            st, msg = _youtube_state()
            item.update(state=st, ready=st != "missing", username="", message=msg)
        else:
            a = accounts.get(pid)
            item.update(state="connected" if a else "disconnected", ready=bool(a),
                        username=a["username"] if a else "",
                        message=(f"Terhubung sebagai {a['username']}" if a
                                 else social.config_hint(pid)))
        out.append(item)
    return out


class ConnectIn(BaseModel):
    username: str


try:
    from modules.social_oauth import router as _oauth_router
    app.include_router(_oauth_router)
except Exception as _exc:
    print(f"⚠️ Route OAuth sosial tidak termuat: {_exc}")


@app.get("/api/platforms")
def platforms_list():
    return {"platforms": _platform_list()}


@app.post("/api/platforms/{pid}/connect")
def platform_connect(pid: str, req: ConnectIn):
    if social is None:
        raise HTTPException(503, "modules/social_real.py tidak termuat.")
    try:
        info = social.connect(pid, req.username)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"message": f"{PLATFORM_META[pid]['label']} terhubung sebagai {info['username']}."}


@app.post("/api/platforms/{pid}/disconnect")
def platform_disconnect(pid: str):
    if social is None:
        raise HTTPException(503, "modules/social_real.py tidak termuat.")
    try:
        social.disconnect(pid)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"message": f"{PLATFORM_META.get(pid, {}).get('label', pid)} diputus."}


@app.get("/api/publish/log/{row_id}")
def publish_log(row_id: str):
    return {"log": social.get_publish_log(row_id) if social else []}


@app.get("/api/account")
def account():
    if os.path.exists(TOKEN_FILE):
        yt = {"state": "connected", "message": "Token tersimpan (token.pickle) — siap upload."}
    elif os.path.exists(CLIENT_SECRET_FILE):
        yt = {"state": "login", "message": "Belum login. Browser server akan terbuka saat upload pertama."}
    else:
        yt = {"state": "missing", "message": "client_secret.json tidak ditemukan di folder project."}
    ok = state.rows is not None
    return {"youtube": yt, "platforms": _platform_list(), "sheet": {"ok": ok, "message": (
        f"Spreadsheet '{SHEET_NAME}' — {len(state.rows)} baris terbaca." if ok
        else f"Belum ada data dari '{SHEET_NAME}'. Klik Tes Koneksi.")}}


@app.post("/api/account/reset-token")
def reset_token():
    if not os.path.exists(TOKEN_FILE):
        raise HTTPException(404, "Tidak ada token.pickle yang tersimpan.")
    try:
        os.remove(TOKEN_FILE)
    except OSError as exc:
        raise HTTPException(500, f"Tidak bisa menghapus token.pickle: {exc}")
    return {"message": "Token YouTube dihapus. Login ulang saat upload berikutnya."}


def _row(row_id):
    return next((r for r in (state.rows or []) if str(r.get("id")) == str(row_id)), None)


@app.get("/api/video/file/{row_id}")
def video_file(row_id: str):
    row = _row(row_id)
    path = os.path.abspath(row.get("output", "")) if row else ""
    if not path or is_url(path) or not os.path.isfile(path):
        raise HTTPException(404, "File video tidak ditemukan.")
    return FileResponse(path)


class PublishIn(BaseModel):
    id: str
    title: str
    description: str = ""
    tags: list[str] = []
    privacy: str = "Public"
    category: str = DEFAULT_CATEGORY
    schedule: str = ""
    synthetic: bool = True
    notify: bool = False
    platforms: list[str] = ["youtube"]


def _publish_task(row_id, path, title, description, tags, category_id, privacy, publish_at,
                  synthetic, notify, platforms):
    items = state.pub["items"]

    def refresh_overall():
        state.pub["progress"] = int(sum(i["progress"] for i in items.values()) / max(1, len(items)))

    def make_cb(pid):
        def cb(pct):
            items[pid]["progress"] = pct
            refresh_overall()
        return cb

    for pid in platforms:
        label, it = PLATFORM_META[pid]["label"], items[pid]
        it["status"] = "running"
        state.pub["message"] = f"Uploading ke {label}…"
        try:
            if pid == "youtube":
                from modules.youtube_uploader import upload_video_to_youtube
                print(f"\n📤 Memulai upload YouTube untuk baris #{row_id}: {title}...")
                url = upload_video_to_youtube(
                    video_path=path, title=title, description=description, tags=tags,
                    category_id=category_id, privacy_status="private" if publish_at else privacy,
                    publish_at=publish_at, synthetic_media=synthetic, notify_subscribers=notify,
                    progress_callback=make_cb(pid))
            else:
                caption = social.build_caption(pid, title, description, tags)
                url = social.upload(pid, path, caption, privacy="private" if publish_at else privacy,
                                    publish_at=publish_at, progress_callback=make_cb(pid))["url"]
            it.update(status="ok", progress=100, url=url)
            print(f"✅ {label}: berhasil" + (f" → {url}" if url else ""))
        except Exception as exc:
            print(f"❌ Upload {label} gagal: {exc}")
            if str(state.settings.get("log_level")).lower() == "debug":
                print("[DEBUG] " + traceback.format_exc())
            it.update(status="error", error=str(exc))
        refresh_overall()
        if social is not None:
            try:
                social.log_publish(row_id, pid, {"ok": it["status"] == "ok", "url": it.get("url"),
                                                 "error": it.get("error"), "title": title})
            except Exception:
                pass

    oks = [p for p in platforms if items[p]["status"] == "ok"]
    fails = [p for p in platforms if items[p]["status"] == "error"]
    real_ok = [p for p in oks if not PLATFORM_META[p].get("dummy")]
    names = lambda ps: ", ".join(PLATFORM_META[p]["label"] for p in ps)

    if not oks:
        state.pub.update(busy=False, error="Semua upload gagal — " + "; ".join(
            f"{PLATFORM_META[p]['label']}: {items[p]['error']}" for p in fails), progress=0)
        return

    for _ in real_ok:
        _bump_analytics("uploaded")
    main_url = (items["youtube"].get("url") if items.get("youtube", {}).get("status") == "ok" else None) \
        or next((items[p]["url"] for p in real_ok if items[p].get("url")), None)

    msg = f"Video #{row_id} " + ("dijadwalkan di " if publish_at else "berhasil dipublish ke ") + names(oks)
    if fails:
        msg += f" — gagal: {names(fails)}"
    if not real_ok:
        msg += " (simulasi — status baris tidak diubah)"
    else:
        try:
            from modules.sheets_manager import update_row_status
            try:
                row_arg = int(str(row_id).strip())
            except (TypeError, ValueError):
                row_arg = row_id
            update_row_status(row_arg, "Done", video_path=main_url if main_url else path)
            print("✅ Status Sheets diperbarui ke Done!")
        except Exception as exc:
            print(f"⚠️ Video sudah terupload ({main_url}) tetapi update status Sheets gagal: {exc}")
            msg = f"Video tayang ({main_url}) tapi status Sheets gagal diperbarui. Ubah baris #{row_id} ke Done manual."
    state.pub.update(busy=False, error=None, url=main_url, message=msg, partial=bool(fails))
    state._rows_ts = 0.0


@app.post("/api/video/publish")
def publish_video(req: PublishIn):
    if state.pub["busy"]:
        raise HTTPException(409, "Upload lain sedang berjalan.")
    platforms = list(dict.fromkeys(req.platforms))
    if not platforms:
        raise HTTPException(400, "Pilih minimal satu platform tujuan.")
    unknown = [p for p in platforms if p not in PLATFORM_META]
    if unknown:
        raise HTTPException(400, "Platform tidak dikenal: " + ", ".join(unknown))
    by_id = {p["id"]: p for p in _platform_list()}
    not_ready = [by_id[p]["label"] for p in platforms if not by_id[p]["ready"]]
    if not_ready:
        raise HTTPException(400, "Platform belum terhubung: " + ", ".join(not_ready) + " (menu Akun).")
    if "youtube" in platforms and yt_seo is None:
        raise HTTPException(400, "modules/youtube_uploader.py tidak bisa dimuat.")
    row = _row(req.id)
    if not row or status_key(row) != "ready for review":
        raise HTTPException(400, "Hanya video berstatus 'Ready for Review' yang bisa dipublish.")
    path, title = row.get("output", ""), req.title.strip()
    if not title:
        raise HTTPException(400, "Isi judul video terlebih dahulu.")
    if not path or not os.path.exists(path):
        raise HTTPException(400, f"File MP4 tidak ditemukan di path: {path}")
    report = _analyze(title, req.description, req.tags, row.get("topic", ""))
    if report["errors"]:
        raise HTTPException(400, "Metadata belum valid: " + "; ".join(report["errors"]))
    privacy = PRIVACY_CHOICES.get(req.privacy, "public")
    publish_at = None
    if privacy == "scheduled":
        try:
            publish_at = _parse_schedule(req.schedule)
        except ValueError as exc:
            raise HTTPException(400, f"Jadwal tidak valid: {exc}")
    state.pub = {"busy": True, "progress": 0, "message": "Uploading…", "error": None, "url": None,
                 "partial": False, "row_id": str(req.id),
                 "items": {p: {"label": PLATFORM_META[p]["label"], "icon": PLATFORM_META[p]["icon"],
                               "dummy": bool(PLATFORM_META[p].get("dummy")), "status": "pending",
                               "progress": 0, "url": None, "error": None} for p in platforms}}
    threading.Thread(target=_publish_task, daemon=True, args=(
        req.id, path, title, req.description, req.tags, CATEGORY_CHOICES.get(req.category, "27"),
        privacy, publish_at, req.synthetic, req.notify, platforms)).start()
    return {"status": "started"}


# ============================================================
# FILE STATIS WEB (index.html, style.css, app.js di folder yang sama)
# ============================================================
def _static(name, route):
    app.get(route, include_in_schema=False)(lambda: FileResponse(os.path.join(BASE_DIR, "web", name)))

_static("index.html", "/")
_static("style.css", "/style.css")
_static("app.js", "/app.js")
_static("office.js", "/office.js")
_static("office.css", "/office.css")
_static("office_sim.js", "/office_sim.js")
_static("sched.js", "/sched.js")
_static("metrix.js", "/metrix.js")
app.mount("/sprites", StaticFiles(directory=os.path.join(BASE_DIR, "web", "sprites"), check_dir=False), name="sprites")


@app.get("/api/history")
def get_history():
    return {"history": state.history}


@app.get("/api/icons")
def list_icons():
    d = os.path.join(BASE_DIR, "assets", "icons")
    return {"icons": [f[:-4] for f in os.listdir(d) if f.endswith(".png")] if os.path.isdir(d) else []}


@app.post("/api/open/{which}")
def open_folder(which: str):
    folder = BASE_DIR if which == "project" else (state.settings.get("output_folder") or DEFAULT_OUTPUT_DIR)
    if not os.path.isdir(folder):
        raise HTTPException(404, f"Folder belum ada: {folder}")
    if os.name == "nt":
        os.startfile(folder)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", folder])
    return {"message": f"Membuka {folder} di komputer server."}


app.mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets"), check_dir=False), name="assets")


# Ikon Flaticon UIcons dari npm (npm i @flaticon/flaticon-uicons) -> /uicons/regular/rounded.css dst.
_UI_REL = os.path.join("node_modules", "@flaticon", "flaticon-uicons", "css")
_UI_DIR = next((p for p in (os.path.join(BASE_DIR, _UI_REL), os.path.join(BASE_DIR, "web", _UI_REL),
                            os.path.join(BASE_DIR, "remotion-app", _UI_REL)) if os.path.isdir(p)), None)
if _UI_DIR:
    app.mount("/uicons", StaticFiles(directory=_UI_DIR), name="uicons")
else:
    print("⚠️ @flaticon/flaticon-uicons belum ditemukan. Jalankan: npm i @flaticon/flaticon-uicons (di folder project).")


if __name__ == "__main__":
    print(f"🚀 Menjalankan Shorts Automation Server (v{APP_VERSION})...")
    uvicorn.run(app, host=os.getenv("SERVER_HOST", "127.0.0.1"), port=int(os.getenv("SERVER_PORT", "8000")), access_log=False)