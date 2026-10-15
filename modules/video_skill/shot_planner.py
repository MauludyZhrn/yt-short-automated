#!/usr/bin/env python3
"""
shot_planner.py — naskah + timestamp kata -> STORYBOARD.json

Menggabungkan:
  * HyperFrames  : lapisan tengah storyboard + timing relatif {ref, offset}
  * shotcraft    : anggarkan hold dulu baru efek (R1), napas tiap 1-2 shot (R5),
                   kuota impact (R4), energy arc 4 segmen
  * OpenMontage  : tabel tone -> hold, hero shot tidak dikompresi, total +/-10%

Pemakaian:
  python shot_planner.py --script naskah.txt --words words.json \
      --niche sejarah --beats beats.json --bg 3 --out STORYBOARD.json

  --words : [{text|word, start, end}, ...] (keluaran tts.py /Input props subtitles)
  --beats : {"bpm":..,"beat0":..,"beatTimes":[..],"beatStrengths":[..]} (opsional)
"""
import argparse
import json
import math
import os
import re
import sys

FPS_DEFAULT = 30
MAX_DURATION = 59.5          # batas YouTube Shorts
MIN_DURATION = 25.0
NARRATION_MAX_HOLD = 7.0     # shot bernarasi paling panjang sebelum dipecah

# Tabel tone -> hold (detik), dari OpenMontage edit-director
TONE_HOLD = {
    "wry":       {"base": 2.0, "min": 1.2, "max": 3.5},   # Fakta Sejarah
    "reverent":  {"base": 3.5, "min": 2.5, "max": 6.0},   # Misteri Alam Semesta
    "urgent":    {"base": 1.2, "min": 0.5, "max": 2.5},
    "elegiac":   {"base": 4.0, "min": 2.5, "max": 7.0},
}
NICHE_TONE = {"sejarah": "wry", "semesta": "reverent", "history": "wry", "space": "reverent"}

# Energy arc: 4 segmen (porsi durasi)
ENERGY_ARC = [
    {"id": "hook",   "share": 0.10, "energy": "high"},
    {"id": "setup",  "share": 0.14, "energy": "medium"},
    {"id": "chain",  "share": 0.60, "energy": "medium"},
    {"id": "closer", "share": 0.16, "energy": "low"},
]

TRANSITION_BY_DELTA = {
    ("high", "high"):    "cut",
    ("high", "medium"):  "dissolve",
    ("high", "low"):     "dissolve",
    ("medium", "high"):  "push",
    ("medium", "medium"): "cut",
    ("medium", "low"):   "dissolve",
    ("low", "high"):     "push",
    ("low", "medium"):   "fade",
    ("low", "low"):      "dissolve",
}
TRANSITION_SEC = {"cut": 0.0, "dissolve": 0.7, "fade": 0.5, "push": 0.4}


def load_words(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):                       # boleh bungkus {"subtitles": [...]}
        data = data.get("subtitles") or data.get("words") or []
    out = []
    for w in data:
        if not isinstance(w, dict):
            continue
        text = str(w.get("word", w.get("text", ""))).strip()
        try:
            s = float(w.get("start")); e = float(w.get("end"))
        except (TypeError, ValueError):
            continue
        if text and e > s:
            out.append({"text": text, "start": round(s, 3), "end": round(e, 3)})
    out.sort(key=lambda x: x["start"])
    return out


def split_sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+", str(text).strip())
    return [p.strip() for p in parts if p.strip()]


def token_of(w):
    return w.get("word", w.get("text", ""))


def map_sentences_to_tokens(sentences, words):
    """Petakan tiap kalimat -> rentang indeks token TTS.

    Token TTS bisa berupa frasa ("Pada 1521, penjelajah"), jadi pencocokan dilakukan
    per kata kalimat sebagai substring di dalam token, berurutan dari kursor.
    """
    def nz(s):
        return re.sub(r"[^0-9a-zA-Z\u00C0-\u024F]", "", str(s)).lower()

    def to_words(s):
        return [nz(w) for w in re.findall(r"[\w\u00C0-\u024F]+", str(s).lower()) if nz(w)]

    # "flat": satu entri per KATA, dengan penanda indeks token aslinya
    flat = []
    for i, w in enumerate(words):
        for sw in to_words(token_of(w)):
            flat.append((sw, i))
    if not flat:
        return []

    spans, cur = [], 0
    for sent in sentences:
        swords = to_words(sent)
        if not swords:
            continue
        start = None
        for j in range(cur, len(flat)):
            if swords[0] in flat[j][0] or flat[j][0] in swords[0]:
                start = j
                break
        if start is None:
            start = min(cur, len(flat) - 1)
        j, si = start, 0
        while j < len(flat) and si < len(swords):
            if swords[si] in flat[j][0] or flat[j][0] in swords[si]:
                si += 1
            j += 1
        end_j = min(j - 1, len(flat) - 1)
        spans.append({"text": sent, "from": flat[start][1], "to": flat[end_j][1]})
        cur = min(end_j + 1, len(flat) - 1)

    # pastikan rentang monoton (kalimat tidak saling tumpang tindih)
    fixed = []
    for sp in spans:
        a = max(sp["from"], fixed[-1]["to"] + 1) if fixed else sp["from"]
        b = sp["to"]
        if b < a:
            continue
        fixed.append({"text": sp["text"], "from": a, "to": b})
    return fixed


def snap_to_beat(t, beats, tol_sec=0.1):
    """Tempelkan titik ke ketukan terdekat bila |delta| <= tol (default 3 frame)."""
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
    if best is not None and best_d <= tol_sec:
        return round(best, 3), True
    return t, False


def build_shots(spans, words, tone, beats, n_bg):
    """Bangun shot dari rentang kalimat.

    Shot WAJIB menutupi seluruh voiceover: bila satu kalimat lebih panjang dari
    `hold.max`, kalimat itu dipecah menjadi beberapa shot (bukan dipotong).
    """
    hold = TONE_HOLD.get(tone, TONE_HOLD["wry"])
    shots = []
    for sp in spans:
        a, b = sp["from"], sp["to"]
        if b < a or a >= len(words):
            continue
        vo_len = words[b]["end"] - words[a]["start"]
        # Video bernarasi: shot boleh lebih panjang dari tabel montase, tapi tidak lebih
        # dari NARRATION_MAX_HOLD (kalau tidak, penonton bosan melihat satu gambar).
        n_parts = max(1, math.ceil(vo_len / max(hold["max"], NARRATION_MAX_HOLD)))
        n_tokens = b - a + 1
        part_size = max(1, math.ceil(n_tokens / n_parts))
        idx = a
        while idx <= b:
            j = min(idx + part_size - 1, b)
            part_vo = words[j]["end"] - words[idx]["start"]
            dur = max(hold["min"], min(max(hold["max"], part_vo + 0.4), part_vo + 0.25))
            start, snapped = snap_to_beat(words[idx]["start"], beats)
            shots.append({
                "id": f"s{len(shots)+1}",
                "start": {"ref": "abs", "offset": round(start, 3)} if not shots
                         else {"ref": shots[-1]["id"], "offset": 0},
                "startSec": round(start, 3),
                "holdSec": round(dur, 2),
                "voSec": round(part_vo, 2),
                "energy": "medium",
                "hero": False,
                "voWords": [idx, j],
                "visual": {"type": "bg", "slot": len(shots) % max(1, n_bg), "motion": "kenburns"},
                "caption": {"style": "karaoke"},
                "transitionIn": "cut",
                "transitionSec": 0.0,
                "status": "built",
            })
            idx = j + 1
    return shots


def apply_energy_arc(shots, total):
    """Tandai segmen & hero, lalu beri energy per posisi."""
    if not shots:
        return shots
    marks = []
    acc = 0.0
    for seg in ENERGY_ARC:
        acc += seg["share"]
        marks.append((acc, seg))
    for i, sh in enumerate(shots):
        pos = (sh["startSec"] + sh["holdSec"] * 0.5) / max(total, 1e-6)
        seg_id = marks[-1][1]["id"]          # default: segmen terakhir (closer)
        for limit, seg in marks:
            if pos <= limit:
                seg_id = seg["id"]
                break
        sh["segment"] = seg_id
        sh["energy"] = {"hook": "high", "setup": "medium", "chain": "medium", "closer": "low"}[seg_id]
        sh["hero"] = seg_id in ("hook", "closer")
    if shots:
        shots[0]["energy"] = "high"
        shots[0]["hero"] = True
        shots[-1]["hero"] = True
    return shots


def apply_napas(shots, budget_sec, napas_dur=1.5):
    """R5: tiap 1-2 shot fakta sisipkan napas (energy low, tanpa callout).

    Napas menambah durasi, jadi jumlahnya dibatasi sisa anggaran (maks 4).
    """
    max_napas = 0 if budget_sec < napas_dur + 0.2 else max(2, min(4, int(budget_sec // napas_dur)))
    out, since, inserted = [], 0, 0
    for sh in shots:
        out.append(sh)
        since += 1
        if (inserted < max_napas and since >= 2 and sh.get("segment") == "chain"
                and sh["energy"] != "low"):
            out.append({
                "id": sh["id"] + "n",
                "start": {"ref": sh["id"], "offset": 0},
                "startSec": round(sh["startSec"] + sh["holdSec"], 3),
                "holdSec": napas_dur,
                "voSec": 0.0,
                "energy": "low",
                "hero": False,
                "voWords": None,
                "visual": {"type": "bg", "slot": (sh["visual"]["slot"] + 1) % 4, "motion": "drift"},
                "caption": {"style": "none"},
                "transitionIn": "dissolve",
                "transitionSec": 0.7,
                "napas": True,
                "segment": "chain",
                "status": "built",
            })
            inserted += 1
            since = 0
    return out


def apply_transitions(shots):
    for i, sh in enumerate(shots):
        if i == 0:
            sh["transitionIn"] = "cut"
        else:
            prev = shots[i - 1]["energy"]
            sh["transitionIn"] = TRANSITION_BY_DELTA.get((prev, sh["energy"]), "cut")
        sh["transitionSec"] = TRANSITION_SEC[sh["transitionIn"]]
    return shots


def close_duration(shots, target):
    """Tutup total durasi ke target: kompres shot non-hero, perpanjang bila kurang.

    Lantai (floor) tiap shot = voSec + 0.15 -> VO tidak pernah terpotong.
    """
    def floor_of(s):
        if s.get("napas"):
            return 1.4                                  # napas harus muat envelope (0.35+0.8+0.25)
        return round(float(s.get("voSec", 0) or 0) + 0.05, 3)

    def total():
        if not shots:
            return 0.0
        return shots[-1]["startSec"] + shots[-1]["holdSec"]

    # rapikan dulu jadi berurutan
    acc = shots[0]["startSec"] if shots else 0.0
    for i, s in enumerate(shots):
        s["startSec"] = round(acc, 3)
        if i > 0:
            s["start"] = {"ref": shots[i - 1]["id"], "offset": 0}
        acc += s["holdSec"]

    for _ in range(40):
        t = total()
        diff = t - target
        if abs(diff) <= max(0.3, target * 0.02):
            break
        if diff > 0:                                  # kelebihan -> kompres non-hero
            cands = [s for s in shots if not s.get("hero")]
            if not cands:
                break
            cands.sort(key=lambda s: -(s["holdSec"] - floor_of(s)))
            step = min(0.4, diff / max(1, len(cands)))
            moved = False
            for s in cands[: max(1, len(cands) // 3)]:
                new = max(floor_of(s), max(0.8, s["holdSec"] - step))
                if new < s["holdSec"] - 0.01:
                    s["holdSec"] = round(new, 2)
                    moved = True
            if not moved:
                break
        else:                                          # kekurangan -> perpanjang non-hero terpendek
            cands = [s for s in shots if not s.get("hero")]
            if not cands:
                break
            cands.sort(key=lambda s: s["holdSec"])
            step = min(0.4, -diff / max(1, len(cands)))
            for s in cands[: max(1, len(cands) // 3)]:
                s["holdSec"] = round(min(7.0, s["holdSec"] + step), 2)

        acc = shots[0]["startSec"]
        for i, s in enumerate(shots):
            s["startSec"] = round(acc, 3)
            if i > 0:
                s["start"] = {"ref": shots[i - 1]["id"], "offset": 0}
            acc += s["holdSec"]
    return shots, total()


def explode_words(words):
    """Token TTS bisa berupa frasa -> pecah jadi kata, durasi dibagi proporsional."""
    flat = []
    for wi, w in enumerate(words):
        toks = str(w["text"]).split()
        if not toks:
            continue
        span = max(float(w["end"]) - float(w["start"]), 1e-6)
        lens = [len(t) for t in toks]
        total = sum(lens) or 1
        t0 = float(w["start"])
        for k, t in enumerate(toks):
            d = span * lens[k] / total
            flat.append({"text": t, "start": round(t0, 3), "end": round(t0 + d, 3), "token": wi})
            t0 += d
    return flat


def build_captions(words, max_words=4, pre_roll=0.15):
    """Halaman caption 3-4 kata (2 baris), mulai sedikit sebelum kata pertama.

    Halaman tidak pernah melewati akhir kalimat (tanda titik/tanya/seru).
    """
    flat = explode_words(words)
    pages, i = [], 0
    while i < len(flat):
        chunk = flat[i:i + max_words]
        text = " ".join(w["text"] for w in chunk).strip()
        start = max(0.0, chunk[0]["start"] - pre_roll)
        end = max(start + 0.4, chunk[-1]["end"])
        # tutup halaman di akhir kalimat
        for k, w in enumerate(chunk):
            if re.search(r"[.!?…,;:]$", w["text"]):
                chunk = chunk[:k + 1]
                text = " ".join(x["text"] for x in chunk).strip()
                end = max(start + 0.4, chunk[-1]["end"] + 0.25)
                break
        pages.append({
            "text": text,
            "start": round(start, 3),
            "end": round(end, 3),
            "words": [chunk[0]["token"], chunk[-1]["token"]],
        })
        i += max(1, len(chunk))
    return pages


def main():
    ap = argparse.ArgumentParser(description="Naskah + kata -> STORYBOARD.json")
    ap.add_argument("--script", help="file naskah .txt (atau - untuk stdin)")
    ap.add_argument("--text", help="naskah langsung")
    ap.add_argument("--words", required=True, help="words.json dari TTS")
    ap.add_argument("--beats", help="beats.json dari beat_detect.py")
    ap.add_argument("--niche", default="sejarah", choices=sorted(NICHE_TONE))
    ap.add_argument("--tone", help="override tone: " + ", ".join(TONE_HOLD))
    ap.add_argument("--bg", type=int, default=4, help="jumlah gambar latar yang tersedia")
    ap.add_argument("--hook", default="", help="teks hook card")
    ap.add_argument("--outro", default="", help="teks outro card")
    ap.add_argument("--out", default="STORYBOARD.json")
    args = ap.parse_args()

    if args.text:
        script = args.text
    elif args.script and args.script != "-":
        with open(args.script, "r", encoding="utf-8") as f:
            script = f.read()
    else:
        script = sys.stdin.read()

    words = load_words(args.words)
    if not words:
        sys.exit("❌ words.json kosong atau formatnya salah.")
    beats = None
    if args.beats and os.path.exists(args.beats):
        with open(args.beats, "r", encoding="utf-8") as f:
            beats = json.load(f)

    tone = args.tone or NICHE_TONE.get(args.niche, "wry")
    sentences = split_sentences(script)
    spans = map_sentences_to_tokens(sentences, words)
    shots = build_shots(spans, words, tone, beats, args.bg)
    if not shots:
        sys.exit("❌ Tidak ada shot yang bisa dibentuk (kalimat tidak cocok dengan words.json).")

    total = words[-1]["end"]
    # rapikan startSec berurutan sebelum menghitung anggaran
    acc = shots[0]["startSec"]
    for i, s in enumerate(shots):
        s["startSec"] = round(acc, 3)
        acc += s["holdSec"]
    base_total = acc

    shots = apply_energy_arc(shots, total)
    budget = MAX_DURATION - base_total
    shots = apply_napas(shots, budget)
    shots = apply_transitions(shots)

    target = min(MAX_DURATION, max(MIN_DURATION, total + 1.2))
    shots, final = close_duration(shots, target)

    storyboard = {
        "meta": {
            "niche": args.niche,
            "tone": tone,
            "fps": FPS_DEFAULT,
            "width": 1080, "height": 1920,
            "voDurationSec": round(total, 2),
            "durationSec": round(final, 2),
            "hookText": args.hook,
            "outroText": args.outro,
            "energyArc": ENERGY_ARC,
            "holdTable": TONE_HOLD[tone],
            "beats": bool(beats),
        },
        "shots": shots,
        "captions": build_captions(words),
        "callouts": [],
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(storyboard, f, indent=2, ensure_ascii=False)

    napas = sum(1 for s in shots if s.get("napas"))
    print(f"✅ {args.out}: {len(shots)} shot ({napas} napas), tone={tone}, "
          f"durasi {final:.1f}s (VO {total:.1f}s), target {target:.1f}s")


if __name__ == "__main__":
    main()
