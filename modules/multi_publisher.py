import os
import time
from modules import youtube_uploader as yt
from modules import social_real as social

try:
    from modules.data_analyst import load_bias   # Agent Metrix: bias keyword terbukti laku
except Exception:
    def load_bias():
        return {}


def _apply_metrix_bias(tags):
    keywords = (load_bias() or {}).get("winning_keywords") or []
    if not keywords:
        return tags
    low = [t.lower() for t in tags]
    added = [kw for kw in keywords if kw.lower() not in low]
    if added:
        print(f"🎯 Metrix: menambahkan {len(added)} keyword terbukti laku ke tag CrossByte: {added}")
    return (tags + added)[:15]


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
    progress_callback=None
):
    """
    CrossByte (Multi-Publisher Agent):
    Mendistribusikan video ke YouTube Shorts (API Asli) dan platform media sosial 
    lainnya (Dummy/Simulasi).
    """
    print(f"🌐 CrossByte: Memulai proses distribusi multi-platform untuk topik '{topic}'...")

    if not platforms:
        platforms = ["youtube"]

    # 1. Generate Metadata Utama & SEO untuk YouTube
    meta = yt.build_seo_metadata(
        topic=topic,
        niche=niche,
        hook=hook_style,
        channel_name=channel_name,
        variant=0,
        disclose_ai=True
    )
    meta["tags"] = _apply_metrix_bias(list(meta.get("tags") or []))

    results = {}
    total_platforms = len(platforms)

    for idx, pid in enumerate(platforms, start=1):
        pid_lower = pid.lower().strip()
        print(f"🚀 [{idx}/{total_platforms}] Memproses platform: {pid_lower.upper()}")
        
        try:
            if pid_lower == "youtube":
                # Upload Asli ke YouTube Data API
                category_id = yt.CATEGORIES.get(yt.DEFAULT_CATEGORY_NAME, "27")
                url = yt.upload_video_to_youtube(
                    video_path=video_path,
                    title=meta["title"],
                    description=meta["description"],
                    tags=meta["tags"],
                    category_id=category_id,
                    privacy_status=privacy_status,
                    publish_at=publish_at,
                    synthetic_media=True,
                    progress_callback=progress_callback
                )
                results[pid_lower] = {"ok": True, "url": url, "type": "real"}
                print(f"✅ YouTube Shorts berhasil terpublikasi: {url}")

            elif pid_lower in social.PLATFORMS:
                # Upload asli TikTok / Instagram Reels / Facebook Reels
                caption = social.build_caption(
                    pid=pid_lower,
                    title=meta["title"],
                    description=meta["description"],
                    tags=meta["tags"]
                )
                res = social.upload(
                    pid=pid_lower,
                    video_path=video_path,
                    caption=caption,
                    privacy=privacy_status,
                    publish_at=publish_at,
                    progress_callback=progress_callback
                )
                results[pid_lower] = {"ok": True, "url": res["url"], "type": "real"}
                print(f"✅ {social.PLATFORMS[pid_lower]['label']} berhasil terpublikasi: {res['url']}")

            else:
                err_msg = f"Platform '{pid_lower}' tidak dikenal."
                print(f"⚠️ {err_msg}")
                results[pid_lower] = {"ok": False, "error": err_msg}

        except Exception as e:
            err_msg = str(e)
            print(f"❌ Gagal publish ke {pid_lower}: {err_msg}")
            results[pid_lower] = {"ok": False, "error": err_msg}

        # Catat riwayat publish ke log
        if row_idx is not None:
            social.log_publish(row_idx, pid_lower, results[pid_lower])

    return results