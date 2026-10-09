import sys
import os
import time
import traceback

from modules.sheets_manager import fetch_next_ready_row, update_row_status
if os.environ.get("USE_OLLAMA", "0") == "1":      # set USE_OLLAMA=1 di .env -> naskah via Ollama (gratis, lokal)
    from modules.ollama_client import generate_script
else:
    from modules.script_gen import generate_script
from modules.tts import generate_speech_with_word_timestamps
from modules.fetch_bg import download_multiple_backgrounds
from modules.remotion_bridge import render_remotion_video
from modules.video_editor import group_words_into_phrases
from modules.youtube_uploader import upload_video_to_youtube
from modules.bgm_gen import get_local_bgm
from modules.motion_cues import detect_theme, build_motion_cues


BGM_VOLUME = float(os.environ.get("BGM_VOLUME", "0.13"))   # sebelumnya 0.08

try:
    from office_bus import notify_office
except ImportError:
    def notify_office(*args, **kwargs):
        pass  # Fallback jika dijalankan terpisah tanpa server

try:
    from modules import social_real as social
except Exception as _exc:  # konektor sosial opsional
    social = None
    print(f"⚠️ social_real tidak bisa dimuat: {_exc}")

# ---- 5 agent tambahan (modules/) ----------------------------------------
try:
    from modules.trend_researcher import run_nexatrend_research   # Agent: NexaTrend
except Exception as _exc:
    run_nexatrend_research = None
    print(f"⚠️ trend_researcher (NexaTrend) tidak bisa dimuat: {_exc}")

try:
    from modules.qc_inspector import inspect_video_quality         # Agent: ByteGuard
except Exception as _exc:
    inspect_video_quality = None
    print(f"⚠️ qc_inspector (ByteGuard) tidak bisa dimuat: {_exc}")

try:
    from modules.data_analyst import MetrixDataAnalyst, load_bias  # Agent: Metrix
except Exception as _exc:
    MetrixDataAnalyst = None
    def load_bias():
        return {}
    print(f"⚠️ data_analyst (Metrix) tidak bisa dimuat: {_exc}")

try:
    from modules.community_manager import EchoBeeCommunityManager  # Agent: EchoBee
except Exception as _exc:
    EchoBeeCommunityManager = None
    print(f"⚠️ community_manager (EchoBee) tidak bisa dimuat: {_exc}")

try:
    from modules.multi_publisher import publish_to_platforms       # Agent: CrossByte
except Exception as _exc:
    publish_to_platforms = None
    print(f"⚠️ multi_publisher (CrossByte) tidak bisa dimuat: {_exc}")


# ==============================================================================
# SETTING MODE UPLOAD
# 'draft' = Render video -> Simpan lokal -> Status 'Ready for Review' (Publish via GUI)
# 'auto'  = Render video -> Upload langsung ke platform terpilih -> Status 'Done'
# ==============================================================================
UPLOAD_MODE = "draft"  # default saat dijalankan manual: python main.py [auto|draft]
DEFAULT_PLATFORMS = ["youtube"]


def _debug_trace():
    """Traceback lengkap hanya jika Log Level = Debug (Settings)."""
    if os.environ.get("LOG_LEVEL", "Info").lower() == "debug":
        traceback.print_exc()



def _apply_metrix_bias(tags):
    """Agent Metrix: selipkan keyword terbukti performa bagus ke tag (auto-tweak SEO)."""
    bias = load_bias()
    keywords = bias.get("winning_keywords") or []
    if not keywords:
        return tags
    low = [t.lower() for t in tags]
    added = [kw for kw in keywords if kw.lower() not in low]
    if added:
        print(f"🎯 Metrix: menambahkan {len(added)} keyword terbukti laku ke tag: {added}")
    return (tags + added)[:15]


def _build_meta(niche, topic, hook, script, channel_name):
    """Judul/deskripsi/tag via modul SEO yang sama dengan Video Studio; fallback generik.
    Tag diselipi bias Metrix (keyword/hook yang terbukti performa bagus)."""
    try:
        from modules import youtube_uploader as yt
        meta = yt.build_seo_metadata(topic, niche, hook, channel_name=channel_name,
                                     variant=0, disclose_ai=True)
        cat = getattr(yt, "CATEGORIES", {}).get(getattr(yt, "DEFAULT_CATEGORY_NAME", ""), "27")
        return meta["title"], meta["description"], _apply_metrix_bias(list(meta["tags"])), cat
    except Exception as exc:
        print(f"⚠️ SEO builder tidak tersedia ({exc}) — memakai metadata generik.")
        clean = niche.replace(" ", "")
        desc = (f"{script[:150]}...\n\n"
                f"Simak fakta menarik seputar {niche} hanya di channel ini!\n"
                f"Video ini dibuat dengan bantuan AI.\n\n"
                f"#Shorts #{clean} #FaktaUnik")
        return topic, desc, _apply_metrix_bias([niche.lower(), "shorts", "faktaunik"]), "27"


def _youtube_upload(path, title, desc, tags, category_id):
    try:
        return upload_video_to_youtube(
            video_path=path, title=title, description=desc, tags=tags,
            category_id=category_id, privacy_status="public", synthetic_media=True)
    except TypeError:  # versi uploader lama tanpa argumen baru
        return upload_video_to_youtube(
            video_path=path, title=title, description=desc, tags=tags, privacy_status="public")


def _auto_publish(row_idx, path, niche, topic, hook, script, platforms, channel_name):
    """Publish ke semua platform terpilih via CrossByte (Agent 8: multi_publisher).
    Return (url_utama_atau_None, ada_upload_asli)."""
    channel_name = channel_name or "MorbMyth"
    main_url, real_ok = None, False

    if publish_to_platforms is not None:
        notify_office(agent="cross", action="publishing",
                      message=f"CrossByte: Mendistribusikan video ke {len(platforms)} platform...", progress=0)
        try:
            results = publish_to_platforms(
                video_path=path, topic=topic, niche=niche, hook_style=hook, script_text=script,
                platforms=platforms, row_idx=row_idx, channel_name=channel_name,
                privacy_status="public")
        except Exception as exc:
            print(f"❌ CrossByte gagal mendistribusikan video: {exc}")
            _debug_trace()
            notify_office(agent="cross", action="alert", message=f"CrossByte: Distribusi gagal — {str(exc)[:80]}", progress=0)
            results = {}

        for pid, info in results.items():
            if info.get("ok"):
                if pid == "youtube":
                    main_url, real_ok = info.get("url") or main_url, True
                elif main_url is None:
                    main_url = info.get("url")
        notify_office(agent="cross", action="idle",
                      message="CrossByte: Distribusi selesai." if results else "CrossByte: Tidak ada platform terpublish.",
                      progress=100)
    else:
        # Fallback jika modul CrossByte tidak termuat: upload YouTube langsung.
        title, desc, tags, cat = _build_meta(niche, topic, hook, script, channel_name)
        for pid in platforms:
            try:
                if pid == "youtube":
                    print("📤 Mode AUTO: upload ke YouTube Shorts (fallback, tanpa CrossByte)...")
                    url = _youtube_upload(path, title, desc, tags, cat)
                    main_url, real_ok = url or main_url, True
                    info = {"ok": True, "url": url}
                elif social is not None and pid in social.PLATFORMS:
                    cap = social.build_caption(pid, title, desc, tags)
                    res = social.upload(pid, path, cap)
                    info = {"ok": True, "url": res["url"]}
                    print(f"✅ {social.PLATFORMS[pid]['label']} → {res['url']}")
                else:
                    print(f"⚠️ Platform '{pid}' dilewati (tidak dikenal).")
                    continue
            except Exception as exc:
                print(f"❌ Upload {pid} gagal: {exc}")
                _debug_trace()
                info = {"ok": False, "error": str(exc)}
            if social is not None:
                try:
                    social.log_publish(row_idx, pid, info)
                except Exception:
                    pass

    # Agent: EchoBee — balas komentar otomatis di video YouTube yang baru naik.
    # Mode boost (lebih banyak balasan) kalau skor engagement rata-rata lagi rendah (bias Metrix).
    if real_ok and main_url and EchoBeeCommunityManager is not None:
        boost = (load_bias() or {}).get("boost_comments", False)
        reply_count = 10 if boost else 5
        mode_msg = "mode BOOST (engagement rendah)" if boost else "mode normal"
        notify_office(agent="echo", action="replying",
                      message=f"EchoBee: Memeriksa & membalas komentar baru ({mode_msg})...", progress=0)
        try:
            manager = EchoBeeCommunityManager()
            video_id = manager.extract_video_id(main_url) or main_url
            replies = manager.auto_manage_comments(video_id, max_reply_count=reply_count)
            notify_office(agent="echo", action="idle",
                          message=f"EchoBee: {len(replies)} komentar dibalas.", progress=100)
        except Exception as exc:
            print(f"⚠️ EchoBee gagal memproses komentar: {exc}")
            notify_office(agent="echo", action="alert", message=f"EchoBee: Gagal — {str(exc)[:80]}", progress=0)

    # Agent: Metrix — susun laporan performa untuk CEO setelah publish.
    if real_ok and MetrixDataAnalyst is not None:
        notify_office(agent="metrix", action="analyzing", message="Metrix: Menyusun laporan performa untuk CEO...", progress=0)
        try:
            MetrixDataAnalyst().generate_ceo_report()
            notify_office(agent="metrix", action="idle", message="Metrix: Laporan performa siap.", progress=100)
        except Exception as exc:
            print(f"⚠️ Metrix gagal menyusun laporan: {exc}")
            notify_office(agent="metrix", action="alert", message=f"Metrix: Gagal — {str(exc)[:80]}", progress=0)

    return main_url, real_ok


def _render_pipeline(row_idx, niche, topic, hook_style):
    """Seluruh proses sampai file MP4 jadi dengan notifikasi WebSocket di setiap tahap, dipantau oleh CEO."""
    
    # 0. CEO Memulai Workflow
    notify_office(agent="ceo", action="delegating", message=f"CEO: Memeriksa proyek '{topic}'. Menugaskan Scriptwriter...", progress=5)
    
    # Tahap 1: Generasi Naskah
    notify_office(agent="scriptwriter", action="typing", message="Menulis naskah video...", progress=20)
    script_data = generate_script(niche=niche, topic=topic, hook_style=hook_style)
    
    # Transisi 1: CEO menyetujui naskah
    notify_office(agent="ceo", action="monitoring", message="CEO: Naskah disetujui! Meminta tim audio & desain menyiapkan aset.", progress=35)
    
    # Tahap 2: Voiceover / TTS
    notify_office(agent="voiceactor", action="speaking", message="Membuat audio & timestamp...", progress=45)
    audio_path, word_subtitles = generate_speech_with_word_timestamps(script_data["script"])
    
    # Tahap 3: Download Background & BGM
    notify_office(agent="designer", action="working", message="Mencari background & BGM...", progress=60)
    bgm_path = get_local_bgm(niche)
    bg_paths = download_multiple_backgrounds(script_data["prompts"])

    output_name = f"shorts_row_{row_idx}.mp4"
    hook_text = (script_data.get("hook_text") or "").strip()
    intro_bumper = hook_text.upper() if hook_text else f"TAHU GAK? {topic.upper()}!"
    theme = detect_theme(niche, topic)
    motion_cues = build_motion_cues(script_data.get("callouts"), word_subtitles)
    print(f"🎞️ Tema: {theme} | {len(motion_cues)} motion graphic cue.")
    outro_bumper = f"SUKA {niche.upper()}? SUBSCRIBE!"
    phrase_subtitles = group_words_into_phrases(word_subtitles, max_words=3)

    # Transisi 2: CEO meneruskan aset ke Editor
    notify_office(agent="ceo", action="approving", message="CEO: Seluruh aset visual & audio lengkap. Menugaskan Editor render video.", progress=75)

    # Tahap 4: Rendering Video (Remotion)
    notify_office(agent="editor", action="rendering", message="Merender video MP4...", progress=85)
    path = render_remotion_video(
        word_subtitles=phrase_subtitles, audio_path=audio_path, bg_paths=bg_paths,
        output_filename=output_name, title_text=intro_bumper, outro_text=outro_bumper,
        logo_path="assets/logo.png", bg_music_path=bgm_path,
        theme=theme, motion_cues=motion_cues, bgm_volume=BGM_VOLUME)
    
    notify_office(agent="editor", action="idle", message="Render video selesai!", progress=95)

    # Tahap 5: QC — Agent ByteGuard memeriksa kelayakan file sebelum publish.
    if inspect_video_quality is not None:
        notify_office(agent="byte", action="inspecting", message="ByteGuard: Memeriksa kualitas video...", progress=97)
        qc = inspect_video_quality(path)
        if not qc.get("passed"):
            notify_office(agent="byte", action="alert", message=f"ByteGuard: QC gagal — {qc.get('reason')}", progress=0)
            raise RuntimeError(f"QC ByteGuard gagal: {qc.get('reason')}")
        notify_office(agent="byte", action="idle", message="ByteGuard: QC lolos, video siap dipublish.", progress=99)

    # Penutup: CEO melakukan validasi akhir
    notify_office(agent="ceo", action="idle", message="CEO: Render disetujui! Video siap di-publish.", progress=100)

    return path, script_data["script"]


def main(mode=UPLOAD_MODE, retries=1, platforms=None, should_stop=None, channel_name=None):
    """
    Proses SATU baris 'Ready'.
    Return:
      False -> antrean kosong / gagal / dihentikan
      dict  -> berhasil render: {"rendered": True, "uploaded": bool, "path": ...}
    retries      : jumlah percobaan render per baris (dari Settings).
    should_stop  : callable() -> True bila automation diminta berhenti.
    platforms    : daftar platform untuk mode auto, default ['youtube'].
    """
    should_stop = should_stop or (lambda: False)
    platforms = list(platforms or DEFAULT_PLATFORMS)
    retries = max(1, int(retries or 1))

    print("🚀 Checking Google Sheets for pending content...")
    task = fetch_next_ready_row("Shorts Content Planner")

    # Agent: NexaTrend — antrean kosong -> riset ide viral otomatis & isi ulang Sheets.
    if not task and run_nexatrend_research is not None:
        notify_office(agent="nexa", action="researching", message="NexaTrend: Antrean kosong, riset topik viral baru...", progress=0)
        try:
            n = run_nexatrend_research(count=3)
            notify_office(agent="nexa", action="idle", message=f"NexaTrend: {n} ide baru ditambahkan.", progress=100)
        except Exception as exc:
            print(f"⚠️ NexaTrend gagal riset ide: {exc}")
            notify_office(agent="nexa", action="alert", message=f"NexaTrend: Gagal — {str(exc)[:80]}", progress=0)
        task = fetch_next_ready_row("Shorts Content Planner")

    if not task:
        print("☕ Tidak ada antrean video dengan status 'Ready' di Google Sheets.")
        return False

    row_idx, niche = task["row_index"], task["niche"]
    topic, hook_style = task["topic"], task["hook_style"]
    print(f"🎯 Memproses Baris #{row_idx} | Topic: {topic} ({niche})")
    update_row_status(row_idx, "Processing")

    # ---- Tahap 1: render (dengan retry) ----
    final_video_path, script_text, last_err = None, "", None
    for attempt in range(1, retries + 1):
        if should_stop():
            print(f"⏹️ Dihentikan sebelum percobaan {attempt}. Baris #{row_idx} dikembalikan ke 'Ready'.")
            update_row_status(row_idx, "Ready")
            return False
        try:
            final_video_path, script_text = _render_pipeline(row_idx, niche, topic, hook_style)
            break
        except Exception as exc:
            last_err = exc
            notify_office(agent="ceo", action="alert", message=f"CEO: Render gagal — {str(exc)[:80]}", progress=0)
            print(f"❌ Render gagal baris #{row_idx} (percobaan {attempt}/{retries}): {exc}")
            _debug_trace()
            if attempt < retries:
                time.sleep(min(5 * attempt, 20))

    if not final_video_path:
        print(f"❌ Baris #{row_idx} ditandai Failed: {last_err}")
        update_row_status(row_idx, "Failed")
        return False

    # ---- Tahap 2: percabangan mode ----
    uploaded = False
    if mode == "auto":
        url, real_ok = _auto_publish(row_idx, final_video_path, niche, topic, hook_style,
                                     script_text, platforms, channel_name)
        if real_ok:
            update_row_status(row_idx, "Done", video_path=url or final_video_path)
            uploaded = True
            print(f"✨ SUKSES! Baris #{row_idx} selesai & di-upload. Link: {url or final_video_path}")
        else:
            # Video SUDAH jadi — jangan dibuang jadi 'Failed'; biarkan di-review & publish manual.
            update_row_status(row_idx, "Ready for Review", video_path=final_video_path)
            print(f"⚠️ Upload otomatis tidak berhasil. Baris #{row_idx} dipindah ke 'Ready for Review' "
                  f"agar bisa dipublish manual. File: {final_video_path}")
    else:
        update_row_status(row_idx, "Ready for Review", video_path=final_video_path)
        print(f"✨ SUKSES! Baris #{row_idx} siap ditinjau di Video Studio. File: {final_video_path}")

    return {"rendered": True, "uploaded": uploaded, "path": final_video_path}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["auto", "draft"]:
        main(mode=sys.argv[1])
    else:
        main()