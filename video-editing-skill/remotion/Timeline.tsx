import React from "react";

/**
 * Timeline.tsx — SATU sumber kebenaran untuk semua angka waktu.
 *
 * Aturan P2 (dari video-shotcraft): jangan pernah mengetik angka frame di komponen.
 * Semua posisi diturunkan dari:
 *   - SHOTS[].from      (hasil storyboard_compile.py)
 *   - wordF(words, i)   (timestamp kata voiceover)
 *   - beatF(n)          (grid ketukan BGM)
 */

export const FPS_DEFAULT = 30;

export const sec2f = (s: number, fps: number = FPS_DEFAULT) => Math.round(s * fps);

/** Frame awal & panjang sebuah kata voiceover. */
export const wordF = (
  words: { start: number; end: number }[],
  i: number,
  fps: number = FPS_DEFAULT
) => {
  const w = words[Math.max(0, Math.min(i, words.length - 1))];
  return {
    from: Math.round((w?.start ?? 0) * fps),
    dur: Math.max(1, Math.round(((w?.end ?? 0) - (w?.start ?? 0)) * fps)),
  };
};

/** Frame ketukan ke-n BGM. Offset 1.28 frame = priming encoder AAC (Remotion 4.x, 48 kHz). */
export const OUTPUT_AUDIO_OFFSET_F = 1.28;
export const beatT = (n: number, beat0: number, interval: number, offsetSec = 0) =>
  beat0 + offsetSec + n * interval;
export const beatF = (
  n: number,
  beat0: number,
  interval: number,
  fps: number = FPS_DEFAULT,
  offsetSec = 0
) => Math.round(beatT(n, beat0, interval, offsetSec) * fps) - Math.round(OUTPUT_AUDIO_OFFSET_F);

/** Ketukan terdekat yang kuat (strength >= 0.5); dipakai untuk menempelkan potongan. */
export const nearestBeat = (
  frame: number,
  beats?: { beatTimes?: number[]; beatStrengths?: number[] } | null,
  fps: number = FPS_DEFAULT,
  tolFrames = 3
): number => {
  const times = beats?.beatTimes ?? [];
  const strengths = beats?.beatStrengths ?? times.map(() => 1);
  let best: number | null = null;
  let bestD = Infinity;
  for (let i = 0; i < times.length; i++) {
    if ((strengths[i] ?? 1) < 0.5) continue;
    const d = Math.abs(times[i] * fps - frame);
    if (d < bestD) {
      bestD = d;
      best = Math.round(times[i] * fps);
    }
  }
  return best !== null && bestD <= tolFrames ? best : frame;
};

/**
 * Envelope IN / HOLD / OUT (HyperFrames + shotcraft R1).
 * Anggarkan HOLD dulu, sisanya baru diisi animasi.
 */
export const envelope = (durationFrames: number, inSec = 0.35, outSec = 0.25, fps: number = FPS_DEFAULT) => {
  const inF = Math.round(inSec * fps);
  const outF = Math.round(outSec * fps);
  const holdF = Math.max(0, durationFrames - inF - outF);
  return { inF, holdF, outF, inEnd: inF, holdEnd: inF + holdF };
};

/** Spring dengan overshoot terkontrol — satu setelan untuk seluruh proyek. */
export const pop = { damping: 11, stiffness: 210, mass: 0.6 } as const;
export const soft = { damping: 20, stiffness: 120, mass: 0.8 } as const;
export const bouncy = { damping: 8, stiffness: 180, mass: 0.7 } as const;

/** Seed deterministik: dilarang Math.random() (render ulang harus identik). */
export const seedOf = (videoId: string, index: number) => `${videoId}-${index}`;

/** Zona aman vertikal Shorts: 320px bawah milik UI platform, 260px atas untuk status. */
export const SAFE = { top: 260, bottom: 320 } as const;

/** Posisi caption yang tidak pernah menabrak zona mati. */
export const captionBottom = (safeBottom = SAFE.bottom) => safeBottom + 40;

export type Shot = {
  id: string;
  from: number;
  durationFrames: number;
  energy?: "low" | "medium" | "high";
  hero?: boolean;
  napas?: boolean;
  segment?: string;
  voWords?: [number, number] | null;
  visual?: { type?: string; slot?: number; motion?: string };
  caption?: { style?: string; emphasis?: number[] };
  transitionIn?: "cut" | "dissolve" | "fade" | "push";
  transitionSec?: number;
  verb?: string;
};

/** Bangun tabel SHOTS dari props storyboard (dipakai semua komponen lain). */
export const buildShots = (storyboard?: { shots?: Shot[] } | null): Record<string, Shot> => {
  const out: Record<string, Shot> = {};
  (storyboard?.shots ?? []).forEach((s) => {
    out[s.id] = s;
  });
  return out;
};

/** Cari shot yang aktif pada frame tertentu. */
export const shotAt = (shots: Shot[], frame: number): Shot | undefined =>
  shots.find((s) => frame >= s.from && frame < s.from + s.durationFrames);
