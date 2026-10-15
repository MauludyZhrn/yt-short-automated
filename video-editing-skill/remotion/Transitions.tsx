import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Transitions.tsx — 4 kosakata transisi yang dipilih dari SELISIH ENERGI (aturan T1/T2).
 *
 * cut       : hard cut, tanpa frame perantara (default; energi sama)
 * dissolve  : cross dissolve 0.5–1.0s (energi turun / ganti topik)
 * fade      : fade 0.5s (masuk/keluar kartu)
 * push      : dorong 0.3–0.5s (energi naik)
 *
 * T4: transisi ADALAH keluarnya shot lama — dua arah digerakkan di frame yang sama.
 *     Jangan menulis animasi keluar sendiri di dalam shot.
 */

export type TransitionName = "cut" | "dissolve" | "fade" | "push";

/** Pilih transisi dari selisih energi antar shot (tabel T2). */
export const transitionFor = (
  prevEnergy: "low" | "medium" | "high" = "medium",
  nextEnergy: "low" | "medium" | "high" = "medium"
): TransitionName => {
  if (prevEnergy === nextEnergy) return "cut";
  const up = (e: string) => (e === "high" ? 2 : e === "medium" ? 1 : 0);
  if (up(nextEnergy) > up(prevEnergy)) return "push";
  if (prevEnergy === "high") return "dissolve";
  return "fade";
};

export const TRANSITION_SEC: Record<TransitionName, number> = {
  cut: 0,
  dissolve: 0.7,
  fade: 0.5,
  push: 0.4,
};

/**
 * Bungkus dua lapisan (A = shot lama, B = shot baru).
 * `from` = frame pertama shot baru; transisi berjalan mundur dari situ.
 */
export const Transition: React.FC<{
  from: number;
  name?: TransitionName;
  seconds?: number;
  prev: React.ReactNode;
  next: React.ReactNode;
  flash?: boolean;
}> = ({ from, name = "cut", seconds, prev, next, flash = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.max(1, Math.round((seconds ?? TRANSITION_SEC[name]) * fps));
  const start = from - dur;
  const p = interpolate(frame, [start, from], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // sebelum jendela transisi: hanya shot lama. sesudahnya: hanya shot baru.
  if (frame < start) return <AbsoluteFill>{prev}</AbsoluteFill>;
  if (frame >= from + 1) return <AbsoluteFill>{next}</AbsoluteFill>;

  const outA = (() => {
    switch (name) {
      case "dissolve":
        return { opacity: 1 - p };
      case "fade":
        return { opacity: 1 - p };
      case "push":
        return { transform: `translateX(${-p * 100}%)`, filter: `blur(${p * 8}px)` };
      default:
        return { opacity: 1 };
    }
  })();

  const inB = (() => {
    switch (name) {
      case "dissolve":
        return { opacity: p };
      case "fade":
        return { opacity: p };
      case "push":
        return { transform: `translateX(${(1 - p) * 100}%)`, filter: `blur(${(1 - p) * 8}px)` };
      default:
        return { opacity: 1 };
    }
  })();

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      <AbsoluteFill style={outA}>{prev}</AbsoluteFill>
      <AbsoluteFill style={inB}>{next}</AbsoluteFill>
      {flash && name === "cut" ? <Flash at={from} /> : null}
    </AbsoluteFill>
  );
};

/** Flash putih 4 frame pada titik potong (aturan T5: mulai 5 frame sebelum potong). */
export const Flash: React.FC<{ at: number; lead?: number; len?: number; peak?: number }> = ({
  at,
  lead = 5,
  len = 10,
  peak = 0.95,
}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [at - lead, at - lead + 4, at - lead + len], [0, peak, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (o <= 0.001) return null;
  return <AbsoluteFill style={{ backgroundColor: "#fff", opacity: o, mixBlendMode: "screen" }} />;
};

/** Light leak hangat singkat — dipakai saat ganti topik besar, bukan tiap potong. */
export const LightLeak: React.FC<{ at: number; len?: number }> = ({ at, len = 18 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [at, at + len * 0.35, at + len], [0, 0.55, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (o <= 0.001) return null;
  return (
    <AbsoluteFill
      style={{
        opacity: o,
        mixBlendMode: "screen",
        background:
          "radial-gradient(circle at 85% 12%, rgba(255,170,70,0.85), transparent 55%), radial-gradient(circle at 10% 90%, rgba(255,70,120,0.5), transparent 50%)",
      }}
    />
  );
};
