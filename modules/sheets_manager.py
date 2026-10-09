import json
import os
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

# Scope API Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
DEFAULT_SHEET = "Shorts Content Planner"


@lru_cache(maxsize=4)
def _client(credentials_path):
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def get_sheet_client(credentials_path=None):
    """Koneksi ke Google Sheets API (client di-cache -> tidak login ulang di tiap panggilan)."""
    return _client(credentials_path or os.getenv("GOOGLE_CREDENTIALS", "google_credentials.json"))


def _sheet(sheet_name):
    return get_sheet_client().open(sheet_name).sheet1


def fetch_next_ready_row(sheet_name=DEFAULT_SHEET):
    """Mengambil baris pertama yang berstatus 'Ready'."""
    records = _sheet(sheet_name).get_all_records()
    for idx, row in enumerate(records, start=2):  # baris 1 = header
        if str(row.get("Status", "")).strip().lower() == "ready":
            return {
                "row_index": idx,
                "niche": row.get("Niche") or "Fakta Sejarah",
                "topic": row.get("Topic") or "Topik Menarik",
                "hook_style": row.get("Hook Style") or "Penasaran",
            }
    return None


def update_row_status(row_index, status, video_path="", sheet_name=DEFAULT_SHEET):
    """Memperbarui kolom Status (E) dan Video Output (F) dalam SATU request API."""
    data = [{"range": f"E{row_index}", "values": [[status]]}]
    if video_path:
        data.append({"range": f"F{row_index}", "values": [[str(video_path)]]})
    _sheet(sheet_name).batch_update(data)


def generate_content_ideas_to_sheet(count=5, sheet_name=DEFAULT_SHEET):
    """
    Menghasilkan ide konten via AI (Ollama/Groq sesuai modul script_gen) lalu mengisinya ke Sheets.
    Fokus HANYA pada 2 niche: 'Fakta Sejarah' dan 'Misteri Alam Semesta'.
    """
    from modules.script_gen import get_llm_response
    print(f"🤖 Meminta AI membuat {count} ide konten baru (Fokus: Fakta Sejarah & Misteri Alam Semesta)...")

    prompt = f"""Buatkan {count} ide konten YouTube Shorts yang sangat unik, segar, tidak pasaran, dan berpotensi viral.

    ATURAN NICHE (SANGAT KETAT):
    Setiap ide WAJIB menggunakan salah satu dari 2 Niche berikut (DILARANG menggunakan niche lain):
    1. "Fakta Sejarah"
    2. "Misteri Alam Semesta"

    ATURAN KREATIVITAS & VARIASI (AGAR TIDAK REPETITIF):
    1. HINDARI topik klise/pasaran yang sudah sering dibahas seperti: Atlantis standar, Piramida Mesir biasa, Segitiga Bermuda, atau penjelasan umum tentang Lubang Hitam.
    2. Cari sudut pandang spesifik, fenomena aneh yang jarang diketahui, fakta sejarah tersembunyi, penemuan kosmik membingungkan, atau konspirasi sains yang menarik.
    3. Variasikan `hook_style` agar tidak monoton (contoh: "Plot twist sejarah", "Pernyataan provokatif", "Fakta mengerikan", "Mind-bending paradox", "Pertanyaan melintasi zaman", "Misteri tak terpecahkan").
    4. Setiap judul/topik harus langsung memicu rasa penasaran tinggi dalam 3 detik pertama.

    Format respon WAJIB berupa JSON Array murni tanpa markdown ```json, tanpa penjelasan, atau teks tambahan:
    [
    {{"niche": "Fakta Sejarah", "topic": "Api Yunani: Senjata Rahasia Bizantium yang Resepnya Hilang Selamanya", "hook_style": "Fakta mengerikan"}},
    {{"niche": "Misteri Alam Semesta", "topic": "Awan Alkohol Raksasa di Luar Angkasa yang Membingungkan Astronom", "hook_style": "Bikin mikir keras"}},
    {{"niche": "Fakta Sejarah", "topic": "Wabah Menari 1518: Ketika Ratusan Orang Menari Sampai Tewas", "hook_style": "Bikin merinding"}},
    {{"niche": "Misteri Alam Semesta", "topic": "Planet Hujan Besi Cair yang Mengorbit Bintang Sekarat", "hook_style": "Mind-bending paradox"}}
    ]
    """

    try:
        response = get_llm_response(prompt)
        clean_res = response.replace("```json", "").replace("```", "").strip()
        a, b = clean_res.find("["), clean_res.rfind("]")           # toleran terhadap teks di luar array
        ideas = json.loads(clean_res[a:b + 1] if a != -1 and b != -1 else clean_res)

        sheet = _sheet(sheet_name)
        next_id = len(sheet.get_all_values())                       # 1x panggilan, bukan per ide
        rows = []
        for item in ideas:
            rows.append([next_id, item.get("niche", "Fakta Sejarah"), item.get("topic", "Topik Menarik"),
                         item.get("hook_style", "Penasaran"), "Ready", ""])
            next_id += 1
        sheet.append_rows(rows, value_input_option="USER_ENTERED")   # 1x request untuk semua baris
        for r in rows:
            print(f"  ✅ Ide ditambahkan: [{r[1]}] {r[2]} (Status: Ready)")
        print(f"🎉 Berhasil menambahkan {len(rows)} ide terfokus ke Google Sheets!")
    except Exception as e:
        print(f"❌ Gagal generate ide ke Sheets: {e}")


def fetch_all_planner_rows(sheet_name=DEFAULT_SHEET):
    """Mengambil seluruh baris data dari Google Sheets untuk ditampilkan di GUI Table."""
    try:
        records = _sheet(sheet_name).get_all_records()
        formatted_rows = []
        for idx, row in enumerate(records, start=2):  # header di baris 1
            status = str(row.get("Status", "Ready")).strip()
            video_path = str(row.get("Video Output") or row.get("Video Path") or "-").strip()
            formatted_rows.append({
                "id": f"{idx:03d}",
                "row_index": idx,
                "niche": row.get("Niche", "-"),
                "topic": row.get("Topic", "-"),
                "hook": row.get("Hook Style", "-"),
                "status": status,
                "output": video_path,
                "tag": status.lower(),  # 'ready', 'processing', 'done', 'failed'
            })
        return formatted_rows
    except Exception as e:
        print(f"❌ Gagal mengambil data dari Google Sheets: {e}")
        return []
