#!/usr/bin/env python3
"""
cue_planner.py — penjadwal callout / infografis (pengganti & perluasan motion_cues.py)

Yang baru dibanding motion_cues.py:
  * kata kerja gerak (`verb`) otomatis per tipe -> dipakai KineticType.tsx  (HyperFrames/shotcraft)
  * jadwal ditempel ke ketukan BGM bila |delta| <= 3 frame                (shotcraft beatF)
  * aturan hold: tiap callout punya IN/HOLD/OUT, HOLD minimal 0.8s        (R1)
  * anchor yang tidak ketemu -> callout DIBUANG (tidak ditebak posisinya)
  * keluaran tetap kompatibel dengan MotionCue di MotionGraphics.tsx

Pemakaian:
  python cue_planner.py --callouts callouts.json --words words.json --beats beats.json \
      --storyboard STORYBOARD.json --out callouts.json
"""
import argparse
import json
import os
import re
import sys

# ---- ambang (detik) -------------------------------------------------
MIN_START = 3.4          # lewati kartu hook
END_MARGIN = 3.2         # lewati kartu outro
MIN_GAP = 0.5            # jeda antar callout
PRE_ROLL = 0.15          # tampil sebelum kata diucapkan
CUE_PER_SECONDS = 6.5    # kepadatan: 1 callout tiap ~6.5 detik
MIN_HOLD = 0.8           # angka/teks harus sempat dibaca
BEAT_TOL = 0.1           # 3 frame @30fps
# Toleransi geser callout yang bentrok. Kartu angka/kata terkunci pada kata yang
# diucapkan (geser besar = meleset dari suara), sedangkan panel data boleh lebih longgar.
DEFER_WORD_LOCKED = 0.8  # year, stat, keyword, question, percent
DEFER_PANEL = 2.0        # compare, timeline
IN_BASE = 0.35           # envelope masuk (detik)
OUT_BASE = 0.25          # envelope keluar (detik)

DURATION = {"year": 2.8, "stat": 3.0, "keyword": 2.4, "question": 2.6,
            "percent": 3.4, "compare": 4.0, "timeline": 4.4}
INFO_TYPES = ("percent", "compare", "timeline")

# kata kerja gerak default per tipe (bisa dioverride LLM lewat field "verb")
VERB_BY_TYPE = {
    "year": "slam", "stat": "countup", "keyword": "pop", "question": "wave",
    "percent": "countup", "compare": "grow", "timeline": "draw",
}
VALID_VERBS = ("slam", "wave", "mask", "type", "pop", "countup", "draw", "glitch", "wipe", "float")

POSES = ("utama", "wow", "berfikir", "bertanya", "terkejut", "wink")
UNITS = {"juta", "miliar", "milyar", "triliun", "ribu", "persen", "tahun", "km", "kilometer", "meter",
         "derajat", "kali", "orang", "kg", "ton", "detik", "jam", "hari", "bulan", "abad"}


def load_json(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_words(path):
    data = load_json(path, [])
    if isinstance(data, dict):
        data = data.get("subtitles") or data.get("words") or []
    out = []
    for w in data:
        if not isinstance(w, dict):
            continue
        text = str(w.get("word", w.get("text", ""))).strip()
        try:
            s, e = float(w.get("start")), float(w.get("end"))
        except (TypeError, ValueError):
            continue
        if text and e > s:
            out.append({"text": text, "start": round(s, 3), "end": round(e, 3)})
    out.sort(key=lambda x: x["start"])
    return out


def _norm(s):
    return re.sub(r"[^0-9a-zA-Z\u00C0-\u024F]", "", str(s)).lower()


def maybe_explode(words):
    """Token TTS kadang berupa frasa ("Pada 1521, penjelajah").

    Bila rata-rata token > 1.6 kata, pecah jadi kata tunggal dengan waktu proporsional
    supaya auto_cues / auto_questions / pencarian anchor presisi per kata.
    """
    n_words = sum(len(w["text"].split()) for w in words)
    if not words or n_words / len(words) <= 1.6:
        return words
    out = []
    for w in words:
        parts = w["text"].split()
        if len(parts) == 1:
            out.append(w)
            continue
        span = max(0.01, w["end"] - w["start"])
        # bobot: proporsional terhadap panjang kata (+0.4 agar kata pendek tidak 0s)
        wts = [len(p) + 0.4 for p in parts]
        tot = sum(wts)
        cur = w["start"]
        for p, wt in zip(parts, wts):
            d = span * wt / tot
            out.append({"text": p, "start": round(cur, 3), "end": round(cur + d, 3)})
            cur += d
    out.sort(key=lambda x: x["start"])
    return out


def find_anchor(words, anchor, from_idx=0):
    """Cari indeks token tempat anchor muncul.

    Token TTS bisa berupa frasa ("Pada 1521, penjelajah"), jadi selain cocok urutan
    token, kita juga mencari anchor sebagai substring di aliran token yang digabung.
    """
    toks = [_norm(t) for t in str(anchor).split() if _norm(t)]
    if not toks:
        return None
    norm = [_norm(w["text"]) for w in words]
    joined = "".join(toks)

    # 1) urutan token persis
    for i in range(from_idx, len(words) - len(toks) + 1):
        if norm[i:i + len(toks)] == toks:
            return i

    # 2) substring di aliran token (menangani token berupa frasa)
    offsets, pos = [], 0
    for n in norm:
        offsets.append(pos)
        pos += len(n)
    stream = "".join(norm)
    start_at = offsets[from_idx] if from_idx < len(offsets) else 0
    k = stream.find(joined, start_at)
    if k < 0 and start_at:
        k = stream.find(joined)           # coba dari awal bila dari kursor gagal
    if k >= 0:
        for i in range(len(offsets)):
            end_i = offsets[i + 1] if i + 1 < len(offsets) else len(stream)
            if offsets[i] <= k < end_i:
                return i

    # 3) cadangan: kata pertama saja
    for i in range(from_idx, len(words)):
        if toks[0] in norm[i]:
            return i
    return None


def auto_cues(words):
    """Cadangan: deteksi tahun & angka+satuan dari naskah."""
    out = []
    for i, w in enumerate(words):
        tok = re.sub(r"[^\d.]", "", w["text"])
        if re.fullmatch(r"(1\d{3}|20\d{2})", tok):
            out.append({"type": "year", "text": tok, "sub": "", "idx": i, "verb": "slam"})
        elif re.fullmatch(r"\d{1,3}(\.\d{3})*|\d+", tok) and i + 1 < len(words):
            unit = _norm(words[i + 1]["text"])
            if unit in UNITS and unit not in ("tahun", "hari", "bulan", "jam", "detik"):
                out.append({"type": "stat", "text": f"{tok} {unit}".upper(), "sub": "", "idx": i, "verb": "countup"})
    return out


def auto_questions(words):
    out = []
    for i, w in enumerate(words):
        if not str(w["text"]).rstrip('"\')”’').endswith("?"):
            continue
        first = max(0, i - 3)
        for j in range(i - 1, first - 1, -1):
            if re.search(r"[.!?…]$", str(words[j]["text"])):
                first = j + 1
                break
        text = " ".join(x["text"] for x in words[first:i + 1]).strip().upper()
        if len(text) >= 6:
            out.append({"type": "question", "text": text, "sub": "", "idx": first, "verb": "wave"})
    return out


def clean_items(ctype, items):
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


def snap(t, beats):
    if not beats:
        return t, False
    times = beats.get("beatTimes") or []
    strengths = beats.get("beatStrengths") or [1.0] * len(times)
    best, best_d = None, 1e9
    for bt, st in zip(times, strengths):
        if st < 0.5:
            continue
        d = abs(bt - t)
        if d < best_d:
            best, best_d = bt, d
    if best is not None and best_d <= BEAT_TOL:
        return round(best, 3), True
    return t, False


def plan(callouts, words, beats=None, total_duration=None, max_extra=True):
    if not words:
        return []
    total = total_duration or words[-1]["end"]
    max_cues = max(3, int(total // CUE_PER_SECONDS))

    cands, cursor = [], 0
    for c in callouts or []:
        if not isinstance(c, dict) or not c.get("text"):
            continue
        idx = None
        if c.get("anchor"):
            idx = find_anchor(words, c["anchor"], cursor)
            if idx is None:
                idx = find_anchor(words, c["anchor"], 0)
        if idx is None and c.get("at") is not None:      # LLM boleh kasih detik langsung
            try:
                at = float(c["at"])
                idx = max(range(len(words)), key=lambda i: -1e9 if words[i]["start"] > at else words[i]["start"])
            except (TypeError, ValueError):
                idx = None
        if idx is None:
            print(f"  ⚠️ anchor '{c.get('anchor')}' tidak ketemu di naskah -> callout dibuang")
            continue
        # anchor terlalu dekat dengan hook? cari kemunculan berikutnya di naskah
        if words[idx]["start"] - PRE_ROLL < MIN_START and c.get("anchor"):
            nxt = find_anchor(words, c["anchor"], idx + 1)
            if nxt is not None:
                idx = nxt
        cursor = idx
        cands.append({**c, "idx": idx})

    cands.sort(key=lambda c: c["idx"])

    if max_extra and len(cands) < max_cues:
        have = {c["idx"] for c in cands}
        extra = [a for a in auto_cues(words) + auto_questions(words) if a["idx"] not in have]
        cands += extra
        cands.sort(key=lambda c: c["idx"])

    cues, last_end, impacts = [], 0.0, 0
    for c in cands:
        ctype = c.get("type") if c.get("type") in DURATION else "keyword"
        start = max(0.0, words[c["idx"]]["start"] - PRE_ROLL)
        start, _ = snap(start, beats)
        dur = DURATION[ctype]
        end = start + dur

        if start < MIN_START:
            print(f"  ⚠️ callout '{str(c.get('text'))[:24]}' di {start:.2f}s masuk zona hook "
                  f"(<{MIN_START}s) -> dibuang")
            continue
        # Bertabrakan? tunda sebentar bila gesernya kecil (lebih baik daripada kehilangan data).
        if start < last_end + MIN_GAP:
            shift = (last_end + MIN_GAP) - start
            if shift <= (DEFER_PANEL if ctype in ("compare", "timeline") else DEFER_WORD_LOCKED):
                print(f"  ⚠️ callout '{str(c.get('text'))[:24]}' ditunda {shift:.2f}s "
                      f"(bentrok dengan yang selesai {last_end:.2f}s)")
                start += shift
                end = start + dur
            else:
                print(f"  ⚠️ callout '{str(c.get('text'))[:24]}' bertabrakan dengan yang sebelumnya "
                      f"(selesai {last_end:.2f}s, perlu geser {shift:.2f}s) -> dibuang")
                continue
        # Melewati outro? potong durasinya dulu, baru dibuang bila hold-nya habis.
        limit = total - END_MARGIN
        if end > limit:
            fit = limit - start
            if fit >= IN_BASE + MIN_HOLD + OUT_BASE:
                print(f"  ⚠️ callout '{str(c.get('text'))[:24]}' dipotong {dur - fit:.2f}s "
                      f"agar tidak masuk zona outro")
                dur = fit
                end = start + dur
            else:
                print(f"  ⚠️ callout '{str(c.get('text'))[:24]}' berakhir {end:.2f}s melewati zona outro "
                      f"(>{limit:.2f}s) -> dibuang")
                continue
        # R1: pastikan HOLD cukup (teks/angka sempat dibaca)
        if dur - 0.35 - 0.25 < MIN_HOLD:
            end = start + 0.35 + MIN_HOLD + 0.25

        cue = {
            "type": ctype,
            "text": str(c["text"]).strip(),
            "sub": str(c.get("sub", "")).strip(),
            "start": round(start, 2),
            "end": round(end, 2),
            "verb": c.get("verb") if c.get("verb") in VALID_VERBS else VERB_BY_TYPE[ctype],
        }
        if str(c.get("pose", "")).lower() in POSES:
            cue["pose"] = str(c["pose"]).lower()
        if c.get("side") in ("left", "right"):
            cue["side"] = c["side"]

        if ctype in INFO_TYPES:
            items = clean_items(ctype, c.get("items"))
            if ctype == "percent" and not re.search(r"\d", str(c["text"])):
                cue["type"] = "keyword"
                cue["verb"] = "pop"
            elif ctype != "percent" and len(items) < 2:
                cue["type"] = "keyword"
                cue["verb"] = "pop"
            elif items:
                cue["items"] = items

        # R4: kuota impact layar penuh <=3, jarak >=6 detik
        if cue["verb"] in ("slam", "glitch"):
            if impacts >= 3 or (cues and start - cues[-1]["start"] < 6.0 and impacts >= 1):
                cue["verb"] = "pop"
            else:
                impacts += 1

        cues.append(cue)
        last_end = end
        if len(cues) >= max_cues:
            break
    return cues


def main():
    ap = argparse.ArgumentParser(description="Jadwalkan callout / infografis")
    ap.add_argument("--callouts", help="callouts.json dari LLM (boleh kosong)")
    ap.add_argument("--words", required=True)
    ap.add_argument("--beats", help="beats.json (opsional)")
    ap.add_argument("--storyboard", help="STORYBOARD.json -> callouts disuntikkan ke dalamnya")
    ap.add_argument("--out", default="callouts.json")
    args = ap.parse_args()

    words = maybe_explode(load_words(args.words))
    if not words:
        sys.exit("❌ words.json kosong.")
    beats = load_json(args.beats)
    raw = load_json(args.callouts, [])
    if isinstance(raw, dict):
        raw = raw.get("callouts", [])

    # Bila disuntik ke storyboard, pakai durasi final storyboard sebagai batas outro.
    total = None
    sb = None
    if args.storyboard and os.path.exists(args.storyboard):
        with open(args.storyboard, "r", encoding="utf-8") as f:
            sb = json.load(f)
        total = (sb.get("meta") or {}).get("durationSec") or None

    cues = plan(raw, words, beats, total_duration=total)

    if sb is not None:
        sb["callouts"] = cues
        with open(args.storyboard, "w", encoding="utf-8") as f:
            json.dump(sb, f, indent=2, ensure_ascii=False)
        print(f"✅ {len(cues)} callout disuntikkan ke {args.storyboard}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(cues, f, indent=2, ensure_ascii=False)
    kinds = {}
    for c in cues:
        kinds[c["type"]] = kinds.get(c["type"], 0) + 1
    print(f"✅ {args.out}: {len(cues)} callout {kinds}")


if __name__ == "__main__":
    main()
