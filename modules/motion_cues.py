"""Tentukan tema visual dan jadwal motion graphic (callout) dari timestamp kata TTS."""
import re

HISTORY_KEYS = ("sejarah", "history", "kuno", "kerajaan", "perang", "kekaisaran", "bizantium", "romawi", "abad")
SPACE_KEYS = ("misteri", "alam semesta", "kosmik", "space", "planet", "bintang", "galaksi",
              "lubang hitam", "luar angkasa", "astronom", "nebula", "asteroid")

UNITS = {"juta", "miliar", "milyar", "triliun", "ribu", "persen", "tahun", "km", "kilometer", "meter",
         "derajat", "kali", "orang", "kg", "ton", "detik", "jam", "hari", "bulan", "abad"}

MIN_START = 3.4        # lewati kartu hook
END_MARGIN = 3.2       # lewati kartu outro
MIN_GAP = 0.5          # jeda antar callout
DURATION = {"year": 2.8, "stat": 3.0, "keyword": 2.4, "question": 2.6,
            "percent": 3.4, "compare": 4.0, "timeline": 4.4}
INFO_TYPES = ("percent", "compare", "timeline")
PRE_ROLL = 0.15        # tampil sedikit sebelum kata diucapkan
CUE_PER_SECONDS = 6.5  # kepadatan grafis: 1 callout tiap ~6.5 detik (sebelumnya 8)

# Pose maskot yang valid (file di remotion/public/char/pose_<nama>.png)
POSES = ("utama", "wow", "berfikir", "bertanya", "terkejut", "wink")


def detect_theme(niche, topic=""):
    n = str(niche).lower()
    if any(k in n for k in HISTORY_KEYS):
        return "history"
    if any(k in n for k in SPACE_KEYS):
        return "space"
    t = str(topic).lower()
    if any(k in t for k in HISTORY_KEYS):
        return "history"
    return "space"


def _norm(s):
    return re.sub(r"[^0-9a-zA-Z\u00C0-\u024F]", "", str(s)).lower()


def _find_anchor(words, anchor, from_idx):
    toks = [_norm(t) for t in str(anchor).split() if _norm(t)]
    if not toks:
        return None
    norm = [_norm(w["word"]) for w in words]
    for i in range(from_idx, len(words) - len(toks) + 1):
        if norm[i:i + len(toks)] == toks:
            return i
    if len(toks) > 1:                       # cadangan: cocokkan kata pertama saja
        for i in range(from_idx, len(words)):
            if norm[i] == toks[0]:
                return i
    return None


def _auto_cues(words):
    """Cadangan: deteksi tahun & angka+satuan dari naskah."""
    out = []
    for i, w in enumerate(words):
        tok = re.sub(r"[^\d.]", "", w["word"])
        if re.fullmatch(r"(1\d{3}|20\d{2})", tok):
            out.append({"type": "year", "text": tok, "sub": "", "idx": i})
        elif re.fullmatch(r"\d{1,3}(\.\d{3})*|\d+", tok) and i + 1 < len(words):
            unit = _norm(words[i + 1]["word"])
            if unit in UNITS and unit not in ("tahun", "hari", "bulan", "jam", "detik"):
                out.append({"type": "stat", "text": f"{tok} {unit}".upper(), "sub": "", "idx": i})
    return out


def _clean_items(ctype, items):
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if ctype == "compare":
            try:
                v = float(str(it.get("value")).replace(".", "").replace(",", "."))
            except (TypeError, ValueError):
                continue
            if it.get("label"):
                out.append({"label": str(it["label"]).strip()[:18], "value": v})
        elif ctype == "timeline":
            y, l = str(it.get("year", "")).strip(), str(it.get("label", "")).strip()
            if y and l:
                out.append({"year": y[:10], "label": l[:26]})
    return out[:4]


def _auto_questions(words):
    """Kalimat tanya -> cue 'question' (maks 4 kata terakhir sebelum tanda tanya)."""
    out = []
    for i, w in enumerate(words):
        if not str(w["word"]).rstrip('"\')”’').endswith("?"):
            continue
        first = max(0, i - 3)
        for j in range(i - 1, first - 1, -1):          # jangan melewati batas kalimat sebelumnya
            if re.search(r"[.!?…]$", str(words[j]["word"])):
                first = j + 1
                break
        text = " ".join(str(x["word"]) for x in words[first:i + 1]).strip().upper()
        if len(text) >= 6:
            out.append({"type": "question", "text": text, "sub": "", "idx": first})
    return out


def build_motion_cues(callouts, words, total_duration=None):
    """
    callouts : list dict {type,text,sub,anchor} dari LLM (boleh kosong).
    words    : word_subtitles [{word,start,end}] dari TTS.
    Return   : list [{type,text,sub,start,end}] dalam detik, tidak saling tumpang tindih.
    """
    if not words:
        return []
    total = total_duration or words[-1]["end"]
    max_cues = max(3, int(total // CUE_PER_SECONDS))

    cands, cursor = [], 0
    for c in callouts or []:
        idx = _find_anchor(words, c["anchor"], cursor)
        if idx is None:
            idx = _find_anchor(words, c["anchor"], 0)
        if idx is None:
            continue
        cursor = idx
        cands.append({**c, "idx": idx})
    cands.sort(key=lambda c: c["idx"])

    # isi dari deteksi otomatis bila LLM kurang (tahun/angka + kalimat tanya)
    if len(cands) < max_cues:
        have = {c["idx"] for c in cands}
        extra = [a for a in _auto_cues(words) + _auto_questions(words) if a["idx"] not in have]
        cands += extra
        cands.sort(key=lambda c: c["idx"])

    cues, last_end = [], 0.0
    for c in cands:
        ctype = c.get("type") if c.get("type") in DURATION else "keyword"
        start = max(0.0, words[c["idx"]]["start"] - PRE_ROLL)
        end = start + DURATION[ctype]
        if start < MIN_START or end > total - END_MARGIN or start < last_end + MIN_GAP:
            continue
        cue = {"type": ctype, "text": c["text"], "sub": c.get("sub", ""),
               "start": round(start, 2), "end": round(end, 2)}
        if c.get("pose") in POSES:                      # opsional dari LLM: pose maskot
            cue["pose"] = c["pose"]
        if ctype in INFO_TYPES:                         # infografis butuh data; tanpa data jadi keyword
            items = _clean_items(ctype, c.get("items"))
            if ctype == "percent" and not re.search(r"\d", str(c["text"])):
                cue["type"] = "keyword"
            elif ctype != "percent" and len(items) < 2:
                cue["type"] = "keyword"
            elif items:
                cue["items"] = items
        cues.append(cue)
        last_end = end
        if len(cues) >= max_cues:
            break
    return cues