import json
import random
from modules.sheets_manager import _sheet, DEFAULT_SHEET
from modules.script_gen import get_llm_response

try:
    from modules.data_analyst import load_bias
except Exception:
    def load_bias():
        return {}

DEFAULT_NICHES = ["Fakta Sejarah", "Misteri Alam Semesta"]


def run_nexatrend_research(count=3, sheet_name=DEFAULT_SHEET, use_metrix_bias=True):
    """
    NexaTrend: Mengumpulkan ide viral menggunakan LLM dan menginject langsung ke Google Sheets.
    Bila use_metrix_bias=True, condongkan niche/hook ke pola yang terbukti laku (hasil Metrix).
    """
    print(f"🕵️‍♂️ NexaTrend: Menganalisa tren saat ini untuk mencari {count} topik viral...")

    bias = load_bias() if use_metrix_bias else {}
    winning_niches = bias.get("winning_niches") or []
    winning_hooks = bias.get("winning_hooks") or []
    winning_keywords = bias.get("winning_keywords") or []

    niches = winning_niches or DEFAULT_NICHES
    selected_niche = random.choice(niches)
    if winning_niches:
        print(f"📊 NexaTrend: Pakai bias Metrix — niche pemenang: {winning_niches}")
    print(f"📊 NexaTrend: Tren hari ini menunjuk ke kategori: '{selected_niche}'")

    bias_block = ""
    if winning_hooks or winning_keywords:
        bias_block = (
            f"\n    DATA PERFORMA TERBARU (dari Metrix, pakai sebagai referensi, bukan diulang mentah):\n"
            f"    - hook_style yang terbukti performa bagus: {winning_hooks or '-'}\n"
            f"    - keyword/topik yang terbukti disukai audiens: {winning_keywords or '-'}\n"
            f"    Condongkan ide baru ke pola ini tanpa mengulang topik yang sama persis.\n"
        )

    prompt = f"""Kamu adalah 'NexaTrend', seorang ahli riset tren YouTube Shorts.
    Buatkan {count} ide konten YouTube Shorts yang sangat unik, segar, tidak pasaran, dan berpotensi viral.

    ATURAN NICHE (SANGAT KETAT):
    Setiap ide WAJIB menggunakan Niche: "{selected_niche}".
{bias_block}
    ATURAN KREATIVITAS & VARIASI:
    1. Cari sudut pandang spesifik, fenomena aneh yang jarang diketahui, fakta sejarah tersembunyi, atau konspirasi sains yang menarik.
    2. Variasikan `hook_style` (contoh: "Plot twist sejarah", "Pernyataan provokatif", "Fakta mengerikan", "Mind-bending paradox").
    3. Setiap judul/topik harus langsung memicu rasa penasaran tinggi dalam 3 detik pertama.

    Format respon WAJIB berupa JSON Array murni tanpa markdown, tanpa penjelasan:
    [
      {{"niche": "{selected_niche}", "topic": "Api Yunani: Senjata Rahasia Bizantium yang Resepnya Hilang Selamanya", "hook_style": "Fakta mengerikan"}}
    ]
    """

    try:
        response = get_llm_response(prompt)
        clean_res = response.replace("```json", "").replace("```", "").strip()
        
        a, b = clean_res.find("["), clean_res.rfind("]")           
        ideas = json.loads(clean_res[a:b + 1] if a != -1 and b != -1 else clean_res)

        sheet = _sheet(sheet_name)
        next_id = len(sheet.get_all_values())                       
        rows = []
        for item in ideas:
            rows.append([
                next_id, 
                item.get("niche", selected_niche), 
                item.get("topic", "Topik Menarik"),
                item.get("hook_style", "Penasaran"), 
                "Ready", 
                ""
            ])
            next_id += 1
            
        sheet.append_rows(rows, value_input_option="USER_ENTERED")   
        for r in rows:
            print(f"  ✅ NexaTrend menambahkan: [{r[1]}] {r[2]} (Status: Ready)")
            
        print(f"🎉 NexaTrend berhasil menyetorkan {len(rows)} ide ke Google Sheets!")
        return len(rows)
        
    except Exception as e:
        print(f"❌ NexaTrend gagal melakukan riset: {e}")
        return 0