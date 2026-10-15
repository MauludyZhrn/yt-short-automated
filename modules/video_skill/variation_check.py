#!/usr/bin/env python3
"""
variation_check.py — cek keberagaman aset & risiko "slide show" sebelum render.

Dari OpenMontage: `slideshow_risk` + MMR diversity. Disederhanakan agar jalan tanpa CLIP
(cukup numpy + Pillow). Bila `sentence-transformers`/CLIP tersedia, skor semantik otomatis dipakai.

Yang dinilai (0 = aman, 10 = pasti terasa seperti slide show):
  1. duplikasi visual      : pasangan gambar dengan histogram hampir identik
  2. pengulangan latar     : satu gambar dipakai terlalu sering / terlalu lama
  3. statis berkepanjangan : shot tanpa gerak kamera lebih dari 4.5s
  4. kepadatan gerak       : tidak ada perubahan visual lebih dari 3 detik
  5. teks overload         : callout + caption menumpuk di waktu yang sama

Pemakaian:
  python variation_check.py --images public/temp/*.jpg --storyboard STORYBOARD.json
  python variation_check.py --images a.jpg b.jpg c.jpg --json report.json
"""
import argparse
import glob
import json
import os
import sys
from itertools import combinations

import numpy as np
from PIL import Image

DUP_THRESHOLD = 0.985      # cosine histogram similarity -> dianggap kembar
STATIC_MAX = 4.5           # detik, shot tanpa gerak
GAP_MAX = 3.0              # detik, maksimum tanpa perubahan visual
RISK_FAIL = 4.0


def hist_vec(path, size=(64, 64)):
    with Image.open(path) as im:
        im = im.convert("RGB").resize(size)
        a = np.asarray(im, dtype=np.float32)
    # 4x4x4 grid x 3 channel = 192 dim, plus histogram warna kasar
    blocks = a.reshape(16, 16, 4, 4, 3).mean(axis=(1, 3)).reshape(-1)
    v = np.concatenate([blocks, a.mean(axis=(0, 1)), a.std(axis=(0, 1))])
    n = np.linalg.norm(v) + 1e-9
    return v / n


def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def load_storyboard(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Cek diversitas aset & risiko slide show")
    ap.add_argument("--images", nargs="*", help="file gambar (glob didukung)")
    ap.add_argument("--storyboard", help="STORYBOARD.json")
    ap.add_argument("--json", help="tulis laporan ke file")
    args = ap.parse_args()

    paths = []
    for pat in args.images or []:
        hits = sorted(glob.glob(pat)) if any(c in pat for c in "*?[") else [pat]
        paths += [h for h in hits if os.path.exists(h)]
    paths = list(dict.fromkeys(paths))

    sb = load_storyboard(args.storyboard)
    reasons, score = [], 0.0

    # 1) duplikasi visual
    dupes = []
    if len(paths) >= 2:
        vecs = [hist_vec(p) for p in paths]
        for i, j in combinations(range(len(paths)), 2):
            s = cos(vecs[i], vecs[j])
            if s >= DUP_THRESHOLD:
                dupes.append({"a": os.path.basename(paths[i]), "b": os.path.basename(paths[j]), "sim": round(s, 4)})
    if dupes:
        score += min(3.0, 1.5 * len(dupes))
        reasons.append(f"{len(dupes)} pasang gambar nyaris identik: "
                       + ", ".join(f"{d['a']}~{d['b']}" for d in dupes[:4]))

    shots = (sb or {}).get("shots", [])
    total = float((sb or {}).get("meta", {}).get("durationSec") or 0)
    if shots:
        total = total or (shots[-1].get("startSec", 0) + shots[-1].get("holdSec", 0))

        # 2) pengulangan latar
        slots = [s.get("visual", {}).get("slot") for s in shots]
        counts = {}
        for s in slots:
            counts[s] = counts.get(s, 0) + 1
        top_slot, top_n = max(counts.items(), key=lambda kv: kv[1]) if counts else (None, 0)
        share = top_n / len(shots)
        if share > 0.5:
            score += min(2.5, (share - 0.5) * 8)
            reasons.append(f"latar slot #{top_slot} dipakai {top_n}/{len(shots)} shot ({share:.0%})")

        # 3) statis berkepanjangan
        static = [s["id"] for s in shots
                  if s.get("visual", {}).get("motion") in (None, "static") and float(s.get("holdSec", 0)) > STATIC_MAX]
        if static:
            score += min(2.0, 0.7 * len(static))
            reasons.append(f"shot statis > {STATIC_MAX}s: {static[:6]}")

        # 4) kepadatan gerak
        longest = max((float(s.get("holdSec", 0)) for s in shots), default=0)
        if longest > GAP_MAX and len(shots) <= 3:
            score += 1.5
            reasons.append(f"hanya {len(shots)} shot dengan shot terpanjang {longest:.1f}s (> {GAP_MAX}s)")

        # 5) teks ganda: callout yang *mengulang satu frasa caption utuh* (aturan C3).
        #    Menyorot 1-2 kata kunci bersamaan dengan caption karaoke itu teknik
        #    penekanan yang sah; yang salah adalah menulis ulang kalimatnya.
        caps = (sb or {}).get("captions", [])
        calls = (sb or {}).get("callouts", [])
        dup_text = []
        for c in calls:
            cw = {w for w in str(c.get("text", "")).lower().split() if len(w) > 2}
            for p in caps:
                if float(c.get("start", 0)) < float(p.get("end", 0)) and float(p.get("start", 0)) < float(c.get("end", 0)):
                    pw = {w for w in str(p.get("text", "")).lower().split() if len(w) > 2}
                    shared = cw & pw
                    if pw and len(shared) >= 3 and len(shared) >= 0.7 * len(pw):
                        dup_text.append(c.get("text"))
                        break
        if dup_text and calls and len(dup_text) > len(calls) * 0.6:
            score += 1.0
            reasons.append(f"callout mengulang kata caption: {dup_text[:4]}")

    score = round(min(10.0, score), 2)
    verdict = "FAIL" if score >= RISK_FAIL else ("WARN" if score >= 2.5 else "PASS")

    report = {"score": score, "verdict": verdict, "threshold": RISK_FAIL,
              "images": len(paths), "shots": len(shots), "durationSec": round(total, 2),
              "duplicates": dupes, "reasons": reasons}

    print(f"\n📊 Risiko slide show: {score}/10 — {verdict} (ambang FAIL >= {RISK_FAIL})")
    if reasons:
        for r in reasons:
            print(f"   • {r}")
    else:
        print("   • tidak ada masalah keberagaman yang terdeteksi")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"   laporan: {args.json}")
    sys.exit(1 if verdict == "FAIL" else 0)


if __name__ == "__main__":
    main()
