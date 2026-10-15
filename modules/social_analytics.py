"""
modules/social_analytics.py
============================
Statistik TikTok / Instagram Reels / Facebook Reels untuk Metrix (data_analyst.py).

Prinsip:
- Selalu coba data ASLI dulu lewat API resmi tiap platform.
- Dummy HANYA dipakai per-platform, dan HANYA ketika API menolak karena platform itu
  masih dalam mode Development/Review (izin/scope belum disetujui) — bukan karena
  video tertentu error. Setiap angka dummy diberi label jelas: is_real_data=False, mode="dev".
- Status terakhir tiap platform (live/dev/error) disimpan ke social_analytics_status.json
  supaya UI bisa menampilkan badge tanpa menunggu run berikutnya.

TikTok  : Display API `video/list/` (scope video.list) — statistik video milik akun sendiri.
Instagram: Graph API field like_count/comments_count (instagram_basic) + insights (opsional,
           butuh instagram_manage_insights; kalau ditolak, field dasar tetap dipakai sebagai data asli).
Facebook: Graph API field likes/comments pada video + video_insights (opsional, butuh read_insights).
"""
import json
import os
import random
import re
import time

import requests

from modules import social_real as social

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_FILE = os.path.join(BASE_DIR, "social_analytics_status.json")
TIMEOUT = 30

PERM_ERROR_HINTS = (
    "scope_not_authorized", "access_token_invalid", "permission", "insufficient",
    "not authorized", "application does not have permission", "(#10)", "(#100)",
)


def _load_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_status(pid, mode, detail=""):
    try:
        data = _load_status()
        data[pid] = {"mode": mode, "detail": detail, "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, STATUS_FILE)
    except OSError:
        pass


def get_status():
    """Status terakhir tiap platform: {pid: {mode, detail, checked_at}}. mode: live|dev|error|unknown."""
    return _load_status()


def _is_permission_error(msg):
    low = str(msg).lower()
    return any(h in low for h in PERM_ERROR_HINTS)


def _dummy_metrics(pid, seed_id):
    """Angka simulasi, stabil per video (seed dari id) supaya tidak melompat tiap refresh."""
    rnd = random.Random(f"{pid}:{seed_id}")
    views = rnd.randint(500, 9000)
    likes = int(views * rnd.uniform(0.03, 0.09))
    comments = int(views * rnd.uniform(0.002, 0.01))
    shares = int(views * rnd.uniform(0.001, 0.02))
    return {"views": views, "likes": likes, "comments": comments, "shares": shares,
            "is_real_data": False, "mode": "dev",
            "note": f"{social.PLATFORMS[pid]['label']} masih mode Development/Review — angka simulasi sementara."}


# ------------------------------------------------------------------ TikTok
def fetch_tiktok_metrics(post_ids):
    """Return {post_id: metrics}. post_ids = TikTok video id numerik (bukan URL)."""
    ids = set(str(x) for x in post_ids if x)
    out = {}
    if not ids:
        return out
    try:
        token = social.tiktok_access_token()
    except Exception as exc:
        for i in ids:
            out[i] = _dummy_metrics("tiktok", i)
        _save_status("tiktok", "dev", f"Belum terhubung: {exc}")
        return out

    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    found = {}
    cursor, has_more, pages = 0, True, 0
    try:
        while has_more and pages < 15 and len(found) < len(ids):
            r = requests.post(
                "https://open.tiktokapis.com/v2/video/list/?fields=id,view_count,like_count,comment_count,share_count",
                headers=H, json={"max_count": 20, "cursor": cursor}, timeout=TIMEOUT)
            data = r.json()
            err = data.get("error") or {}
            if err.get("code") not in (None, "ok"):
                raise RuntimeError(f"{err.get('code')}: {err.get('message')}")
            for v in (data.get("data") or {}).get("videos", []):
                if v.get("id") in ids:
                    found[v["id"]] = v
            d = data.get("data") or {}
            cursor, has_more, pages = d.get("cursor", 0), bool(d.get("has_more")), pages + 1
    except Exception as exc:
        mode = "dev" if _is_permission_error(exc) else "error"
        _save_status("tiktok", mode, str(exc))
        for i in ids:
            if mode == "dev":
                out[i] = _dummy_metrics("tiktok", i)
            else:
                out[i] = {"views": None, "likes": None, "comments": None, "shares": None,
                          "is_real_data": False, "mode": "error", "note": f"Gagal ambil statistik TikTok: {exc}"}
        return out

    _save_status("tiktok", "live")
    for i in ids:
        v = found.get(i)
        if not v:
            out[i] = {"views": None, "likes": None, "comments": None, "shares": None,
                      "is_real_data": False, "mode": "error",
                      "note": "Video tidak ditemukan di daftar akun (mungkin dihapus/private)."}
            continue
        out[i] = {"views": int(v.get("view_count", 0)), "likes": int(v.get("like_count", 0)),
                  "comments": int(v.get("comment_count", 0)), "shares": int(v.get("share_count", 0)),
                  "is_real_data": True, "mode": "live", "note": ""}
    return out


# ------------------------------------------------------------------ Instagram
def fetch_instagram_metrics(media_ids):
    """Return {media_id: metrics}. media_id = ID numerik media IG (bukan shortcode permalink)."""
    ids = [str(x) for x in media_ids if x]
    out = {}
    if not ids:
        return out
    tk = social.get_tokens("instagram")
    if not tk:
        for i in ids:
            out[i] = _dummy_metrics("instagram", i)
        _save_status("instagram", "dev", "Instagram belum terhubung.")
        return out

    g, tok = social.graph_base(), tk["page_token"]
    any_real, any_insight_denied = False, False
    for i in ids:
        try:
            base = requests.get(f"{g}/{i}", timeout=TIMEOUT, params={
                "fields": "like_count,comments_count", "access_token": tok}).json()
            if "error" in base:
                raise RuntimeError(base["error"].get("message", "unknown"))
            likes, comments = int(base.get("like_count", 0) or 0), int(base.get("comments_count", 0) or 0)
            any_real = True
        except Exception as exc:
            mode = "dev" if _is_permission_error(exc) else "error"
            if mode == "dev":
                out[i] = _dummy_metrics("instagram", i)
            else:
                out[i] = {"views": None, "likes": None, "comments": None, "shares": None,
                          "is_real_data": False, "mode": "error", "note": f"Gagal ambil data Instagram: {exc}"}
            continue

        plays = shares = None
        try:
            ins = requests.get(f"{g}/{i}/insights", timeout=TIMEOUT, params={
                "metric": "plays,reach,shares,saved", "access_token": tok}).json()
            if "error" in ins:
                raise RuntimeError(ins["error"].get("message", "unknown"))
            vals = {row["name"]: (row.get("values") or [{}])[0].get("value", 0) for row in ins.get("data", [])}
            plays, shares = vals.get("plays"), vals.get("shares")
        except Exception as exc:
            any_insight_denied = _is_permission_error(exc) or any_insight_denied  # insights opsional, bukan fatal

        out[i] = {"views": plays, "likes": likes, "comments": comments, "shares": shares,
                  "is_real_data": True, "mode": "live",
                  "note": "" if shares is not None else "Insight (views/share) butuh izin instagram_manage_insights — likes & komentar tetap data asli."}

    if any_real:
        _save_status("instagram", "live", "insights terbatas" if any_insight_denied else "")
    return out


# ------------------------------------------------------------------ Facebook
def fetch_facebook_metrics(video_ids):
    """Return {video_id: metrics}."""
    ids = [str(x) for x in video_ids if x]
    out = {}
    if not ids:
        return out
    tk = social.get_tokens("facebook")
    if not tk:
        for i in ids:
            out[i] = _dummy_metrics("facebook", i)
        _save_status("facebook", "dev", "Facebook belum terhubung.")
        return out

    g, tok = social.graph_base(), tk["page_token"]
    any_real, any_insight_denied = False, False
    for i in ids:
        try:
            base = requests.get(f"{g}/{i}", timeout=TIMEOUT, params={
                "fields": "likes.summary(true).limit(0),comments.summary(true).limit(0)",
                "access_token": tok}).json()
            if "error" in base:
                raise RuntimeError(base["error"].get("message", "unknown"))
            likes = int((base.get("likes", {}).get("summary") or {}).get("total_count", 0) or 0)
            comments = int((base.get("comments", {}).get("summary") or {}).get("total_count", 0) or 0)
            any_real = True
        except Exception as exc:
            mode = "dev" if _is_permission_error(exc) else "error"
            if mode == "dev":
                out[i] = _dummy_metrics("facebook", i)
            else:
                out[i] = {"views": None, "likes": None, "comments": None, "shares": None,
                          "is_real_data": False, "mode": "error", "note": f"Gagal ambil data Facebook: {exc}"}
            continue

        plays = shares = None
        try:
            ins = requests.get(f"{g}/{i}/video_insights", timeout=TIMEOUT, params={
                "metric": "post_video_views,post_video_social_actions", "access_token": tok}).json()
            if "error" in ins:
                raise RuntimeError(ins["error"].get("message", "unknown"))
            for row in ins.get("data", []):
                vals = (row.get("values") or [{}])[0].get("value")
                if row.get("name") == "post_video_views":
                    plays = int(vals or 0)
                elif row.get("name") == "post_video_social_actions" and isinstance(vals, dict):
                    shares = int(vals.get("SHARE", 0) or 0)
        except Exception as exc:
            any_insight_denied = _is_permission_error(exc) or any_insight_denied

        out[i] = {"views": plays, "likes": likes, "comments": comments, "shares": shares,
                  "is_real_data": True, "mode": "live",
                  "note": "" if plays is not None else "Insight (views/share) butuh izin read_insights — likes & komentar tetap data asli."}

    if any_real:
        _save_status("facebook", "live", "insights terbatas" if any_insight_denied else "")
    return out


FETCHERS = {"tiktok": fetch_tiktok_metrics, "instagram": fetch_instagram_metrics, "facebook": fetch_facebook_metrics}


# ------------------------------------------------------------------ helper ekstrak ID dari URL hasil publish
_PATTERNS = {
    "tiktok": re.compile(r"tiktok\.com/(?:@[\w.-]+/)?video/(\d+)"),
    "facebook": re.compile(r"facebook\.com/reel/(\d+)"),
    # Instagram SENGAJA tidak di-regex dari permalink: /reel/{shortcode}/ pakai shortcode,
    # bukan ID media Graph API numerik yang dibutuhkan endpoint insights. Shortcode->ID tidak
    # bisa ditebak tanpa panggilan API tambahan, jadi hanya ID numerik tersimpan yang dipakai.
}


def extract_post_id(pid, url_or_id):
    """ID post dari URL hasil publish (fallback utk log lama tanpa post_id tersimpan).
    Hanya berguna utk TikTok & Facebook karena URL-nya memang memuat ID numerik asli.
    Instagram selalu butuh post_id tersimpan langsung — permalink tidak bisa ditebak balik."""
    if not url_or_id:
        return None
    s = str(url_or_id).strip()
    if s.isdigit():
        return s
    m = _PATTERNS.get(pid)
    if m:
        found = m.search(s)
        if found:
            return found.group(1)
    return None


def fetch(pid, ids):
    """Dispatcher: fetch_tiktok_metrics / fetch_instagram_metrics / fetch_facebook_metrics."""
    fn = FETCHERS.get(pid)
    return fn(ids) if fn else {}