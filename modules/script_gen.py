import json
import requests
from groq import Groq
from config.settings import GROQ_API_KEY

GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b"
]

# Target durasi: WAJIB di bawah batas YouTube Shorts 60.0 detik (dicek ByteGuard QC).
# TTS Indonesia ~2.6 kata/detik -> 130 kata ≈ 50 detik, beri marjin aman di bawah 60.
MIN_WORDS = 110
TARGET_WORDS = "125 - 145"
MAX_WORDS = 150          # ~57.7 detik di 2.6 kata/detik; hard cap, dipotong kalau LLM kelebihan
MAX_ATTEMPTS = 3
CALLOUT_TYPES = ("year", "stat", "keyword", "question", "percent", "compare", "timeline")
POSES = ("utama", "wow", "berfikir", "bertanya", "terkejut", "wink")


def get_llm_response(prompt):
    """
    Fungsi umum untuk mengirim prompt ke LLM.
    Mencoba Groq API terlebih dahulu, jika gagal beralih ke Ollama lokal.
    """
    # 1. Groq API
    if GROQ_API_KEY:
        for model_name in GROQ_MODELS:
            try:
                client = Groq(api_key=GROQ_API_KEY)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that outputs clean responses."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=8000,                              # output panjang + reasoning model
                    extra_body={"reasoning_effort": "low"}        # gpt-oss: jangan habiskan token untuk berpikir
                )
                choice = response.choices[0]
                text = (choice.message.content or "").strip()
                if not text:
                    raise ValueError(f"balasan kosong (finish_reason={choice.finish_reason})")
                print(f"  ⚡ Berhasil via Groq API (Model: {model_name})")
                return text
            except Exception as e:
                print(f"  ⚠️ Groq ({model_name}) error: {e}")

    # 2. Fallback Ollama (Lokal)
    print("🔄 Beralih ke Ollama (Local AI)...")
    try:
        ollama_url = "http://localhost:11434/api/generate"
        payload = {"model": "llama3.2", "prompt": prompt, "stream": False}
        res = requests.post(ollama_url, json=payload, timeout=300)
        if res.status_code == 200:
            return res.json().get("response", "").strip()
        raise Exception(f"Ollama HTTP Status: {res.status_code}")
    except Exception as e:
        raise Exception(f"💥 Gagal memproses prompt via Groq maupun Ollama: {e}")


def _parse_json(raw):
    clean = raw.replace("```json", "").replace("```", "").strip()
    a, b = clean.find("{"), clean.rfind("}")
    if a != -1 and b != -1:
        clean = clean[a:b + 1]
    return json.loads(clean)


def _normalize(data):
    """Lengkapi field opsional supaya pipeline tidak patah bila LLM lupa mengisi."""
    script = str(data.get("script", "")).strip()
    if not script:
        raise ValueError("Field 'script' kosong.")
    data["script"] = script

    prompts = [str(p).strip() for p in data.get("prompts", []) if str(p).strip()]
    if len(prompts) < 4:
        raise ValueError("Kurang dari 4 visual prompt.")
    data["prompts"] = prompts[:6]          # foto latar sedikit; sisanya motion graphic & infografis

    hook_text = str(data.get("hook_text", "")).strip().strip('"')
    if not hook_text:
        first = script.split(".")[0].split("?")[0].split("!")[0]
        hook_text = " ".join(first.split()[:6])
    data["hook_text"] = " ".join(hook_text.split()[:8])

    callouts = []
    for c in data.get("callouts", []) or []:
        if isinstance(c, dict) and c.get("text") and c.get("anchor"):
            ctype = str(c.get("type", "keyword")).lower()
            if ctype not in CALLOUT_TYPES:
                ctype = "keyword"
            item = {
                "type": ctype,
                "text": str(c["text"]).strip(),
                "sub": str(c.get("sub", "")).strip(),
                "anchor": str(c["anchor"]).strip(),
            }
            if str(c.get("pose", "")).lower() in POSES:
                item["pose"] = str(c["pose"]).lower()
            if isinstance(c.get("items"), list):
                item["items"] = c["items"]
            callouts.append(item)
    data["callouts"] = callouts
    return data


def _trim_to_word_cap(script, max_words):
    """Potong naskah ke <= max_words kata, berhenti di akhir kalimat terdekat biar TTS tidak terputus aneh."""
    words = script.split()
    if len(words) <= max_words:
        return script
    cut = " ".join(words[:max_words])
    last_end = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    if last_end >= int(len(cut) * 0.5):   # ada akhir kalimat yang cukup dekat batas -> pakai itu
        return cut[:last_end + 1].strip()
    return cut.rstrip(",;: ") + "."       # tidak ada akhir kalimat dekat -> potong paksa + tutup titik


def build_prompt(niche, topic, hook_style):
    return f"""
    Lo adalah storyteller YouTube Shorts ternama yang ahli membawakan cerita misteri.
    Buatkan naskah video tentang: {topic} (Niche: {niche}).
    Gaya Hook: {hook_style}.
    Tone: Penasaran, sinematik, misterius, dramatis (wajib sapaan santai 'lo/gue').

    STRUKTUR NASKAH WAJIB (urut):
    1. HOOK (2 kalimat, MAKS 25 kata): kalimat 1 = fakta/klaim paling gila atau mustahil dari topik ini, langsung tanpa basa-basi.
       Kalimat 2 = buka celah penasaran ("dan yang bikin lo merinding, ...").
       DILARANG pembuka basi: "Tahu nggak", "Halo guys", "Hari ini kita bahas", "Pernah nggak lo".
       Pilih SATU teknik: angka mengejutkan / pernyataan yang melawan logika / pertanyaan yang menusuk / "lo nggak bakal percaya".
    2. KONTEKS (2-3 kalimat): latar singkat, siapa/apa/kapan.
    3. BODY (3 bagian eskalasi, tiap bagian 3-4 kalimat): tiap bagian lebih mengejutkan dari sebelumnya,
       penuh detail konkret (angka, tahun, nama, tempat).
    4. RE-HOOK di tengah (1 kalimat): misal "Tapi tunggu, bagian paling gila belum lo dengar."
    5. TWIST (3-4 kalimat): fakta/plot twist puncak.
    6. OUTRO (2 kalimat): pertanyaan pancingan komentar + kalimat yang nyambung balik ke "HOOK awal" agar penonton replay.

    [PENTING - DURASI]: Panjang naskah {TARGET_WORDS} KATA (durasi bicara 48 - 56 detik). MINIMAL {MIN_WORDS} kata.
    JANGAN melebihi {MAX_WORDS} kata: video WAJIB di bawah 60 detik (batas YouTube Shorts).
    JANGAN masukkan petunjuk adegan seperti [musik dramatis]. Tulis angka tahun/angka penting dengan digit (contoh: 1518, 300 juta).
    [PENTING - TANPA SINGKATAN]: naskah dibacakan mesin suara. Tulis SEMUA kata secara lengkap, jangan disingkat:
    "kilometer" (bukan km), "kilogram" (bukan kg), "dan lain-lain" (bukan dll), "dan sebagainya" (bukan dsb),
    "yang" (bukan yg), "dengan" (bukan dgn), "untuk" (bukan utk), "Sebelum Masehi" (bukan SM), "Masehi" (bukan M),
    "derajat Celsius" (bukan °C), "persen" (bukan %), "Perserikatan Bangsa-Bangsa" (bukan PBB), "nomor" (bukan no.).

    Output DALAM FORMAT JSON MURNI:
    {{
        "script": "Teks naskah lengkap",
        "hook_text": "Teks overlay 3-6 kata KAPITAL yang memancing (contoh: 400 ORANG MENARI SAMPAI MATI)",
        "prompts": ["kw 1", "kw 2", "kw 3", "kw 4", "kw 5"],
        "callouts": [
            {{"type": "year", "text": "1518", "sub": "Strasbourg", "anchor": "1518"}},
            {{"type": "stat", "text": "400 ORANG", "sub": "Korban", "anchor": "400"}},
            {{"type": "percent", "text": "73%", "sub": "Permukaan Bumi adalah air", "anchor": "73"}},
            {{"type": "compare", "text": "UKURAN", "sub": "km", "anchor": "dibanding bulan",
              "items": [{{"label": "Bumi", "value": 12742}}, {{"label": "Bulan", "value": 3474}}]}},
            {{"type": "timeline", "text": "LINIMASA", "sub": "", "anchor": "tahun berikutnya",
              "items": [{{"year": "1518", "label": "Wabah mulai"}}, {{"year": "1519", "label": "Mereda"}}, {{"year": "1520", "label": "Dilarang"}}]}},
            {{"type": "keyword", "text": "WABAH MENARI", "sub": "", "anchor": "wabah menari", "pose": "wow"}},
            {{"type": "question", "text": "APA PENYEBABNYA?", "sub": "", "anchor": "penyebabnya"}}
        ],
        "music_prompt": "english music description"
    }}

    Catatan 'prompts': HANYA 4 SAMPAI 5 kata kunci pencarian Pexels untuk foto latar (visual utama kini motion graphic,
    tipografi, dan infografis), SANGAT SIMPEL dan KONKRET, bahasa Inggris, maks 2-3 kata.
    DILARANG kata AI seperti "hyper-realistic", "8k", "cinematic lighting". Pexels adalah stok foto nyata!
    Contoh Fakta Sejarah: ["ancient pyramid", "egypt pharaoh", "old manuscript", "battlefield smoke", "vintage map"]
    Contoh Misteri Alam Semesta: ["black hole space", "galaxy stars", "deep space nebula", "astronaut floating", "alien planet"]

    Catatan 'callouts': 6 SAMPAI 10 item motion graphic, urut sesuai alur naskah, tersebar merata (jangan menumpuk di awal).
    - type:
        "year"     = tahun (text HANYA angka tahun)
        "stat"     = angka + satuan (contoh "384.400 KM")
        "keyword"  = istilah kunci (maks 4 kata)
        "question" = pertanyaan pancingan
        "percent"  = persentase (text berisi angka 0-100, contoh "73%"; sub = keterangan singkat)
        "compare"  = perbandingan 2-3 benda (WAJIB items [{{"label","value"}}] value angka murni; text = judul pendek; sub = satuan)
        "timeline" = urutan 2-4 peristiwa (WAJIB items [{{"year","label"}}] label maks 4 kata; text = judul pendek)
    - Pakai MINIMAL 1 infografis (percent/compare/timeline) bila naskah memuat angka/perbandingan/urutan waktu.
    - text: PENDEK (maks 4 kata). Untuk year, isi HANYA angka tahun.
    - anchor: 1-3 kata PERSIS seperti tertulis di naskah, tempat grafik muncul. Tiap anchor harus ada di naskah.
    - pose (opsional): maskot bereaksi: "utama" (menunjuk), "wow", "berfikir", "bertanya", "terkejut", "wink".
    """


def generate_script(niche="Fakta Sejarah", topic="Misteri Piramida Mesir Kuno",
                    hook_style="Bikin merinding dan mikir keras"):
    """
    Naskah YouTube Shorts di bawah 60 detik + hook kuat + data callout untuk motion graphic.
    Niche: Fakta Sejarah / Misteri Alam Semesta.
    """
    prompt = build_prompt(niche, topic, hook_style)

    print(f"✍️ Generating script for topic: '{topic}' ({niche})...")

    best, last_err = None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = get_llm_response(prompt if best is None else _expand_prompt(best))
            data = _normalize(_parse_json(raw))
        except Exception as exc:
            last_err = exc
            print(f"  ⚠️ Percobaan {attempt}/{MAX_ATTEMPTS} gagal parse: {exc}")
            print(f"     preview balasan: {locals().get('raw', '')[:200]!r}")
            continue

        words = len(data["script"].split())
        if best is None or words > len(best["script"].split()):
            best = data
        if words >= MIN_WORDS:
            break
        print(f"  ⚠️ Naskah {words} kata < {MIN_WORDS}. Minta LLM memperpanjang...")

    if best is None:
        raise RuntimeError(f"Gagal membuat naskah: {last_err}")

    wc = len(best["script"].split())
    if wc > MAX_WORDS:
        print(f"  ⚠️ Naskah {wc} kata > {MAX_WORDS} (bakal lewat 60 detik). Memotong ke batas aman...")
        best["script"] = _trim_to_word_cap(best["script"], MAX_WORDS)
        wc = len(best["script"].split())

    print(f"⚡ Success! Naskah {wc} kata (~{wc / 2.6:.0f} detik), {len(best['prompts'])} visual prompts, "
          f"{len(best['callouts'])} callouts.")
    return best


def _expand_prompt(data):
    n = len(data["script"].split())
    return f"""Naskah berikut baru {n} kata, terlalu pendek. Kembangkan jadi {TARGET_WORDS} kata
    dengan menambah detail konkret, eskalasi fakta, dan satu re-hook di tengah. Pertahankan hook, tone 'lo/gue', dan semua field JSON.
    Pastikan setiap 'anchor' di callouts tetap ada di naskah baru.
    Balas JSON MURNI dengan field yang sama (script, hook_text, prompts, callouts, music_prompt).

    {json.dumps(data, ensure_ascii=False)}
    """