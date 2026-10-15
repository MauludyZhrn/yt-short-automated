"""
modules/trend_researcher.py
===========================
NexaTrend — Trend Researcher Agent.

Tugas utamanya sekarang: **mengecek tren untuk SETIAP platform**, bukan sekadar membuat
daftar ide generik. Setiap platform punya karakter algoritma & format sendiri, jadi
NexaTrend menjalankan satu sesi riset per platform:

    YouTube Shorts  -> retensi + curiosity gap + Search
    TikTok          -> completion rate + hook 1 detik + tren audio
    Instagram Reels -> saves/shares + estetika + konten "saveable"
    Facebook Reels  -> komentar & share + nostalgia + kisah komunitas

Hasil riset langsung ditandai platform-nya di Google Sheets (kolom ke-7) sekaligus
disimpan ke row_platforms.json, sehingga CrossByte tahu ide itu harus tayang di mana.
"""
import json
import math
import random

from modules.sheets_manager import _sheet, DEFAULT_SHEET
from modules.script_gen import get_llm_response

try:
    from modules.data_analyst import load_bias
except Exception:                                             # noqa: BLE001
    def load_bias():
        return {}

try:
    from modules import row_platforms
except Exception:                                             # noqa: BLE001
    row_platforms = None

try:
    from modules import social_real as social
except Exception:                                             # noqa: BLE001
    social = None


DEFAULT_NICHES = ["Fakta Sejarah", "Misteri Alam Semesta"]
PLATFORM_ORDER = ("youtube", "tiktok", "instagram", "facebook")

# Karakter tren tiap platform — jadi "kacamata" NexaTrend saat riset.
PLATFORM_TREND_BRIEF = {
    "youtube": {
        "label": "YouTube Shorts",
        "icon": "fi-brands-youtube",
        "color": "#FF0000",
        "brief": (
            "Algoritma Shorts menghargai retensi dan watch time. Judul harus menjanjikan "
            "curiosity gap yang terjawab di akhir video. Durasi ideal 30-55 detik. Judul, deskripsi "
            "dan tag masih berpengaruh ke Search & Suggested. Tren yang cocok: fakta cepat, "
            "'tahukah kamu', misteri sejarah, sebelum/sesudah, penjelasan 30 detik."
        ),
    },
    "tiktok": {
        "label": "TikTok",
        "icon": "fi-brands-tiktok",
        "color": "#000000",
        "brief": (
            "FYP digerakkan completion rate, rewatch, dan komentar. Hook visual WAJIB kuat di "
            "1 detik pertama. Durasi optimal 15-30 detik. Tren audio, efek transisi, dan teks "
            "besar di layar sangat berpengaruh. Caption pendek + 3-5 hashtag niche. Tren yang "
            "cocok: POV, storytime, reaksi, fakta mengejutkan, 'aku baru tahu'."
        ),
    },
    "instagram": {
        "label": "Instagram Reels",
        "icon": "fi-brands-instagram",
        "color": "#C13584",
        "brief": (
            "Reels didorong oleh saves dan shares. Estetika visual rapi dan teks on-screen yang "
            "enak dibaca penting. Durasi 15-30 detik. Audiens suka konten yang layak disimpan: "
            "tips, fakta, listicle, sebelum/sesudah. Caption bisa lebih panjang, 5-10 hashtag. "
            "Tren: carousel-Reels, 'comment X for part 2', rangkuman fakta."
        ),
    },
    "facebook": {
        "label": "Facebook Reels",
        "icon": "fi-brands-facebook",
        "color": "#1877F2",
        "brief": (
            "Reels menjangkau audiens yang lebih tua dan berbasis komunitas. Konten yang memicu "
            "komentar & share (nostalgia, kisah nyata, 'setuju?') paling kuat. Durasi 30-60 detik. "
            "Caption naratif 1-2 paragraf, hashtag secukupnya. Tren: nostalgia 90-an, kisah lokal, "
            "fakta kehidupan sehari-hari, misteri yang bikin debat."
        ),
    },
}


def platform_label(pid):
    return PLATFORM_TREND_BRIEF.get(pid, {}).get("label", pid)


def connected_platforms():
    """Platform yang benar-benar bisa dipakai saat ini (YouTube selalu dihitung)."""
    out = ["youtube"]
    if social is None:
        return out
    try:
        accounts = social.get_accounts() or {}
    except Exception:                                         # noqa: BLE001
        accounts = {}
    for pid in PLATFORM_ORDER:
        if pid != "youtube" and accounts.get(pid) and pid not in out:
            out.append(pid)
    return out


def platform_bias(pid, bias=None):
    """Ambil data performa AKUN INI di satu platform (hasil olahan Metrix)."""
    bias = bias if bias is not None else (load_bias() or {})
    by_p = (bias.get("by_platform") or {}) if isinstance(bias, dict) else {}
    return (by_p.get(pid) or {}) if isinstance(by_p, dict) else {}


def trend_snapshot(platforms=None, use_metrix=True):
    """Ringkasan tren per platform untuk UI: karakter platform + pemenang terakhir.

    Tidak memanggil LLM (cepat, aman dipanggil berkali-kali dari web).
    """
    bias = (load_bias() if use_metrix else {}) or {}
    conn = connected_platforms()
    out = []
    for pid in (platforms or PLATFORM_ORDER):
        spec = PLATFORM_TREND_BRIEF.get(pid, {"label": pid, "icon": "fi-rr-share", "color": "#6B7280", "brief": ""})
        pb = platform_bias(pid, bias)
        out.append({
            "id": pid,
            "label": spec.get("label", pid),
            "icon": spec.get("icon", "fi-rr-share"),
            "color": spec.get("color", "#6B7280"),
            "brief": spec.get("brief", ""),
            "connected": pid in conn,
            "winning_niches": pb.get("winning_niches") or (bias.get("winning_niches") or []),
            "winning_hooks": pb.get("winning_hooks") or (bias.get("winning_hooks") or []),
            "winning_keywords": pb.get("winning_keywords") or (bias.get("winning_keywords") or []),
            "avg_engagement_rate": pb.get("avg_engagement_rate", bias.get("avg_engagement_rate")),
            "videos": pb.get("videos"),
        })
    return out


def _bias_block(pb, global_bias):
    """Blok prompt berisi data performa — per platform, fallback ke global."""
    niches = pb.get("winning_niches") or global_bias.get("winning_niches") or []
    hooks = pb.get("winning_hooks") or global_bias.get("winning_hooks") or []
    keywords = pb.get("winning_keywords") or global_bias.get("winning_keywords") or []
    if not (niches or hooks or keywords):
        return ""
    extra = ""
    if pb.get("avg_engagement_rate") is not None:
        extra = f"    - rata-rata engagement di platform ini: {pb['avg_engagement_rate']}%\n"
    return (
        "\n    DATA PERFORMA AKUN INI di platform tersebut (dari Metrix, pakai sebagai referensi, bukan diulang mentah):\n"
        f"    - niche yang terbukti laku: {niches or '-'}\n"
        f"    - hook_style yang terbukti laku: {hooks or '-'}\n"
        f"    - keyword/topik yang disukai audiens: {keywords or '-'}\n"
        f"{extra}"
        "    Condongkan ide baru ke pola ini tanpa mengulang topik yang sama persis.\n"
    )


def _prompt_for(pid, count, selected_niche, pb, global_bias):
    spec = PLATFORM_TREND_BRIEF[pid]
    return f"""Kamu adalah 'NexaTrend', analis tren yang sedang memantau {spec['label']}.

    TUGAS:
    1. Bayangkan apa yang SEDANG NAIK di {spec['label']} saat ini (format, gaya hook, durasi, topik).
    2. Berikan {count} ide konten video pendek yang paling cocok untuk platform itu.

    KARAKTER & TREN {spec['label'].upper()}:
    {spec['brief']}

    ATURAN NICHE (KETAT):
    Setiap ide WAJIB memakai niche: "{selected_niche}".
{_bias_block(pb, global_bias)}
    ATURAN KREATIVITAS:
    1. Cari sudut pandang spesifik, fenomena aneh, fakta tersembunyi, atau paradoks sains.
    2. Variasikan `hook_style` (contoh: "Plot twist sejarah", "Pernyataan provokatif", "Fakta mengerikan", "Mind-bending paradox").
    3. 3 detik pertama harus memicu rasa penasaran tinggi.
    4. `trend_note`: satu kalimat berisi sinyal tren {spec['label']} yang kamu pakai untuk ide itu.

    Format respon WAJIB JSON Array murni, tanpa markdown, tanpa penjelasan:
    [
      {{"niche": "{selected_niche}", "topic": "Api Yunani: Senjata Rahasia Bizantium yang Resepnya Hilang Selamanya", "hook_style": "Fakta mengerikan", "trend_note": "Format fakta 30 detik dengan teks besar sedang naik di {spec['label']}."}}
    ]
    """


def _parse_ideas(response):
    clean = str(response or "").replace("```json", "").replace("```", "").strip()
    a, b = clean.find("["), clean.rfind("]")
    data = json.loads(clean[a:b + 1] if a != -1 and b != -1 else clean)
    if isinstance(data, dict):                      # kadang LLM membungkus dengan {"ideas": [...]}
        for key in ("ideas", "data", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def run_nexatrend_research(count=3, sheet_name=DEFAULT_SHEET, use_metrix_bias=True,
                           platforms=None, per_platform=None):
    """Riset tren per platform lalu inject ide ke Google Sheets.

    count        : total ide yang diinginkan (dibagi rata ke tiap platform)
    platforms    : daftar platform yang mau dicek tren-nya (default: yang terhubung)
    per_platform : jumlah ide per platform (override pembagian `count`)

    Return dict: {"added": n, "per_platform": {pid: n}, "platforms": [...], "ideas": [...]}
    """
    targets = [p for p in (platforms or connected_platforms()) if p in PLATFORM_TREND_BRIEF] or ["youtube"]
    total = max(1, int(count or 1))
    per = max(1, int(per_platform or math.ceil(total / len(targets))))

    print(f"🕵️‍♂️ NexaTrend: mengecek tren di {len(targets)} platform "
          f"({', '.join(platform_label(p) for p in targets)}) — target {per} ide/platform...")

    bias = (load_bias() if use_metrix_bias else {}) or {}
    winning_niches = bias.get("winning_niches") or []
    niches = winning_niches or DEFAULT_NICHES
    if winning_niches:
        print(f"📊 NexaTrend: bias Metrix aktif — niche pemenang: {winning_niches}")

    ideas, per_done = [], {}
    for pid in targets:
        pb = platform_bias(pid, bias)
        selected_niche = random.choice(pb.get("winning_niches") or niches)
        print(f"📡 NexaTrend [{platform_label(pid)}]: tren hari ini → niche '{selected_niche}'")
        try:
            raw = get_llm_response(_prompt_for(pid, per, selected_niche, pb, bias))
            got = _parse_ideas(raw)[:per]
        except Exception as exc:                              # noqa: BLE001
            print(f"❌ NexaTrend gagal riset untuk {platform_label(pid)}: {exc}")
            got = []
        if not got:
            print(f"⚠️ NexaTrend [{platform_label(pid)}]: tidak ada ide yang berhasil diurai, dilewati.")
            per_done[pid] = 0
            continue
        for item in got:
            ideas.append({
                "niche": item.get("niche") or selected_niche,
                "topic": item.get("topic") or "Topik Menarik",
                "hook_style": item.get("hook_style") or "Penasaran",
                "platform": pid,
                "trend_note": item.get("trend_note") or "",
            })
        per_done[pid] = len(got)
        print(f"  ✅ NexaTrend [{platform_label(pid)}]: {len(got)} ide — {got[0].get('topic', '')[:60]}")

    if not ideas:
        print("❌ NexaTrend: tidak ada ide dari semua platform. Sheets tidak diubah.")
        return {"added": 0, "per_platform": per_done, "platforms": targets, "ideas": []}

    try:
        sheet = _sheet(sheet_name)
        next_id = len(sheet.get_all_values())
        rows, pairs = [], []
        for item in ideas:
            rows.append([
                next_id,
                item["niche"],
                item["topic"],
                item["hook_style"],
                "Ready",
                "",
                item["platform"],           # kolom ke-7: target publish baris ini
            ])
            pairs.append((next_id, item["platform"]))
            if item["trend_note"]:
                print(f"     📈 [{platform_label(item['platform'])}] {item['trend_note']}")
            print(f"  ✅ NexaTrend menambahkan #{next_id}: [{item['niche']}] {item['topic']} "
                  f"→ {platform_label(item['platform'])} (Status: Ready)")
            next_id += 1

        sheet.append_rows(rows, value_input_option="USER_ENTERED")

        # Simpan target platform per baris (sumber kebenaran untuk CrossByte & UI)
        if row_platforms is not None:
            try:
                row_platforms.set_many(pairs, sheet_name=sheet_name)
            except Exception as exc:                          # noqa: BLE001
                print(f"⚠️ NexaTrend: gagal menyimpan target platform per baris: {exc}")

        print(f"🎉 NexaTrend berhasil menyetorkan {len(rows)} ide ke Google Sheets "
              f"({', '.join(f'{platform_label(p)}: {n}' for p, n in per_done.items() if n)}).")
        return {"added": len(rows), "per_platform": per_done, "platforms": targets, "ideas": ideas}

    except Exception as exc:                                  # noqa: BLE001
        print(f"❌ NexaTrend gagal menulis ke Google Sheets: {exc}")
        return {"added": 0, "per_platform": per_done, "platforms": targets, "ideas": ideas}
