#!/usr/bin/env python3
"""
storyboard_compile.py — STORYBOARD.json -> input_props.json untuk Remotion.

Tugas utamanya: mengubah timing RELATIF menjadi frame ABSOLUT (aturan P2).
Frame absolut dihitung sekali di sini; komponen React hanya membaca hasilnya.

  {"ref":"abs","offset":0}      -> detik 0
  {"ref":"s3","offset":0}       -> persis setelah shot s3 selesai
  {"ref":"s3","offset":-0.4}    -> overlap 0.4s sebelum s3 selesai
  {"ref":"word:12","offset":-0.15} -> 0.15s sebelum kata ke-12 diucapkan
  {"ref":"beat:8","offset":0}   -> pada ketukan ke-8 BGM

Keluaran tetap kompatibel dengan ShortsVideo.tsx (field lama dipertahankan) DAN
menambah `storyboard`, `beats`, `wordFrames`, `safeArea` untuk StoryboardVideo.tsx.

Pemakaian:
  python storyboard_compile.py STORYBOARD.json --words words.json --beats beats.json \
      --audio temp/voice.mp3 --bgm temp/bgm.mp3 --bg temp/bg_0.jpg temp/bg_1.jpg \
      --out public/input_props.json
"""
import argparse
import json
import os
import sys

IN_BASE, MIN_HOLD, OUT_BASE = 0.35, 0.8, 0.25
MAX_DURATION = 59.5


def load(path, default=None):
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def words_list(path):
    data = load(path, [])
    if isinstance(data, dict):
        data = data.get("subtitles") or data.get("words") or []
    out = []
    for w in data:
        if not isinstance(w, dict):
            continue
        t = str(w.get("word", w.get("text", ""))).strip()
        try:
            s, e = float(w.get("start")), float(w.get("end"))
        except (TypeError, ValueError):
            continue
        if t:
            out.append({"word": t, "start": round(s, 3), "end": round(e, 3)})
    return out


def resolve(shots, words, beats, fps):
    """Kembalikan dict id -> (startSec, holdSec) + daftar peringatan."""
    ends, warns = {}, []
    order = []
    for sh in shots:
        ref = (sh.get("start") or {}).get("ref", "abs")
        off = float((sh.get("start") or {}).get("offset", 0) or 0)
        sid = sh.get("id")
        if ref in ("abs", None, "beat:snap"):
            start = off                       # offset = detik absolut
        elif ref.startswith("word:"):
            i = int(ref.split(":")[1])
            start = words[min(i, len(words) - 1)]["start"] + off if words else off
        elif ref.startswith("beat:"):
            times = (beats or {}).get("beatTimes") or []
            i = int(ref.split(":")[1])
            start = times[min(i, len(times) - 1)] + off if times else off
        elif ref in ends:
            start = ends[ref] + off
        else:
            warns.append(f"shot {sid}: ref '{ref}' tidak dikenal -> diperlakukan sebagai start lama")
            start = float(sh.get("startSec", 0) or 0)
        start = max(0.0, start)
        hold = float(sh.get("holdSec", 2.0) or 2.0)
        if hold < IN_BASE + MIN_HOLD + OUT_BASE:
            warns.append(f"shot {sid}: hold {hold:.2f}s terlalu pendek untuk envelope "
                         f"(min {IN_BASE + MIN_HOLD + OUT_BASE:.2f}s) -> frame puncak tidak akan terlihat")
        ends[sid] = start + hold
        sh["startSec"] = round(start, 3)
        sh["holdSec"] = round(hold, 3)
        order.append((sid, start, hold))
    return order, warns


def main():
    ap = argparse.ArgumentParser(description="Storyboard -> input_props.json (Remotion)")
    ap.add_argument("storyboard")
    ap.add_argument("--words", help="words.json (untuk ref word:N & wordFrames)")
    ap.add_argument("--beats", help="beats.json (untuk ref beat:N)")
    ap.add_argument("--audio", default="", help="path audio relatif ke public/ (mis. temp/voice.mp3)")
    ap.add_argument("--bgm", default="", help="path BGM relatif ke public/")
    ap.add_argument("--bg", nargs="*", default=[], help="path gambar latar relatif ke public/")
    ap.add_argument("--logo", default="")
    ap.add_argument("--bgm-volume", type=float, default=0.15)
    ap.add_argument("--subtitle-style", default="karaoke", choices=["karaoke", "slide", "typewriter"])
    ap.add_argument("--style", default="stack", choices=["stack", "cinematic"],
                    help="stack = gaya referensi @rizkzul (default); cinematic = gaya lama Space Grotesk+gold.")
    ap.add_argument("--out", default="input_props.json")
    args = ap.parse_args()

    sb = load(args.storyboard)
    if sb is None:
        sys.exit(f"❌ Storyboard tidak ditemukan: {args.storyboard}")
    fps = int((sb.get("meta") or {}).get("fps", 30) or 30)
    words = words_list(args.words) if args.words else []
    beats = load(args.beats)
    shots = sb.get("shots", [])
    if not shots:
        sys.exit("❌ Storyboard tidak punya shot.")

    order, warns = resolve(shots, words, beats, fps)
    for w in warns:
        print("  ⚠️ " + w)

    duration_sec = max((s + h for _, s, h in order), default=0)
    if duration_sec > MAX_DURATION:
        print(f"  ⚠️ durasi {duration_sec:.1f}s melebihi {MAX_DURATION}s — Shorts akan terpotong!")

    meta = sb.get("meta", {})
    theme = "history" if meta.get("niche") in ("sejarah", "history") else (
        "space" if meta.get("niche") in ("semesta", "space") else "cinematic")
    style = args.style
    # auto-promote theme: kalau style=stack, theme sebaiknya cinematic (jadi GLOW_THEMES bekerja)
    if style == "stack":
        theme = "cinematic"

    storyboard_out = []
    for sid, start, hold in order:
        sh = next(s for s in shots if s.get("id") == sid)
        storyboard_out.append({
            "id": sid,
            "from": int(round(start * fps)),
            "durationFrames": int(round(hold * fps)),
            "energy": sh.get("energy", "medium"),
            "hero": bool(sh.get("hero")),
            "napas": bool(sh.get("napas")),
            "segment": sh.get("segment"),
            "voWords": sh.get("voWords"),
            "visual": sh.get("visual", {}),
            "caption": sh.get("caption", {}),
            "transitionIn": sh.get("transitionIn", "cut"),
            "transitionSec": sh.get("transitionSec", 0.0),
            "verb": (sh.get("callout") or {}).get("verb"),
        })

    word_frames = [[int(round(w["start"] * fps)), int(round(w["end"] * fps))] for w in words]

    props = {
        # ---- field lama (kompatibel dengan ShortsVideo.tsx yang sudah ada) ----
        "audioPath": args.audio,
        "bgMusicPath": args.bgm or None,
        "bgImages": list(args.bg),
        "titleText": meta.get("hookText", ""),
        "outroText": meta.get("outroText", ""),
        "logoPath": args.logo or None,
        "subtitles": sb.get("captions") or words,
        "durationInFrames": int(round(duration_sec * fps)),
        "fps": fps,
        "theme": theme,
        "style": style,
        "motionCues": sb.get("callouts", []),
        "bgmVolume": args.bgm_volume,
        # ---- field baru (dipakai StoryboardVideo.tsx) ----
        "subtitleStyle": args.subtitle_style,
        "storyboard": {
            "shots": storyboard_out,
            "meta": {**meta, "durationSec": round(duration_sec, 2), "theme": theme, "style": style},
        },
        "beats": beats,
        "wordFrames": word_frames,
        "safeArea": {"top": 260, "bottom": 320},
        "envelope": {"in": IN_BASE, "minHold": MIN_HOLD, "out": OUT_BASE},
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(props, f, indent=2, ensure_ascii=False)

    print(f"✅ {args.out}: {len(storyboard_out)} shot, {len(sb.get('callouts', []))} callout, "
          f"{props['durationInFrames']} frame ({duration_sec:.2f}s @ {fps}fps), tema {theme}, style {style}")


if __name__ == "__main__":
    main()
