import os
import re
import json
import shutil
import asyncio
import subprocess
import threading
import wave
 
import edge_tts
from moviepy import AudioFileClip
from config import settings as _settings
 
AUDIO_DIR = _settings.AUDIO_DIR
 
VOICE = getattr(_settings, "TTS_VOICE", "id-ID-ArdiNeural")
RATE = getattr(_settings, "TTS_RATE", "-3%")      # sedikit lebih pelan = lebih berat/dramatis
PITCH = getattr(_settings, "TTS_PITCH", "-20Hz")   # nada turun = suara deep
VOLUME = getattr(_settings, "TTS_VOLUME", "+0%")
SUBTITLE_LEAD = float(getattr(_settings, "SUBTITLE_LEAD", 0.04))
 
# --- VO pro: sintesis per kalimat + prosodi dinamis + jeda dramatis + mastering ---
VO_PRO = str(getattr(_settings, "TTS_PRO", "1")).lower() not in ("0", "false", "no")
VO_MASTER = str(getattr(_settings, "TTS_MASTER", "1")).lower() not in ("0", "false", "no")
LOUDNESS_LUFS = float(getattr(_settings, "TTS_LUFS", -14.5))
SR = 24000                 # sample rate kerja (sama dengan keluaran edge-tts)
TRIM_THRESHOLD = 450       # amplitudo int16 dianggap hening
HEAD_KEEP = 0.025          # detik napas sebelum suara
TAIL_KEEP = 0.06           # detik ekor setelah suara
FADE_SEC = 0.006           # fade pendek anti-klik antar segmen
PAUSE_AFTER = {".": 0.30, "?": 0.40, "!": 0.28, "…": 0.50, ":": 0.26, ";": 0.22}
HOOK_BEAT = 0.14           # jeda tambahan setelah kalimat hook
CLOSER_LEAD = 0.10         # jeda tambahan sebelum kalimat penutup

MAX_RETRIES = 3
MIN_WORD_DURATION = 0.08   # detik
CLOSE_GAP_BELOW = 0.35     # celah antar kata di bawah ini ditutup (anti-flicker)
 
_TICKS = 10_000_000        # edge-tts memakai satuan 100 nanodetik
 
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F000-\U0001F2FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_SOFT_PAUSE = ",;:"
_HARD_PAUSE = ".?!…"
 
 
# ---------------------------------------------------------------------------
# Pembersihan teks
# ---------------------------------------------------------------------------
def clean_text_for_tts(text):
    """Bersihkan teks agar dibaca natural & subtitle tidak memuat simbol aneh."""
    text = str(text or "")
    text = _URL_RE.sub(" ", text)
    text = _EMOJI_RE.sub(" ", text)
    text = text.replace("&", " dan ").replace("%", " persen")
    text = re.sub(r"[#*_`~>|\[\]{}<>]", " ", text)      # sisa markdown / hashtag
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201C\u201D]", '"', text)
    text = re.sub(r"\s*[\r\n]+\s*", ". ", text)          # baris baru = jeda kalimat
    text = re.sub(r"\s+([.?!,;:])", r"\1", text)         # spasi sebelum tanda baca
    text = re.sub(r"([.?!,;:])\1+", r"\1", text)         # tanda baca ganda
    text = re.sub(r"\.\s*\.", ".", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
 
 
# ---------------------------------------------------------------------------
# Singkatan -> dibaca LENGKAP (hanya untuk suara; subtitle tetap memakai teks asli)
# ---------------------------------------------------------------------------
_ABBR = {
    # umum
    "dll": "dan lain-lain", "dsb": "dan sebagainya", "dst": "dan seterusnya", "dkk": "dan kawan-kawan",
    "yg": "yang", "dgn": "dengan", "dg": "dengan", "utk": "untuk", "untk": "untuk", "tdk": "tidak",
    "jg": "juga", "sbg": "sebagai", "krn": "karena", "dlm": "dalam", "pd": "pada", "spt": "seperti",
    "tsb": "tersebut", "hrs": "harus", "bhw": "bahwa", "sdh": "sudah", "blm": "belum", "tgl": "tanggal",
    "thn": "tahun", "bln": "bulan", "hlm": "halaman", "dpt": "dapat", "sy": "saya", "kpd": "kepada",
    "dr": "dokter", "Dr": "Doktor", "Prof": "Profesor", "prof": "profesor", "Ir": "Insinyur",
    "Drs": "Doktorandus", "Jend": "Jenderal", "Kol": "Kolonel", "Mayjen": "Mayor Jenderal",
    "vs": "versus", "jt": "juta", "rb": "ribu",
    # era & satuan (tanpa angka di depan)
    "SM": "Sebelum Masehi", "km": "kilometer", "kg": "kilogram", "cm": "sentimeter", "mm": "milimeter",
    "mg": "miligram", "km/jam": "kilometer per jam", "m/s": "meter per detik",
    "km2": "kilometer persegi", "km²": "kilometer persegi", "m²": "meter persegi", "m³": "meter kubik",
    "°C": "derajat Celsius", "°F": "derajat Fahrenheit", "°": "derajat",
    # lembaga & istilah
    "PBB": "Perserikatan Bangsa-Bangsa", "AS": "Amerika Serikat", "RI": "Republik Indonesia",
    "UEA": "Uni Emirat Arab", "WHO": "Organisasi Kesehatan Dunia", "ESA": "Badan Antariksa Eropa",
    "AI": "kecerdasan buatan", "TV": "televisi", "SD": "sekolah dasar", "SMP": "sekolah menengah pertama",
    "SMA": "sekolah menengah atas", "TNI": "Tentara Nasional Indonesia", "KPK": "Komisi Pemberantasan Korupsi",
    "USD": "dolar Amerika", "IDR": "rupiah", "Rp": "rupiah", "US$": "dolar Amerika", "$": "dolar",
    "WIB": "Waktu Indonesia Barat", "VOC": "Vereenigde Oostindische Compagnie",
}
_UNITS_AFTER_NUM = {   # singkatan satu huruf/ambigu: hanya dibaca setelah angka
    "m": "meter", "g": "gram", "ha": "hektare", "l": "liter", "s": "detik", "ton": "ton", "Hz": "hertz", "kHz": "kilohertz", "MHz": "megahertz",
}
_SPELL = {"DNA", "RNA", "CPU", "GPS", "USB", "LED", "FBI", "CIA", "KGB", "UFO", "BBC", "CNN", "IQ", "PC", "HP", "DPR", "MPR", "UN", "EU", "UK", "NASA_X"}
_LETTER = {"A": "a", "B": "be", "C": "ce", "D": "de", "E": "e", "F": "ef", "G": "ge", "H": "ha", "I": "i", "J": "je",
           "K": "ka", "L": "el", "M": "em", "N": "en", "O": "o", "P": "pe", "Q": "ki", "R": "er", "S": "es",
           "T": "te", "U": "u", "V": "ve", "W": "we", "X": "eks", "Y": "ye", "Z": "zet"}
_ONES = ["nol", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas"]


def _terbilang(n):
    """Angka -> kata Indonesia (0..999999), dipakai untuk 'ke-15' -> 'ke lima belas'."""
    if n < 12:
        return _ONES[n]
    if n < 20:
        return _ONES[n - 10] + " belas"
    if n < 100:
        t, o = divmod(n, 10)
        return _ONES[t] + " puluh" + (" " + _ONES[o] if o else "")
    if n < 200:
        return "seratus" + (" " + _terbilang(n - 100) if n > 100 else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return _ONES[h] + " ratus" + (" " + _terbilang(r) if r else "")
    if n < 2000:
        return "seribu" + (" " + _terbilang(n - 1000) if n > 1000 else "")
    if n < 1_000_000:
        k, r = divmod(n, 1000)
        return _terbilang(k) + " ribu" + (" " + _terbilang(r) if r else "")
    return str(n)


_TOKEN_SPLIT = re.compile(r"^([^\w°$]*)(.*?)([^\w°²³/]*)$", re.S)


def _is_num(tok):
    return bool(tok) and bool(re.fullmatch(r"\d+([.,]\d+)*", re.sub(r"[^\w.,]", "", tok)))


def _speak_core(core, prev_core, next_core):
    """Bentuk ucapan lengkap untuk satu token (tanpa tanda baca). Bisa lebih dari satu kata."""
    if not core:
        return core
    # 1.000.000 -> 1000000 (tetap satu token, dibaca benar oleh mesin TTS)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", core):
        return core.replace(".", "")
    # 1000-2000 -> 1000 sampai 2000
    m = re.fullmatch(r"(\d+)[-–](\d+)", core)
    if m:
        return f"{m.group(1)} sampai {m.group(2)}"
    # 5km, 30°C, 10m/s -> angka + satuan lengkap
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(km/jam|m/s|km²|km2|m²|m³|km|kg|cm|mm|mg|ha|°C|°F|Hz|kHz|MHz|m|g|l)", core)
    if m:
        unit = _ABBR.get(m.group(2)) or _UNITS_AFTER_NUM.get(m.group(2), m.group(2))
        return f"{m.group(1)} {unit}"
    # ke-15 -> ke lima belas (ke-1 -> pertama)
    m = re.fullmatch(r"[Kk]e-(\d{1,6})", core)
    if m:
        n = int(m.group(1))
        return "pertama" if n == 1 else f"ke {_terbilang(n)}"
    # Rp5 / Rp.5 -> rupiah 5 (angka menyusul sebagai token terpisah bila ada spasi)
    if core in ("Rp", "Rp.") and _is_num(next_core or ""):
        return "rupiah"
    if core == "M" and _is_num(prev_core or ""):                      # 1453 M -> Masehi / 5 M -> miliar
        digits = re.sub(r"\D", "", prev_core)
        return "Masehi" if digits and int(digits) <= 2100 else "miliar"
    if core in _UNITS_AFTER_NUM and _is_num(prev_core or ""):
        return _UNITS_AFTER_NUM[core]
    if core in _ABBR:
        return _ABBR[core]
    low = core.lower()
    if low in _ABBR and core.islower():
        return _ABBR[low]
    if core in ("No", "no") and _is_num(next_core or ""):
        return "nomor"
    if core in _SPELL or (core.isupper() and 2 <= len(core) <= 5 and core.isalpha() and not re.search(r"[AIUEO]", core)):
        return " ".join(_LETTER.get(c, c) for c in core)
    return core


def speak_tokens(tokens):
    """tokens (teks tampilan) -> (daftar ucapan per token, jumlah kata ucapan per token)."""
    parts = [(_TOKEN_SPLIT.match(t).groups() if _TOKEN_SPLIT.match(t) else ("", t, "")) for t in tokens]
    spoken, counts = [], []
    for i, (lead, core, trail) in enumerate(parts):
        prev_core = parts[i - 1][1] if i > 0 else ""
        next_core = parts[i + 1][1] if i + 1 < len(parts) else ""
        sp = _speak_core(core, prev_core, next_core)
        if sp != core and trail.startswith(".") and i < len(parts) - 1 and not re.search(r"\d", core):
            trail = trail[1:]                       # titik singkatan di tengah kalimat bukan jeda
        out = f"{lead}{sp}{trail}".strip()
        if not out:
            out = tokens[i]
        spoken.append(out)
        counts.append(max(1, len(out.split())))
    return spoken, counts


def normalize_for_speech(text):
    """Teks utuh -> teks ucapan dengan semua singkatan dibaca lengkap."""
    toks = text.split()
    spoken, _ = speak_tokens(toks)
    return re.sub(r"\s+", " ", " ".join(spoken)).strip()


def split_sentences(text):
    """Pecah per kalimat; kalimat sangat pendek digabung ke tetangganya agar intonasi tidak patah."""
    prot = re.sub(r"\b(dll|dsb|dst|dkk|dr|prof|yg|hlm|no|sm)\.", lambda m: m.group(1) + "\u2024", text, flags=re.I)  # singkatan bukan akhir kalimat
    parts = [p.strip().replace("\u2024", ".") for p in re.split(r"(?<=[.?!…])\s+", prot) if p.strip()]
    merged = []
    for p in parts:
        if merged and len(p.split()) < 3:
            merged[-1] = f"{merged[-1]} {p}"
        else:
            merged.append(p)
    if len(merged) > 1 and len(merged[0].split()) < 3:
        merged[1] = f"{merged[0]} {merged[1]}"
        merged.pop(0)
    return merged or [text]


def _num(s, unit):
    m = re.match(r"^\s*([+-]?\d+)\s*" + unit + r"\s*$", str(s), re.I)
    return int(m.group(1)) if m else 0


def _sentence_prosody(idx, total, sent):
    """Rate/pitch/volume per kalimat: hook bertenaga, tanya naik, angka pelan, penutup hangat."""
    rate, pitch, vol = _num(RATE, "%"), _num(PITCH, "Hz"), _num(VOLUME, "%")
    end = sent.rstrip('"\')”’')[-1:]
    if idx == 0:                       # hook: lebih cepat & energik
        rate += 6; pitch += 6; vol += 6
    elif idx == total - 1 and total > 2:   # penutup: lebih pelan & hangat
        rate -= 5; pitch -= 4
    if end == "?":
        pitch += 10; rate -= 2
    elif end == "!":
        pitch += 6; rate += 4; vol += 8
    if re.search(r"\d", sent):         # angka/tahun: pelan agar jelas
        rate -= 3
    pitch += (-2, 2)[idx % 2]          # variasi kecil anti-monoton
    rate = max(-25, min(25, rate))
    pitch = max(-50, min(30, pitch))
    vol = max(-20, min(30, vol))
    return f"{rate:+d}%", f"{pitch:+d}Hz", f"{vol:+d}%"


# ---------------------------------------------------------------------------
# Utilitas kata & bobot durasi
# ---------------------------------------------------------------------------
def _norm(s):
    return re.sub(r"[^0-9a-zA-Z\u00C0-\u024F]", "", str(s)).lower()
 
 
def _syllables(word):
    """Perkiraan jumlah suku kata (cukup baik untuk bahasa Indonesia)."""
    groups = re.findall(r"[aeiouAEIOU]+", word)
    digits = len(re.findall(r"\d", word))
    return max(1, len(groups)) + digits * 0.6
 
 
def _weight(token):
    """Bobot waktu ucap sebuah token: suku kata + jeda tanda baca di belakangnya."""
    w = _syllables(token) + 0.15 * len(_norm(token)) / 4.0
    tail = token.rstrip('"\')”’')[-1:] if token else ""
    if tail and tail in _HARD_PAUSE:
        w += 1.6
    elif tail and tail in _SOFT_PAUSE:
        w += 0.8
    return w
 
 
def _distribute(tokens, start, end):
    """Bagi rentang [start, end] ke token secara proporsional terhadap bobotnya."""
    tokens = [t for t in tokens if t]
    if not tokens or end <= start:
        return []
    weights = [_weight(t) for t in tokens]
    total = sum(weights)
    out, cursor = [], start
    for tok, w in zip(tokens, weights):
        dur = (end - start) * (w / total)
        out.append({"word": tok, "start": cursor, "end": cursor + dur})
        cursor += dur
    return out
 
 
def _align_to_source(boundary_words, source_tokens):
    """
    Samakan kata dari TTS dengan token teks sumber (agar tanda baca & kapitalisasi ikut).
    Greedy berurutan dengan jendela pencarian kecil; jika tak cocok, pakai teks TTS apa adanya.
    """
    aligned, j = [], 0
    src_norm = [_norm(t) for t in source_tokens]
    for bw in boundary_words:
        target = _norm(bw["word"])
        display = bw["word"]
        if target:
            for k in range(j, min(j + 4, len(source_tokens))):
                if src_norm[k] == target or (target and src_norm[k].startswith(target)):
                    display = source_tokens[k]
                    j = k + 1
                    break
        aligned.append({"word": display, "start": bw["start"], "end": bw["end"]})
    return aligned
 
 
# ---------------------------------------------------------------------------
# Pembangun timeline subtitle
# ---------------------------------------------------------------------------
def _from_word_events(words, source_tokens):
    words = sorted(words, key=lambda w: w["start"])
    return _align_to_source(words, source_tokens)
 
 
def _from_sentence_events(sentences):
    out = []
    for s in sorted(sentences, key=lambda s: s["start"]):
        tokens = s["word"].split()
        out.extend(_distribute(tokens, s["start"], s["end"]))
    return out
 
 
def _from_audio_duration(text, total_duration):
    """Fallback terakhir: bobot per kata di seluruh durasi audio (bukan bagi rata)."""
    return _distribute(text.split(), 0.0, total_duration)
 
 
def _finalize(subs, audio_duration=None):
    """Monotonic, tanpa overlap, tutup celah kecil, terapkan lead, clamp ke durasi audio."""
    if not subs:
        return []
    subs = sorted(subs, key=lambda s: s["start"])
 
    # 1) geser sedikit lebih awal supaya teks terasa 'menempel' ke suara
    for s in subs:
        s["start"] = max(0.0, s["start"] - SUBTITLE_LEAD)
        s["end"] = max(s["start"] + MIN_WORD_DURATION, s["end"] - SUBTITLE_LEAD)
 
    # 2) hilangkan overlap & tutup celah kecil
    for i in range(len(subs) - 1):
        cur, nxt = subs[i], subs[i + 1]
        if nxt["start"] < cur["start"] + MIN_WORD_DURATION:
            nxt["start"] = cur["start"] + MIN_WORD_DURATION
        if cur["end"] > nxt["start"]:
            cur["end"] = nxt["start"]
        elif nxt["start"] - cur["end"] < CLOSE_GAP_BELOW:
            cur["end"] = nxt["start"]
        if cur["end"] - cur["start"] < MIN_WORD_DURATION:
            cur["end"] = cur["start"] + MIN_WORD_DURATION
 
    # 3) kata terakhir jangan melewati audio
    last = subs[-1]
    if audio_duration:
        last["end"] = min(last["end"], audio_duration)
        if last["end"] - last["start"] < MIN_WORD_DURATION:
            last["start"] = max(0.0, last["end"] - MIN_WORD_DURATION)
 
    return [
        {"word": s["word"], "start": round(s["start"], 3), "end": round(s["end"], 3)}
        for s in subs
    ]
 
 
# ---------------------------------------------------------------------------
# Inti: panggil edge-tts
# ---------------------------------------------------------------------------
async def _synthesize(text, voice, boundary, tmp_path, rate=None, pitch=None, volume=None):
    """Sintesis satu kali. Return (words, sentences)."""
    kwargs = dict(rate=rate or RATE, pitch=pitch or PITCH, volume=volume or VOLUME)
    try:
        communicate = edge_tts.Communicate(text, voice, boundary=boundary, **kwargs)
    except TypeError:
        # edge-tts versi lama: tidak ada parameter boundary (WordBoundary sudah default)
        communicate = edge_tts.Communicate(text, voice, **kwargs)
 
    words, sentences, got_audio = [], [], False
    with open(tmp_path, "wb") as f:
        async for chunk in communicate.stream():
            ctype = chunk.get("type")
            if ctype == "audio":
                got_audio = True
                f.write(chunk["data"])
            elif ctype in ("WordBoundary", "SentenceBoundary"):
                start = chunk["offset"] / _TICKS
                item = {
                    "word": chunk["text"],
                    "start": start,
                    "end": start + chunk["duration"] / _TICKS,
                }
                (words if ctype == "WordBoundary" else sentences).append(item)
    if not got_audio:
        raise RuntimeError("Edge-TTS tidak mengembalikan audio.")
    return words, sentences
 
 
async def _synthesize_with_retry(text, voice, boundary, tmp_path, **prosody):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await _synthesize(text, voice, boundary, tmp_path, **prosody)
        except Exception as exc:  # jaringan / NoAudioReceived / dsb.
            last_err = exc
            print(f"⚠️ TTS percobaan {attempt}/{MAX_RETRIES} gagal: {exc}")
            await asyncio.sleep(1.5 * attempt)
    raise RuntimeError(f"Edge-TTS gagal setelah {MAX_RETRIES}x percobaan: {last_err}")
 
 
def _audio_duration(path):
    try:
        clip = AudioFileClip(path)
        try:
            return float(clip.duration)
        finally:
            clip.close()
    except Exception:
        return None
 
 
async def _generate_single_pass(text, filename="voiceover.mp3"):
    """Mode lama (satu kali sintesis, tanpa mastering). Dipakai sebagai cadangan."""
    print("🎙️ Generating Text-to-Speech & subtitle timestamps...")
    os.makedirs(AUDIO_DIR, exist_ok=True)
    output_audio_path = os.path.join(AUDIO_DIR, filename)
    tmp_path = output_audio_path + ".part"
 
    clean = clean_text_for_tts(text)
    if not clean:
        raise ValueError("Teks narasi kosong setelah dibersihkan.")
    source_tokens = clean.split()
 
    # Percobaan 1: WordBoundary (paling akurat)
    spoken_all = normalize_for_speech(clean)
    words, sentences = await _synthesize_with_retry(spoken_all, VOICE, "WordBoundary", tmp_path)
    method = "word"
 
    # Percobaan 2: service tidak mengirim WordBoundary -> minta SentenceBoundary
    if not words:
        print("⚠️ WordBoundary tidak dikirim server, memakai SentenceBoundary + bobot suku kata.")
        words, sentences = await _synthesize_with_retry(spoken_all, VOICE, "SentenceBoundary", tmp_path)
        method = "sentence" if sentences else "audio"
 
    os.replace(tmp_path, output_audio_path)
    duration = _audio_duration(output_audio_path)
 
    if words:
        raw = _from_word_events(words, source_tokens)
    elif sentences:
        raw = _from_sentence_events(sentences)
    else:
        print("⚠️ Tidak ada metadata timing, estimasi dari durasi audio.")
        raw = _from_audio_duration(clean, duration or max(1.0, len(source_tokens) * 0.35))
        method = "audio"
 
    subtitles = _finalize(raw, duration)
 
    # Simpan timing untuk debugging (dan bisa dipakai ulang oleh modul lain)
    try:
        with open(os.path.splitext(output_audio_path)[0] + ".words.json", "w", encoding="utf-8") as f:
            json.dump({"method": method, "voice": VOICE, "duration": duration,
                       "words": subtitles}, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
 
    print(f"✅ Audio & {len(subtitles)} word timestamps saved! (sumber timing: {method})")
    return output_audio_path, subtitles
 
 
# ---------------------------------------------------------------------------
# VO PRO: sintesis per kalimat -> trim -> jeda dramatis -> mastering broadcast
# ---------------------------------------------------------------------------
def _ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _decode_mono(ffmpeg, path):
    import numpy as np
    raw = subprocess.run(
        [ffmpeg, "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32)


def _trim_voice(x):
    """Buang hening di awal/akhir segmen; return (sampel, detik_yang_dibuang_di_awal)."""
    import numpy as np
    idx = np.flatnonzero(np.abs(x) > TRIM_THRESHOLD)
    if idx.size == 0:
        return x, 0.0
    a = max(0, int(idx[0]) - int(HEAD_KEEP * SR))
    b = min(len(x), int(idx[-1]) + int(TAIL_KEEP * SR))
    y = x[a:b].copy()
    n = min(len(y) // 2, int(FADE_SEC * SR))
    if n > 1:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        y[:n] *= ramp
        y[-n:] *= ramp[::-1]
    return y, a / SR


def _pause_after(sent, idx, total):
    end = sent.rstrip('"\')”’')[-1:]
    gap = PAUSE_AFTER.get(end, 0.24)
    if idx == 0:
        gap += HOOK_BEAT
    if idx == total - 2:
        gap += CLOSER_LEAD
    return gap


def _write_wav(path, samples):
    import numpy as np
    pcm = np.clip(samples, -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# Rantai mastering: bersihkan rumble, hangatkan bass, naikkan presence, redam desis "s",
# kompres supaya rata, ambience ruangan sangat tipis, loudness standar Shorts/Reels.
MASTER_CHAIN = ",".join([
    "highpass=f=70",
    "lowpass=f=14000",
    "equalizer=f=160:t=q:w=0.9:g=2.5",
    "equalizer=f=2800:t=q:w=1.1:g=2.2",
    "equalizer=f=6800:t=q:w=2:g=-3.5",
    "acompressor=threshold=0.089:ratio=3.2:attack=6:release=140:makeup=2.2",
    "aecho=0.9:0.85:30|62:0.10|0.05",
    "alimiter=limit=0.89",
    "loudnorm=I={lufs}:TP=-1.5:LRA=8",
    "aresample=44100",
])


def _master(ffmpeg, wav_path, out_mp3):
    chain = MASTER_CHAIN.format(lufs=LOUDNESS_LUFS) if VO_MASTER else "anull"
    base = [ffmpeg, "-y", "-v", "error", "-i", wav_path]
    enc = ["-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "2", out_mp3]
    try:
        subprocess.run(base + ["-af", chain] + enc, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        print(f"⚠️ Mastering gagal ({exc.stderr.decode(errors='ignore')[:120]}); encode tanpa efek.")
        subprocess.run(base + enc, check=True, capture_output=True)


async def _generate_pro(text, filename):
    import numpy as np
    print("🎙️ VO Pro: sintesis per kalimat + prosodi dinamis + mastering...")
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("ffmpeg tidak ditemukan")

    os.makedirs(AUDIO_DIR, exist_ok=True)
    out_path = os.path.join(AUDIO_DIR, filename)
    stem = os.path.splitext(out_path)[0]

    clean = clean_text_for_tts(text)
    if not clean:
        raise ValueError("Teks narasi kosong setelah dibersihkan.")
    sentences = split_sentences(clean)
    total = len(sentences)

    chunks, all_words, plan, cursor = [], [], [], 0.0
    for i, sent in enumerate(sentences):
        rate, pitch, vol = _sentence_prosody(i, total, sent)
        seg_mp3 = f"{stem}.seg{i}.mp3"
        tokens = sent.split()
        spoken_toks, counts = speak_tokens(tokens)
        spoken = " ".join(spoken_toks)
        words, sents = await _synthesize_with_retry(spoken, VOICE, "WordBoundary", seg_mp3,
                                                    rate=rate, pitch=pitch, volume=vol)
        samples = _decode_mono(ffmpeg, seg_mp3)
        voice, head = _trim_voice(samples)
        seg_dur = len(voice) / SR

        if words and len(words) == sum(counts):
            # gabungkan kata ucapan hasil ekspansi kembali ke 1 token tampilan (subtitle tetap singkatan asli)
            words = sorted(words, key=lambda w: w["start"])
            seg_words, k = [], 0
            for tok, c in zip(tokens, counts):
                seg_words.append({"word": tok, "start": words[k]["start"], "end": words[k + c - 1]["end"]})
                k += c
            for w in seg_words:
                w["start"] = max(0.0, w["start"] - head)
                w["end"] = max(w["start"] + MIN_WORD_DURATION, w["end"] - head)
        elif words:
            seg_words = _from_word_events(words, tokens)
            for w in seg_words:
                w["start"] = max(0.0, w["start"] - head)
                w["end"] = max(w["start"] + MIN_WORD_DURATION, w["end"] - head)
        else:
            seg_words = _distribute(tokens, 0.0, seg_dur)

        for w in seg_words:
            all_words.append({"word": w["word"], "start": w["start"] + cursor, "end": min(w["end"], seg_dur) + cursor})

        chunks.append(voice)
        cursor += seg_dur
        gap = 0.0
        if i < total - 1:
            gap = _pause_after(sent, i, total)
            chunks.append(np.zeros(int(gap * SR), dtype=np.float32))
            cursor += gap
        plan.append({"i": i, "rate": rate, "pitch": pitch, "volume": vol, "pause_after": round(gap, 2), "text": sent})
        try:
            os.remove(seg_mp3)
        except OSError:
            pass

    wav_path = stem + ".raw.wav"
    _write_wav(wav_path, np.concatenate(chunks))
    tmp_mp3 = out_path + ".part.mp3"
    _master(ffmpeg, wav_path, tmp_mp3)
    os.replace(tmp_mp3, out_path)
    try:
        os.remove(wav_path)
    except OSError:
        pass

    duration = _audio_duration(out_path)
    subtitles = _finalize(all_words, duration)
    try:
        with open(stem + ".words.json", "w", encoding="utf-8") as f:
            json.dump({"method": "pro-per-sentence", "voice": VOICE, "duration": duration,
                       "sentences": plan, "words": subtitles}, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    print(f"✅ VO Pro selesai: {total} kalimat, {len(subtitles)} kata, {duration or 0:.1f}s")
    return out_path, subtitles


async def _generate_audio_async(text, filename="voiceover.mp3"):
    if VO_PRO:
        try:
            return await _generate_pro(text, filename)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ VO Pro gagal ({exc}). Beralih ke mode single-pass.")
    return await _generate_single_pass(text, filename)


# ---------------------------------------------------------------------------
# API sinkron (dipanggil main.py / GUI)
# ---------------------------------------------------------------------------
def _run_sync(coro):
    """asyncio.run yang aman walau sudah ada event loop yang berjalan di thread ini."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
 
    result, error = {}, {}
 
    def runner():
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001
            error["value"] = exc
 
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join()
    if "value" in error:
        raise error["value"]
    return result["value"]
 
 
def generate_speech_with_word_timestamps(text, filename="voiceover.mp3"):
    """Fungsi utama yang dipanggil oleh main.py secara sinkron."""
    return _run_sync(_generate_audio_async(text, filename))
 
 
def generate_audio(text, filename="voiceover.mp3"):
    """Alias jika modul lain memanggil dengan nama generate_audio."""
    return generate_speech_with_word_timestamps(text, filename)