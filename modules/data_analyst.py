import os
import json
import time
import re
import pickle
import datetime
import googleapiclient.discovery
import googleapiclient.errors

# Import modul sheets manager untuk sync laporan
try:
    from modules import sheets_manager as sheets
except ImportError:
    sheets = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
BIAS_FILE = os.path.join(BASE_DIR, "metrix_bias.json")
SHEET_NAME = "Shorts Content Planner"
YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

os.makedirs(REPORTS_DIR, exist_ok=True)

LOW_SCORE_THRESHOLD = 45   # avg engagement score di bawah ini -> EchoBee boost komentar lebih agresif
STOPWORDS_ID = {"yang", "dan", "di", "ke", "dari", "untuk", "dengan", "pada", "dalam", "ini", "itu",
                "adalah", "atau", "akan", "oleh", "sebuah", "satu", "para", "juga", "saat", "bisa",
                "tidak", "apa", "kenapa", "kok", "sih", "the", "and", "of", "with"}


def load_bias():
    """Baca bias engagement terakhir yang disimpan Metrix. Return {} bila belum ada."""
    try:
        with open(BIAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class MetrixDataAnalyst:
    """
    Agent: Metrix (Data Analyst Agent)
    Tugas:
    1. Mengambil statistik real-time (views, likes, comments) dari YouTube Data API
    2. Menghitung Engagement Rate dan Performance Score tiap konten
    3. Menyusun Laporan Ringkas / Insight Performansi untuk MorbMyth (CEO)
    4. Menyinkronkan data performa balik ke Google Sheets
    """

    def __init__(self, youtube_client=None):
        self.agent_name = "Metrix"
        self.creds = None
        self.youtube = youtube_client or self._init_youtube_client()
        self.analytics = self._init_analytics_client()

    def _init_youtube_client(self):
        """Otorisasi ke YouTube Data API v3. Token kedaluwarsa di-refresh otomatis."""
        if not os.path.exists(TOKEN_FILE):
            print(f"❌ [{self.agent_name}] token.pickle tidak ditemukan. Login YouTube dulu (jalankan upload sekali).")
            return None
        try:
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
            if creds and not creds.valid and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(TOKEN_FILE, "wb") as token:
                    pickle.dump(creds, token)
            self.creds = creds
            return googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        except Exception as exc:
            print(f"❌ [{self.agent_name}] Gagal inisialisasi API YouTube: {exc}")
            return None

    def extract_video_id(self, url_or_id):
        """Ambil ID video YouTube dari shorts/watch/youtu.be/embed/live atau ID mentah. None kalau bukan YouTube."""
        if not url_or_id:
            return None
        s = str(url_or_id).strip()
        if YT_ID_RE.match(s):
            return s
        m = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", s) \
            or re.search(r"youtube\.com/(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})", s) \
            or re.search(r"[?&]v=([A-Za-z0-9_-]{11})", s)
        return m.group(1) if m else None

    def _build_metrics(self, item):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))      # kosong bila creator sembunyikan like
        comments = int(stats.get("commentCount", 0))  # kosong bila komentar dimatikan
        # Engagement Rate = ((Likes + Comments) / Views) * 100
        engagement_rate = round(((likes + comments) / views * 100), 2) if views > 0 else 0.0
        return {
            "video_id": item.get("id", ""),
            "title": snippet.get("title", ""),
            "published_at": snippet.get("publishedAt", ""),
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": engagement_rate,
            "score": self._calculate_performance_score(views, engagement_rate),
            "is_real_data": True,
        }

    def fetch_videos_metrics(self, video_ids):
        """Ambil statistik banyak video sekaligus (50 ID per request, hemat quota). Return {video_id: metrics}."""
        if not self.youtube:
            raise RuntimeError("Klien YouTube belum siap (token.pickle hilang/invalid).")
        out = {}
        ids = list(dict.fromkeys(video_ids))
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            resp = self.youtube.videos().list(part="snippet,statistics", id=",".join(chunk)).execute()
            for item in resp.get("items", []):
                out[item["id"]] = self._build_metrics(item)
        return out

    def fetch_video_metrics(self, video_url_or_id):
        """Statistik satu video. None bila ID invalid / video tidak ada / API error. Tidak ada data palsu."""
        video_id = self.extract_video_id(video_url_or_id)
        if not video_id:
            return None
        try:
            return self.fetch_videos_metrics([video_id]).get(video_id)
        except Exception as exc:
            print(f"❌ [{self.agent_name}] Error ambil metrik ({video_id}): {exc}")
            return None

    def _init_analytics_client(self):
        """YouTube Analytics API v2 (shares, retensi, watch time). None bila belum bisa."""
        if not self.creds:
            return None
        try:
            return googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=self.creds)
        except Exception as exc:
            print(f"⚠️ [{self.agent_name}] Analytics API tidak siap: {exc}")
            return None

    def fetch_analytics(self, video_ids, since):
        """Return {video_id: {shares, avg_view_pct, avg_view_sec, watch_minutes, subs_gained}}.
        Kosong + peringatan jelas bila gagal (scope kurang / API belum diaktifkan)."""
        if not self.analytics or not video_ids:
            return {}
        out = {}
        ids = list(video_ids)
        try:
            for i in range(0, len(ids), 200):
                chunk = ids[i:i + 200]
                resp = self.analytics.reports().query(
                    ids="channel==MINE", startDate=since,
                    endDate=datetime.date.today().isoformat(),
                    metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,shares,subscribersGained",
                    dimensions="video", filters="video==" + ",".join(chunk),
                    sort="-views", maxResults=200).execute()
                for r in resp.get("rows", []):
                    out[r[0]] = {"views_analytics": int(r[1]), "watch_minutes": round(float(r[2]), 1),
                                 "avg_view_sec": round(float(r[3]), 1), "avg_view_pct": round(float(r[4]), 1),
                                 "shares": int(r[5]), "subs_gained": int(r[6])}
        except Exception as exc:
            print(f"⚠️ [{self.agent_name}] Analytics API gagal: {exc}\n"
                  f"   Cek: (1) YouTube Analytics API sudah di-Enable di Google Cloud, "
                  f"(2) login ulang agar scope yt-analytics.readonly ikut.")
        return out

    def _merge_analytics(self, fetched):
        if not fetched:
            return
        since = min((m["published_at"][:10] for m in fetched.values() if m.get("published_at")),
                    default="2020-01-01")
        extra = self.fetch_analytics(list(fetched), since)
        for vid, m in fetched.items():
            a = extra.get(vid)
            if not a:
                m.update(shares=None, avg_view_pct=None, avg_view_sec=None, watch_minutes=None, subs_gained=None)
                continue
            m.update({k: a[k] for k in ("shares", "avg_view_pct", "avg_view_sec", "watch_minutes", "subs_gained")})
            if m["views"] > 0:   # engagement ikut menghitung share
                m["engagement_rate"] = round((m["likes"] + m["comments"] + a["shares"]) / m["views"] * 100, 2)
            m["score"] = self._calculate_performance_score(m["views"], m["engagement_rate"],
                                                           a["avg_view_pct"], a["shares"])

    def _calculate_performance_score(self, views, engagement_rate, avg_view_pct=None, shares=None):
        """Kalkulasi skor kriteria performa (1 - 100) untuk evaluasi MorbMyth (CEO)."""
        if avg_view_pct is not None:
            # Skor lengkap (retensi + share): base 30, views maks +25, engagement maks +20, retensi maks +25, share maks +10
            score = 30
            score += 25 if views >= 10000 else 18 if views >= 2000 else 8 if views >= 500 else 0
            score += 20 if engagement_rate >= 8 else 14 if engagement_rate >= 4 else 7 if engagement_rate >= 2 else 0
            score += 25 if avg_view_pct >= 100 else 18 if avg_view_pct >= 80 else 10 if avg_view_pct >= 60 else 5 if avg_view_pct >= 40 else 0
            share_rate = (shares or 0) / views * 100 if views else 0
            score += 10 if share_rate >= 1.0 else 5 if share_rate >= 0.3 else 0
            return min(100, score)
        score = 40  # Base Score (tanpa data Analytics)
        if views >= 10000: score += 30
        elif views >= 2000: score += 20
        elif views >= 500: score += 10

        if engagement_rate >= 8.0: score += 30
        elif engagement_rate >= 4.0: score += 20
        elif engagement_rate >= 2.0: score += 10

        return min(100, score)

    def generate_ceo_report(self, rows_data=None):
        """
        Menyusun laporan eksekutif lengkap mengenai statistik dan performa konten
        khusus untuk MorbMyth (CEO).
        """
        print(f"\n📈 [{self.agent_name}] Memulai analisis statistik performa konten untuk MorbMyth (CEO)...")

        if not rows_data and sheets:
            try:
                rows_data = sheets.fetch_all_planner_rows(SHEET_NAME)
            except Exception as e:
                print(f"⚠️ [{self.agent_name}] Gagal mengambil baris dari sheets: {e}")
                rows_data = []

        # Hanya baris dengan output = link/ID YouTube asli. URL TikTok/IG/FB (dummy) dilewati.
        candidates = {}
        skipped = 0
        for row in rows_data or []:
            vid = self.extract_video_id(str(row.get("output", "") or ""))
            if vid:
                candidates[vid] = row
            elif str(row.get("output", "")).lower().startswith("http"):
                skipped += 1
        if skipped:
            print(f"ℹ️ [{self.agent_name}] {skipped} baris dilewati (bukan link YouTube).")

        fetch_error = None
        fetched = {}
        if candidates:
            try:
                fetched = self.fetch_videos_metrics(list(candidates))
            except Exception as exc:
                fetch_error = str(exc)
                print(f"❌ [{self.agent_name}] Gagal tarik statistik YouTube: {exc}")
        missing = [v for v in candidates if v not in fetched]
        if missing and not fetch_error:
            print(f"⚠️ [{self.agent_name}] {len(missing)} video tidak ditemukan (dihapus/private): {missing[:5]}")

        self._merge_analytics(fetched)

        results = []
        total_views = 0
        total_likes = 0
        for vid, metrics in fetched.items():
            row = candidates[vid]
            metrics["row_id"] = row.get("id", "-")
            metrics["niche"] = row.get("niche", "General")
            metrics["topic"] = row.get("topic", "Untitled")
            metrics["hook"] = row.get("hook", "-")
            results.append(metrics)
            total_views += metrics["views"]
            total_likes += metrics["likes"]

        # Urutkan berdasarkan skor performa tertinggi
        results.sort(key=lambda x: x["score"], reverse=True)

        report_summary = {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_videos_analyzed": len(results),
            "videos_missing": len(missing),
            "error": fetch_error,
            "aggregate_stats": {
                "total_views": total_views,
                "total_likes": total_likes,
                "total_shares": sum(r.get("shares") or 0 for r in results),
                "avg_view_percentage": (round(sum(r["avg_view_pct"] for r in results if r.get("avg_view_pct") is not None) /
                                              max(1, sum(1 for r in results if r.get("avg_view_pct") is not None)), 1)
                                        if any(r.get("avg_view_pct") is not None for r in results) else None),
                "avg_engagement_rate": round(sum(r["engagement_rate"] for r in results) / len(results), 2) if results else 0
            },
            "top_performer": results[0] if results else None,
            "detailed_metrics": results
        }

        # Simpan Laporan Fisik ke /reports
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(REPORTS_DIR, f"metrix_report_{timestamp}.json")
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_summary, f, indent=2, ensure_ascii=False)
            print(f"💾 [{self.agent_name}] Laporan analitik berhasil disimpan ke '{os.path.basename(report_file)}'")
        except Exception as exc:
            print(f"⚠️ [{self.agent_name}] Gagal menyimpan file laporan: {exc}")

        # Cetak Ringkasan Laporan di Terminal
        print("\n==================================================")
        print("📊 LAPORAN ANALITIK KONTEN — MORBMYTH (CEO)")
        print("==================================================")
        print(f"• Total Video Dianalisis : {report_summary['total_videos_analyzed']}")
        print(f"• Total Views            : {total_views:,}")
        print(f"• Total Likes            : {total_likes:,}")
        print(f"• Rata-rata Engagement   : {report_summary['aggregate_stats']['avg_engagement_rate']}%")
        print(f"• Total Shares           : {report_summary['aggregate_stats']['total_shares']:,}")
        print(f"• Rata-rata Retensi      : {report_summary['aggregate_stats']['avg_view_percentage']}%")
        if report_summary["top_performer"]:
            top = report_summary["top_performer"]
            print(f"🏆 Top Performer         : Baris #{top['row_id']} - [{top['niche']}] {top['topic']}")
            print(f"                           Views: {top['views']:,} | Engagement: {top['engagement_rate']}% | Score: {top['score']}")
        print("==================================================\n")

        # Bangun & simpan bias engagement untuk NexaTrend / SEO builder / EchoBee.
        if results:
            self.build_engagement_bias(report_summary)
        else:
            print(f"ℹ️ [{self.agent_name}] Tidak ada data nyata — bias lama dipertahankan.")

        return report_summary

    def _keywords(self, text, limit=5):
        import re
        out = []
        for w in re.findall(r"[A-Za-zÀ-ÿ0-9]{4,}", str(text).lower()):
            if w in STOPWORDS_ID or w in out:
                continue
            out.append(w)
            if len(out) >= limit:
                break
        return out

    def build_engagement_bias(self, report_summary):
        """
        Olah laporan performa jadi 'bias' yang bisa dipakai agent lain:
        - winning_niches / winning_hooks / winning_keywords: dari video skor tertinggi
          -> dipakai NexaTrend (riset ide) & _build_meta (judul/tag render berikutnya).
        - boost_comments: True kalau rata-rata engagement di bawah ambang
          -> dipakai EchoBee buat balas komentar lebih agresif.
        Disimpan ke metrix_bias.json, dibaca modul lain lewat load_bias().
        """
        results = report_summary.get("detailed_metrics") or []
        top_n = results[:3]

        niches, hooks, keywords = [], [], []
        for r in top_n:
            if r.get("niche") and r["niche"] not in niches:
                niches.append(r["niche"])
            if r.get("hook") and r["hook"] not in hooks and r["hook"] != "-":
                hooks.append(r["hook"])
            keywords.extend(self._keywords(r.get("topic", ""), limit=3))
        keywords = list(dict.fromkeys(keywords))[:8]   # unik, pertahankan urutan

        avg_engagement = report_summary.get("aggregate_stats", {}).get("avg_engagement_rate", 0)
        top = report_summary.get("top_performer")
        avg_score = (sum(r["score"] for r in results) / len(results)) if results else 0

        bias = {
            "generated_at": report_summary.get("generated_at"),
            "winning_niches": niches,
            "winning_hooks": hooks,
            "winning_keywords": keywords,
            "top_topic": top.get("topic") if top else None,
            "avg_engagement_rate": avg_engagement,
            "avg_score": round(avg_score, 1),
            "boost_comments": avg_score < LOW_SCORE_THRESHOLD,
        }
        try:
            with open(BIAS_FILE, "w", encoding="utf-8") as f:
                json.dump(bias, f, indent=2, ensure_ascii=False)
            print(f"🎯 [{self.agent_name}] Bias engagement disimpan ({len(niches)} niche, "
                  f"{len(keywords)} keyword, boost_comments={bias['boost_comments']}).")
        except OSError as exc:
            print(f"⚠️ [{self.agent_name}] Gagal menyimpan bias engagement: {exc}")
        return bias


def analyze_and_report():
    """Fungsi utama pendukung untuk eksekusi cepat Metrix."""
    analyst = MetrixDataAnalyst()
    return analyst.generate_ceo_report()

if __name__ == "__main__":
    analyze_and_report()