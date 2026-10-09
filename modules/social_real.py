"""
modules/social_real.py
======================
Konektor ASLI untuk TikTok, Instagram Reels, dan Facebook Reels.
Antarmuka sama dengan social_dummy.py (PLATFORMS, get_accounts, upload, ...),
jadi server.py / main.py / multi_publisher.py cukup ganti nama import.

Kredensial (.env):
    TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET
    META_APP_ID, META_APP_SECRET            (satu app Meta untuk Instagram + Facebook)
    OAUTH_REDIRECT_BASE                     (default http://localhost:8000)
Opsional:
    TIKTOK_SCOPES      default "user.info.basic,video.publish,video.upload"
    TIKTOK_POST_MODE   "direct" (default) atau "inbox" (masuk draft TikTok, dipublish manual)
    META_PAGE_ID       pilih Page tertentu bila akun punya banyak Page
    GRAPH_API_VERSION  default v26.0

File data (jangan di-commit, masukkan ke .gitignore):
    social_accounts.json  info publik akun (username)
    social_tokens.json    access/refresh token
"""
import datetime
import json
import os
import secrets
import threading
import time
import urllib.parse

import requests

from modules import social_dummy as _base   # pakai ulang build_caption & riwayat publish

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "social_accounts.json")
TOKENS_FILE = os.path.join(BASE_DIR, "social_tokens.json")
_lock = threading.Lock()
_states = {}          # state OAuth -> {"pid":..., "ts":...}
TIMEOUT = 60

PLATFORMS = {
    "youtube": dict(_base.PLATFORMS["youtube"]),
    "tiktok": {**_base.PLATFORMS["tiktok"], "dummy": False},
    "instagram": {**_base.PLATFORMS["instagram"], "dummy": False},
    "facebook": {**_base.PLATFORMS["facebook"], "dummy": False},
}
REAL_IDS = ["tiktok", "instagram", "facebook"]
PROVIDER = {"tiktok": "tiktok", "instagram": "meta", "facebook": "meta"}

build_caption = _base.build_caption
log_publish = _base.log_publish
get_publish_log = _base.get_publish_log


# ------------------------------------------------------------------ config
def _env(name, default=""):
    return (os.environ.get(name) or default).strip()


def _graph():
    return f"https://graph.facebook.com/{_env('GRAPH_API_VERSION', 'v26.0')}"


def _gv():
    return _env("GRAPH_API_VERSION", "v26.0")


def redirect_uri(provider):
    base = _env("OAUTH_REDIRECT_BASE", f"http://localhost:{_env('SERVER_PORT', '8000')}").rstrip("/")
    return f"{base}/api/oauth/{provider}/callback"


def missing_config(pid):
    keys = ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"] if pid == "tiktok" else ["META_APP_ID", "META_APP_SECRET"]
    return [k for k in keys if not _env(k)]


def config_hint(pid):
    miss = missing_config(pid)
    if miss:
        return "Isi dulu di .env: " + ", ".join(miss)
    return "Belum terhubung. Klik Hubungkan untuk login."


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
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def get_accounts():
    """Hanya akun asli (record dummy lama diabaikan). Tanpa token."""
    with _lock:
        acc = _load(ACCOUNTS_FILE, {})
    return {k: v for k, v in acc.items() if k in REAL_IDS and not v.get("dummy")}


def is_connected(pid):
    return pid in get_accounts()


def _tokens(pid):
    with _lock:
        return _load(TOKENS_FILE, {}).get(pid) or {}


def _store(pid, username, tokens):
    with _lock:
        acc = _load(ACCOUNTS_FILE, {})
        acc[pid] = {"username": username, "connected_at": time.strftime("%Y-%m-%d %H:%M:%S"), "dummy": False}
        _save(ACCOUNTS_FILE, acc)
        tk = _load(TOKENS_FILE, {})
        tk[pid] = tokens
        _save(TOKENS_FILE, tk)


def connect(pid, username=None):
    raise ValueError("Akun asli dihubungkan lewat login OAuth (tombol Hubungkan), bukan username.")


def disconnect(pid):
    with _lock:
        acc = _load(ACCOUNTS_FILE, {})
        if pid not in acc:
            raise ValueError("Akun belum terhubung.")
        acc.pop(pid)
        _save(ACCOUNTS_FILE, acc)
        tk = _load(TOKENS_FILE, {})
        tk.pop(pid, None)
        _save(TOKENS_FILE, tk)


# ------------------------------------------------------------------ http helpers
def _json(resp, what):
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"{what}: respons bukan JSON (HTTP {resp.status_code}) {resp.text[:200]}")
    return data


def _meta_check(resp, what):
    data = _json(resp, what)
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        msg = err.get("message") if isinstance(err, dict) else str(err)
        code = err.get("code") if isinstance(err, dict) else ""
        raise RuntimeError(f"{what} gagal (HTTP {resp.status_code}, kode {code}): {msg}")
    return data


def _tt_check(resp, what):
    data = _json(resp, what)
    err = data.get("error")
    if isinstance(err, dict):
        if err.get("code") not in (None, "ok"):
            raise RuntimeError(f"{what} gagal: {err.get('code')} — {err.get('message')}")
    elif err:                                   # endpoint OAuth: {"error": "...", "error_description": "..."}
        raise RuntimeError(f"{what} gagal: {err} — {data.get('error_description', '')}")
    if resp.status_code >= 400:
        raise RuntimeError(f"{what} gagal (HTTP {resp.status_code}) {resp.text[:200]}")
    return data


def _to_epoch(publish_at):
    if not publish_at:
        return None
    if isinstance(publish_at, (int, float)):
        return int(publish_at)
    if isinstance(publish_at, datetime.datetime):
        dt = publish_at
    else:
        dt = datetime.datetime.fromisoformat(str(publish_at).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return int(dt.timestamp())


# ------------------------------------------------------------------ OAuth
def auth_url(pid):
    """URL login OAuth untuk platform pid (tiktok / instagram / facebook)."""
    if pid not in REAL_IDS:
        raise ValueError(f"Platform '{pid}' tidak dikenal.")
    miss = missing_config(pid)
    if miss:
        raise ValueError("Kredensial belum diisi di .env: " + ", ".join(miss))
    state = secrets.token_urlsafe(24)
    now = time.time()
    for k in [k for k, v in _states.items() if now - v["ts"] > 900]:
        _states.pop(k, None)
    _states[state] = {"pid": pid, "ts": now}

    if pid == "tiktok":
        q = {"client_key": _env("TIKTOK_CLIENT_KEY"),
             "scope": _env("TIKTOK_SCOPES", "user.info.basic,video.publish,video.upload"),
             "response_type": "code", "redirect_uri": redirect_uri("tiktok"), "state": state}
        return "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(q)

    q = {"client_id": _env("META_APP_ID"), "redirect_uri": redirect_uri("meta"), "state": state,
         "response_type": "code",
         "scope": "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"}
    return f"https://www.facebook.com/{_gv()}/dialog/oauth?" + urllib.parse.urlencode(q)


def handle_callback(provider, code, state):
    """Tukar code -> token, simpan akun. Return list pid yang berhasil terhubung."""
    st = _states.pop(state, None)
    if not st or time.time() - st["ts"] > 900:
        raise RuntimeError("State OAuth tidak valid / kedaluwarsa. Ulangi dari tombol Hubungkan.")
    if PROVIDER.get(st["pid"]) != provider:
        raise RuntimeError("State OAuth tidak cocok dengan provider.")
    return _tiktok_callback(code) if provider == "tiktok" else _meta_callback(code)


def _tiktok_token_request(payload):
    r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data=payload, timeout=TIMEOUT,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    return _tt_check(r, "TikTok token")


def _tiktok_pack(d, old=None):
    now = int(time.time())
    return {"access_token": d["access_token"], "refresh_token": d.get("refresh_token") or (old or {}).get("refresh_token"),
            "open_id": d.get("open_id") or (old or {}).get("open_id"),
            "expires_at": now + int(d.get("expires_in", 86400)),
            "refresh_expires_at": now + int(d.get("refresh_expires_in", 31536000)),
            "scope": d.get("scope", "")}


def _tiktok_callback(code):
    d = _tiktok_token_request({
        "client_key": _env("TIKTOK_CLIENT_KEY"), "client_secret": _env("TIKTOK_CLIENT_SECRET"),
        "code": urllib.parse.unquote(code), "grant_type": "authorization_code",
        "redirect_uri": redirect_uri("tiktok")})
    tokens = _tiktok_pack(d)
    name = "akun TikTok"
    try:
        r = requests.get("https://open.tiktokapis.com/v2/user/info/", timeout=TIMEOUT,
                         params={"fields": "open_id,display_name"},
                         headers={"Authorization": f"Bearer {tokens['access_token']}"})
        name = _tt_check(r, "TikTok user info")["data"]["user"].get("display_name") or name
    except Exception as exc:
        print(f"⚠️ TikTok: nama akun tidak terbaca ({exc})")
    _store("tiktok", name, tokens)
    return ["tiktok"]


def _tiktok_access():
    tk = _tokens("tiktok")
    if not tk:
        raise RuntimeError("TikTok belum terhubung (menu Akun).")
    if tk.get("expires_at", 0) - 300 > time.time():
        return tk["access_token"]
    if tk.get("refresh_expires_at", 0) < time.time() or not tk.get("refresh_token"):
        raise RuntimeError("Token TikTok kedaluwarsa. Hubungkan ulang akun TikTok.")
    d = _tiktok_token_request({
        "client_key": _env("TIKTOK_CLIENT_KEY"), "client_secret": _env("TIKTOK_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": tk["refresh_token"]})
    new = _tiktok_pack(d, old=tk)
    acc = get_accounts().get("tiktok", {})
    _store("tiktok", acc.get("username", "akun TikTok"), new)
    return new["access_token"]


def _meta_callback(code):
    g, app_id, secret = _graph(), _env("META_APP_ID"), _env("META_APP_SECRET")
    r = requests.get(f"{g}/oauth/access_token", timeout=TIMEOUT, params={
        "client_id": app_id, "client_secret": secret, "redirect_uri": redirect_uri("meta"), "code": code})
    short = _meta_check(r, "Meta token")["access_token"]
    r = requests.get(f"{g}/oauth/access_token", timeout=TIMEOUT, params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": secret,
        "fb_exchange_token": short})
    long_user = _meta_check(r, "Meta long-lived token")["access_token"]

    r = requests.get(f"{g}/me/accounts", timeout=TIMEOUT, params={
        "fields": "id,name,access_token,instagram_business_account{id,username}",
        "limit": 100, "access_token": long_user})
    pages = _meta_check(r, "Meta daftar Page").get("data", [])
    if not pages:
        raise RuntimeError("Tidak ada Facebook Page di akun ini. Buat/kelola Page dulu, lalu ulangi.")
    want = _env("META_PAGE_ID")
    page = next((p for p in pages if p["id"] == want), None) if want else None
    page = page or next((p for p in pages if p.get("instagram_business_account")), pages[0])

    connected = []
    _store("facebook", page["name"], {"page_id": page["id"], "page_token": page["access_token"]})
    connected.append("facebook")
    ig = page.get("instagram_business_account")
    if ig:
        _store("instagram", ig.get("username") or page["name"],
               {"ig_user_id": ig["id"], "page_token": page["access_token"]})
        connected.append("instagram")
    else:
        print("⚠️ Instagram: Page ini belum tertaut ke akun IG Business/Creator — Instagram tidak terhubung.")
    return connected


# ------------------------------------------------------------------ upload: TikTok
_TT = "https://open.tiktokapis.com/v2/post/publish"
_MB = 1024 * 1024


def _upload_tiktok(path, caption, privacy, publish_at, cb):
    if publish_at:
        raise ValueError("TikTok API tidak mendukung jadwal tayang. Kosongkan jadwal untuk TikTok.")
    token = _tiktok_access()
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    size = os.path.getsize(path)
    chunk = size if size <= 64 * _MB else 32 * _MB
    total = max(1, size // chunk)               # chunk terakhir menyerap sisa
    source = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": total}
    mode = _env("TIKTOK_POST_MODE", "direct").lower()

    note = ""
    if mode == "inbox":
        body, url = {"source_info": source}, f"{_TT}/inbox/video/init/"
        note = "Masuk draft/inbox TikTok — buka app TikTok untuk menyelesaikan & publish."
    else:
        ci = _tt_check(requests.post(f"{_TT}/creator_info/query/", headers=H, json={}, timeout=TIMEOUT),
                       "TikTok creator info")["data"]
        opts = ci.get("privacy_level_options") or ["SELF_ONLY"]
        wanted = "PUBLIC_TO_EVERYONE" if str(privacy).lower() == "public" else "SELF_ONLY"
        level = wanted if wanted in opts else ("SELF_ONLY" if "SELF_ONLY" in opts else opts[0])
        if level != wanted:
            note = f"Privasi diturunkan ke {level} (opsi yang diizinkan TikTok: {', '.join(opts)})."
        limit = ci.get("max_video_post_duration_sec")
        if limit:
            print(f"ℹ️ TikTok: batas durasi akun ini {limit} detik.")
        body = {"post_info": {"title": caption[:2200], "privacy_level": level, "disable_duet": False,
                              "disable_comment": False, "disable_stitch": False, "is_aigc": True},
                "source_info": source}
        url = f"{_TT}/video/init/"

    init = _tt_check(requests.post(url, headers=H, json=body, timeout=TIMEOUT), "TikTok init")["data"]
    publish_id, upload_url = init["publish_id"], init["upload_url"]

    with open(path, "rb") as f:
        for i in range(total):
            start = i * chunk
            end = size - 1 if i == total - 1 else start + chunk - 1
            data = f.read(end - start + 1)
            r = requests.put(upload_url, data=data, timeout=300, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(f"TikTok upload chunk {i + 1}/{total} gagal (HTTP {r.status_code}): {r.text[:200]}")
            if cb:
                cb(int((i + 1) / total * 90))

    post_id = None
    deadline = time.time() + 240
    while time.time() < deadline:
        d = _tt_check(requests.post(f"{_TT}/status/fetch/", headers=H, json={"publish_id": publish_id},
                                    timeout=TIMEOUT), "TikTok status")["data"]
        st = d.get("status")
        if st == "FAILED":
            raise RuntimeError(f"TikTok menolak video: {d.get('fail_reason', 'unknown')}")
        if st in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            ids = d.get("publicaly_available_post_id") or d.get("publicly_available_post_id") or []
            post_id = ids[0] if ids else None
            break
        time.sleep(4)
    else:
        note = (note + " " if note else "") + "Status akhir belum terkonfirmasi (masih diproses TikTok)."
    if cb:
        cb(100)
    if mode != "inbox" and not post_id:
        note = (note + " " if note else "") + (
            "Post belum punya ID publik. Jika app belum lolos audit TikTok, semua post otomatis PRIVATE.")
    link = f"https://www.tiktok.com/video/{post_id}" if post_id else "https://www.tiktok.com/tiktokstudio"
    return {"id": post_id or publish_id, "url": link, "dummy": False, "note": note.strip()}


# ------------------------------------------------------------------ upload: Instagram
def _upload_instagram(path, caption, privacy, publish_at, cb):
    if publish_at:
        raise ValueError("Instagram Reels API tidak mendukung jadwal tayang. Kosongkan jadwal untuk Instagram.")
    tk = _tokens("instagram")
    if not tk:
        raise RuntimeError("Instagram belum terhubung (menu Akun).")
    g, tok, ig = _graph(), tk["page_token"], tk["ig_user_id"]
    size = os.path.getsize(path)

    r = requests.post(f"{g}/{ig}/media", timeout=TIMEOUT, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption[:2200],
        "share_to_feed": "true", "access_token": tok})
    d = _meta_check(r, "Instagram buat container")
    cid = d["id"]
    uri = d.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{_gv()}/{cid}"
    if cb:
        cb(10)

    with open(path, "rb") as f:
        r = requests.post(uri, data=f, timeout=600, headers={
            "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)})
    _meta_check(r, "Instagram upload video")
    if cb:
        cb(60)

    deadline = time.time() + 300
    while time.time() < deadline:
        s = _meta_check(requests.get(f"{g}/{cid}", timeout=TIMEOUT, params={
            "fields": "status_code,status", "access_token": tok}), "Instagram status")
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram menolak video ({code}): {s.get('status', '')}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram: pemrosesan video melebihi 5 menit.")
    if cb:
        cb(85)

    pub = _meta_check(requests.post(f"{g}/{ig}/media_publish", timeout=TIMEOUT, data={
        "creation_id": cid, "access_token": tok}), "Instagram publish")
    media_id = pub["id"]
    link = f"https://www.instagram.com/reel/{media_id}/"
    try:
        link = _meta_check(requests.get(f"{g}/{media_id}", timeout=TIMEOUT, params={
            "fields": "permalink", "access_token": tok}), "Instagram permalink").get("permalink", link)
    except Exception:
        pass
    if cb:
        cb(100)
    return {"id": media_id, "url": link, "dummy": False}


# ------------------------------------------------------------------ upload: Facebook
def _upload_facebook(path, caption, privacy, publish_at, cb):
    tk = _tokens("facebook")
    if not tk:
        raise RuntimeError("Facebook belum terhubung (menu Akun).")
    g, tok, page = _graph(), tk["page_token"], tk["page_id"]
    size = os.path.getsize(path)

    d = _meta_check(requests.post(f"{g}/{page}/video_reels", timeout=TIMEOUT, data={
        "upload_phase": "start", "access_token": tok}), "Facebook mulai sesi")
    vid, upload_url = d["video_id"], d["upload_url"]
    if cb:
        cb(10)

    with open(path, "rb") as f:
        r = requests.post(upload_url, data=f, timeout=600, headers={
            "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)})
    _meta_check(r, "Facebook upload video")
    if cb:
        cb(65)

    fin = {"upload_phase": "finish", "video_id": vid, "description": caption[:2200], "access_token": tok}
    epoch = _to_epoch(publish_at)
    if epoch:
        fin.update(video_state="SCHEDULED", scheduled_publish_time=str(epoch))
    else:
        fin["video_state"] = "PUBLISHED"
    _meta_check(requests.post(f"{g}/{page}/video_reels", timeout=TIMEOUT, data=fin), "Facebook publish")

    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            s = _meta_check(requests.get(f"{g}/{vid}", timeout=TIMEOUT, params={
                "fields": "status", "access_token": tok}), "Facebook status").get("status", {})
        except Exception:
            break
        vs = s.get("video_status")
        if vs in ("ready", "published", "scheduled"):
            break
        if vs == "error":
            raise RuntimeError(f"Facebook menolak video: {json.dumps(s, ensure_ascii=False)[:200]}")
        time.sleep(4)
    if cb:
        cb(100)
    return {"id": vid, "url": f"https://www.facebook.com/reel/{vid}", "dummy": False, "scheduled": bool(epoch)}


# ------------------------------------------------------------------ entry point
_UPLOADERS = {"tiktok": _upload_tiktok, "instagram": _upload_instagram, "facebook": _upload_facebook}


def upload(pid, video_path, caption, privacy="public", publish_at=None, progress_callback=None):
    """Upload asli. Return dict {id, url, dummy: False, ...}. Raise Exception bila gagal."""
    if pid not in _UPLOADERS:
        raise ValueError(f"Platform '{pid}' tidak didukung oleh konektor ini.")
    if not is_connected(pid):
        raise RuntimeError(f"Akun {PLATFORMS[pid]['label']} belum terhubung (menu Akun).")
    if not video_path or not os.path.isfile(video_path):
        raise FileNotFoundError(f"File video tidak ditemukan: {video_path}")
    if not (caption or "").strip():
        raise ValueError("Caption kosong.")
    print(f"📤 Upload ke {PLATFORMS[pid]['label']} (@{get_accounts()[pid]['username']})...")
    res = _UPLOADERS[pid](video_path, caption, privacy, publish_at, progress_callback)
    res["caption_len"] = len(caption)
    if res.get("note"):
        print(f"ℹ️ {PLATFORMS[pid]['label']}: {res['note']}")
    return res