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
import webbrowser
import traceback
import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
from dotenv import load_dotenv, set_key

# ============================================================
# PATH & KONFIGURASI DASAR
# Semua path absolut dari lokasi file ini, jadi .env, token.pickle
# dan `import main` selalu ketemu walau app dijalankan dari folder lain.
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Modul SEO/copywriting YouTube (library Google di-import lazy di dalamnya)
try:
    from modules import youtube_uploader as yt_seo
except Exception as _exc:  # GUI tetap jalan walau modul bermasalah
    yt_seo = None
    print(f"⚠️ Modul youtube_uploader tidak bisa dimuat: {_exc}")

CATEGORY_CHOICES = dict(yt_seo.CATEGORIES) if yt_seo else {"Education": "27"}
DEFAULT_CATEGORY = yt_seo.DEFAULT_CATEGORY_NAME if yt_seo else "Education"
DEFAULT_CHANNEL_NAME = yt_seo.CHANNEL_NAME if yt_seo else "MorbMyth"
TITLE_MAX = getattr(yt_seo, "TITLE_MAX", 100)
DESC_MAX_BYTES = getattr(yt_seo, "DESC_MAX_BYTES", 5000)
TAGS_MAX_CHARS = getattr(yt_seo, "TAGS_MAX_CHARS", 500)

# Label tampilan -> nilai API. "scheduled" = upload private lalu tayang otomatis sesuai jadwal.
PRIVACY_CHOICES = {
    "Public": "public",
    "Unlisted": "unlisted",
    "Private": "private",
    "Jadwalkan": "scheduled",
}

ENV_FILE = os.path.join(BASE_DIR, ".env")
SETTINGS_FILE = os.path.join(BASE_DIR, "gui_settings.json")
HISTORY_FILE = os.path.join(BASE_DIR, "gui_history.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "client_secret.json")
TEMP_DIR = os.path.join(BASE_DIR, "remotion-app", "public", "temp")
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")

load_dotenv(ENV_FILE)

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

APP_VERSION = "2.4.0 Pro"
SHEET_NAME = "Shorts Content Planner"
ROWS_CACHE_TTL = 15  # detik: cegah fetch Google Sheets berulang

# Mode upload -> argumen `mode` untuk main.main().
# PENTING: sesuaikan "auto" dengan nilai yang dikenali main.py kamu.
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
}

MONTHS_ID = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]

# ============================================================
# SKEMA WARNA (desain v2.4 Pro: sidebar gelap + aksen kuning)
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

# Status Google Sheets -> (warna teks, warna latar, tag Treeview)
STATUS_STYLE = {
    "ready":            (AMBER_DARK,   AMBER_BG,   "ready"),
    "processing":       (SKY_DARK,     SKY_BG,     "processing"),
    "ready for review": ("#111317",    YELLOW,     "review"),
    "done":             (EMERALD_DARK, EMERALD_BG, "done"),
    "failed":           (ROSE_DARK,    ROSE_BG,    "failed"),
}

FONT_UI = None
FONT_MONO = "Consolas"


def F(size=13, weight="normal", mono=False):
    return ctk.CTkFont(family=FONT_MONO if mono else FONT_UI, size=size, weight=weight)


# ============================================================
# IKON (DUMMY / PLACEHOLDER)
# Semua ikon dikumpulkan di sini supaya gampang diganti nanti.
#  - Ikon sidebar: taruh PNG di  assets/icons/<nama>.png  -> otomatis dipakai
#    menggantikan glyph di bawah. Nama file: dashboard, planner, studio,
#    account, notifications, settings, help. Ukuran ideal 40x40 px (putih/abu).
#  - Ikon lain masih glyph teks: cukup ubah nilai di dict ICON.
# ============================================================
ICON_DIR = os.path.join(BASE_DIR, "assets", "icons")
ICON = {
    # sidebar
    "dashboard": "▦", "planner": "▤", "studio": "▶", "account": "◉",
    "notifications": "◔", "settings": "✱", "help": "?",
    "brand": "▶", "search": "⌕", "collapse": "«", "expand": "»",
    # aksi
    "play": "▶", "stop": "■", "refresh": "⟳", "sparkle": "✦", "rocket": "➤",
    "save": "▣", "eye": "◎", "folder": "▭", "link": "⌁", "seo": "✦",
    # status / kartu
    "check": "✓", "cross": "✗", "clock": "◆", "bolt": "ϟ", "review": "◈",
    "up": "↗", "dot": "●", "dot_off": "○", "film": "▣", "empty": "▢",
    "bell": "◔", "youtube": "▶", "sheet": "▦", "cloud": "☁",
}
_ICON_CACHE = {}


def icon_image(name, size=20):
    """CTkImage dari assets/icons/<name>.png kalau ada, kalau tidak None (pakai glyph)."""
    key = (name, size)
    if key not in _ICON_CACHE:
        img = None
        path = os.path.join(ICON_DIR, f"{name}.png")
        if os.path.isfile(path):
            try:
                from PIL import Image
                pil = Image.open(path)
                img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(size, size))
            except Exception:
                img = None
        _ICON_CACHE[key] = img
    return _ICON_CACHE[key]


SB_EXPANDED = 268
SB_COLLAPSED = 84

NAV_LABELS = {
    "dashboard": "Dashboard", "planner": "Content Planner", "preview": "Video Studio & Upload",
    "account": "User / Akun", "notifications": "Notifications", "settings": "Settings",
    "help": "Help Centre",
}
NAV_ICON = {
    "dashboard": "dashboard", "planner": "planner", "preview": "studio", "account": "account",
    "notifications": "notifications", "settings": "settings", "help": "help",
}

STOPWORDS_ID = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "dalam", "ini", "itu", "adalah",
    "atau", "akan", "oleh", "sebuah", "satu", "para", "juga", "saat", "bisa", "tidak", "detik",
    "the", "and", "of", "with",
}


class Tooltip:
    """Tooltip ringan; teks diambil dari fungsi (kosong = tidak tampil)."""

    def __init__(self, widget, text_fn):
        self.widget, self.text_fn = widget, text_fn
        self.tip, self.job = None, None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<Button-1>", self._leave, add="+")

    def _enter(self, _e=None):
        self._cancel()
        self.job = self.widget.after(350, self._show)

    def _cancel(self):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None

    def _show(self):
        text = self.text_fn()
        if not text or self.tip is not None:
            return
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
        y = self.widget.winfo_rooty() + max(0, self.widget.winfo_height() // 2 - 14)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=text, bg="#121316", fg="#FFFFFF", padx=10, pady=5, bd=1, relief="solid",
                 font=(FONT_UI or "TkDefaultFont", 10, "bold")).pack()
        self.tip = tw

    def _leave(self, _e=None):
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


# ============================================================
# SEO: skor lokal (cadangan bila modul youtube_uploader tidak termuat)
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
    """Return (skor 0-100, 8 cek). Tiap cek = (True ok | None sebagian | False gagal, teks)."""
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
    """Fallback bila modules/youtube_uploader.py tidak termuat; bentuk sama dengan yt_seo.analyze_metadata."""
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
    """Pastikan semua kolom ada. `id` dibiarkan apa adanya karena dipakai update_row_status."""
    row = dict(raw)
    for key in ("niche", "topic", "hook", "status", "output"):
        value = row.get(key)
        row[key] = "" if value is None else str(value)
    row.setdefault("id", "-")
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


def open_path(path):
    if os.name == "nt":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])


def is_inside(ancestor, widget):
    """True jika `widget` adalah `ancestor` atau turunannya (dipakai untuk efek hover kartu)."""
    while widget is not None:
        if widget is ancestor:
            return True
        widget = getattr(widget, "master", None)
    return False


# ============================================================
# REDIRECTOR STDOUT -> QUEUE (thread-safe)
# ============================================================
class TextRedirector:
    def __init__(self, ui_queue):
        self.ui_queue = ui_queue

    def write(self, text):
        if text:
            self.ui_queue.put(("log", text))

    def flush(self):
        pass

    def isatty(self):
        return False


# ============================================================
# APLIKASI UTAMA
# ============================================================
class ShortsAutoBotApp(ctk.CTk):
    TAB_META = {
        "dashboard": ("Dashboard Control", "Pantau dan kendalikan proses automasi secara real-time"),
        "planner": ("Content Planner", "Kelola dan hasilkan ide konten baru secara otomatis"),
        "preview": ("Video Studio & Upload", "Tinjau hasil render, sesuaikan metadata, lalu upload ke YouTube"),
        "account": ("User / Akun", "Status nyata koneksi layanan eksternal yang dipakai bot"),
        "notifications": ("Notifications", "Riwayat notifikasi selama aplikasi berjalan"),
        "settings": ("Settings", "Kredensial, preferensi, dan perilaku automasi"),
        "help": ("Help Centre", "Panduan singkat, shortcut, dan pemecahan masalah"),
    }

    def __init__(self):
        super().__init__()
        self._pick_fonts()

        self.title("YouTube Shorts Automation Studio — v" + APP_VERSION)
        self.geometry("1360x860")
        self.minsize(1120, 700)
        self.configure(fg_color=SIDEBAR)

        self.settings = load_settings()
        self.history = load_json(HISTORY_FILE, {})
        self.ui_queue = queue.Queue()

        self.is_running = False
        self.automation_thread = None
        self.selected_video_data = None
        self.rows = None
        self._rows_ts = 0.0
        self._rows_loading = False
        self._review_count = None
        self._publishing = False
        self._generating = False
        self._sheet_ok = None
        self._announce_next = False
        self._toast_widget = None
        self._toast_job = None
        self._log_tag = "info"
        self._log_visible = True
        self._preview_cards = {}
        self._row_by_iid = {}
        self._niche_names = []
        self._nav_badges = {}
        self._sb_animating = False
        self._seo_job = None
        self._seo_variant = 0
        self._drafts = {}
        self._editor_loaded_id = None
        self.sidebar_collapsed = bool(self.settings.get("sidebar_collapsed", False))
        self._current_tab = "dashboard"
        self.search_text = ""
        self.notifications = []
        self.unread = 0
        self.chart_days = 12
        self._chart_cols = []
        today = datetime.date.today()
        self.cal_year, self.cal_month = today.year, today.month

        self._style_treeview()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._create_sidebar()
        self._create_main_container()
        self._set_sidebar_collapsed(self.sidebar_collapsed, animate=False, persist=False)

        self.select_tab("dashboard")
        self._apply_settings_to_ui()
        self._refresh_account_status()
        self._render_notifications()
        self._update_kpi_footers()
        self._build_calendar()

        sys.stdout = TextRedirector(self.ui_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._bind_shortcuts()
        self.after(60, self._poll_queue)
        self.after(400, lambda: self.load_rows(force=True))
        self.after(700, self._pulse)
        if self.settings.get("autostart"):
            self.after(1500, self.toggle_automation)

    # ------------------------------------------------------------
    # INFRA
    # ------------------------------------------------------------
    def _pick_fonts(self):
        global FONT_UI, FONT_MONO
        families = set(tkfont.families(self))
        FONT_UI = next((f for f in ("Plus Jakarta Sans", "Segoe UI", "SF Pro Text",
                                    "Helvetica Neue", "Ubuntu", "DejaVu Sans") if f in families), None)
        FONT_MONO = next((f for f in ("JetBrains Mono", "Consolas", "Menlo",
                                      "DejaVu Sans Mono", "Courier New") if f in families), "Courier")

    def _bind_shortcuts(self):
        def bind(seq, fn):
            self.bind_all(seq, lambda e: (fn(), "break")[1])

        for key in ("k", "K"):
            bind(f"<Control-{key}>", self._focus_search)
        for key in ("r", "R"):
            bind(f"<Control-{key}>", self.refresh_all)
        for key in ("b", "B"):
            bind(f"<Control-{key}>", self.toggle_sidebar)
        for i, tab in enumerate(("dashboard", "planner", "preview", "account"), start=1):
            bind(f"<Control-Key-{i}>", lambda t=tab: self.select_tab(t))

    def _focus_search(self):
        self.entry_search.focus_set()

    def ui(self, fn):
        """Jadwalkan fungsi di main thread (aman dipanggil dari thread lain)."""
        self.ui_queue.put(("call", fn))

    def _poll_queue(self):
        try:
            for _ in range(300):
                kind, payload = self.ui_queue.get_nowait()
                try:
                    if kind == "log":
                        self._append_log(payload)
                    else:
                        payload()
                except Exception:
                    if sys.__stderr__:
                        traceback.print_exc(file=sys.__stderr__)
        except queue.Empty:
            pass
        self.after(60, self._poll_queue)

    def _pulse(self):
        """Titik hijau di Live Log berkedip saat automasi berjalan."""
        on = getattr(self, "_pulse_on", True)
        self._pulse_on = not on
        color = EMERALD if (on or not self.is_running) else "#A7F3D0"
        try:
            self.log_dot.configure(text_color=color)
        except Exception:
            pass
        self.after(700, self._pulse)

    @staticmethod
    def _classify_log(text):
        if any(m in text for m in ("❌", "Error", "Traceback", "Exception")):
            return "err"
        if "⚠️" in text or "Warning" in text:
            return "warn"
        if any(m in text for m in ("✅", "✨", "🎉", "⏹️")):
            return "ok"
        return "info"

    def _append_log(self, text):
        """Tag warna dihitung per baris, jadi print() multi-baris tetap berwarna benar."""
        level = self.opt_log_level.get() if hasattr(self, "opt_log_level") else "Info"
        try:
            self.log_box.configure(state="normal")
            for line in text.splitlines(keepends=True):
                if line.strip():
                    self._log_tag = self._classify_log(line)
                    if level == "Error":
                        self._log_visible = self._log_tag == "err"
                    elif level == "Warning":
                        self._log_visible = self._log_tag in ("err", "warn")
                    else:
                        self._log_visible = True
                if self._log_visible:
                    self.log_box.insert("end", line, self._log_tag)
            if int(self.log_box.index("end-1c").split(".")[0]) > 1500:
                self.log_box.delete("1.0", "300.0")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def export_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"shorts-bot-log-{time.strftime('%Y%m%d-%H%M%S')}.txt",
            filetypes=[("Text", "*.txt")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_box.get("1.0", "end-1c"))
            self.toast(f"Log diekspor ke:\n{path}", "success", duration=5000)
        except OSError as exc:
            messagebox.showerror("Gagal ekspor", str(exc))

    # ------------------------------------------------------------
    # NOTIFIKASI + TOAST
    # ------------------------------------------------------------
    def _notify(self, kind, message):
        self.notifications.insert(0, {"time": time.strftime("%H:%M:%S"), "kind": kind, "msg": message})
        del self.notifications[100:]
        if self._current_tab != "notifications":
            self.unread += 1
        self._update_bell()
        if self._current_tab == "notifications":
            self._render_notifications()

    def _update_bell(self):
        if self.unread > 0:
            self.bell_dot.place(x=29, y=8)
        else:
            self.bell_dot.place_forget()
        self._nav_badges["notifications"] = self.unread
        self._render_nav_button("notifications")

    def toast(self, message, kind="info", action_text=None, action=None, duration=4500):
        self._notify(kind, message)
        if kind in ("info", "success") and not self.settings.get("notifications", True):
            return
        color = {"info": YELLOW, "success": EMERALD, "warn": "#F59E0B", "error": ROSE}.get(kind, YELLOW)

        if self._toast_job:
            self.after_cancel(self._toast_job)
        if self._toast_widget is not None:
            self._toast_widget.destroy()

        frame = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=16, border_width=1, border_color=color)
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(padx=16, pady=12)
        ctk.CTkLabel(inner, text="●", text_color=color, font=F(14)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            inner, text=message, text_color="#FFFFFF", font=F(12, "bold"),
            wraplength=340, justify="left"
        ).pack(side="left")
        if action and action_text:
            def _run():
                self._dismiss_toast()
                action()
            ctk.CTkButton(
                inner, text=action_text, command=_run, width=100, height=30,
                fg_color=YELLOW, hover_color=YELLOW_HOVER, text_color="#111317",
                font=F(11, "bold"), corner_radius=15
            ).pack(side="left", padx=(14, 0))

        frame.place(relx=1.0, rely=1.0, x=-28, y=-28, anchor="se")
        frame.tkraise()
        self._toast_widget = frame
        self._toast_job = self.after(duration, self._dismiss_toast)

    def _dismiss_toast(self):
        if self._toast_job:
            self.after_cancel(self._toast_job)
            self._toast_job = None
        if self._toast_widget is not None:
            self._toast_widget.destroy()
            self._toast_widget = None

    def _on_close(self):
        self.is_running = False
        sys.stdout = sys.__stdout__
        self.destroy()

    # ------------------------------------------------------------
    # RIWAYAT PRODUKSI (untuk grafik & kalender, data nyata lokal)
    # ------------------------------------------------------------
    def _bump(self, kind, n=1):
        key = datetime.date.today().isoformat()
        day = self.history.setdefault(key, {"rendered": 0, "uploaded": 0})
        day[kind] = int(day.get(kind, 0)) + n
        for old in sorted(self.history)[:-180]:
            self.history.pop(old, None)
        try:
            save_json(HISTORY_FILE, self.history)
        except OSError:
            pass
        self._draw_chart()
        self._build_calendar()
        self._update_kpi_footers()

    def _uploaded_today(self):
        return int(self.history.get(datetime.date.today().isoformat(), {}).get("uploaded", 0))

    # ------------------------------------------------------------
    # WIDGET HELPER
    # ------------------------------------------------------------
    def _sc(self):
        """Faktor skala DPI CustomTkinter (tk.Canvas tidak ikut diskalakan otomatis)."""
        try:
            return float(self._get_window_scaling())
        except Exception:
            return 1.0

    def _badge(self, parent, text, size=34, fg=YELLOW_SOFT, color="#111317", font=None, radius=None):
        """Lencana ikon dengan ukuran PERSIS (tidak melar jadi oval saat DPI tinggi)."""
        box = ctk.CTkFrame(parent, width=size, height=size,
                           corner_radius=size // 2 if radius is None else radius, fg_color=fg)
        box.pack_propagate(False)
        ctk.CTkLabel(box, text=text, text_color=color, font=font or F(13, "bold"),
                     fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        return box

    def _btn(self, parent, text, command, kind="primary", **kw):
        styles = {
            "primary": dict(fg_color=YELLOW, hover_color=YELLOW_HOVER, text_color="#111317", border_width=0),
            "dark":    dict(fg_color="#141518", hover_color="#2A2D33", text_color="#FFFFFF", border_width=0),
            "danger":  dict(fg_color=ROSE, hover_color="#C93D42", text_color="#FFFFFF", border_width=0),
            "ghost":   dict(fg_color="transparent", hover_color=GRAY_100, text_color=TEXT_MUTED,
                            border_width=1, border_color=BORDER),
        }
        cfg = dict(font=F(13, "bold"), height=38, corner_radius=12)
        cfg.update(styles[kind])
        cfg.update(kw)
        return ctk.CTkButton(parent, text=text, command=command, **cfg)

    def _entry(self, parent, placeholder="", **kw):
        cfg = dict(
            placeholder_text=placeholder, fg_color="#FFFFFF", text_color=TEXT,
            placeholder_text_color=TEXT_FAINT, border_color=BORDER, border_width=1,
            corner_radius=10, height=38, font=F(13)
        )
        cfg.update(kw)
        return ctk.CTkEntry(parent, **cfg)

    def _option(self, parent, values, **kw):
        cfg = dict(
            values=values, fg_color="#F9FAFB", button_color=YELLOW, button_hover_color=YELLOW_HOVER,
            text_color=TEXT, dropdown_fg_color="#FFFFFF", dropdown_hover_color=YELLOW_SOFT,
            dropdown_text_color=TEXT, corner_radius=10, height=36, font=F(12, "bold"),
            dropdown_font=F(12)
        )
        cfg.update(kw)
        return ctk.CTkOptionMenu(parent, **cfg)

    def _label(self, parent, text, size=13, weight="normal", color=TEXT, **kw):
        return ctk.CTkLabel(parent, text=text, font=F(size, weight), text_color=color, **kw)

    def _field_label(self, parent, text, top=14):
        self._label(parent, text, 12, "bold", TEXT_MUTED).pack(anchor="w", pady=(top, 6))

    def _pill(self, parent, text, key=None, fg=None, bg=None):
        if key is not None:
            fg, bg, _ = status_style(key)
        return ctk.CTkLabel(
            parent, text=f"  {text}  ", font=F(11, "bold"), text_color=fg,
            fg_color=bg, corner_radius=11, height=24
        )

    def _card(self, parent, **kwargs):
        defaults = dict(fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER)
        defaults.update(kwargs)
        return ctk.CTkFrame(parent, **defaults)

    def _scroll(self, parent, **kw):
        return ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color="#D1D5DB",
            scrollbar_button_hover_color="#9CA3AF", **kw
        )

    def _empty_state(self, parent, icon, title, subtitle):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(pady=40)
        ctk.CTkLabel(box, text=icon, font=F(34), text_color=GRAY_200).pack()
        self._label(box, title, 13, "bold", TEXT_MUTED).pack(pady=(8, 2))
        self._label(box, subtitle, 11, "normal", TEXT_FAINT, justify="center").pack()

    def _bind_click(self, widget, callback):
        """Pasang klik ke widget DAN semua anaknya (label di dalam kartu ikut responsif)."""
        try:
            widget.bind("<Button-1>", lambda e: callback(), add="+")
            widget.configure(cursor="hand2")
        except Exception:
            pass
        for child in widget.winfo_children():
            self._bind_click(child, callback)

    def _bind_hover(self, widget, on_enter, on_leave):
        def enter(_e):
            on_enter()

        def leave(_e):
            x, y = widget.winfo_pointerxy()
            if not is_inside(widget, widget.winfo_containing(x, y)):
                on_leave()

        def attach(w):
            try:
                w.bind("<Enter>", enter, add="+")
                w.bind("<Leave>", leave, add="+")
            except Exception:
                pass
            for c in w.winfo_children():
                attach(c)
        attach(widget)

    # ------------------------------------------------------------
    # STYLE TREEVIEW
    # ------------------------------------------------------------
    def _style_treeview(self):
        base = FONT_UI or "TkDefaultFont"
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Glass.Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
            rowheight=int(42 * self._sc()), borderwidth=0, font=(base, 10),
        )
        style.configure(
            "Glass.Treeview.Heading", background="#F9FAFB", foreground=TEXT_MUTED,
            borderwidth=0, relief="flat", font=(base, 10, "bold"), padding=(10, 10),
        )
        style.map(
            "Glass.Treeview",
            background=[("selected", YELLOW_SOFT)],
            foreground=[("selected", TEXT)],
        )
        style.map("Glass.Treeview.Heading", background=[("active", GRAY_100)])
        style.layout("Glass.Treeview", [("Glass.Treeview.treearea", {"sticky": "nswe"})])

    # ------------------------------------------------------------
    # SIDEBAR
    # ------------------------------------------------------------
    def _create_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, width=SB_EXPANDED, border_width=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.pack_propagate(False)
        self.sidebar_frame = sb

        # Brand
        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.pack(fill="x", pady=(26, 18))
        self.brand_logo = self._badge(brand, ICON["brand"], 38, YELLOW, "#111317", F(16, "bold"), radius=12)
        self.brand_logo.pack(side="left", padx=(20, 12))
        self.brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        self.brand_text.pack(side="left")
        self._label(self.brand_text, "SHORTS BOT", 15, "bold", "#FFFFFF").pack(anchor="w")
        self._label(self.brand_text, "STUDIO & PUBLISHER", 9, "bold", "#C9A21E").pack(anchor="w")

        # Search (mode lebar = kolom input, mode sempit = tombol ikon)
        self.search_wrap = ctk.CTkFrame(sb, fg_color="transparent")
        self.search_wrap.pack(fill="x", padx=18, pady=(0, 14))
        self.entry_search = ctk.CTkEntry(
            self.search_wrap, placeholder_text=f"{ICON['search']}  Cari konten…   Ctrl+K", height=38,
            fg_color="#1A1C20", border_color="#1A1C20", border_width=1, corner_radius=19,
            text_color="#E5E7EB", placeholder_text_color="#6B7280", font=F(12)
        )
        self.entry_search.pack(fill="x")
        self.entry_search.bind("<KeyRelease>", self._on_search_change)
        self.entry_search.bind("<Return>", lambda e: self.select_tab("planner"))
        self.entry_search.bind("<Escape>", lambda e: self._clear_search())
        self.btn_search_icon = ctk.CTkButton(
            self.search_wrap, text=ICON["search"], width=44, height=44, corner_radius=22, font=F(15),
            fg_color="#1A1C20", hover_color=SIDEBAR_HOVER, text_color=SIDEBAR_TEXT,
            command=self._expand_and_search
        )

        # Heading menu + tombol collapse
        self.menu_head = ctk.CTkFrame(sb, fg_color="transparent")
        self.menu_head.pack(fill="x", padx=16, pady=(0, 4))
        self.btn_collapse = ctk.CTkButton(
            self.menu_head, text=ICON["collapse"], width=34, height=28, corner_radius=14,
            font=F(13, "bold"), fg_color="transparent", hover_color=SIDEBAR_HOVER,
            text_color=SIDEBAR_TEXT, command=self.toggle_sidebar
        )
        self.btn_collapse.pack(side="right")
        self.lbl_menu = self._label(self.menu_head, "MAIN MENU", 10, "bold", SIDEBAR_FAINT)
        self.lbl_menu.pack(side="left", padx=(12, 0))

        self.nav_buttons = {}

        def add_nav(key):
            btn = ctk.CTkButton(
                sb, text="", command=lambda k=key: self.select_tab(k),
                font=F(13, "bold"), fg_color="transparent", text_color=SIDEBAR_TEXT,
                hover_color=SIDEBAR_HOVER, anchor="w", height=42, corner_radius=21
            )
            btn.pack(fill="x", padx=16, pady=2)
            self.nav_buttons[key] = btn
            Tooltip(btn, lambda k=key: self._nav_tooltip(k))

        for key in ("dashboard", "planner", "preview", "account"):
            add_nav(key)

        self.lbl_settings_section = self._label(sb, "SETTINGS", 10, "bold", SIDEBAR_FAINT, anchor="w", height=20)
        self.lbl_settings_section.pack(fill="x", padx=28, pady=(10, 4))
        for key in ("notifications", "settings", "help"):
            add_nav(key)

        # Kartu status di bawah
        card = ctk.CTkFrame(sb, fg_color=SIDEBAR_CARD, corner_radius=18, border_width=1, border_color=SIDEBAR_LINE)
        card.pack(side="bottom", fill="x", padx=16, pady=20)
        self.status_inner = ctk.CTkFrame(card, fg_color="transparent")
        self.status_inner.pack(fill="x", padx=16, pady=14)

        self.status_full = ctk.CTkFrame(self.status_inner, fg_color="transparent")
        self.status_full.pack(fill="x")
        top = ctk.CTkFrame(self.status_full, fg_color="transparent")
        top.pack(fill="x")
        self._label(top, "SYSTEM STATUS", 9, "bold", SIDEBAR_FAINT).pack(side="left")
        self.status_light = ctk.CTkLabel(top, text=ICON["dot"], font=F(12), text_color=EMERALD)
        self.status_light.pack(side="right")

        self.status_dot = self._label(self.status_full, "Idle", 17, "bold", "#FFFFFF")
        self.status_dot.pack(anchor="w", pady=(6, 0))
        self.lbl_status_sub = self._label(self.status_full, "Automator siap dijalankan", 11, "normal", "#9CA3AF")
        self.lbl_status_sub.pack(anchor="w", pady=(1, 0))
        self.lbl_countdown = self._label(self.status_full, "", 11, "normal", "#FDE68A")
        self.lbl_countdown.pack(anchor="w")
        ctk.CTkFrame(self.status_full, fg_color=SIDEBAR_LINE, height=1).pack(fill="x", pady=(10, 10))

        self.status_bottom = ctk.CTkFrame(self.status_inner, fg_color="transparent")
        self.status_bottom.pack(fill="x")
        self.lbl_sync = ctk.CTkLabel(
            self.status_bottom, text=" Belum sinkron ", font=F(10, "bold"), text_color="#9CA3AF",
            fg_color="#22252B", corner_radius=10, height=22
        )
        self.lbl_sync.pack(side="left")
        self.btn_mini_play = ctk.CTkButton(
            self.status_bottom, text=ICON["play"], width=30, height=30, corner_radius=15,
            font=F(12, "bold"), fg_color=YELLOW, hover_color=YELLOW_HOVER, text_color="#111317",
            command=self.toggle_automation
        )
        self.btn_mini_play.pack(side="right")

        Tooltip(self.btn_collapse, lambda: "Perluas sidebar (Ctrl+B)" if self.sidebar_collapsed else "Kecilkan sidebar (Ctrl+B)")
        Tooltip(self.btn_search_icon, lambda: "Cari konten (Ctrl+K)")
        Tooltip(self.btn_mini_play, lambda: "Start / Stop Automation" if self.sidebar_collapsed else "")

    # --- sidebar collapse / expand ---
    def _nav_tooltip(self, key):
        if not self.sidebar_collapsed:
            return ""
        badge = self._nav_badges.get(key, 0)
        return NAV_LABELS[key] + (f" ({badge})" if badge else "")

    def _render_nav_button(self, key):
        name = NAV_ICON[key]
        glyph, label = ICON[name], NAV_LABELS[key]
        badge = self._nav_badges.get(key, 0)
        img = icon_image(name, 20)
        btn = self.nav_buttons[key]
        if self.sidebar_collapsed:
            btn.configure(text="" if img else glyph, image=img, anchor="center", compound="left")
        else:
            suffix = f"  ({badge})" if badge else ""
            btn.configure(text=(f"  {label}" if img else f"{glyph}   {label}") + suffix,
                          image=img, anchor="w", compound="left")

    def _apply_sidebar_content(self, collapsed):
        # Brand
        if collapsed:
            self.brand_text.pack_forget()
            self.brand_logo.pack_configure(padx=(23, 0))
        else:
            self.brand_logo.pack_configure(padx=(20, 12))
            self.brand_text.pack(side="left")
        # Search
        if collapsed:
            self.entry_search.pack_forget()
            self.btn_search_icon.pack()
        else:
            self.btn_search_icon.pack_forget()
            self.entry_search.pack(fill="x")
        # Heading + tombol collapse
        self.btn_collapse.configure(text=ICON["expand"] if collapsed else ICON["collapse"])
        if collapsed:
            self.lbl_menu.pack_forget()
            self.btn_collapse.pack_configure(side="top")
        else:
            self.btn_collapse.pack_configure(side="right")
            self.lbl_menu.pack(side="left", padx=(12, 0))
        self.lbl_settings_section.configure(text="" if collapsed else "SETTINGS", height=8 if collapsed else 20)
        # Menu
        for key in self.nav_buttons:
            self._render_nav_button(key)
        # Kartu status
        if collapsed:
            self.status_full.pack_forget()
            self.lbl_sync.pack_forget()
            self.btn_mini_play.pack_configure(side="top")
            self.status_inner.pack_configure(padx=6)
        else:
            self.status_inner.pack_configure(padx=16)
            self.status_full.pack(fill="x", before=self.status_bottom)
            self.lbl_sync.pack(side="left")
            self.btn_mini_play.pack_configure(side="right")

    def toggle_sidebar(self):
        if not self._sb_animating:
            self._set_sidebar_collapsed(not self.sidebar_collapsed)

    def _expand_and_search(self):
        if self.sidebar_collapsed:
            self.toggle_sidebar()
        self.after(320, self._focus_search)

    def _set_sidebar_collapsed(self, collapsed, animate=True, persist=True):
        self.sidebar_collapsed = collapsed
        if persist:
            self.settings["sidebar_collapsed"] = collapsed
            try:
                save_json(SETTINGS_FILE, self.settings)
            except OSError:
                pass
        target = SB_COLLAPSED if collapsed else SB_EXPANDED
        if not animate:
            self._apply_sidebar_content(collapsed)
            self.sidebar_frame.configure(width=target)
            return

        start = SB_EXPANDED if collapsed else SB_COLLAPSED
        if collapsed:
            self._apply_sidebar_content(True)  # sembunyikan teks dulu, lalu menyempit
        self._sb_animating = True
        steps = 8

        def step(i):
            ease = 1 - (1 - i / steps) ** 3
            self.sidebar_frame.configure(width=int(start + (target - start) * ease))
            if i < steps:
                self.after(14, lambda: step(i + 1))
            else:
                self._sb_animating = False
                if not collapsed:
                    self._apply_sidebar_content(False)  # tampilkan teks setelah melebar
        step(1)

    def _on_search_change(self, _event=None):
        text = self.entry_search.get()
        if text == self.search_text:
            return
        self.search_text = text
        self._apply_filters()

    def _clear_search(self):
        self.entry_search.delete(0, "end")
        self.search_text = ""
        self._apply_filters()

    def select_tab(self, name):
        self._current_tab = name
        for btn in self.nav_buttons.values():
            btn.configure(fg_color="transparent", text_color=SIDEBAR_TEXT, hover_color=SIDEBAR_HOVER)
        for frame in self.tab_frames.values():
            frame.pack_forget()

        if name in self.nav_buttons:
            self.nav_buttons[name].configure(fg_color=YELLOW, text_color="#111317", hover_color=YELLOW)
        self.tab_frames[name].pack(fill="both", expand=True, padx=30, pady=(0, 22))

        title, sub = self.TAB_META[name]
        self.lbl_page_title.configure(text=title)
        self.lbl_page_sub.configure(text=sub)

        if name == "notifications":
            self.unread = 0
            self._update_bell()
            self._render_notifications()
        if name in ("dashboard", "planner", "preview"):
            self.load_rows()
        if name == "dashboard":
            self.after(80, self._draw_chart)

    # ------------------------------------------------------------
    # MAIN CONTAINER + TOP BAR
    # ------------------------------------------------------------
    def _create_main_container(self):
        self.main_container = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=30)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self._create_topbar()

        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        self.frame_dashboard = self._scroll(self.content_area)
        self.frame_planner = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_preview = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_account = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_notifications = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_settings = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.frame_help = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.tab_frames = {
            "dashboard": self.frame_dashboard, "planner": self.frame_planner,
            "preview": self.frame_preview, "account": self.frame_account,
            "notifications": self.frame_notifications, "settings": self.frame_settings,
            "help": self.frame_help,
        }

        self._build_dashboard_tab()
        self._build_planner_tab()
        self._build_preview_tab()
        self._build_account_tab()
        self._build_notifications_tab()
        self._build_settings_tab()
        self._build_help_tab()

    def _create_topbar(self):
        bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=36, pady=(26, 16))

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", anchor="w")
        self.lbl_page_title = self._label(left, "Dashboard Control", 27, "bold", "#111317")
        self.lbl_page_title.pack(anchor="w")
        self.lbl_page_sub = self._label(left, "", 13, "normal", TEXT_MUTED)
        self.lbl_page_sub.pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", anchor="e")

        # Profil / koneksi YouTube (data nyata dari token.pickle)
        profile = ctk.CTkFrame(right, fg_color="#FFFFFF", border_width=1, border_color=BORDER, corner_radius=24)
        profile.pack(side="right", padx=(12, 0))
        pin = ctk.CTkFrame(profile, fg_color="transparent")
        pin.pack(padx=(6, 16), pady=5)
        self._badge(pin, ICON["youtube"], 36, "#1E293B", YELLOW, F(12, "bold")).pack(side="left", padx=(0, 10))
        pcol = ctk.CTkFrame(pin, fg_color="transparent")
        pcol.pack(side="left")
        self._label(pcol, "YouTube Channel", 12, "bold", "#111317").pack(anchor="w")
        self.lbl_profile_status = self._label(pcol, "Memeriksa…", 10, "normal", TEXT_FAINT)
        self.lbl_profile_status.pack(anchor="w")
        self._bind_click(profile, lambda: self.select_tab("account"))

        # Bell
        self.btn_bell = ctk.CTkButton(
            right, text=ICON["bell"], width=46, height=46, corner_radius=23, font=F(15),
            fg_color="#FFFFFF", hover_color=GRAY_100, text_color=TEXT_MUTED,
            border_width=1, border_color=BORDER, command=lambda: self.select_tab("notifications")
        )
        self.btn_bell.pack(side="right", padx=(12, 0))
        self.bell_dot = ctk.CTkFrame(self.btn_bell, width=11, height=11, corner_radius=6, fg_color=YELLOW,
                                     border_width=2, border_color="#FFFFFF")

        # Start / Stop
        self.btn_start_auto = self._btn(
            right, f"{ICON['play']}  Start Automation", self.toggle_automation,
            height=44, width=200, corner_radius=22, font=F(13, "bold")
        )
        self.btn_start_auto.pack(side="right")

    # ------------------------------------------------------------
    # DATA LAYER: satu fetch -> semua tampilan
    # ------------------------------------------------------------
    def load_rows(self, force=False, announce=False):
        if announce:
            self._announce_next = True
        if self._rows_loading:
            return
        if not force and self.rows is not None and time.time() - self._rows_ts < ROWS_CACHE_TTL:
            return

        self._rows_loading = True
        self.lbl_sync.configure(text=f" {ICON['refresh']} Sinkron… ", text_color="#FDE68A")

        def task():
            rows, error = None, None
            try:
                from modules.sheets_manager import fetch_all_planner_rows
                rows = [normalize_row(r) for r in (fetch_all_planner_rows(SHEET_NAME) or [])]
            except Exception as exc:
                error = str(exc)
            self.ui(lambda: self._rows_done(rows, error))

        threading.Thread(target=task, daemon=True).start()

    def _rows_done(self, rows, error):
        self._rows_loading = False
        if error is not None:
            self._sheet_ok = False
            self.lbl_sync.configure(text=f" {ICON['cross']} Gagal sinkron ", text_color="#FB7185")
            print(f"⚠️ Gagal mengambil data Google Sheets: {error}")
            self.toast(f"Gagal mengambil data Google Sheets: {error}", "error", duration=7000)
            self._refresh_account_status()
            if self.rows is None:
                self.rows = []
                self._on_rows([])
            self._announce_next = False
            return

        self.rows = rows
        self._rows_ts = time.time()
        self._sheet_ok = True
        self.lbl_sync.configure(text=f" {ICON['check']} {time.strftime('%H:%M:%S')} ", text_color="#34D399")

        review_now = sum(1 for r in rows if status_key(r) == "ready for review")
        prev = self._review_count
        self._review_count = review_now
        gained = review_now - prev if prev is not None and review_now > prev else 0
        if gained:
            self._bump("rendered", gained)

        self._on_rows(rows)
        self._refresh_account_status()

        if self._announce_next:
            self._announce_next = False
            self.toast(f"Terhubung ke Google Sheets — {len(rows)} baris dimuat.", "success")
        elif gained:
            self.toast(
                f"{gained} video baru siap ditinjau!", "success",
                action_text="Buka Studio", action=lambda: self.select_tab("preview")
            )

    def _on_rows(self, rows):
        done = sum(1 for r in rows if status_key(r) == "done")
        queued = sum(1 for r in rows if status_key(r) == "ready")
        review = sum(1 for r in rows if status_key(r) == "ready for review")
        self._niche_names = sorted({r["niche"].strip() for r in rows
                                    if r["niche"].strip() and r["niche"] != "-"})

        self.kpi_done["value"].configure(text=str(done))
        self.kpi_ready["value"].configure(text=str(queued))
        self.kpi_niche["value"].configure(text=str(len(self._niche_names)))
        self.kpi_review["value"].configure(text=str(review))
        self._update_kpi_footers()

        self._nav_badges["preview"] = review
        self._render_nav_button("preview")

        self._update_planner_table(rows)
        self._render_dashboard_video_list(rows)
        self._render_queue_list(rows)
        self._render_preview_list(rows)

    def refresh_all(self):
        self.load_rows(force=True)

    # ------------------------------------------------------------
    # TAB 1: DASHBOARD
    # ------------------------------------------------------------
    def _build_dashboard_tab(self):
        root = self.frame_dashboard

        # --- KPI ---
        stats = ctk.CTkFrame(root, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 16))
        stats.columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        self.kpi_done = self._kpi_card(stats, 0, "Completed Videos", "shorts", ICON["check"], "#ECFDF5", EMERALD_DARK)
        self.kpi_ready = self._kpi_card(stats, 1, "Pending in Queue", "render queue", ICON["clock"], "#FFFBEB", AMBER_DARK)
        self.kpi_niche = self._kpi_card(stats, 2, "Active Niches", "niche", ICON["bolt"], "#F0F9FF", SKY_DARK)
        self.kpi_review = self._kpi_card(stats, 3, "Menunggu Review", "video", ICON["review"], "#FFF1F2", ROSE_DARK)
        self._bind_click(self.kpi_review["card"], lambda: self.select_tab("preview"))

        # --- Chart + Kalender ---
        mid = ctk.CTkFrame(root, fg_color="transparent")
        mid.pack(fill="x", pady=(0, 16))
        mid.columnconfigure(0, weight=2, uniform="mid")
        mid.columnconfigure(1, weight=1, uniform="mid")

        chart_card = self._card(mid)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ch = ctk.CTkFrame(chart_card, fg_color="transparent")
        ch.pack(fill="x", padx=22, pady=(18, 0))
        chl = ctk.CTkFrame(ch, fg_color="transparent")
        chl.pack(side="left")
        self._label(chl, "Upload & Production Overview", 16, "bold").pack(anchor="w")
        self._label(chl, "Video dirender vs diupload per hari (dicatat aplikasi ini)", 11, "normal",
                    TEXT_FAINT).pack(anchor="w")
        chr_ = ctk.CTkFrame(ch, fg_color="transparent")
        chr_.pack(side="right")
        self.opt_chart_range = self._option(
            chr_, ["7 Hari", "12 Hari", "30 Hari"], width=110, command=self._on_chart_range
        )
        self.opt_chart_range.set("12 Hari")
        self.opt_chart_range.pack(side="right")
        legend = ctk.CTkFrame(chart_card, fg_color="transparent")
        legend.pack(fill="x", padx=22, pady=(10, 0))
        for color, name in ((YELLOW, "Uploaded"), ("#D1D5DB", "Rendered")):
            ctk.CTkLabel(legend, text=ICON["dot"], text_color=color, font=F(12)).pack(side="left")
            self._label(legend, name, 11, "normal", TEXT_MUTED).pack(side="left", padx=(3, 14))

        self.chart_canvas = tk.Canvas(chart_card, height=int(230 * self._sc()), bg=CARD,
                                      highlightthickness=0, bd=0)
        self.chart_canvas.pack(fill="both", expand=True, padx=16, pady=(6, 16))
        self.chart_canvas.bind("<Configure>", lambda e: self._draw_chart())
        self.chart_canvas.bind("<Motion>", self._chart_hover)
        self.chart_canvas.bind("<Leave>", lambda e: self.chart_canvas.delete("tip"))

        cal_card = self._card(mid)
        cal_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        cin = ctk.CTkFrame(cal_card, fg_color="transparent")
        cin.pack(fill="both", expand=True, padx=20, pady=18)

        self._label(cin, "Batch Calendar", 15, "bold").pack(anchor="w")
        nav = ctk.CTkFrame(cin, fg_color="transparent")
        nav.pack(fill="x", pady=(8, 0))
        self._btn(nav, "‹", lambda: self._shift_month(-1), "ghost", width=34, height=30, corner_radius=15,
                  border_width=0, font=F(15, "bold")).pack(side="left")
        self._btn(nav, "›", lambda: self._shift_month(1), "ghost", width=34, height=30, corner_radius=15,
                  border_width=0, font=F(15, "bold")).pack(side="right")
        self.lbl_cal_title = self._label(nav, "", 13, "bold", "#374151")
        self.lbl_cal_title.pack(expand=True)

        # Kalender digambar di canvas: angka tidak akan terpotong di DPI tinggi (seperti grafik)
        self.cal_canvas = tk.Canvas(cin, height=int(7 * 32 * self._sc()) + 4, bg=CARD,
                                    highlightthickness=0, bd=0)
        self.cal_canvas.pack(fill="x", pady=(8, 0))
        self.cal_canvas.bind("<Configure>", lambda e: self._build_calendar())
        leg = ctk.CTkFrame(cin, fg_color="transparent")
        leg.pack(anchor="w", pady=(6, 0))
        for color, text in ((YELLOW, "Hari ini"), ("#FCD34D", "Ada upload")):
            ctk.CTkLabel(leg, text=ICON["dot"], text_color=color, font=F(11)).pack(side="left")
            self._label(leg, text, 10, "normal", TEXT_FAINT).pack(side="left", padx=(3, 12))

        ctk.CTkFrame(cin, fg_color=GRAY_100, height=1).pack(fill="x", pady=(10, 10))
        qh = ctk.CTkFrame(cin, fg_color="transparent")
        qh.pack(fill="x")
        self._label(qh, "ANTRIAN BERIKUTNYA", 10, "bold", TEXT_FAINT).pack(side="left")
        self.lbl_queue_count = self._label(qh, "0 Pending", 11, "bold", YELLOW_HOVER)
        self.lbl_queue_count.pack(side="right")
        self.queue_box = ctk.CTkFrame(cin, fg_color="transparent")
        self.queue_box.pack(fill="x", pady=(8, 0))

        # --- Video List + Live Log ---
        low = ctk.CTkFrame(root, fg_color="transparent")
        low.pack(fill="x")
        low.columnconfigure(0, weight=7, uniform="low")
        low.columnconfigure(1, weight=5, uniform="low")

        vcard = self._card(low)
        vcard.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        vin = ctk.CTkFrame(vcard, fg_color="transparent")
        vin.pack(fill="both", expand=True, padx=22, pady=18)

        vh = ctk.CTkFrame(vin, fg_color="transparent")
        vh.pack(fill="x")
        vt = ctk.CTkFrame(vh, fg_color="transparent")
        vt.pack(side="left")
        self._label(vt, "Video List", 16, "bold").pack(anchor="w")
        self._label(vt, "Klik video untuk membuka di Video Studio", 11, "normal", TEXT_FAINT).pack(anchor="w")
        self._btn(vh, ICON["refresh"], self.refresh_all, "ghost", width=38, height=38, corner_radius=12,
                  font=F(15)).pack(side="right")
        ctk.CTkFrame(vin, fg_color=GRAY_100, height=1).pack(fill="x", pady=(12, 8))

        self.dashboard_video_box = ctk.CTkFrame(vin, fg_color="transparent")
        self.dashboard_video_box.pack(fill="x")

        vfoot = ctk.CTkFrame(vin, fg_color="transparent")
        vfoot.pack(fill="x", pady=(12, 0))
        self.lbl_video_foot = self._label(vfoot, "", 11, "normal", TEXT_MUTED)
        self.lbl_video_foot.pack(side="left")
        link = self._label(vfoot, "Buka Seluruh Queue  ›", 12, "bold", "#1F2937")
        link.pack(side="right")
        self._bind_click(link, lambda: self.select_tab("planner"))

        lcard = self._card(low)
        lcard.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        lin = ctk.CTkFrame(lcard, fg_color="transparent")
        lin.pack(fill="both", expand=True, padx=22, pady=18)

        lh = ctk.CTkFrame(lin, fg_color="transparent")
        lh.pack(fill="x")
        self.log_dot = ctk.CTkLabel(lh, text="●", text_color=EMERALD, font=F(12))
        self.log_dot.pack(side="left", padx=(0, 6))
        self._label(lh, "Live Log System", 16, "bold").pack(side="left")
        ctk.CTkLabel(
            lh, text=" STDOUT ", font=F(10, "bold", mono=True), text_color=TEXT_FAINT,
            fg_color=GRAY_100, corner_radius=8, height=22
        ).pack(side="right")
        ctk.CTkFrame(lin, fg_color=GRAY_100, height=1).pack(fill="x", pady=(12, 12))

        self.log_box = ctk.CTkTextbox(
            lin, fg_color=TERMINAL_BG, text_color=LOG_COLORS["info"],
            font=F(11, mono=True), wrap="word", corner_radius=14, border_width=1,
            border_color="#1F2937", height=250, scrollbar_button_color="#2D3139",
            scrollbar_button_hover_color="#3F4450"
        )
        self.log_box.pack(fill="both", expand=True)
        for tag, color in LOG_COLORS.items():
            self.log_box.tag_config(tag, foreground=color)
        self.log_box.insert("end", "● [INIT] System ready. Klik 'Start Automation' untuk memulai.\n", "ok")
        self.log_box.configure(state="disabled")

        lfoot = ctk.CTkFrame(lin, fg_color="transparent")
        lfoot.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(lfoot, text="●", text_color=EMERALD, font=F(9)).pack(side="left")
        self._label(lfoot, " Buffer streaming aktif", 11, "normal", TEXT_FAINT).pack(side="left")
        for text, cmd in (("Clear Console", self.clear_log), ("Export Log (.txt)", self.export_log)):
            ctk.CTkButton(
                lfoot, text=text, command=cmd, width=10, height=22, fg_color="transparent",
                hover_color=GRAY_100, text_color=TEXT_MUTED, font=F(11, "bold"), corner_radius=8
            ).pack(side="right", padx=(2, 0))

    def _kpi_card(self, parent, col, title, unit, icon, icon_bg, icon_fg):
        card = self._card(parent, corner_radius=18)
        card.grid(row=0, column=col, padx=6, sticky="nsew")
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 0))
        self._label(top, title, 12, "bold", TEXT_MUTED).pack(side="left")
        self._badge(top, icon, 36, icon_bg, icon_fg, F(13, "bold")).pack(side="right")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(6, 0))
        value = self._label(row, "–", 32, "bold", "#111317")
        value.pack(side="left")
        self._label(row, unit, 11, "normal", TEXT_FAINT).pack(side="left", padx=(8, 0), pady=(10, 0))
        footer = self._label(card, "", 11, "bold", TEXT_MUTED, anchor="w", justify="left")
        footer.pack(anchor="w", padx=18, pady=(4, 16))
        return {"card": card, "value": value, "footer": footer}

    def _update_kpi_footers(self):
        if not hasattr(self, "kpi_review"):
            return
        n = self._uploaded_today()
        if n:
            self.kpi_done["footer"].configure(text=f"{ICON['up']} +{n} diupload hari ini", text_color=EMERALD_DARK)
        else:
            self.kpi_done["footer"].configure(text="Belum ada upload hari ini", text_color=TEXT_FAINT)

        if self.is_running:
            self.kpi_ready["footer"].configure(text="● Automasi berjalan", text_color=EMERALD_DARK)
        else:
            self.kpi_ready["footer"].configure(text="○ Automasi berhenti", text_color=TEXT_FAINT)

        names = self._niche_names
        self.kpi_niche["footer"].configure(
            text=shorten(" & ".join(names), 30) if names else "Belum ada data",
            text_color=TEXT_MUTED
        )
        review = self._review_count or 0
        self.kpi_review["footer"].configure(
            text="Klik untuk buka Video Studio  ›" if review else "Tidak ada yang menunggu",
            text_color=ROSE_DARK if review else TEXT_FAINT
        )

    # --- Chart ---
    def _on_chart_range(self, value):
        self.chart_days = int(value.split()[0])
        self._draw_chart()

    def _draw_chart(self):
        if not hasattr(self, "chart_canvas"):
            return
        c = self.chart_canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 80 or h < 80:
            return

        today = datetime.date.today()
        n = self.chart_days
        dates = [today - datetime.timedelta(days=i) for i in range(n - 1, -1, -1)]
        vals = []
        for d in dates:
            info = self.history.get(d.isoformat(), {})
            vals.append((int(info.get("rendered", 0)), int(info.get("uploaded", 0))))
        peak = max([max(r, u) for r, u in vals] + [4])

        sc = self._sc()
        fpx = lambda n: -int(round(n * sc))  # font piksel, ikut skala DPI
        left, right, top, bottom = int(34 * sc), int(8 * sc), int(44 * sc), int(28 * sc)
        plot_h = h - top - bottom
        base_y = h - bottom
        slot = (w - left - right) / n
        bar_w = max(4 * sc, min(14 * sc, slot * 0.30))
        font = FONT_UI or "TkDefaultFont"

        for frac in (0, 0.5, 1):
            y = base_y - plot_h * frac
            c.create_line(left, y, w - right, y, fill=GRAY_100, dash=(3, 3))
            c.create_text(left - 8 * sc, y, text=str(int(round(peak * frac))), anchor="e",
                          fill=TEXT_FAINT, font=(font, fpx(11)))

        self._chart_cols = []
        step = 1 if n <= 12 else (2 if n <= 20 else 3)
        for i, (d, (r, u)) in enumerate(zip(dates, vals)):
            cx = left + slot * (i + 0.5)
            is_today = d == today
            c.create_rectangle(cx - bar_w - 2, base_y - plot_h, cx + bar_w + 2, base_y,
                               fill=YELLOW_FAINT if is_today else "#F9FAFB", outline="")
            if r:
                c.create_rectangle(cx - bar_w - 1, base_y - max(3 * sc, plot_h * r / peak), cx - 1, base_y,
                                   fill="#D1D5DB", outline="")
            if u:
                c.create_rectangle(cx + 1, base_y - max(3 * sc, plot_h * u / peak), cx + bar_w + 1, base_y,
                                   fill=YELLOW, outline="")
            if i % step == 0 or is_today:
                c.create_text(cx, base_y + 14 * sc, text=f"{d.day:02d}",
                              fill="#111317" if is_today else TEXT_FAINT,
                              font=(font, fpx(11), "bold" if is_today else "normal"))
            self._chart_cols.append((cx - slot / 2, cx + slot / 2, d, r, u))

        if not any(r or u for r, u in vals):
            c.create_text(w / 2, base_y - plot_h / 2,
                          text="Belum ada aktivitas.\nGrafik terisi otomatis saat video dirender / dipublish.",
                          fill=TEXT_FAINT, justify="center", font=(font, fpx(13)))

    def _chart_hover(self, event):
        c = self.chart_canvas
        c.delete("tip")
        for x0, x1, d, r, u in self._chart_cols:
            if x0 <= event.x < x1:
                cx = (x0 + x1) / 2
                text = f"{short_date(d)}\nRendered  {r}   Uploaded  {u}"
                t = c.create_text(cx, 20, text=text, fill="#FFFFFF", justify="center",
                                  font=(FONT_UI or "TkDefaultFont", -int(12 * self._sc()), "bold"), tags="tip")
                bx0, by0, bx1, by1 = c.bbox(t)
                shift = 0
                if bx0 - 10 < 0:
                    shift = 10 - bx0
                elif bx1 + 10 > c.winfo_width():
                    shift = c.winfo_width() - bx1 - 10
                if shift:
                    c.move(t, shift, 0)
                    bx0, by0, bx1, by1 = c.bbox(t)
                rect = c.create_rectangle(bx0 - 10, by0 - 6, bx1 + 10, by1 + 6, fill="#121316",
                                          outline="#2D3139", tags="tip")
                c.tag_lower(rect, t)
                return

    # --- Kalender ---
    def _shift_month(self, delta):
        m = self.cal_month + delta
        y = self.cal_year
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        self.cal_month, self.cal_year = m, y
        self._build_calendar()

    def _build_calendar(self):
        if not hasattr(self, "cal_canvas"):
            return
        c = self.cal_canvas
        c.delete("all")
        y, m = self.cal_year, self.cal_month
        self.lbl_cal_title.configure(text=f"{MONTHS_ID[m - 1]} {y}")
        w = c.winfo_width()
        if w < 60:
            return
        sc = self._sc()
        fpx = lambda n: -int(round(n * sc))
        font = FONT_UI or "TkDefaultFont"
        col_w, rh, rad = w / 7, 32 * sc, 13 * sc

        for i, name in enumerate(("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min")):
            c.create_text(col_w * (i + 0.5), rh * 0.5, text=name, fill=TEXT_FAINT, font=(font, fpx(11), "bold"))

        today = datetime.date.today().isoformat()
        for r, week in enumerate(calendar.Calendar(0).monthdayscalendar(y, m), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue
                key = datetime.date(y, m, day).isoformat()
                is_today = key == today
                has_upload = int(self.history.get(key, {}).get("uploaded", 0)) > 0
                cx, cy = col_w * (col + 0.5), rh * (r + 0.5)
                if is_today or has_upload:
                    c.create_oval(cx - rad, cy - rad, cx + rad, cy + rad,
                                  fill=YELLOW if is_today else "#FDE68A", outline="")
                c.create_text(cx, cy, text=str(day),
                              fill="#111317" if (is_today or has_upload) else "#4B5563",
                              font=(font, fpx(12), "bold" if (is_today or has_upload) else "normal"))

    def _render_queue_list(self, rows):
        for child in self.queue_box.winfo_children():
            child.destroy()
        ready = sorted((r for r in rows if status_key(r) == "ready"), key=id_sort_key)
        self.lbl_queue_count.configure(text=f"{len(ready)} Pending")
        if not ready:
            self._label(self.queue_box, "Antrian kosong — generate ide di Content Planner.",
                        11, "normal", TEXT_FAINT, wraplength=250, justify="left").pack(anchor="w")
            return
        for i, row in enumerate(ready[:3]):
            first = i == 0
            item = ctk.CTkFrame(
                self.queue_box, corner_radius=12, border_width=1,
                fg_color=YELLOW_FAINT if first else "#F9FAFB",
                border_color="#FDE68A" if first else GRAY_100
            )
            item.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(item, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=7)
            ctk.CTkLabel(inner, text="●", font=F(9), text_color=YELLOW if first else "#D1D5DB"
                         ).pack(side="left", padx=(0, 8))
            col = ctk.CTkFrame(inner, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True)
            self._label(col, shorten(row["topic"] or "(tanpa judul)", 34), 11, "bold",
                        anchor="w").pack(anchor="w")
            self._label(col, row["niche"] or "-", 10, "normal", TEXT_MUTED, anchor="w").pack(anchor="w")
            ctk.CTkLabel(inner, text=f"#{row['id']}", font=F(10, "bold"), text_color="#374151",
                         fg_color="#FFFFFF", corner_radius=8, width=54, height=24).pack(side="right")
            self._bind_click(item, lambda: self.select_tab("planner"))

    # --- Video List ---
    def _render_dashboard_video_list(self, rows):
        for child in self.dashboard_video_box.winfo_children():
            child.destroy()

        allv = [r for r in rows if status_key(r) in ("ready for review", "done", "processing")]
        allv.sort(key=id_sort_key, reverse=True)
        shown = allv[:4]
        self.lbl_video_foot.configure(text=f"Menampilkan {len(shown)} dari {len(allv)} video")

        if not shown:
            self._empty_state(
                self.dashboard_video_box, ICON["film"], "Belum ada video",
                "Jalankan 'Start Automation' untuk mulai membuat video."
            )
            return

        for row_data in shown:
            key = status_key(row_data)
            item = ctk.CTkFrame(self.dashboard_video_box, fg_color="#FFFFFF", corner_radius=14,
                                border_width=1, border_color=GRAY_100)
            item.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(item, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)

            icon = ctk.CTkLabel(inner, text=ICON["film"], width=42, height=42, corner_radius=12,
                                fg_color=GRAY_100, text_color=TEXT_MUTED, font=F(16))
            icon.pack(side="left", padx=(0, 14))

            self._pill(inner, row_data["status"], key=key).pack(side="right", padx=(10, 0))

            col = ctk.CTkFrame(inner, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True)
            self._label(col, shorten(row_data["topic"] or f"Video #{row_data['id']}", 90),
                        12, "bold", "#111317", anchor="w", justify="left",
                        wraplength=270).pack(anchor="w")
            meta = f"Niche: {row_data['niche'] or '-'}  •  #{row_data['id']}"
            if row_data.get("duration"):
                meta += f"  •  {row_data['duration']}"
            self._label(col, meta, 11, "normal", TEXT_FAINT, anchor="w").pack(anchor="w", pady=(2, 0))

            self._bind_click(item, lambda d=row_data: self._open_in_studio(d))
            self._bind_hover(
                item,
                lambda i=item, ic=icon: (i.configure(border_color=YELLOW, fg_color=YELLOW_FAINT),
                                         ic.configure(fg_color=YELLOW, text_color="#111317")),
                lambda i=item, ic=icon: (i.configure(border_color=GRAY_100, fg_color="#FFFFFF"),
                                         ic.configure(fg_color=GRAY_100, text_color=TEXT_MUTED)),
            )

    def _open_in_studio(self, row_data):
        self.select_tab("preview")
        self.select_video_for_editing(row_data)

    # ------------------------------------------------------------
    # TAB 2: CONTENT PLANNER
    # ------------------------------------------------------------
    def _build_planner_tab(self):
        gen_card = self._card(self.frame_planner)
        gen_card.pack(fill="x", pady=(0, 16))
        gen = ctk.CTkFrame(gen_card, fg_color="transparent")
        gen.pack(fill="x", padx=24, pady=20)

        text_col = ctk.CTkFrame(gen, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        self._label(text_col, "Generate Ide Konten via AI", 16, "bold").pack(anchor="w", pady=(0, 4))
        self._label(
            text_col,
            "Fokus terkunci pada 'Fakta Sejarah' dan 'Misteri Alam Semesta'.\n"
            "Ide baru langsung didaftarkan ke Google Sheets dengan status 'Ready'.",
            12, "normal", TEXT_MUTED, justify="left"
        ).pack(anchor="w")

        self.btn_gen = self._btn(gen, f"{ICON['sparkle']}  Generate 5 Ide Baru", self.generate_ideas_thread,
                                 width=220, height=44, corner_radius=22)
        self.btn_gen.pack(side="right", padx=(20, 0))

        th = ctk.CTkFrame(self.frame_planner, fg_color="transparent")
        th.pack(fill="x", pady=(0, 10))
        self._label(th, "Daftar Konten", 15, "bold").pack(side="left")
        self.lbl_table_count = self._label(th, "", 11, "normal", TEXT_FAINT)
        self.lbl_table_count.pack(side="left", padx=(12, 0))
        self._btn(th, f"{ICON['refresh']}  Refresh", self.refresh_all, "ghost", height=36, width=110, corner_radius=18,
                  font=F(12, "bold")).pack(side="right")
        self.opt_status_filter = self._option(
            th, ["Semua", "Ready", "Processing", "Ready for Review", "Done", "Failed"],
            width=160, command=lambda v: self._apply_filters()
        )
        self.opt_status_filter.pack(side="right", padx=(0, 10))
        self._label(th, "Filter status", 11, "normal", TEXT_FAINT).pack(side="right", padx=(0, 8))

        table_card = self._card(self.frame_planner)
        table_card.pack(fill="both", expand=True)
        wrap = ctk.CTkFrame(table_card, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        columns = ("id", "niche", "topic", "hook", "status", "output")
        self.content_table = ttk.Treeview(wrap, columns=columns, show="headings", style="Glass.Treeview")
        headings = {
            "id": ("ID", 60, False), "niche": ("Niche", 160, False),
            "topic": ("Topic", 300, True), "hook": ("Hook Style", 140, False),
            "status": ("Status", 130, False), "output": ("Output", 200, False),
        }
        for col, (label, width, stretch) in headings.items():
            self.content_table.heading(col, text=label, anchor="w")
            self.content_table.column(col, width=width, anchor="w", stretch=stretch)

        for _key, (fg, _bg, tag) in STATUS_STYLE.items():
            self.content_table.tag_configure(tag, foreground=fg if tag != "review" else "#8A6D00")
        self.content_table.tag_configure("odd", background="#FAFAFC")

        scroll = ctk.CTkScrollbar(wrap, command=self.content_table.yview,
                                  button_color="#D1D5DB", button_hover_color="#9CA3AF")
        self.content_table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(6, 0))
        self.content_table.pack(side="left", fill="both", expand=True)
        self.content_table.bind("<Double-1>", self._on_table_double_click)

    def _planner_filtered(self, rows):
        q = self.search_text.strip().lower()
        st = self.opt_status_filter.get().lower() if hasattr(self, "opt_status_filter") else "semua"
        out = []
        for r in rows:
            if st != "semua" and status_key(r) != st:
                continue
            haystack = " ".join([str(r["id"]), r["niche"], r["topic"], r["hook"], r["status"], r["output"]])
            if q and q not in haystack.lower():
                continue
            out.append(r)
        return out

    def _apply_filters(self):
        self._update_planner_table(self.rows or [])

    def _update_planner_table(self, rows):
        for item in self.content_table.get_children():
            self.content_table.delete(item)
        self._row_by_iid = {}

        filtered = self._planner_filtered(rows)
        for i, row in enumerate(filtered):
            tag = status_style(status_key(row))[2]
            tags = (tag, "odd") if i % 2 else (tag,)
            iid = self.content_table.insert(
                "", "end", tags=tags,
                values=(row["id"], row["niche"], row["topic"], row["hook"], row["status"], row["output"])
            )
            self._row_by_iid[iid] = row

        suffix = f'  ·  filter: "{self.search_text.strip()}"' if self.search_text.strip() else ""
        self.lbl_table_count.configure(text=f"{len(filtered)} dari {len(rows)} baris{suffix}")

    def _on_table_double_click(self, _event):
        sel = self.content_table.selection()
        if sel and sel[0] in self._row_by_iid:
            self._open_in_studio(self._row_by_iid[sel[0]])

    def generate_ideas_thread(self):
        if self._generating:
            return
        self._generating = True
        self.btn_gen.configure(state="disabled", text="Generating…")

        def task():
            try:
                from modules.sheets_manager import generate_content_ideas_to_sheet
                print("\n✨ Meminta AI membuat ide baru...")
                generate_content_ideas_to_sheet(count=5)
                print("✅ 5 ide baru ditambahkan ke Google Sheets.")
                self.ui(lambda: self.toast("5 ide baru berhasil ditambahkan.", "success"))
            except Exception as exc:
                msg = str(exc)
                print(f"❌ Gagal generate ide: {msg}")
                self.ui(lambda: self.toast(f"Gagal generate ide: {msg}", "error", duration=7000))
            finally:
                self._generating = False
                self.ui(lambda: self.btn_gen.configure(state="normal", text=f"{ICON['sparkle']}  Generate 5 Ide Baru"))
                self.ui(self.refresh_all)

        threading.Thread(target=task, daemon=True).start()

    # ------------------------------------------------------------
    # TAB 3: VIDEO STUDIO
    # ------------------------------------------------------------
    def _build_preview_tab(self):
        split = ctk.CTkFrame(self.frame_preview, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=4, uniform="st")
        split.columnconfigure(1, weight=6, uniform="st")
        split.rowconfigure(0, weight=1)

        left = self._card(split)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lh = ctk.CTkFrame(left, fg_color="transparent")
        lh.pack(fill="x", padx=20, pady=(18, 8))
        self._label(lh, "Daftar Video", 15, "bold").pack(side="left")
        self._btn(lh, ICON["refresh"], self.refresh_all, "ghost", width=36, height=36, corner_radius=12,
                  font=F(15)).pack(side="right")
        self.preview_scroll = self._scroll(left)
        self.preview_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        right = self._card(split)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        # Bar aksi dipin di bawah supaya tombol Publish selalu terlihat (tidak ikut scroll)
        self.actions_bar = ctk.CTkFrame(right, fg_color="transparent")
        self.editor_body = ctk.CTkFrame(right, fg_color="transparent")
        self.editor_body.pack(fill="both", expand=True, padx=20, pady=(18, 6))
        self.editor_scroll = self._scroll(self.editor_body)
        self.editor_scroll.pack(fill="both", expand=True)

        self.editor_placeholder = ctk.CTkFrame(self.editor_scroll, fg_color="transparent")
        self._empty_state(
            self.editor_placeholder, ICON["film"], "Pilih video di sebelah kiri",
            "Metadata dan tombol publish akan muncul di sini."
        )
        self.editor_placeholder.pack(fill="x")

        form = ctk.CTkFrame(self.editor_scroll, fg_color="transparent")
        self.editor_form = form

        head = ctk.CTkFrame(form, fg_color="transparent")
        head.pack(fill="x")
        self._label(head, "Edit Metadata & Publish", 16, "bold").pack(side="left")
        self.editor_pill_holder = ctk.CTkFrame(head, fg_color="transparent")
        self.editor_pill_holder.pack(side="right")

        self.lbl_file = self._label(form, "", 11, "normal", TEXT_MUTED, anchor="w",
                                    wraplength=520, justify="left")
        self.lbl_file.pack(anchor="w", pady=(6, 0))

        # ---------- Panel SEO: generator + skor ----------
        seo = ctk.CTkFrame(form, fg_color=YELLOW_FAINT, corner_radius=14, border_width=1, border_color="#FDE68A")
        seo.pack(fill="x", pady=(14, 0))
        sin = ctk.CTkFrame(seo, fg_color="transparent")
        sin.pack(fill="x", padx=16, pady=14)
        stop = ctk.CTkFrame(sin, fg_color="transparent")
        stop.pack(fill="x")
        self._label(stop, f"{ICON['seo']}  SEO & Copywriting", 13, "bold").pack(side="left")
        self.lbl_seo_score = self._label(stop, "Skor SEO: -", 12, "bold", TEXT_MUTED)
        self.lbl_seo_score.pack(side="right")
        self.seo_bar = ctk.CTkProgressBar(sin, height=8, corner_radius=4, progress_color=YELLOW, fg_color="#FDE68A")
        self.seo_bar.set(0)
        self.seo_bar.pack(fill="x", pady=(10, 10))
        sbtn = ctk.CTkFrame(sin, fg_color="transparent")
        sbtn.pack(fill="x")
        self._btn(sbtn, f"{ICON['sparkle']}  Generate SEO", self.generate_seo_metadata,
                  width=160, height=34, corner_radius=17, font=F(12, "bold")).pack(side="left", padx=(0, 8))
        self._btn(sbtn, f"{ICON['refresh']}  Variasi Judul", self.cycle_title_variant, "ghost",
                  width=150, height=34, corner_radius=17, font=F(12, "bold")).pack(side="left")

        def field_row(text, counter_text):
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=(14, 6))
            self._label(row, text, 12, "bold", TEXT_MUTED).pack(side="left")
            counter = self._label(row, counter_text, 11, "normal", TEXT_FAINT)
            counter.pack(side="right")
            return counter

        # ---------- Judul / Deskripsi / Tags ----------
        self.lbl_title_count = field_row("Judul Video (#Shorts ditambahkan otomatis)", f"0/{TITLE_MAX}")
        self.entry_yt_title = self._entry(form)
        self.entry_yt_title.pack(fill="x")
        self.entry_yt_title.bind("<KeyRelease>", self._schedule_seo_refresh)

        self.lbl_desc_count = field_row("Deskripsi Video", f"0/{DESC_MAX_BYTES} byte")
        self.txt_yt_desc = ctk.CTkTextbox(
            form, fg_color="#FFFFFF", text_color=TEXT, border_color=BORDER,
            border_width=1, corner_radius=10, height=190, font=F(13)
        )
        self.txt_yt_desc.pack(fill="x")
        self.txt_yt_desc.bind("<KeyRelease>", self._schedule_seo_refresh)

        self.lbl_tags_count = field_row("Tags (pisahkan dengan koma)", f"0/{TAGS_MAX_CHARS}")
        self.entry_yt_tags = self._entry(form)
        self.entry_yt_tags.pack(fill="x")
        self.entry_yt_tags.bind("<KeyRelease>", self._schedule_seo_refresh)

        # ---------- Kategori & privasi ----------
        opts = ctk.CTkFrame(form, fg_color="transparent")
        opts.pack(fill="x", pady=(14, 0))
        opts.columnconfigure(0, weight=1, uniform="yt_opts")
        opts.columnconfigure(1, weight=1, uniform="yt_opts")
        self._label(opts, "Kategori", 12, "bold", TEXT_MUTED).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._label(opts, "Status Privasi", 12, "bold", TEXT_MUTED).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 6))
        self.opt_yt_category = self._option(opts, list(CATEGORY_CHOICES.keys()), height=38, font=F(13))
        self.opt_yt_category.set(DEFAULT_CATEGORY if DEFAULT_CATEGORY in CATEGORY_CHOICES else next(iter(CATEGORY_CHOICES)))
        self.opt_yt_category.grid(row=1, column=0, sticky="ew")
        self.opt_yt_privacy = self._option(opts, list(PRIVACY_CHOICES.keys()), height=38, font=F(13),
                                           command=self._on_privacy_change)
        self.opt_yt_privacy.set("Public")
        self.opt_yt_privacy.grid(row=1, column=1, sticky="ew", padx=(10, 0))

        self._field_label(form, "Jadwal Tayang (aktif jika privasi = Jadwalkan)")
        self.entry_yt_schedule = self._entry(form, "YYYY-MM-DD HH:MM  (waktu lokal komputer)")
        self.entry_yt_schedule.pack(fill="x")
        self.entry_yt_schedule.configure(state="disabled")

        # ---------- Opsi tambahan ----------
        self.var_yt_synthetic = ctk.BooleanVar(value=True)
        self.var_yt_notify = ctk.BooleanVar(value=True)
        switch_kw = dict(
            font=F(12), text_color=TEXT, fg_color="#D1D5DB", progress_color=YELLOW,
            button_color="#FFFFFF", button_hover_color=GRAY_100, onvalue=True, offvalue=False
        )
        ctk.CTkSwitch(form, text="Konten memakai suara AI / visual sintetis (disclosure YouTube)",
                      variable=self.var_yt_synthetic, **switch_kw).pack(anchor="w", pady=(16, 0))
        ctk.CTkSwitch(form, text="Beritahu subscriber saat video tayang",
                      variable=self.var_yt_notify, **switch_kw).pack(anchor="w", pady=(10, 0))

        # ---------- Checklist SEO ----------
        self._field_label(form, "Audit SEO (otomatis)", top=18)
        self.seo_checks_frame = ctk.CTkFrame(form, fg_color="#F9FAFB", corner_radius=12)
        self.seo_checks_frame.pack(fill="x", pady=(0, 6))

        # ---------- Aksi (dipin di bawah) ----------
        self.upload_progress = ctk.CTkProgressBar(self.actions_bar, progress_color=YELLOW, height=8)
        self.upload_progress.set(0)  # baru di-pack saat upload berjalan
        self.actions_btn_row = ctk.CTkFrame(self.actions_bar, fg_color="transparent")
        self.actions_btn_row.pack(fill="x")
        actions = self.actions_btn_row
        self.btn_play_preview = self._btn(actions, f"{ICON['play']}  Play Video", self._play_selected_video, "ghost",
                                          width=140, height=44, corner_radius=22)
        self.btn_play_preview.pack(side="left", padx=(0, 8))
        self.btn_open_folder = self._btn(actions, ICON["folder"], self._open_selected_folder, "ghost",
                                         width=50, height=44, corner_radius=22)
        self.btn_open_folder.pack(side="left", padx=(0, 8))
        self.btn_publish_now = self._btn(
            actions, f"Publish to YouTube  {ICON['rocket']}", self.publish_selected_video,
            height=44, corner_radius=22, text_color_disabled=TEXT_FAINT
        )
        self.btn_publish_now.pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------
    # Video Studio: helper metadata & SEO
    # ------------------------------------------------------------
    @staticmethod
    def _set_entry(entry, text):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)

    def _read_tags(self):
        return [t.strip().lstrip("#") for t in self.entry_yt_tags.get().split(",") if t.strip()]

    def _on_privacy_change(self, choice):
        scheduled = PRIVACY_CHOICES.get(choice) == "scheduled"
        self.entry_yt_schedule.configure(state="normal")
        if scheduled:
            if not self.entry_yt_schedule.get().strip():
                slot = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(
                    hour=19, minute=0, second=0, microsecond=0)
                self.entry_yt_schedule.insert(0, slot.strftime("%Y-%m-%d %H:%M"))
        else:
            self.entry_yt_schedule.configure(state="disabled")

    def _update_title_counter(self):
        """Nama lama dipertahankan; sekarang menyegarkan seluruh panel SEO."""
        self._schedule_seo_refresh()

    def _schedule_seo_refresh(self, _event=None):
        if self._seo_job is not None:
            try:
                self.after_cancel(self._seo_job)
            except Exception:
                pass
        self._seo_job = self.after(200, self._refresh_seo_panel)  # debounce saat mengetik

    def _seo_report(self):
        title = self.entry_yt_title.get()
        desc = self.txt_yt_desc.get("1.0", "end-1c")
        tags = self._read_tags()
        topic = (self.selected_video_data or {}).get("topic", "")
        if yt_seo is not None:
            return yt_seo.analyze_metadata(title, desc, tags, topic)
        return local_report(title, desc, tags, topic)

    def _refresh_seo_panel(self):
        self._seo_job = None
        if not hasattr(self, "seo_checks_frame"):
            return
        report = self._seo_report()
        c = report["counts"]
        self.lbl_title_count.configure(
            text=f"{c['title']}/{TITLE_MAX}", text_color=ROSE if c["title"] > TITLE_MAX else TEXT_FAINT)
        self.lbl_desc_count.configure(
            text=f"{c['desc_bytes']}/{DESC_MAX_BYTES} byte",
            text_color=ROSE if c["desc_bytes"] > DESC_MAX_BYTES else TEXT_FAINT)
        self.lbl_tags_count.configure(
            text=f"{c['tags']}/{TAGS_MAX_CHARS}", text_color=ROSE if c["tags"] > TAGS_MAX_CHARS else TEXT_FAINT)

        score = report["score"]
        color = EMERALD if score >= 85 else ("#F59E0B" if score >= 60 else ROSE)
        self.lbl_seo_score.configure(text=f"Skor SEO: {score}/100", text_color=color)
        self.seo_bar.set(max(0, min(1, score / 100)))
        self.seo_bar.configure(progress_color=color)

        for child in self.seo_checks_frame.winfo_children():
            child.destroy()
        icons = {"ok": (ICON["check"], EMERALD_DARK), "warn": (ICON["dot"], AMBER_DARK),
                 "err": (ICON["cross"], ROSE_DARK)}
        ctk.CTkFrame(self.seo_checks_frame, fg_color="transparent", height=6).pack()
        for status, msg in report["checks"]:
            mark, col = icons.get(status, icons["warn"])
            row = ctk.CTkFrame(self.seo_checks_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            self._label(row, mark, 12, "bold", col, width=18).pack(side="left", anchor="n")
            self._label(row, msg, 11, "normal", TEXT_MUTED if status == "ok" else TEXT,
                        anchor="w", justify="left", wraplength=470).pack(side="left", fill="x", expand=True, padx=(6, 0))
        ctk.CTkFrame(self.seo_checks_frame, fg_color="transparent", height=6).pack()

    def _build_seo(self, variant):
        data = self.selected_video_data or {}
        return yt_seo.build_seo_metadata(
            data.get("topic", ""), data.get("niche", ""), data.get("hook", ""),
            channel_name=self.settings.get("channel_name", DEFAULT_CHANNEL_NAME),
            variant=variant, disclose_ai=self.var_yt_synthetic.get()
        )

    def _snapshot(self):
        return (self.entry_yt_title.get(), self.txt_yt_desc.get("1.0", "end-1c"), self.entry_yt_tags.get())

    def _restore_fields(self, snap):
        self._set_entry(self.entry_yt_title, snap[0])
        self.txt_yt_desc.delete("1.0", "end")
        self.txt_yt_desc.insert("1.0", snap[1])
        self._set_entry(self.entry_yt_tags, snap[2])
        self._refresh_seo_panel()

    def generate_seo_metadata(self, announce=True):
        """Isi ulang judul, deskripsi, dan tags dari topik/niche/hook baris terpilih."""
        if not self.selected_video_data:
            self.toast("Pilih video terlebih dahulu.", "warn")
            return
        if yt_seo is None:
            self.toast("Modul youtube_uploader tidak termuat.", "warn")
            return
        prev = self._snapshot()
        meta = self._build_seo(self._seo_variant)
        self._seo_variant = meta["variant"]
        self._set_entry(self.entry_yt_title, meta["title"])
        self.txt_yt_desc.delete("1.0", "end")
        self.txt_yt_desc.insert("1.0", meta["description"])
        self._set_entry(self.entry_yt_tags, ", ".join(meta["tags"]))
        self._refresh_seo_panel()
        if announce and any(prev):
            self.toast("SEO di-generate ulang (judul, deskripsi, tags).", "info",
                       action_text="Batalkan", action=lambda: self._restore_fields(prev))

    def cycle_title_variant(self):
        """Ganti judul ke variasi hook berikutnya (deskripsi & tags tidak diubah)."""
        if not self.selected_video_data or yt_seo is None:
            self.toast("Pilih video terlebih dahulu.", "warn")
            return
        meta = self._build_seo(self._seo_variant + 1)
        self._seo_variant = meta["variant"]
        self._set_entry(self.entry_yt_title, meta["title"])
        self._refresh_seo_panel()
        self.toast(f"Variasi judul {meta['variant'] + 1}/{len(meta['title_variants'])}", "info", duration=2000)

    def _render_preview_list(self, rows):
        for child in self.preview_scroll.winfo_children():
            child.destroy()
        self._preview_cards = {}

        order = {"ready for review": 0, "processing": 1, "done": 2}
        shown = [r for r in rows if status_key(r) in order]
        shown.sort(key=lambda r: (order[status_key(r)], -id_sort_key(r)))

        if not shown:
            self._empty_state(
                self.preview_scroll, ICON["empty"], "Belum ada video",
                "Video berstatus 'Ready for Review' akan muncul di sini."
            )
            self.selected_video_data = None
            self._show_editor(False)
            return

        for row_data in shown:
            key = status_key(row_data)
            card = ctk.CTkFrame(self.preview_scroll, fg_color="#FFFFFF", corner_radius=14,
                                border_width=1, border_color=GRAY_100)
            card.pack(fill="x", pady=4)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)

            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill="x")
            self._pill(top, row_data["status"], key=key).pack(side="right")
            self._label(top, f"#{row_data['id']}", 11, "bold", TEXT_FAINT).pack(side="left")

            self._label(inner, shorten(row_data["topic"] or "(tanpa judul)", 80), 12, "bold", "#111317",
                        anchor="w", wraplength=240, justify="left").pack(anchor="w", pady=(6, 0))
            self._label(inner, f"Niche: {row_data['niche'] or '-'}", 11, "normal", TEXT_FAINT,
                        anchor="w").pack(anchor="w", pady=(2, 0))

            self._bind_click(card, lambda d=row_data: self.select_video_for_editing(d))
            self._preview_cards[str(row_data["id"])] = card

        # Pertahankan pilihan (dan ketikan user) saat refresh
        current_id = str(self.selected_video_data.get("id")) if self.selected_video_data else None
        latest = {str(r["id"]): r for r in shown}
        if current_id in latest:
            self.selected_video_data = latest[current_id]
            self._show_editor(True)
            self._highlight_selected()
            self._update_editor_state()
        else:
            self.select_video_for_editing(shown[0])

    def _show_editor(self, visible):
        if visible:
            self.editor_placeholder.pack_forget()
            self.editor_form.pack(fill="x")
            self.actions_bar.pack(side="bottom", fill="x", padx=20, pady=(4, 18), before=self.editor_body)
        else:
            self.editor_form.pack_forget()
            self.actions_bar.pack_forget()
            self.editor_placeholder.pack(fill="x")
            self._editor_loaded_id = None

    def _highlight_selected(self):
        sel = str(self.selected_video_data.get("id")) if self.selected_video_data else None
        for rid, card in self._preview_cards.items():
            if rid == sel:
                card.configure(border_color=YELLOW, border_width=2, fg_color=YELLOW_FAINT)
            else:
                card.configure(border_color=GRAY_100, border_width=1, fg_color="#FFFFFF")

    def _capture_draft(self, vid):
        """Simpan isi form per video supaya editan tidak hilang saat pindah video."""
        if vid is None or not hasattr(self, "entry_yt_title"):
            return
        self._drafts[vid] = {
            "title": self.entry_yt_title.get(), "desc": self.txt_yt_desc.get("1.0", "end-1c"),
            "tags": self.entry_yt_tags.get(), "category": self.opt_yt_category.get(),
            "privacy": self.opt_yt_privacy.get(), "schedule": self.entry_yt_schedule.get(),
            "synthetic": bool(self.var_yt_synthetic.get()), "notify": bool(self.var_yt_notify.get()),
            "variant": self._seo_variant,
        }

    def _restore_draft(self, d):
        self._set_entry(self.entry_yt_title, d["title"])
        self.txt_yt_desc.delete("1.0", "end")
        self.txt_yt_desc.insert("1.0", d["desc"])
        self._set_entry(self.entry_yt_tags, d["tags"])
        if d["category"] in CATEGORY_CHOICES:
            self.opt_yt_category.set(d["category"])
        self.opt_yt_privacy.set(d["privacy"])
        self._set_entry(self.entry_yt_schedule, d["schedule"])
        self._on_privacy_change(d["privacy"])
        self.var_yt_synthetic.set(d["synthetic"])
        self.var_yt_notify.set(d["notify"])
        self._seo_variant = d.get("variant", 0)
        self._refresh_seo_panel()

    def select_video_for_editing(self, video_data):
        vid = str(video_data.get("id"))
        self.selected_video_data = video_data
        self._show_editor(True)

        if self._editor_loaded_id != vid:  # video berbeda -> simpan draft lama, muat/generate yang baru
            if self._editor_loaded_id is not None:
                self._capture_draft(self._editor_loaded_id)
            draft = self._drafts.get(vid)
            if draft:
                self._restore_draft(draft)
            elif yt_seo is not None:
                self._seo_variant = 0
                self.generate_seo_metadata(announce=False)
            else:  # fallback minimal jika modul SEO tidak termuat
                topic, niche = video_data.get("topic", ""), video_data.get("niche", "")
                self._set_entry(self.entry_yt_title, topic)
                self.txt_yt_desc.delete("1.0", "end")
                self.txt_yt_desc.insert(
                    "1.0", f"Simak fakta menarik seputar {topic} hanya di channel ini!\n\n"
                          f"#Shorts #{niche.replace(' ', '')} #FaktaUnik")
                self._set_entry(self.entry_yt_tags, f"shorts, {niche.lower()}, faktaunik, misteri, edukasi")
                self._refresh_seo_panel()
            self._editor_loaded_id = vid

        self._highlight_selected()
        self._update_editor_state()

    def _update_editor_state(self):
        """Sinkronkan pill status, info file, dan tombol dengan baris yang dipilih."""
        data = self.selected_video_data
        if not data or self._publishing:
            return
        key = status_key(data)
        output = data.get("output", "")
        url = is_url(output)
        exists = url or (bool(output) and os.path.exists(os.path.abspath(output)))

        for child in self.editor_pill_holder.winfo_children():
            child.destroy()
        self._pill(self.editor_pill_holder, data["status"], key=key).pack()

        if url:
            self.lbl_file.configure(text=f"{ICON['link']} {output}", text_color=EMERALD_DARK)
        elif exists:
            self.lbl_file.configure(text=f"{ICON['folder']} {output}   {ICON['check']} file ditemukan", text_color=TEXT_MUTED)
        else:
            self.lbl_file.configure(
                text=f"{ICON['folder']} {output or '(belum ada output)'}   {ICON['cross']} file tidak ditemukan",
                text_color=ROSE if key == "ready for review" else TEXT_FAINT
            )

        self.btn_play_preview.configure(text=f"{ICON['link']}  Buka di YouTube" if url else f"{ICON['play']}  Play Video")
        self.btn_open_folder.configure(state="disabled" if url or not exists else "normal")

        if key == "ready for review":
            self.btn_publish_now.configure(
                state="normal" if exists else "disabled", text=f"Publish to YouTube  {ICON['rocket']}",
                fg_color=YELLOW if exists else GRAY_200
            )
        else:
            label = {"done": f"{ICON['check']}  Sudah Dipublish", "processing": "Sedang Diproses…"}.get(key, "Belum Siap Publish")
            self.btn_publish_now.configure(state="disabled", text=label, fg_color=GRAY_200)

    def _play_selected_video(self):
        if not self.selected_video_data:
            self.toast("Pilih video terlebih dahulu.", "warn")
            return
        output = self.selected_video_data.get("output", "")
        if is_url(output):
            webbrowser.open(output)
            return
        full_path = os.path.abspath(output) if output else ""
        if full_path and os.path.exists(full_path):
            open_path(full_path)
        else:
            self.toast(f"File video belum ditemukan:\n{full_path or '-'}", "warn", duration=6000)

    def _open_selected_folder(self):
        if not self.selected_video_data:
            return
        output = self.selected_video_data.get("output", "")
        full_path = os.path.abspath(output) if output else ""
        if not full_path or not os.path.exists(full_path):
            return
        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", full_path])
        else:
            open_path(os.path.dirname(full_path))

    def publish_selected_video(self):
        data = self.selected_video_data
        if not data:
            self.toast("Tidak ada video yang dipilih.", "warn")
            return
        if status_key(data) != "ready for review":
            self.toast("Hanya video berstatus 'Ready for Review' yang bisa dipublish.", "warn")
            return
        if yt_seo is None:
            messagebox.showerror("Modul hilang", "modules/youtube_uploader.py tidak bisa dimuat.")
            return

        row_idx = data.get("id")
        video_path = data.get("output")
        title = self.entry_yt_title.get().strip()
        description = self.txt_yt_desc.get("1.0", "end-1c")
        tags = self._read_tags()
        privacy_label = self.opt_yt_privacy.get()
        privacy = PRIVACY_CHOICES.get(privacy_label, "public")
        category_name = self.opt_yt_category.get()
        category_id = CATEGORY_CHOICES.get(category_name, "27")
        synthetic = bool(self.var_yt_synthetic.get())
        notify = bool(self.var_yt_notify.get())

        if not title:
            messagebox.showwarning("Judul kosong", "Isi judul video terlebih dahulu.")
            return
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error File", f"File MP4 tidak ditemukan di path:\n{video_path}")
            return

        # Audit SEO: error = wajib diperbaiki, warning = boleh lanjut setelah konfirmasi
        report = yt_seo.analyze_metadata(title, description, tags, data.get("topic", ""))
        if report["errors"]:
            messagebox.showerror(
                "Metadata belum valid",
                "Perbaiki dulu sebelum publish:\n\n• " + "\n• ".join(report["errors"])
            )
            return

        publish_at = None
        if privacy == "scheduled":
            try:
                publish_at = yt_seo.parse_schedule(self.entry_yt_schedule.get())
            except ValueError as exc:
                messagebox.showwarning("Jadwal tidak valid", str(exc))
                return

        final_title = yt_seo.finalize_title(title)
        privacy_line = (
            f"Dijadwalkan: {self.entry_yt_schedule.get().strip()} (waktu lokal)"
            if publish_at else f"Privasi: {privacy_label}"
        )
        confirm = (
            f"Upload video ini ke YouTube?\n\nJudul: {final_title}\n{privacy_line}\n"
            f"Kategori: {category_name}\nSkor SEO: {report['score']}/100"
        )
        if report["warnings"]:
            confirm += "\n\nSaran SEO:\n• " + "\n• ".join(report["warnings"][:5])
        if not messagebox.askyesno("Konfirmasi Publish", confirm):
            return

        self._publishing = True
        self.btn_publish_now.configure(state="disabled", text="Uploading to YouTube…")
        self.upload_progress.set(0)
        self.upload_progress.pack(fill="x", pady=(0, 8), before=self.actions_btn_row)

        def on_progress(pct):
            self.ui(lambda p=pct: self.upload_progress.set(p / 100))

        def finish():
            self._publishing = False
            self.ui(self.upload_progress.pack_forget)
            self.ui(self._update_editor_state)
            self.ui(self.refresh_all)

        def task():
            video_url = None
            try:
                from modules.youtube_uploader import upload_video_to_youtube

                print(f"\n📤 Memulai upload YouTube untuk baris #{row_idx}: {final_title}...")
                video_url = upload_video_to_youtube(
                    video_path=video_path, title=title, description=description,
                    tags=tags, category_id=category_id,
                    privacy_status="private" if publish_at else privacy,
                    publish_at=publish_at, synthetic_media=synthetic,
                    notify_subscribers=notify, progress_callback=on_progress
                )
            except Exception as exc:
                msg = str(exc)  # simpan ke variabel biasa; `exc` dihapus Python setelah blok except
                print(f"❌ Upload Gagal: {msg}")
                self.ui(lambda: messagebox.showerror("Upload Error", f"Gagal upload video:\n{msg}"))
                finish()
                return

            # ---- Upload SUDAH sukses: catat di grafik, lalu update status Sheets (dipisah agar error tidak menyesatkan)
            self.ui(lambda: self._bump("uploaded"))
            self.ui(lambda: self._drafts.pop(str(row_idx), None))
            try:
                from modules.sheets_manager import update_row_status

                # Id dari Sheets bisa berupa teks ("047"); update_row_status butuh angka.
                try:
                    row_arg = int(str(row_idx).strip())
                except (TypeError, ValueError):
                    row_arg = row_idx
                update_row_status(row_arg, "Done", video_path=video_url if video_url else video_path)
                print("✅ Upload berhasil & status Sheets diperbarui!")
                done_msg = (
                    f"Video #{row_idx} dijadwalkan tayang" if publish_at
                    else f"Video #{row_idx} berhasil dipublish 🎉"
                )
                self.ui(lambda: self.toast(done_msg, "success"))
            except Exception as exc:
                msg = str(exc)
                url_txt = video_url or "(URL tidak tersedia)"
                print(f"⚠️ Video sudah terupload ({url_txt}) tetapi update status Sheets gagal: {msg}")
                self.ui(lambda: messagebox.showwarning(
                    "Video sudah tayang, status belum terupdate",
                    f"Video BERHASIL diupload:\n{url_txt}\n\n"
                    f"Tetapi status di Google Sheets gagal diperbarui:\n{msg}\n\n"
                    f"Ubah status baris #{row_idx} menjadi Done secara manual agar tidak terupload dua kali."
                ))
            finally:
                finish()

        threading.Thread(target=task, daemon=True).start()

    # ------------------------------------------------------------
    # TAB 4: USER / AKUN
    # ------------------------------------------------------------
    def _build_account_tab(self):
        self.conn_yt = self._create_connection_card(
            ICON["youtube"], "YouTube Channel", "Switch / Reset Akun YouTube", self.reset_youtube_token)
        self.conn_sheet = self._create_connection_card(
            ICON["sheet"], "Google Sheets", "Tes Koneksi", lambda: self.load_rows(force=True, announce=True))
        self.conn_drive = self._create_connection_card(
            ICON["cloud"], "Google Drive", "Segera Hadir", None)
        self.conn_drive["button"].configure(state="disabled")
        self._set_connection(
            self.conn_drive, False, "Integrasi Drive belum tersedia di versi ini.", pill="Segera Hadir")

    def _create_connection_card(self, icon, title, action_text, action_command):
        card = self._card(self.frame_account)
        card.pack(fill="x", pady=(0, 14))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=20)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        self._badge(top, icon, 46, YELLOW_SOFT, "#8A6D00", F(17, "bold"), radius=14).pack(side="left", padx=(0, 14))
        col = ctk.CTkFrame(top, fg_color="transparent")
        col.pack(side="left", fill="x", expand=True)
        self._label(col, title, 16, "bold").pack(anchor="w")
        status_lbl = self._label(col, "", 12, "normal", TEXT_MUTED, anchor="w", justify="left")
        status_lbl.pack(anchor="w", pady=(2, 0))

        pill_holder = ctk.CTkFrame(top, fg_color="transparent")
        pill_holder.pack(side="right", padx=(12, 0))

        button = self._btn(inner, action_text, action_command, "ghost", width=240, height=38,
                           corner_radius=19, font=F(12, "bold"))
        button.pack(anchor="w", pady=(16, 0))
        return {"status": status_lbl, "pill_holder": pill_holder, "button": button}

    def _set_connection(self, conn, connected, text, pill=None):
        conn["status"].configure(text=text)
        for child in conn["pill_holder"].winfo_children():
            child.destroy()
        if connected:
            label, fg, bg = "Connected", EMERALD_DARK, EMERALD_BG
        elif pill == "Checking":
            label, fg, bg = "Checking…", AMBER_DARK, AMBER_BG
        elif pill == "Segera Hadir":
            label, fg, bg = "Segera Hadir", TEXT_MUTED, GRAY_200
        else:
            label, fg, bg = pill or "Not Connected", ROSE_DARK, ROSE_BG
        self._pill(conn["pill_holder"], label, fg=fg, bg=bg).pack()

    def _refresh_account_status(self):
        if not hasattr(self, "conn_yt"):
            return
        if os.path.exists(TOKEN_FILE):
            self._set_connection(self.conn_yt, True, "Token tersimpan (token.pickle) — siap upload.")
            self.lbl_profile_status.configure(text="● Connected", text_color=EMERALD_DARK)
        elif os.path.exists(CLIENT_SECRET_FILE):
            self._set_connection(
                self.conn_yt, False,
                "Belum login. Browser akan terbuka saat upload pertama.", pill="Belum Login")
            self.lbl_profile_status.configure(text="● Belum login", text_color=AMBER_DARK)
        else:
            self._set_connection(
                self.conn_yt, False, "client_secret.json tidak ditemukan di folder project.")
            self.lbl_profile_status.configure(text="● Tidak terhubung", text_color=ROSE_DARK)

        if self._sheet_ok is None:
            self._set_connection(self.conn_sheet, False, f"Memeriksa '{SHEET_NAME}'…", pill="Checking")
        elif self._sheet_ok:
            n = len(self.rows or [])
            self._set_connection(self.conn_sheet, True, f"Spreadsheet '{SHEET_NAME}' — {n} baris terbaca.")
        else:
            self._set_connection(self.conn_sheet, False, f"Gagal membaca '{SHEET_NAME}'. Cek koneksi & kredensial.")

    def reset_youtube_token(self):
        if not os.path.exists(TOKEN_FILE):
            self.toast("Tidak ada token.pickle yang tersimpan.", "warn")
            return
        if not messagebox.askyesno(
            "Reset Akun YouTube",
            "Hapus token login YouTube?\nBrowser akan terbuka untuk login ulang saat upload berikutnya."
        ):
            return
        try:
            os.remove(TOKEN_FILE)
        except OSError as exc:
            messagebox.showerror("Gagal", f"Tidak bisa menghapus token.pickle:\n{exc}")
            return
        self._refresh_account_status()
        self.toast("Token YouTube dihapus. Login ulang saat upload berikutnya.", "success")

    # ------------------------------------------------------------
    # TAB 5: NOTIFICATIONS
    # ------------------------------------------------------------
    def _build_notifications_tab(self):
        card = self._card(self.frame_notifications)
        card.pack(fill="both", expand=True)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 6))
        self._label(head, "Riwayat Notifikasi", 16, "bold").pack(side="left")
        self._btn(head, "Hapus Semua", self._clear_notifications, "ghost", width=120, height=34,
                  corner_radius=17, font=F(12, "bold")).pack(side="right")
        self.notif_scroll = self._scroll(card)
        self.notif_scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _clear_notifications(self):
        self.notifications.clear()
        self.unread = 0
        self._update_bell()
        self._render_notifications()

    def _render_notifications(self):
        if not hasattr(self, "notif_scroll"):
            return
        for child in self.notif_scroll.winfo_children():
            child.destroy()
        if not self.notifications:
            self._empty_state(self.notif_scroll, ICON["bell"], "Belum ada notifikasi",
                              "Notifikasi upload, sinkronisasi, dan error akan muncul di sini.")
            return
        colors = {"info": YELLOW, "success": EMERALD, "warn": "#F59E0B", "error": ROSE}
        for n in self.notifications:
            row = ctk.CTkFrame(self.notif_scroll, fg_color="#F9FAFB", corner_radius=12)
            row.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)
            ctk.CTkLabel(inner, text="●", text_color=colors.get(n["kind"], YELLOW), font=F(12)
                         ).pack(side="left", padx=(0, 10))
            self._label(inner, n["msg"], 12, "normal", "#111317", anchor="w", justify="left",
                        wraplength=760).pack(side="left", fill="x", expand=True)
            self._label(inner, n["time"], 11, "normal", TEXT_FAINT).pack(side="right", padx=(12, 0))

    # ------------------------------------------------------------
    # TAB 6: SETTINGS
    # ------------------------------------------------------------
    def _build_settings_tab(self):
        footer = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=(12, 0))
        self._btn(footer, f"{ICON['save']}  Simpan Pengaturan", self.save_all_settings, width=220, height=44,
                  corner_radius=22).pack(side="right")
        self._label(footer, "API key disimpan ke .env, preferensi ke gui_settings.json",
                    11, "normal", TEXT_FAINT).pack(side="left")

        scroll = self._scroll(self.frame_settings)
        scroll.pack(fill="both", expand=True)

        api = self._settings_section(scroll, "API & Integrations", "Kredensial untuk generate konten")
        self.entry_groq = self._setting_input(api, "Groq API Key", "gsk_...", os.getenv("GROQ_API_KEY", ""),
                                              secret=True, top=0)
        self.entry_pexels = self._setting_input(api, "Pexels API Key", "5634b...",
                                                os.getenv("PEXELS_API_KEY", ""), secret=True)
        self.entry_magick = self._setting_input(
            api, "ImageMagick Executable Path", "C:\\...",
            os.getenv("IMAGEMAGICK_PATH", r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"))
        self.entry_channel = self._setting_input(
            api, "Nama Channel (dipakai generator SEO & deskripsi)", DEFAULT_CHANNEL_NAME, "")

        gen = self._settings_section(scroll, "General", "Preferensi dasar aplikasi")
        self.var_notif = self._setting_switch(
            gen, "Popup Notifikasi", "Tampilkan popup saat video selesai / aksi berhasil (riwayat tetap dicatat)")
        self.var_autostart = self._setting_switch(
            gen, "Jalankan Otomatis Saat Dibuka", "Mulai automation loop begitu aplikasi dijalankan")

        auto = self._settings_section(scroll, "Automation & Publishing", "Atur perilaku loop automasi")
        self._field_label(auto, "Mode Upload YouTube", top=0)
        self.upload_mode_option = self._option(auto, list(UPLOAD_MODES.keys()), height=38, font=F(13))
        self.upload_mode_option.pack(anchor="w", fill="x")

        self.entry_interval = self._setting_input(auto, "Interval Pengecekan (detik, min. 5)", "30", "")
        self.entry_retries = self._setting_input(auto, "Maksimal Percobaan Ulang (1–10)", "3", "")

        self._field_label(auto, "Folder Output Video")
        picker = ctk.CTkFrame(auto, fg_color="transparent")
        picker.pack(fill="x")
        self.entry_output_folder = self._entry(picker, "output/")
        self.entry_output_folder.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._btn(picker, "Browse", self.browse_output_folder, "ghost", width=90, height=38,
                  font=F(12, "bold")).pack(side="left")

        adv = self._settings_section(scroll, "Advanced", "Pemecahan masalah")
        self._field_label(adv, "Log Level (filter tampilan Live Log)", top=0)
        self.opt_log_level = self._option(adv, ["Info", "Debug", "Warning", "Error"], height=38,
                                          font=F(13), width=200)
        self.opt_log_level.pack(anchor="w")

        danger = ctk.CTkFrame(adv, fg_color="transparent")
        danger.pack(fill="x", pady=(20, 0))
        self._btn(danger, "Clear Cache Render", self.clear_cache, "ghost", width=180, height=38,
                  corner_radius=19, font=F(12, "bold")).pack(side="left", padx=(0, 10))
        self._btn(danger, "Reset Preferensi", self.reset_application, "danger", width=170, height=38,
                  corner_radius=19, font=F(12, "bold")).pack(side="left")

        about = self._settings_section(scroll, "About", "Informasi aplikasi")
        self._label(about, f"YouTube Shorts Automation Studio — versi {APP_VERSION}",
                    12, "normal", TEXT_MUTED).pack(anchor="w")

    def _settings_section(self, parent, title, subtitle):
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.pack(fill="x", pady=(0, 18))
        self._label(wrapper, title, 15, "bold").pack(anchor="w")
        self._label(wrapper, subtitle, 12, "normal", TEXT_FAINT).pack(anchor="w", pady=(2, 10))
        card = self._card(wrapper)
        card.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=20)
        return inner

    def _setting_input(self, parent, label_text, placeholder, default="", secret=False, top=14):
        self._field_label(parent, label_text, top=top)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")
        entry = self._entry(row, placeholder, show="•" if secret else "")
        entry.pack(side="left", fill="x", expand=True)
        if default:
            entry.insert(0, default)
        if secret:
            def toggle(e=entry):
                e.configure(show="" if e.cget("show") else "•")
            self._btn(row, ICON["eye"], toggle, "ghost", width=44, height=38).pack(side="left", padx=(8, 0))
        return entry

    def _setting_switch(self, parent, title, description):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=8)
        col = ctk.CTkFrame(row, fg_color="transparent")
        col.pack(side="left", fill="x", expand=True)
        self._label(col, title, 13, "bold").pack(anchor="w")
        self._label(col, description, 11, "normal", TEXT_FAINT).pack(anchor="w", pady=(2, 0))
        var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            row, text="", variable=var, onvalue=True, offvalue=False,
            fg_color="#D1D5DB", progress_color=YELLOW,
            button_color="#FFFFFF", button_hover_color=GRAY_100
        ).pack(side="right")
        return var

    def _apply_settings_to_ui(self):
        s = self.settings
        self.var_notif.set(bool(s.get("notifications", True)))
        self.var_autostart.set(bool(s.get("autostart", False)))
        mode = s.get("upload_mode")
        self.upload_mode_option.set(mode if mode in UPLOAD_MODES else DEFAULT_SETTINGS["upload_mode"])
        self.opt_log_level.set(s.get("log_level", "Info"))
        for entry, value in (
            (self.entry_interval, s.get("interval", 30)),
            (self.entry_retries, s.get("retries", 3)),
            (self.entry_output_folder, s.get("output_folder", "")),
            (self.entry_channel, s.get("channel_name", DEFAULT_CHANNEL_NAME)),
        ):
            entry.delete(0, "end")
            entry.insert(0, str(value))

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.entry_output_folder.delete(0, "end")
            self.entry_output_folder.insert(0, folder)

    def save_all_settings(self):
        try:
            interval = int(self.entry_interval.get().strip() or 30)
            retries = int(self.entry_retries.get().strip() or 3)
        except ValueError:
            messagebox.showwarning("Input tidak valid", "Interval dan retry harus berupa angka bulat.")
            return
        if interval < 5:
            messagebox.showwarning("Interval terlalu kecil", "Interval minimal 5 detik.")
            return
        if not 1 <= retries <= 10:
            messagebox.showwarning("Retry tidak valid", "Percobaan ulang harus 1–10.")
            return

        out_folder = self.entry_output_folder.get().strip()
        env_values = {
            "GROQ_API_KEY": self.entry_groq.get().strip(),
            "PEXELS_API_KEY": self.entry_pexels.get().strip(),
            "IMAGEMAGICK_PATH": self.entry_magick.get().strip(),
        }
        if out_folder:
            env_values["OUTPUT_DIR"] = out_folder

        try:
            if not os.path.exists(ENV_FILE):
                open(ENV_FILE, "w", encoding="utf-8").close()
            for key, value in env_values.items():
                set_key(ENV_FILE, key, value)
                os.environ[key] = value  # langsung aktif tanpa restart

            self.settings.update({
                "upload_mode": self.upload_mode_option.get(),
                "interval": interval,
                "retries": retries,
                "output_folder": out_folder,
                "log_level": self.opt_log_level.get(),
                "notifications": bool(self.var_notif.get()),
                "autostart": bool(self.var_autostart.get()),
                "channel_name": self.entry_channel.get().strip() or DEFAULT_CHANNEL_NAME,
            })
            save_json(SETTINGS_FILE, self.settings)
        except OSError as exc:
            messagebox.showerror("Gagal menyimpan", f"Tidak bisa menulis file pengaturan:\n{exc}")
            return

        self.toast("Pengaturan disimpan dan langsung aktif.", "success")

    def clear_cache(self):
        if not os.path.isdir(TEMP_DIR):
            self.toast(f"Folder cache belum ada:\n{TEMP_DIR}", "warn", duration=6000)
            return
        if not messagebox.askyesno(
            "Clear Cache Render",
            f"Hapus semua file sementara di:\n{TEMP_DIR}\n\nVideo final di folder output tidak ikut terhapus."
        ):
            return
        removed, failed = 0, 0
        for name in os.listdir(TEMP_DIR):
            path = os.path.join(TEMP_DIR, name)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    removed += 1
                except OSError:
                    failed += 1
        msg = f"{removed} file cache dihapus." + (f" {failed} gagal (sedang dipakai)." if failed else "")
        self.toast(msg, "warn" if failed else "success")

    def reset_application(self):
        if not messagebox.askyesno(
            "Reset Preferensi",
            "Kembalikan preferensi (interval, mode upload, dll.) ke default?\nAPI key di .env tidak diubah."
        ):
            return
        self.settings = dict(DEFAULT_SETTINGS)
        try:
            save_json(SETTINGS_FILE, self.settings)
        except OSError:
            pass
        self._apply_settings_to_ui()
        self.toast("Preferensi dikembalikan ke default.", "success")

    # ------------------------------------------------------------
    # TAB 7: HELP CENTRE
    # ------------------------------------------------------------
    def _build_help_tab(self):
        scroll = self._scroll(self.frame_help)
        scroll.pack(fill="both", expand=True)

        def section(title, body_lines):
            card = self._card(scroll)
            card.pack(fill="x", pady=(0, 14))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=24, pady=20)
            self._label(inner, title, 15, "bold").pack(anchor="w", pady=(0, 8))
            for line in body_lines:
                self._label(inner, line, 12, "normal", "#374151", anchor="w", justify="left",
                            wraplength=900).pack(anchor="w", pady=2)
            return inner

        section("Alur Kerja", [
            "1.  Content Planner → Generate ide baru (status 'Ready') atau isi langsung di Google Sheets.",
            "2.  Dashboard → Start Automation. Bot membuat video dan mengubah status menjadi 'Ready for Review'.",
            "3.  Video Studio → Generate SEO / Variasi Judul, cek skor & audit SEO, atur kategori/privasi/jadwal, lalu Publish to YouTube.",
            "4.  Setelah upload, status baris berubah menjadi 'Done' dan link YouTube tersimpan di kolom Output.",
        ])
        section("Shortcut Keyboard", [
            "Ctrl + K   Fokus ke kolom pencarian (Enter = buka Content Planner, Esc = hapus filter)",
            "Ctrl + R   Refresh data dari Google Sheets",
            "Ctrl + B   Kecilkan / perluas sidebar",
            "Ctrl + 1 … 4   Pindah ke Dashboard / Planner / Video Studio / Akun",
        ])
        section("Pemecahan Masalah", [
            "•  'Gagal mengambil data Google Sheets' → cek internet, client_secret.json, dan nama sheet.",
            "•  Tombol Publish nonaktif → file video di kolom Output tidak ditemukan atau status bukan 'Ready for Review'.",
            "•  Ubah Log Level ke 'Debug' di Settings untuk melihat traceback lengkap saat error.",
            "•  Generate SEO tidak jalan → pastikan modules/youtube_uploader.py bisa dimuat (lihat Live Log saat app dibuka).",
            "•  Login YouTube salah akun → User / Akun → Switch / Reset Akun YouTube.",
        ])
        tools = section("Pintasan Folder", [])
        row = ctk.CTkFrame(tools, fg_color="transparent")
        row.pack(anchor="w")
        self._btn(row, f"{ICON['folder']}  Folder Project", lambda: open_path(BASE_DIR), "ghost", width=170, height=38,
                  corner_radius=19, font=F(12, "bold")).pack(side="left", padx=(0, 10))
        self._btn(row, f"{ICON['folder']}  Folder Output", self._open_output_folder, "ghost", width=170, height=38,
                  corner_radius=19, font=F(12, "bold")).pack(side="left")

    def _open_output_folder(self):
        folder = self.settings.get("output_folder") or DEFAULT_OUTPUT_DIR
        if os.path.isdir(folder):
            open_path(folder)
        else:
            self.toast(f"Folder output belum ada:\n{folder}", "warn", duration=6000)

    # ------------------------------------------------------------
    # AUTOMATION LOOP (thread-safe, tanpa dobel thread)
    # ------------------------------------------------------------
    def _set_automation_ui(self, state):
        if state == "running":
            self.btn_start_auto.configure(text=f"{ICON['stop']}  Stop Automation", state="normal",
                                          fg_color="#141518", hover_color="#2A2D33", text_color="#FFFFFF")
            self.btn_mini_play.configure(text=ICON["stop"], state="normal")
            self.status_dot.configure(text="Running")
            self.lbl_status_sub.configure(text="Automation loop aktif")
            self.status_light.configure(text_color=EMERALD)
        elif state == "stopping":
            self.btn_start_auto.configure(text="Menghentikan…", state="disabled")
            self.btn_mini_play.configure(state="disabled")
            self.status_dot.configure(text="Stopping")
            self.lbl_status_sub.configure(text="Menunggu tugas terakhir selesai")
            self.status_light.configure(text_color="#F59E0B")
        else:
            self.btn_start_auto.configure(text=f"{ICON['play']}  Start Automation", state="normal",
                                          fg_color=YELLOW, hover_color=YELLOW_HOVER, text_color="#111317")
            self.btn_mini_play.configure(text=ICON["play"], state="normal")
            self.status_dot.configure(text="Stopped")
            self.lbl_status_sub.configure(text="Automator siap dijalankan")
            self.status_light.configure(text_color=ROSE)
            self.lbl_countdown.configure(text="")
        self._update_kpi_footers()

    def toggle_automation(self):
        if not self.is_running:
            if self.automation_thread and self.automation_thread.is_alive():
                return  # loop lama masih menyelesaikan tugas
            self.is_running = True
            self._set_automation_ui("running")
            self.automation_thread = threading.Thread(target=self.run_automation_loop, daemon=True)
            self.automation_thread.start()
        else:
            self.is_running = False
            self._set_automation_ui("stopping")
            print("Automation berhenti setelah tugas yang sedang berjalan selesai...")

    def _interruptible_sleep(self, seconds):
        for remaining in range(int(seconds), 0, -1):
            if not self.is_running:
                return
            self.ui(lambda r=remaining: self.lbl_countdown.configure(text=f"Cek berikutnya: {r} dtk"))
            time.sleep(1)

    def run_automation_loop(self):
        try:
            from main import main as run_single_task
        except Exception as exc:
            msg = str(exc)
            print(f"❌ Gagal mengimpor main.py: {msg}")
            self.is_running = False
            self.ui(lambda: self._set_automation_ui("stopped"))
            self.ui(lambda: self.toast(f"Gagal mengimpor main.py: {msg}", "error", duration=7000))
            return

        while self.is_running:
            cfg = dict(self.settings)
            mode = UPLOAD_MODES.get(cfg.get("upload_mode"), "draft")
            interval = max(5, int(cfg.get("interval", 30)))
            retries = max(1, int(cfg.get("retries", 3)))

            print(f"\n🚀 Mengecek Google Sheets (mode: {mode})...")
            for attempt in range(1, retries + 1):
                if not self.is_running:
                    break
                try:
                    run_single_task(mode=mode)
                    break
                except Exception as exc:
                    print(f"❌ Execution Error (percobaan {attempt}/{retries}): {exc}")
                    if cfg.get("log_level") == "Debug":
                        print(traceback.format_exc())
                    if attempt < retries:
                        self._interruptible_sleep(min(5 * attempt, 20))

            # Satu kali refresh: semua kartu/tabel ikut terbarui. Toast + catatan grafik
            # otomatis muncul jika jumlah video 'Ready for Review' bertambah.
            self.ui(lambda: self.load_rows(force=True))

            print(f"💤 Menunggu {interval} detik sebelum pengecekan berikutnya...")
            self._interruptible_sleep(interval)

        print("⏹️ Automation loop berhenti.")
        self.ui(lambda: self._set_automation_ui("stopped"))


# ============================================================
# RUN APPLICATION
# ============================================================
if __name__ == "__main__":
    app = ShortsAutoBotApp()
    app.mainloop()