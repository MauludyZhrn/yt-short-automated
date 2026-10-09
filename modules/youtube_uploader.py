"""
modules/youtube_uploader.py — Upload YouTube Shorts + generator copywriting & SEO.

Yang baru:
- build_seo_metadata()   : judul (5 variasi hook), deskripsi terstruktur, hashtag, dan tags otomatis.
- analyze_metadata()     : audit SEO (checklist + skor) untuk ditampilkan di GUI sebelum publish.
- parse_schedule()       : jadwal publish (waktu lokal -> UTC RFC3339).
- upload_video_to_youtube(): API lama tetap kompatibel; ditambah publish_at, synthetic_media,
                             bahasa default, notifikasi subscriber, retry, dan progress callback.

Library Google di-import lazy, jadi modul ini ringan di-import dari GUI hanya untuk helper SEO.
"""
import os
import re
import time
import pickle
from datetime import datetime, timezone, timedelta


SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]  # readonly: dipakai Metrix (data_analyst.py) baca statistik video

CHANNEL_NAME = "MorbMyth"
SHORTS_TAG = "#Shorts"

TITLE_MAX = 100
DESC_MAX_BYTES = 5000
TAGS_MAX_CHARS = 500
TAGS_SOFT_LIMIT = 450          # sisakan ruang aman (tag berspasi dihitung + tanda kutip)
VISIBLE_TITLE_IDEAL = 70       # judul di atas ini sering terpotong di feed/pencarian

# Nama kategori -> categoryId resmi YouTube
CATEGORIES = {
    "Education": "27",
    "Science & Technology": "28",
    "Entertainment": "24",
    "People & Blogs": "22",
    "News & Politics": "25",
}
DEFAULT_CATEGORY_NAME = "Education"

RETRIABLE_STATUS = {500, 502, 503, 504}
MAX_UPLOAD_RETRIES = 6


# ============================================================
# 1) HELPER TEKS
# ============================================================
def _sanitize(text):
    """YouTube API menolak '<' dan '>' di judul/deskripsi; buang juga karakter kontrol."""
    text = str(text or "")
    text = text.replace("<", "").replace(">", "")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def _clean_topic(topic):
    topic = re.sub(r"\s+", " ", _sanitize(topic)).strip()
    return topic.rstrip(" .!?:;,-–—")


def _truncate_words(text, limit):
    """Potong di batas kata (bukan di tengah kata) dan tanpa tanda baca menggantung."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" .!?:;,-–—") or text[:limit]


def make_hashtag(text, max_words=4, max_len=30):
    """'Misteri Segitiga Bermuda' -> '#MisteriSegitigaBermuda' (None jika tidak layak)."""
    words = re.findall(r"[0-9A-Za-zÀ-ÿ]+", str(text or ""))
    if not words or len(words) > max_words:
        return None
    tag = "".join(w[:1].upper() + w[1:] for w in words)
    return f"#{tag}" if len(tag) <= max_len else None


def _dedupe(items):
    seen, out = set(), []
    for it in items:
        key = it.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(it.strip())
    return out


def _tags_cost(tags):
    """Panjang tags menurut YouTube: tag berspasi dihitung dengan tanda kutip; koma sebagai pemisah."""
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)


def fit_tags(tags, limit=TAGS_SOFT_LIMIT):
    out = []
    for t in _dedupe([_sanitize(t).replace(",", " ").strip() for t in tags]):
        if len(t) > 60:
            continue
        if _tags_cost(out + [t]) <= limit:
            out.append(t)
    return out


def finalize_title(title):
    """Pastikan judul berakhiran #Shorts dan muat 100 karakter (yang dipotong adalah isi, bukan tag)."""
    title = re.sub(r"\s+", " ", _sanitize(title)).strip()
    if "#shorts" in title.lower():
        return title[:TITLE_MAX]
    room = TITLE_MAX - len(SHORTS_TAG) - 1
    return f"{_truncate_words(title, room)} {SHORTS_TAG}"


# ============================================================
# 2) COPYWRITING & SEO
# ============================================================
# {t} = topik. Pola dipilih agar ada curiosity gap + kata kunci di awal.
TITLE_PATTERNS = [
    "{t}: Fakta yang Jarang Diketahui",
    "Ternyata Ini Rahasia di Balik {t}",
    "{t} — Ini yang Tidak Pernah Diceritakan",
    "Banyak Orang Salah Paham Soal {t}",
    "{t}: Ini Faktanya!",
]


def build_title_variants(topic, hook=""):
    """Daftar judul (sudah lengkap dengan #Shorts) diurutkan dari yang paling direkomendasikan."""
    t = _clean_topic(topic)
    if not t:
        return [finalize_title("Fakta Unik Hari Ini")]

    variants = []
    hook = _clean_topic(hook)
    # Topik yang sudah berupa kalimat/pertanyaan panjang sudah cukup 'menjual': pakai apa adanya.
    if len(t) >= 45 or str(topic).strip().endswith("?"):
        variants.append(t + ("?" if str(topic).strip().endswith("?") else ""))
    if hook and 25 <= len(hook) <= 70:
        variants.append(hook)
    room = TITLE_MAX - len(SHORTS_TAG) - 1
    for pat in TITLE_PATTERNS:
        candidate = pat.format(t=t)
        if len(candidate) <= room:            # pola yang tidak muat dibuang, bukan dipotong
            variants.append(candidate)
    if not variants:                          # topik sangat panjang: pakai topik saja
        variants.append(t)

    final = []
    for v in variants:
        f = finalize_title(_truncate_words(v, room))
        if f not in final:
            final.append(f)
    return final


def build_hashtags(topic, niche="", channel_name=CHANNEL_NAME):
    """
    Maks. 4 hashtag di deskripsi (+ #Shorts di judul = 5 total, batas ideal).
    Spesifik topik dulu, lalu niche & umum.
    """
    candidates = [
        make_hashtag(_clean_topic(topic)),
        make_hashtag(niche),
        "#FaktaUnik",
        f"#{channel_name}",
        "#Edukasi",
    ]
    return _dedupe([c for c in candidates if c])[:4]


def build_tags(topic, niche="", channel_name=CHANNEL_NAME):
    t = _clean_topic(topic).lower()
    n = str(niche or "").strip().lower()
    tags = [
        t,
        f"{t} fakta" if t else "",
        f"fakta {t}" if t else "",
        n,
        f"fakta {n}" if n else "",
        "shorts",
        "youtube shorts",
        "fakta unik",
        "fakta menarik",
        "fakta sejarah",
        "misteri",
        "edukasi",
        "tahukah kamu",
        channel_name.lower(),
    ]
    return fit_tags([x for x in tags if x])


def build_description(topic, niche="", hook="", channel_name=CHANNEL_NAME, hashtags=None,
                      disclose_ai=True):
    """
    Struktur deskripsi (dirancang untuk Shorts):
      1) Baris hook + kata kunci (±125 karakter pertama yang terlihat tanpa 'Lihat selengkapnya')
      2) Ringkasan singkat
      3) CTA (tonton sampai habis, subscribe, komentar)
      4) Hashtag
      5) Disclosure konten AI
    """
    t = _clean_topic(topic) or "fakta unik hari ini"
    n = str(niche or "").strip()
    hook = _sanitize(hook).strip()
    hashtags = hashtags if hashtags is not None else build_hashtags(topic, niche, channel_name)

    lead = hook if hook else f"{t} — fakta singkat yang bikin kamu berpikir dua kali."
    if t.lower() not in lead.lower():
        lead = f"{t}: {lead}"

    where = f" dalam kategori {n}" if n else ""
    summary = (
        f"Di video Shorts ini kita bahas {t}{where} secara singkat, padat, dan mudah dipahami. "
        f"Cocok buat kamu yang suka {('fakta ' + n.lower()) if n else 'fakta unik'} "
        f"tapi tidak punya waktu untuk artikel panjang."
    )

    cta = (
        "👉 Tonton sampai habis, ada fakta terakhir yang paling mengejutkan.\n"
        f"🔔 Subscribe {channel_name} untuk fakta menarik setiap hari.\n"
        "💬 Menurutmu bagaimana? Tulis pendapatmu di kolom komentar!"
    )

    parts = [lead, summary, cta, " ".join(hashtags)]
    if disclose_ai:
        parts.append("ℹ️ Narasi memakai suara AI (text-to-speech) dan visual ilustrasi.")
    return _sanitize("\n\n".join(p for p in parts if p))


def build_seo_metadata(topic, niche="", hook="", channel_name=CHANNEL_NAME, variant=0,
                       disclose_ai=True):
    """
    Satu pintu untuk GUI/pipeline. `variant` memilih judul (siklus otomatis).
    Return dict: title, description, tags(list), hashtags(list), title_variants(list), variant(int)
    """
    variants = build_title_variants(topic, hook)
    idx = variant % len(variants)
    hashtags = build_hashtags(topic, niche, channel_name)
    return {
        "title": variants[idx],
        "description": build_description(topic, niche, hook, channel_name, hashtags, disclose_ai),
        "tags": build_tags(topic, niche, channel_name),
        "hashtags": hashtags,
        "title_variants": variants,
        "variant": idx,
    }


# ============================================================
# 3) AUDIT METADATA (dipakai GUI sebelum publish)
# ============================================================
_HASHTAG_RE = re.compile(r"(?<!\w)#[0-9A-Za-zÀ-ÿ_]+")
_CTA_WORDS = ("subscribe", "langganan", "like", "komentar", "comment", "follow", "tonton")


def analyze_metadata(title, description, tags, topic=""):
    """
    Return dict:
      checks : [(status, pesan)]  status ∈ {"ok","warn","err"}
      errors : [str]  -> harus diperbaiki (upload akan gagal / ditolak)
      warnings: [str] -> saran perbaikan
      score  : 0..100
      counts : {"title","desc_bytes","tags","hashtags"}
    """
    checks = []

    def add(status, msg):
        checks.append((status, msg))

    eff_title = finalize_title(title) if str(title).strip() else ""
    desc = str(description or "")
    desc_bytes = len(desc.encode("utf-8"))
    tag_list = [t for t in (tags or []) if str(t).strip()]
    tag_cost = _tags_cost(tag_list)
    hashtags = _HASHTAG_RE.findall(f"{eff_title}\n{desc}")

    # --- Judul
    if not eff_title:
        add("err", "Judul kosong.")
    elif len(eff_title) > TITLE_MAX:
        add("err", f"Judul {len(eff_title)}/{TITLE_MAX} karakter (terlalu panjang).")
    else:
        body_len = len(eff_title.replace(SHORTS_TAG, "").strip())
        if body_len < 25:
            add("warn", f"Judul cukup pendek ({body_len} karakter). Tambahkan kata kunci / hook.")
        elif len(eff_title) > VISIBLE_TITLE_IDEAL + len(SHORTS_TAG):
            add("warn", f"Judul {len(eff_title)} karakter — berisiko terpotong di feed. Ideal ≤ {VISIBLE_TITLE_IDEAL}.")
        else:
            add("ok", f"Panjang judul pas ({len(eff_title)} karakter, #Shorts otomatis).")

    if "<" in title or ">" in title or "<" in desc or ">" in desc:
        add("err", "Karakter '<' atau '>' tidak diizinkan YouTube (akan dibuang otomatis).")

    # --- Kata kunci di judul & 125 karakter pertama deskripsi
    kw = [w for w in re.findall(r"[0-9A-Za-zÀ-ÿ]+", str(topic).lower()) if len(w) > 3]
    if kw:
        if any(w in eff_title.lower() for w in kw):
            add("ok", "Kata kunci topik ada di judul.")
        else:
            add("warn", "Kata kunci topik belum ada di judul.")
        if any(w in desc[:125].lower() for w in kw):
            add("ok", "Kata kunci ada di 125 karakter pertama deskripsi.")
        else:
            add("warn", "Taruh kata kunci di 125 karakter pertama deskripsi (bagian yang terlihat).")

    # --- Deskripsi
    if desc_bytes > DESC_MAX_BYTES:
        add("err", f"Deskripsi {desc_bytes}/{DESC_MAX_BYTES} byte (terlalu panjang).")
    elif len(desc.strip()) < 120:
        add("warn", "Deskripsi terlalu singkat; tambahkan ringkasan & CTA.")
    else:
        add("ok", f"Deskripsi lengkap ({desc_bytes}/{DESC_MAX_BYTES} byte).")

    if any(w in desc.lower() for w in _CTA_WORDS):
        add("ok", "Ada ajakan aksi (CTA) di deskripsi.")
    else:
        add("warn", "Belum ada CTA (subscribe / komentar) di deskripsi.")

    # --- Hashtag
    n_h = len(hashtags)
    if n_h > 15:
        add("err", f"{n_h} hashtag — YouTube mengabaikan SEMUA hashtag jika lebih dari 15.")
    elif n_h > 5:
        add("warn", f"{n_h} hashtag — terlalu banyak, ideal 3–5.")
    elif n_h < 3:
        add("warn", f"Baru {n_h} hashtag — ideal 3–5 (3 pertama tampil di atas judul).")
    else:
        add("ok", f"{n_h} hashtag (ideal 3–5).")

    # --- Tags
    if tag_cost > TAGS_MAX_CHARS:
        add("err", f"Tags {tag_cost}/{TAGS_MAX_CHARS} karakter (melebihi batas).")
    elif len(tag_list) < 5:
        add("warn", f"Baru {len(tag_list)} tag — tambahkan variasi kata kunci (ideal 8–15).")
    else:
        add("ok", f"{len(tag_list)} tag ({tag_cost}/{TAGS_MAX_CHARS} karakter).")

    weights = {"ok": 1.0, "warn": 0.5, "err": 0.0}
    score = round(100 * sum(weights[s] for s, _ in checks) / max(1, len(checks)))
    return {
        "checks": checks,
        "errors": [m for s, m in checks if s == "err"],
        "warnings": [m for s, m in checks if s == "warn"],
        "score": score,
        "counts": {
            "title": len(eff_title),
            "desc_bytes": desc_bytes,
            "tags": tag_cost,
            "hashtags": n_h,
        },
    }


# ============================================================
# 4) JADWAL PUBLISH
# ============================================================
def parse_schedule(text, min_minutes_ahead=10):
    """
    Terima waktu LOKAL ("2026-10-05 19:30" atau "05/10/2026 19:30"),
    kembalikan string RFC3339 UTC untuk `status.publishAt`.
    """
    text = str(text or "").strip()
    if not text:
        raise ValueError("Waktu jadwal kosong.")
    dt = None
    for fmt in ("%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        raise ValueError("Format jadwal salah. Gunakan YYYY-MM-DD HH:MM, contoh 2026-10-05 19:30")
    dt_utc = dt.astimezone().astimezone(timezone.utc)        # naive -> zona waktu komputer -> UTC
    if dt_utc < datetime.now(timezone.utc) + timedelta(minutes=min_minutes_ahead):
        raise ValueError(f"Jadwal harus minimal {min_minutes_ahead} menit dari sekarang.")
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ============================================================
# 5) AUTENTIKASI
# ============================================================
def get_authenticated_service(client_secret_file="client_secret.json", token_file="token.pickle"):
    """
    OAuth2 ke akun YouTube. Saat pertama kali dijalankan browser akan terbuka untuk login.
    Token yang kedaluwarsa di-refresh otomatis; jika refresh gagal (mis. akses dicabut)
    token dihapus dan login diulang.
    """
    import google_auth_oauthlib.flow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError

    creds = None
    if os.path.exists(token_file):
        try:
            with open(token_file, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None

    # Token lama tanpa scope baru (mis. Analytics) -> paksa login ulang sekali
    if creds and not set(SCOPES) <= set(getattr(creds, "scopes", None) or SCOPES):
        print("⚠️ Token lama kurang scope (Analytics). Login ulang diperlukan.")
        creds = None

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            print("🔄 Refreshing YouTube API Token...")
            creds.refresh(Request())
        except RefreshError:
            print("⚠️ Refresh token ditolak, login ulang diperlukan.")
            creds = None
            try:
                os.remove(token_file)
            except OSError:
                pass

    if not creds or not creds.valid:
        if not os.path.exists(client_secret_file):
            raise FileNotFoundError(
                f"❌ File '{client_secret_file}' tidak ditemukan! "
                "Pastikan kamu sudah menaruh file OAuth Client ID dari Google Cloud Console di root folder."
            )
        print("🔑 Membuka browser untuk login ke akun YouTube...")
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secret_file, SCOPES
        )
        creds = flow.run_local_server(port=0)

    with open(token_file, "wb") as token:
        pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


# ============================================================
# 6) UPLOAD
# ============================================================
def upload_video_to_youtube(
    video_path,
    title,
    description,
    tags=None,
    category_id="27",
    privacy_status="public",
    publish_at=None,
    synthetic_media=None,
    default_language="id",
    notify_subscribers=True,
    progress_callback=None,
):
    """
    Unggah video ke YouTube Shorts.

    - publish_at        : string RFC3339 UTC (lihat parse_schedule). Jika diisi, video diunggah
                          sebagai 'private' lalu tayang otomatis pada waktu tersebut.
    - synthetic_media   : True/False untuk mengisi disclosure "konten hasil AI/dimodifikasi"
                          (status.containsSyntheticMedia). None = tidak diisi.
    - progress_callback : fungsi(percent:int) opsional untuk progress bar GUI.
    Return URL Shorts, atau None jika file tidak ada.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    if not video_path or not os.path.exists(video_path):
        print(f"❌ File video tidak ditemukan di path: {video_path}")
        return None

    title_final = finalize_title(title)
    if not title_final.replace(SHORTS_TAG, "").strip():
        raise ValueError("Judul video kosong.")

    description = _sanitize(description)
    while len(description.encode("utf-8")) > DESC_MAX_BYTES:      # potong aman per karakter
        description = description[:-50]
    description = description.strip()

    if tags is None:
        tags = build_tags(title, "")
    tags = fit_tags(tags, limit=TAGS_MAX_CHARS - 30)

    status = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at:
        status["privacyStatus"] = "private"       # syarat YouTube untuk video terjadwal
        status["publishAt"] = publish_at
    if synthetic_media is not None:
        status["containsSyntheticMedia"] = bool(synthetic_media)

    body = {
        "snippet": {
            "title": title_final,
            "description": description,
            "tags": tags,
            "categoryId": str(category_id),
            "defaultLanguage": default_language,
            "defaultAudioLanguage": default_language,
        },
        "status": status,
    }

    print(f"🚀 Memulai upload video ke YouTube: '{title_final}'"
          + (f" (dijadwalkan {publish_at})" if publish_at else "") + "...")

    youtube = get_authenticated_service()

    # Chunk 8 MB (kelipatan 256 KB): ada progress nyata + bisa dilanjutkan jika koneksi putus.
    media_body = MediaFileUpload(
        video_path, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4"
    )
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media_body,
        notifySubscribers=bool(notify_subscribers),
    )

    response, retries, last_pct = None, 0, -1
    while response is None:
        try:
            chunk_status, response = request.next_chunk()
            if chunk_status:
                pct = int(chunk_status.progress() * 100)
                if pct != last_pct:
                    last_pct = pct
                    print(f"  📤 Progress Upload: {pct}%")
                    if progress_callback:
                        progress_callback(pct)
            retries = 0
        except HttpError as err:
            code = getattr(err.resp, "status", 0)
            if code in RETRIABLE_STATUS and retries < MAX_UPLOAD_RETRIES:
                retries += 1
                wait = min(2 ** retries, 30)
                print(f"  ⚠️ Server error {code}, coba lagi dalam {wait}s ({retries}/{MAX_UPLOAD_RETRIES})")
                time.sleep(wait)
                continue
            content = (getattr(err, "content", b"") or b"").decode("utf-8", "ignore")
            
            # Cek jika batas jumlah upload harian channel YouTube habis
            if "uploadlimitexceeded" in content.lower() or "exceeded the number of videos" in content.lower():
                raise RuntimeError(
                    "⚠️ Batas maksimum upload harian YouTube tercapai (Akun Limit)! "
                    "Tunggu 24 jam atau lakukan verifikasi fitur tingkat lanjut di YouTube Studio."
                ) from err

            # Cek jika kuota YouTube Data API habis
            if code == 403 and "quota" in content.lower():
                raise RuntimeError(
                    "Kuota YouTube Data API harian habis (upload memakai ±1600 unit dari 10.000). "
                    "Coba lagi besok atau ajukan penambahan kuota di Google Cloud Console."
                ) from err
            raise
        except (ConnectionError, TimeoutError, OSError) as err:
            if retries < MAX_UPLOAD_RETRIES:
                retries += 1
                wait = min(2 ** retries, 30)
                print(f"  ⚠️ Koneksi bermasalah ({err}), coba lagi dalam {wait}s")
                time.sleep(wait)
                continue
            raise

    video_id = response.get("id")
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"🎉 SUKSES! Video berhasil terupload ke YouTube: {video_url}")
    if progress_callback:
        progress_callback(100)
    return video_url