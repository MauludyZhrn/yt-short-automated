"""Jembatan 5 agen baru <-> pipeline <-> Office HQ.

Tiap fungsi membungkus modul agen + mengirim event ke kantor 3D (notify_office) supaya
karakter bergerak di lantai masing-masing. Semua fungsi AMAN: error di agen tidak boleh mematahkan pipeline utama.

  run_trend()   NexaTrend   riset topik viral -> Google Sheets          (modules/trend_researcher.py)
  run_qc()      ByteGuard   cek mp4 (durasi, 9:16, audio, ukuran)       (modules/qc_inspector.py)
  run_publish() CrossByte   distribusi ke YouTube/TikTok/IG/FB          (modules/multi_publisher.py)
  run_echo()    EchoBee     balas komentar penonton dengan LLM          (modules/community_manager.py)
  run_report()  Metrix      statistik performa + laporan untuk CEO      (modules/data_analyst.py)

Flag .env (default "1" = aktif):  AUTO_TREND, QC_ENABLED, QC_STRICT, ECHO_ENABLED, METRIX_ENABLED
"""
import os
import re
import traceback

try:
    from office_bus import notify_office
except ImportError:                                   # dijalankan terpisah tanpa server
    def notify_office(*args, **kwargs):
        pass


def flag(name, default="1"):
    return str(os.environ.get(name, default)).strip().lower() not in ("0", "false", "no", "off", "")


def _debug():
    if os.environ.get("LOG_LEVEL", "Info").lower() == "debug":
        traceback.print_exc()


def video_id_of(url_or_id):
    """ID video YouTube dari URL Shorts / youtu.be / watch?v= / ID polos (11 karakter)."""
    s = str(url_or_id or "").strip()
    for pat in (r"youtube\.com/shorts/([\w-]{11})", r"youtu\.be/([\w-]{11})", r"[?&]v=([\w-]{11})"):
        m = re.search(pat, s)
        if m:
            return m.group(1)
    return s if re.fullmatch(r"[\w-]{11}", s) else None


# ---------------------------------------------------------------- NexaTrend
def run_trend(count=3, progress=2):
    """Riset tren -> topik baru berstatus 'Ready' di Sheets. Return jumlah topik yang ditambahkan."""
    notify_office(agent="nexa", action="researching", message=f"NexaTrend: riset {count} topik viral (Trends/TikTok/Reddit)…", progress=progress)
    try:
        from modules.trend_researcher import run_nexatrend_research
        n = int(run_nexatrend_research(count=count) or 0)
        notify_office(agent="nexa", action="idle" if n else "alert", message=f"NexaTrend: {n} topik panas masuk Google Sheets" if n else "NexaTrend: tidak ada topik baru", progress=progress)
        return n
    except Exception as exc:
        print(f"❌ NexaTrend error: {exc}")
        _debug()
        notify_office(agent="nexa", action="alert", message=f"NexaTrend gagal: {str(exc)[:70]}", progress=progress)
        return 0


# ---------------------------------------------------------------- ByteGuard
def run_qc(video_path, progress=96):
    """Return {"passed": bool, "reason": str, "details"?: dict}. Modul QC tidak ada / moviepy hilang -> dilewati (passed=True)."""
    notify_office(agent="byte", action="inspecting", message="ByteGuard: cek durasi, rasio 9:16, audio & ukuran file…", progress=progress)
    if not flag("QC_ENABLED"):
        notify_office(agent="byte", action="idle", message="ByteGuard: QC dimatikan (QC_ENABLED=0)", progress=progress)
        return {"passed": True, "reason": "QC dinonaktifkan."}
    try:
        from modules.qc_inspector import inspect_video_quality
    except Exception as exc:
        print(f"⚠️ ByteGuard tidak bisa dimuat ({exc}) — QC dilewati.")
        notify_office(agent="byte", action="idle", message="ByteGuard: modul QC tidak tersedia, dilewati", progress=progress)
        return {"passed": True, "reason": f"QC dilewati: {exc}"}
    try:
        res = inspect_video_quality(video_path)
    except Exception as exc:
        _debug()
        res = {"passed": False, "reason": f"QC error: {exc}"}
    if res.get("passed"):
        d = res.get("details") or {}
        notify_office(agent="byte", action="idle", message=f"ByteGuard: LULUS · {d.get('resolution', '')} · {d.get('duration_sec', '?')} dtk", progress=progress)
    else:
        notify_office(agent="byte", action="alert", message=f"ByteGuard: GAGAL — {str(res.get('reason'))[:80]}", progress=progress)
    return res


# ---------------------------------------------------------------- CrossByte
def run_publish(video_path, topic, niche="", hook_style="", script_text="", platforms=None, row_idx=None,
                channel_name="MorbMyth", privacy_status="public", publish_at=None):
    """Return dict hasil per platform: {pid: {ok, url?, error?, type: real|dummy}}."""
    platforms = list(platforms or ["youtube"])
    notify_office(agent="cross", action="publishing", message=f"CrossByte: distribusi ke {len(platforms)} platform…", progress=96)
    last = {"p": -1}

    def cb(pct):                                      # progress upload -> pesan kantor (dibatasi tiap 25%)
        try:
            step = int(pct) // 25
            if step != last["p"]:
                last["p"] = step
                notify_office(agent="cross", action="publishing", message=f"CrossByte: upload {int(pct)}%…", progress=96)
        except Exception:
            pass
    try:
        from modules.multi_publisher import publish_to_platforms
        res = publish_to_platforms(video_path=video_path, topic=topic, niche=niche, hook_style=hook_style, script_text=script_text,
                                   platforms=platforms, row_idx=row_idx, channel_name=channel_name or "MorbMyth",
                                   privacy_status=privacy_status, publish_at=publish_at, progress_callback=cb)
    except Exception as exc:
        print(f"❌ CrossByte error: {exc}")
        _debug()
        notify_office(agent="cross", action="alert", message=f"CrossByte gagal: {str(exc)[:70]}", progress=96)
        return {}
    ok = [p for p, r in res.items() if r.get("ok")]
    bad = [p for p, r in res.items() if not r.get("ok")]
    notify_office(agent="cross", action="idle" if ok else "alert", message=f"CrossByte: {len(ok)} sukses" + (f", {len(bad)} gagal ({', '.join(bad)})" if bad else ""), progress=97)
    return res


# ---------------------------------------------------------------- EchoBee
def run_echo(video_url_or_id=None, max_replies=5, progress=98):
    """Balas komentar video (atau 3 video Done terakhir bila tidak diberi). Return daftar balasan."""
    if not flag("ECHO_ENABLED"):
        return []
    targets = []
    if video_url_or_id:
        vid = video_id_of(video_url_or_id)
        targets = [vid] if vid else []
    else:
        try:
            from modules.sheets_manager import fetch_all_planner_rows
            for r in fetch_all_planner_rows():
                if str(r.get("status", "")).strip().lower() == "done":
                    vid = video_id_of(r.get("output"))
                    if vid:
                        targets.append(vid)
            targets = targets[-3:]
        except Exception as exc:
            print(f"⚠️ EchoBee tidak bisa membaca Sheets: {exc}")
    if not targets:
        notify_office(agent="echo", action="idle", message="EchoBee: belum ada video untuk dicek komentarnya", progress=progress)
        return []
    notify_office(agent="echo", action="replying", message=f"EchoBee: memeriksa komentar di {len(targets)} video…", progress=progress)
    out = []
    try:
        from modules.community_manager import EchoBeeCommunityManager
        bee = EchoBeeCommunityManager()
        for vid in targets:
            out += bee.auto_manage_comments(vid, max_reply_count=max_replies)
        notify_office(agent="echo", action="idle", message=f"EchoBee: {len(out)} komentar dibalas", progress=progress)
    except Exception as exc:
        print(f"❌ EchoBee error: {exc}")
        _debug()
        notify_office(agent="echo", action="alert", message=f"EchoBee gagal: {str(exc)[:70]}", progress=progress)
    return out


# ---------------------------------------------------------------- Metrix
def run_report(progress=99):
    """Statistik semua video Done -> laporan JSON (folder reports/) untuk CEO. Return ringkasan atau None."""
    if not flag("METRIX_ENABLED"):
        return None
    notify_office(agent="metrix", action="analyzing", message="Metrix: menarik statistik & menyusun laporan harian…", progress=progress)
    try:
        from modules.data_analyst import analyze_and_report
        rep = analyze_and_report()
        agg = (rep or {}).get("aggregate_stats", {})
        sim = (rep or {}).get("simulated_count", 0)
        msg = f"Metrix: {rep.get('total_videos_analyzed', 0)} video · {agg.get('total_views', 0):,} views · ER {agg.get('avg_engagement_rate', 0)}%" + (" (data simulasi)" if sim else "")
        notify_office(agent="metrix", action="idle", message=msg, progress=progress)
        return rep
    except Exception as exc:
        print(f"❌ Metrix error: {exc}")
        _debug()
        notify_office(agent="metrix", action="alert", message=f"Metrix gagal: {str(exc)[:70]}", progress=progress)
        return None
