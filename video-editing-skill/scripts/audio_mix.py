#!/usr/bin/env python3
"""
audio_mix.py — campur VO + BGM (+ SFX) dengan ducking & loudness YouTube.

Aturan yang sudah teruji (OpenMontage audio_mixer + shotcraft sound-design):
  * amix SELALU normalize=0        -> tanpa itu N track dibagi N, musik menang
  * ducking = sidechaincompress    -> bukan menurunkan volume statis
  * kompensasi setelah ducking     -> volume = music_vol * 3
  * akhir wajib loudnorm -14 LUFS / -1 dBTP (YouTube, TikTok, Reels)
  * SFX 0.2-0.6; rentetan pakai dua sampel bergantian + volume menurun

Pemakaian:
  python audio_mix.py --vo voice.mp3 --bgm bgm.mp3 --out mix.m4a
  python audio_mix.py --vo voice.mp3 --bgm bgm.mp3 --segments "0-3,48-52" --out mix.m4a
  python audio_mix.py --vo voice.mp3 --bgm bgm.mp3 --sfx sfx.json --out mix.m4a
  python audio_mix.py --vo voice.mp3 --bgm bgm.mp3 --video video_nomix.mp4 --out final.mp4

sfx.json: [{"file":"sfx/pop.wav","at":3.6,"volume":0.5,"duration":0.2}, ...]
"""
import argparse
import json
import os
import subprocess
import sys

LOUDNORM = "loudnorm=I=-14:LRA=11:TP=-1.5"


def probe_duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", path],
                             stdout=subprocess.PIPE, check=True, text=True).stdout.strip()
        return float(out)
    except Exception:
        return None


def build_filter(has_vo, has_bgm, music_vol, segments, sfx, duck=True, loudnorm=LOUDNORM):
    """Kembalikan (filter_complex, label_output)."""
    parts = []
    labels = []

    vo_idx, bgm_idx = 0, 1
    if has_vo:
        labels.append("[0:a]")
    if has_bgm:
        bg = f"[{bgm_idx}:a]"
        if segments:
            expr = segmented_volume(segments, music_vol)
            parts.append(f"{bg}volume='{expr}':eval=frame[bg0]")
        else:
            parts.append(f"{bg}volume={music_vol}[bg0]")
        if duck and has_vo:
            # VO dipakai dua kali: sebagai sidechain (pemicu) dan sebagai trek utama
            parts.append("[0:a]asplit=2[vosc][vomix]")
            parts.append("[bg0][vosc]sidechaincompress=threshold=0.02:ratio=9:"
                         "attack=200:release=500:level_sc=1:mix=0.9[bgducked]")
            parts.append(f"[bgducked]volume={min(3.0, music_vol * 3)}[bgm_out]")
            parts.append("[vomix][bgm_out]amix=inputs=2:duration=longest:normalize=0[mixed]")
        else:
            parts.append("[0:a][bg0]amix=inputs=2:duration=longest:normalize=0[mixed]")
    else:
        parts.append("[0:a]anull[vomix]")
        parts.append("[vomix]amix=inputs=1:normalize=0[mixed]")

    # SFX (delay + volume, dipanahkan ke [mixed])
    if sfx:
        cur = "mixed"
        for i, s in enumerate(sfx):
            src = i + 2                       # input index setelah vo & bgm
            ms = int(round(float(s["at"]) * 1000))
            vol = float(s.get("volume", 0.4))
            parts.append(f"[{src}:a]volume={vol},adelay={ms}|{ms}[sfx{i}]")
            parts.append(f"[{cur}][sfx{i}]amix=inputs=2:duration=first:normalize=0[m{i}]")
            cur = f"m{i}"
        parts.append(f"[{cur}]{loudnorm},aresample=48000[out]")
    else:
        parts.append(f"[mixed]{loudnorm},aresample=48000[out]")
    return ";".join(parts)


def segmented_volume(segments, vol, fade=1.0):
    """volume(t): 0 di luar segmen, naik/turun linear di tepinya (fade detik)."""
    expr = "0"
    for (s, e) in reversed(segments):
        inner = (f"if(lt(t,{s + fade}),{vol}*(t-{s})/{fade},"
                 f"if(lt(t,{max(s + fade, e - fade)}),{vol},"
                 f"if(lt(t,{e}),{vol}*({e}-t)/{fade},0)))")
        expr = f"if(lt(t,{s}),0,if(lt(t,{e}),{inner},{expr}))"
    return expr


def parse_segments(text):
    out = []
    if not text:
        return out
    for chunk in str(text).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            a, b = chunk.split("-")
            out.append((float(a), float(b)))
        except ValueError:
            print(f"  ⚠️ segmen '{chunk}' diabaikan (format: 'awal-akhir', contoh 0-3)")
    return out


def main():
    ap = argparse.ArgumentParser(description="Campur VO + BGM + SFX (ffmpeg)")
    ap.add_argument("--vo")
    ap.add_argument("--bgm")
    ap.add_argument("--sfx", help="sfx.json [{file,at,volume}]")
    ap.add_argument("--segments", help="BGM hanya di segmen tertentu: '0-3,48-52'")
    ap.add_argument("--music-vol", type=float, default=0.15, help="volume BGM saat VO bicara (default 0.15)")
    ap.add_argument("--no-duck", action="store_true", help="matikan sidechain ducking")
    ap.add_argument("--video", help="gabungkan ke video (stream video di-copy)")
    ap.add_argument("--loudnorm", default=LOUDNORM)
    ap.add_argument("--out", default="mix.m4a")
    args = ap.parse_args()
    loudnorm = args.loudnorm

    if not args.vo and not args.bgm:
        sys.exit("❌ Butuh minimal --vo atau --bgm.")

    inputs, has_vo, has_bgm = [], False, False
    if args.vo:
        if not os.path.exists(args.vo):
            sys.exit(f"❌ VO tidak ada: {args.vo}")
        inputs += ["-i", args.vo]; has_vo = True
    if args.bgm:
        if not os.path.exists(args.bgm):
            sys.exit(f"❌ BGM tidak ada: {args.bgm}")
        inputs += ["-i", args.bgm]; has_bgm = True

    sfx = []
    if args.sfx:
        with open(args.sfx, "r", encoding="utf-8") as f:
            sfx = json.load(f)
        for s in sfx:
            if not os.path.exists(s["file"]):
                sys.exit(f"❌ SFX tidak ada: {s['file']}")
            inputs += ["-i", s["file"]]

    segments = parse_segments(args.segments)
    fc = build_filter(has_vo, has_bgm, args.music_vol, segments, sfx,
                     duck=not args.no_duck and has_vo, loudnorm=loudnorm)

    if args.video:
        cmd = ["ffmpeg", "-y", "-i", args.video, *inputs,
               "-filter_complex", fc, "-map", "0:v:0", "-map", "[out]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", args.out]
    else:
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc,
               "-map", "[out]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", args.out]

    print("🎛️  " + " ".join(cmd[:6]) + " …")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("❌ ffmpeg gagal (lihat log di atas).")

    dur = probe_duration(args.out)
    print(f"✅ {args.out}" + (f" ({dur:.2f}s)" if dur else ""))

    # laporan loudness
    if os.path.exists(args.out):
        r = subprocess.run(["ffmpeg", "-i", args.out, "-af", "volumedetect", "-f", "null", "-"],
                           stderr=subprocess.PIPE, text=True)
        for line in (r.stderr or "").splitlines():
            if "mean_volume" in line or "max_volume" in line:
                print("   " + line.strip())


if __name__ == "__main__":
    main()
