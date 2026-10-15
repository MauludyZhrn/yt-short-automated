#!/usr/bin/env python3
"""
qc_check.py — gerbang mutu pra-render & pasca-render.

Pra-render : python qc_check.py --pre --storyboard STORYBOARD.json --words words.json
Pasca      : python qc_check.py video.mp4 --storyboard STORYBOARD.json --words words.json --beats beats.json

Keluaran: tabel PASS/WARN/FAIL + daftar frame bermasalah.
FAIL = jangan publish.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

MAX_DURATION = 59.5
MIN_WORDS, MAX_WORDS = 110, 150
FPS = 30
SAFE_BOTTOM = 320
SAFE_TOP = 260
CAPTION_MIN_PX = 96
BLACK_FRAME_BYTES = 2000


class Report:
    def __init__(self):
        self.rows = []

    def add(self, code, status, msg):
        self.rows.append((code, status, msg))

    def check(self, code, ok, msg, warn_only=False):
        self.add(code, "PASS" if ok else ("WARN" if warn_only else "FAIL"), msg)
        return ok

    def render(self):
        w = max(len(r[2]) for r in self.rows) if self.rows else 10
        print("\n" + "=" * (w + 16))
        for code, st, msg in self.rows:
            print(f"{st:<5} {code:<5} {msg}")
        print("=" * (w + 16))
        fails = [r for r in self.rows if r[1] == "FAIL"]
        warns = [r for r in self.rows if r[1] == "WARN"]
        print(f"FAIL: {len(fails)} | WARN: {len(warns)}")
        if fails:
            print("❌ Ada butir FAIL — perbaiki sebelum render/publish.")
        elif warns:
            print("⚠️  Lolos dengan catatan.")
        else:
            print("✅ Semua butir lolos.")
        return 1 if fails else 0


def ffprobe(path, entries, of="default=nw=1:nk=1"):
    try:
        out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", entries, "-of", of, path],
                             stdout=subprocess.PIPE, check=True, text=True).stdout.strip()
        return out
    except Exception as e:
        return f"ERROR: {e}"


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- pra-render
def pre_check(sb, words, rep):
    meta = sb.get("meta", {})
    shots = sb.get("shots", [])
    callouts = sb.get("callouts", [])
    captions = sb.get("captions", [])
    dur = float(meta.get("durationSec") or (shots[-1]["startSec"] + shots[-1]["holdSec"] if shots else 0))

    rep.check("A1", dur <= MAX_DURATION, f"durasi {dur:.2f}s (batas {MAX_DURATION}s)")
    n_words = sum(len(str(w.get("word", w.get("text", ""))).split()) for w in words)
    rep.check("A2", MIN_WORDS <= n_words <= MAX_WORDS,
              f"naskah {n_words} kata dari {len(words)} token TTS (target {MIN_WORDS}-{MAX_WORDS})", warn_only=True)

    hold_tab = meta.get("holdTable") or {"min": 1.2}
    bad = [s["id"] for s in shots if float(s.get("holdSec", 0)) < 0.5]
    rep.check("A4", not bad, f"shot dengan hold < 0.5s: {bad[:6]}" if bad else "semua shot punya hold >= 0.5s")

    napas = sum(1 for s in shots if s.get("napas"))
    rep.check("A5a", napas >= 2, f"shot napas: {napas} (minimal 2)", warn_only=True)
    if dur > 0:
        density = len(callouts) / (dur / 6.5)
        rep.check("A5b", 0.6 <= density <= 1.6,
                  f"kepadatan callout {density:.2f}x (ideal 1 per 6.5s)", warn_only=True)
    early = [c["text"] for c in callouts if float(c.get("start", 0)) < 3.4]
    late = [c["text"] for c in callouts if float(c.get("end", 0)) > dur - 3.2]
    rep.check("A5c", not early and not late,
              (f"callout di zona terlarang: awal{early} akhir{late}" if (early or late)
               else "callout tidak masuk zona hook/outro"))
    overlap = []
    for a, b in zip(callouts, callouts[1:]):
        if float(a["end"]) > float(b["start"]) - 0.5:
            overlap.append((a.get("text"), b.get("text")))
    rep.check("A5d", not overlap, f"callout berdekatan: {overlap[:3]}" if overlap else "callout tidak bertabrakan")

    info = [c for c in callouts if c.get("type") in ("percent", "compare", "timeline")]
    rep.check("A6", len(info) >= 1, f"infografis: {len(info)} (minimal 1 bila naskah punya angka)", warn_only=True)
    bad_items = [c.get("text") for c in info if c["type"] != "percent" and len(c.get("items", [])) < 2]
    rep.check("A6b", not bad_items, f"infografis tanpa data cukup: {bad_items}" if bad_items else "data infografis lengkap")

    long_cap = [c["text"] for c in captions if len(str(c["text"]).split()) > 4]
    rep.check("C1", not long_cap, f"caption > 4 kata: {long_cap[:4]}" if long_cap else "caption <= 4 kata/baris")

    no_verb = [c.get("text") for c in callouts if not c.get("verb")]
    rep.check("K1", not no_verb, f"callout tanpa kata kerja gerak: {no_verb[:4]}" if no_verb else "semua callout punya verb")

    impacts = [c for c in callouts if c.get("verb") in ("slam", "glitch")]
    rep.check("R4", len(impacts) <= 3, f"impact layar penuh: {len(impacts)} (kuota 3)")

    trans = {s.get("transitionIn") for s in shots}
    rep.check("T1", len(trans) <= 4, f"kosakata transisi: {sorted(t for t in trans if t)} ({len(trans)} jenis)")

    no_start = [s["id"] for s in shots if not s.get("start")]
    rep.check("P2", not no_start, f"shot tanpa timing relatif: {no_start}" if no_start else "semua shot pakai start{ref,offset}", warn_only=True)
    return rep


# --------------------------------------------------------------- pasca-render
def post_check(path, sb, words, beats, rep):
    dur = ffprobe(path, "format=duration")
    try:
        dur = float(dur)
    except ValueError:
        rep.add("B1", "FAIL", f"ffprobe gagal: {dur}")
        return rep
    rep.check("B1", dur <= MAX_DURATION + 0.5, f"durasi file {dur:.2f}s")
    if sb:
        plan = float(sb.get("meta", {}).get("durationSec", 0) or 0)
        if plan:
            drift = abs(dur - plan) / plan * 100
            rep.check("B1b", drift <= 2.0, f"simpangan terhadap rencana {drift:.1f}% (ambang 2%)", warn_only=True)

    v = ffprobe(path, "stream=width,height,r_frame_rate,codec_type", of="csv=p=0")
    has_audio = "audio" in v
    rep.check("B5", has_audio, f"stream: {v.replace(chr(10), ' | ')}")
    rep.check("B6", "1080" in v and "1920" in v, "resolusi 1080x1920" if ("1080" in v and "1920" in v) else f"resolusi tidak sesuai: {v}")

    # frame hitam di 10/35/65/90%
    tmpdir = tempfile.mkdtemp(prefix="qc_")
    blacks = []
    for pct in (10, 35, 65, 90):
        t = dur * pct / 100.0
        out = os.path.join(tmpdir, f"f{pct}.png")
        subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{t:.2f}", "-i", path,
                        "-frames:v", "1", "-y", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(out) and os.path.getsize(out) < BLACK_FRAME_BYTES:
            blacks.append(pct)
    rep.check("B2", not blacks, f"frame hitam di {blacks}%" if blacks else "tidak ada frame hitam (sampling 4 titik)")

    r = subprocess.run(["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                       stderr=subprocess.PIPE, text=True)
    err = r.stderr or ""
    mean = mx = None
    for line in err.splitlines():
        if "mean_volume" in line:
            mean = float(line.split("mean_volume:")[1].split("dB")[0])
        if "max_volume" in line:
            mx = float(line.split("max_volume:")[1].split("dB")[0])
    if mean is None:
        rep.add("B4", "WARN", "volumedetect tidak tersedia")
    else:
        rep.check("B4a", mean > -60, f"mean_volume {mean:.1f} dB (ambang > -60)")
        rep.check("B4b", mx is not None and mx < -0.5, f"max_volume {mx:.1f} dB (ambang < -0.5)")

    if words and beats:
        rep.add("B7", "INFO", "sinkron caption vs ketukan: jalankan dengan --beats untuk detail")
    return rep


def main():
    ap = argparse.ArgumentParser(description="QC pra-render & pasca-render")
    ap.add_argument("video", nargs="?", help="file video untuk pemeriksaan pasca-render")
    ap.add_argument("--pre", action="store_true", help="hanya pemeriksaan pra-render")
    ap.add_argument("--storyboard")
    ap.add_argument("--words")
    ap.add_argument("--beats")
    args = ap.parse_args()

    # Kenyamanan: argumen posisi yang berakhir .json otomatis dianggap storyboard.
    if args.video and args.video.lower().endswith(".json") and not args.storyboard:
        args.storyboard, args.video = args.video, None

    rep = Report()
    sb = load(args.storyboard)
    words = load(args.words, [])
    beats = load(args.beats)

    if sb is None and not args.video:
        sys.exit("❌ Butuh --storyboard (pra-render) atau file video (pasca-render).")

    if sb is not None:
        pre_check(sb, words, rep)
    if args.video:
        if not os.path.exists(args.video):
            sys.exit(f"❌ Video tidak ada: {args.video}")
        post_check(args.video, sb, words, beats, rep)

    sys.exit(rep.render())


if __name__ == "__main__":
    main()
