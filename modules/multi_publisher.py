"""
modules/multi_publisher.py
==========================
CrossByte — Multi-Publisher Agent (satu-satunya mesin publish di project ini).

Dipakai dua jalur yang sebelumnya berjalan sendiri-sendiri (dan itu sumber bug):
  * main.py  -> mode 'auto'  : publish setelah render selesai
  * server.py-> /api/video/publish : publish manual dari Video Studio
Sekarang keduanya lewat fungsi yang sama, jadi perilaku & log-nya identik.

Yang diperbaiki dibanding versi lama
------------------------------------
1. Import modul tidak lagi bikin server gagal start: `youtube_uploader` / `social_real`
   yang error ditandai, platform terkait dilaporkan "tidak siap" (bukan crash).
2. Progress tidak lagi melompat: tiap platform dapat porsi 100/n, dan ada callback
   per-platform terpisah (`platform_progress_callback`) untuk UI multi-bar.
3. Platform yang belum terhubung dilewati dengan alasan yang jelas
   (`skipped=True, reason=...`) — bukan dicatat sebagai "gagal" misterius.
4. Metadata per-platform: YouTube pakai SEO builder; TikTok/IG/FB pakai caption
   builder-nya `social_real`, dan bisa di-override per platform lewat `captions`.
5. Gagal di satu platform tidak menggagalkan platform lain, dan SEMUA hasil
   (termasuk yang dilewati) tetap tercatat ke publish_log.
6. Satu hasil terstruktur + `publish_summary()` (main_url / real_ok / oks / fails)
   sehingga pemanggil tidak perlu menebak-nebak lagi.
7. Metadata YouTube yang dibangun gagal -> fallback sederhana, distribusi tetap jalan.
8. Terintegrasi dengan `row_platforms`: tiap baris Content Planner punya target
   publish sendiri (`publish_for_row`).
"""
import os

# --- konektor platform (opsional: kegagalan import tidak boleh membunuh server) ---
try:
    from modules import youtube_uploader as yt
except Exception as _exc:                                     # noqa: BLE001
    yt = None
    print(f"⚠️ CrossByte: modules/youtube_uploader tidak bisa dimuat: {_exc}")

try:
    from modules import social_real as social
except Exception as _exc:                                     # noqa: BLE001
    social = None
    print(f"⚠️ CrossByte: modules/social_real tidak bisa dimuat: {_exc}")

try:
    from modules import row_platforms
except Exception:                                             # noqa: BLE001
    row_platforms = None

try:
    from modules.data_analyst import load_bias
except Exception:                                             # noqa: BLE001
    def load_bias():
        return {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Fallback metadata platform kalau social_real tidak termuat (tetap bisa lapor status)
_FALLBACK_META = {
    "youtube": {"label": "YouTube Shorts", "icon": "fi-brands-youtube", "color": "#FF0000", "dummy": False},
    "tiktok": {"label": "TikTok", "icon": "fi-brands-tiktok", "color": "#000000", "dummy": True},
    "instagram": {"label": "Instagram Reels", "icon": "fi-brands-instagram", "color": "#C13584", "dummy": True},
    "facebook": {"label": "Facebook Reels", "icon": "fi-brands-facebook", "color": "#1877F2", "dummy": True},
}
DEFAULT_PLATFORM = "youtube"


# ------------------------------------------------------------------ helper
def platform_meta(pid):
    """Metadata tampilan sebuah platform (label/ikon/warna/dummy)."""
    pid = str(pid or "").lower().strip()
    if social is not None and pid in getattr(social, "PLATFORMS", {}):
        return dict(social.PLATFORMS[pid])
    if pid == "youtube":
        return dict(_FALLBACK_META["youtube"])
    return dict(_FALLBACK_META.get(pid, {"label": pid or "?", "icon": "fi-rr-share", "color": "#6B7280", "dummy": True}))


def platform_label(pid):
    return platform_meta(pid).get("label", str(pid))


def _is_dummy(pid):
    return bool(platform_meta(pid).get("dummy"))


def _youtube_ready():
    if yt is None:
        return False, "modules/youtube_uploader.py tidak bisa dimuat."
    if os.path.exists(os.path.join(BASE_DIR, "token.pickle")):
        return True, ""
    if os.path.exists(os.path.join(BASE_DIR, "client_secret.json")):
        return True, ""          # login interaktif akan dibuka saat upload pertama
    return False, "client_secret.json tidak ditemukan di folder project."


def platform_state(pid, accounts=None):
    """(ready, reason) — dipakai sebelum upload supaya errornya jelas, bukan menebak."""
    pid = str(pid or "").lower().strip()
    if pid == DEFAULT_PLATFORM:
        return _youtube_ready()
    if social is None:
        return False, "modules/social_real.py tidak bisa dimuat."
    if pid not in getattr(social, "PLATFORMS", {}):
        return False, f"Platform '{pid}' tidak dikenal CrossByte."
    try:
        accs = accounts if accounts is not None else (social.get_accounts() or {})
    except Exception as exc:                                  # noqa: BLE001
        return False, f"Status akun {platform_label(pid)} tidak bisa dibaca: {exc}"
    if not accs.get(pid):
        try:
            hint = social.config_hint(pid)
        except Exception:                                     # noqa: BLE001
            hint = ""
        return False, (f"{platform_label(pid)} belum terhubung." + (f" {hint}" if hint else " Hubungkan dulu di menu Akun."))
    return True, ""


def _apply_metrix_bias(tags):
    """Agent Metrix: selipkan keyword yang terbukti laku ke tag YouTube/CrossByte."""
    try:
        keywords = (load_bias() or {}).get("winning_keywords") or []
    except Exception:                                         # noqa: BLE001
        keywords = []
    if not keywords:
        return list(tags or [])
    low = [str(t).lower() for t in (tags or [])]
    added = [kw for kw in keywords if str(kw).lower() not in low]
    if added:
        print(f"🎯 Metrix: menambahkan {len(added)} keyword terbukti laku ke tag CrossByte: {added}")
    return (list(tags or []) + added)[:15]


def _youtube_metadata(topic, niche, hook_style, channel_name, title=None, description=None,
                      tags=None, disclose_ai=True, variant=0):
    """Metadata final untuk YouTube. Kalau UI sudah mengirim judul/deskripsi/tag hasil
    edit user, itu yang dipakai (jangan ditimpa otomatis)."""
    if title:
        return {"title": title, "description": description or "", "tags": list(tags or [])}
    if yt is None:
        raise RuntimeError("modules/youtube_uploader.py tidak bisa dimuat — metadata tidak bisa dibuat.")
    meta = yt.build_seo_metadata(topic=topic, niche=niche, hook=hook_style, channel_name=channel_name,
                                 variant=variant, disclose_ai=disclose_ai)
    meta = dict(meta or {})
    meta["tags"] = _apply_metrix_bias(list(meta.get("tags") or []))
    return meta


def _fallback_metadata(topic, niche, hook_style):
    clean = "".join(ch for ch in (niche or "Fakta") if ch.isalnum()) or "Fakta"
    return {
        "title": (topic or "Fakta Unik")[:100],
        "description": f"{(hook_style or 'Simak fakta menarik ini.')} {topic or ''}\n\n#{clean} #Shorts",
        "tags": [clean.lower(), "shorts"],
    }


def _log_publish(row_idx, pid, info):
    if social is None or row_idx is None:
        return
    try:
        social.log_publish(row_idx, pid, info)
    except Exception as exc:                                  # noqa: BLE001
        print(f"⚠️ CrossByte: riwayat publish {platform_label(pid)} gagal dicatat: {exc}")


def publish_summary(results):
    """Ringkas hasil publish: main_url, real_ok, oks, fails, skipped.

    real_ok = minimal satu platform NON-dummy sukses (yaitu benar-benar tayang).
    """
    results = results or {}
    oks = [p for p, r in results.items() if r.get("ok")]
    fails = [p for p, r in results.items() if r.get("ok") is False and not r.get("skipped")]
    skipped = [p for p, r in results.items() if r.get("skipped")]
    real_ok = any(not _is_dummy(p) for p in oks)

    main_url = None
    if "youtube" in oks and results["youtube"].get("url"):
        main_url = results["youtube"]["url"]
    if main_url is None:
        main_url = next((results[p].get("url") for p in oks if not _is_dummy(p) and results[p].get("url")), None)
    if main_url is None:
        main_url = next((results[p].get("url") for p in oks if results[p].get("url")), None)
    return {"main_url": main_url, "real_ok": real_ok, "oks": oks, "fails": fails, "skipped": skipped}


# ------------------------------------------------------------------ engine
def publish_to_platforms(
    video_path,
    topic,
    niche="",
    hook_style="",
    script_text="",
    platforms=None,
    row_idx=None,
    channel_name="MorbMyth",
    privacy_status="public",
    publish_at=None,
    progress_callback=None,          # (pct) 0-100 untuk SELURUH proses
    platform_progress_callback=None, # (pid, pct) 0-100 per platform (untuk UI multi-bar)
    captions=None,                   # override caption per platform: {"tiktok": "..."}
    title=None, description=None, tags=None,
    category_id=None,
    synthetic_media=True,
    notify_subscribers=False,
    skip_unconnected=True,
    variant=0,
    disclose_ai=True,
):
    """Distribusikan satu video ke banyak platform.

    Return {pid: {"ok", "url", "post_id", "label", "dummy", "type", "error"/"reason", "skipped"}}.
    """
    print(f"🌐 CrossByte: memulai distribusi multi-platform untuk topik '{topic}'...")

    platforms = [str(p).lower().strip() for p in (platforms or [DEFAULT_PLATFORM])]
    platforms = list(dict.fromkeys(platforms))
    captions = captions or {}
    total = len(platforms)

    # --- metadata dasar (YouTube) ---
    try:
        meta = _youtube_metadata(topic, niche, hook_style, channel_name, title=title,
                                 description=description, tags=tags,
                                 disclose_ai=disclose_ai, variant=variant)
    except Exception as exc:                                  # noqa: BLE001
        print(f"⚠️ CrossByte: pembuat metadata gagal ({exc}) — memakai metadata darurat.")
        meta = _fallback_metadata(topic, niche, hook_style)

    if category_id is None and yt is not None:
        try:
            category_id = yt.CATEGORIES.get(yt.DEFAULT_CATEGORY_NAME, "27")
        except Exception:                                     # noqa: BLE001
            category_id = "27"

    accounts = None
    if social is not None:
        try:
            accounts = social.get_accounts() or {}
        except Exception:                                     # noqa: BLE001
            accounts = {}

    results = {}

    def emit(idx, pid, pct):
        pct = max(0, min(100, int(pct or 0)))
        if platform_progress_callback:
            try:
                platform_progress_callback(pid, pct)
            except Exception:                                 # noqa: BLE001
                pass
        if progress_callback:
            try:
                progress_callback(int(((idx - 1) + pct / 100.0) / max(1, total) * 100))
            except Exception:                                 # noqa: BLE001
                pass

    for idx, pid in enumerate(platforms, start=1):
        info = {"ok": False, "url": None, "post_id": None, "label": platform_label(pid),
                "dummy": _is_dummy(pid), "skipped": False, "error": None}
        print(f"🚀 [{idx}/{total}] CrossByte memproses platform: {info['label']}")

        ready, reason = platform_state(pid, accounts)
        if not ready:
            if skip_unconnected:
                info.update(skipped=True, error=reason, type="skipped")
                print(f"⏭️ {info['label']} dilewati — {reason}")
                results[pid] = info
                _log_publish(row_idx, pid, {"ok": False, "error": reason, "skipped": True, "title": title or meta.get("title", "")})
                emit(idx, pid, 100)
                continue
            print(f"⚠️ {info['label']}: {reason} (tetap dicoba karena skip_unconnected=False)")

        try:
            if pid == DEFAULT_PLATFORM:
                url = yt.upload_video_to_youtube(
                    video_path=video_path,
                    title=meta["title"],
                    description=meta.get("description", ""),
                    tags=meta.get("tags", []),
                    category_id=category_id or "27",
                    privacy_status=privacy_status,
                    publish_at=publish_at,
                    synthetic_media=synthetic_media,
                    notify_subscribers=notify_subscribers,
                    progress_callback=lambda p, _i=idx, _p=pid: emit(_i, _p, p),
                )
                info.update(ok=True, url=url, type="real")
                print(f"✅ YouTube Shorts berhasil terpublikasi: {url}")

            else:
                override = (captions.get(pid) or "").strip()
                caption = override or social.build_caption(pid=pid, title=meta["title"],
                                                           description=meta.get("description", ""),
                                                           tags=meta.get("tags", []))
                res = social.upload(pid=pid, video_path=video_path, caption=caption,
                                    privacy=privacy_status, publish_at=publish_at,
                                    progress_callback=lambda p, _i=idx, _p=pid: emit(_i, _p, p))
                info.update(ok=True, url=(res or {}).get("url"), post_id=(res or {}).get("id"),
                            type="real" if not _is_dummy(pid) else "dummy")
                print(f"✅ {info['label']} berhasil terpublikasi: {info['url']}")

        except Exception as exc:                              # noqa: BLE001
            err = str(exc)
            info.update(ok=False, error=err, type="error")
            print(f"❌ Gagal publish ke {info['label']}: {err}")

        results[pid] = info
        _log_publish(row_idx, pid, {"ok": info["ok"], "url": info.get("url"),
                                    "post_id": info.get("post_id"), "error": info.get("error"),
                                    "title": meta.get("title", "")})
        emit(idx, pid, 100)

    s = publish_summary(results)
    print(f"🌐 CrossByte selesai: {len(s['oks'])} sukses, {len(s['fails'])} gagal, {len(s['skipped'])} dilewati.")
    return results


def publish_for_row(row, video_path, script_text="", default_platforms=None, **kw):
    """Publish satu baris Content Planner ke platform milik baris itu sendiri.

    row boleh berupa dict baris (punya 'id' & 'platforms') atau id baris saja.
    """
    if isinstance(row, dict):
        row_id = row.get("id")
        row_plats = row.get("platforms")
        topic = kw.pop("topic", None) or row.get("topic", "")
        niche = kw.pop("niche", None) or row.get("niche", "")
        hook_style = kw.pop("hook_style", None) or row.get("hook_style") or row.get("hook", "")
    else:
        row_id, row_plats, topic = row, None, kw.pop("topic", "")
        niche, hook_style = kw.pop("niche", ""), kw.pop("hook_style", "")

    if row_platforms is not None:
        platforms = row_platforms.resolve(row_id, row_plats, default_platforms)
    else:
        platforms = list(row_plats) if row_plats else (default_platforms or [DEFAULT_PLATFORM])

    print(f"🎯 Baris #{row_id}: target publish → {', '.join(platform_label(p) for p in platforms)}")
    results = publish_to_platforms(video_path=video_path, topic=topic, niche=niche,
                                   hook_style=hook_style, script_text=script_text,
                                   platforms=platforms, row_idx=row_id, **kw)
    summary = publish_summary(results)
    summary["results"] = results
    summary["platforms"] = platforms
    return summary
