import React from "react";
import { AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadSpace } from "@remotion/google-fonts/SpaceGrotesk";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

loadPlayfair();
loadSpace();
loadMono();

/**
 * Gaya "cinematic" ala CapCut/After Effects premium data-story:
 * latar gelap, glow lembut, tipografi minimal, kartu data & pill chip.
 * Referensi: judul besar ber-glow, eyebrow italic serif, badge "01 · LABEL",
 * kartu border tipis dengan highlight, angka besar outline glow.
 */

export const FONT_GLOW_DISPLAY = "'Space Grotesk', 'Montserrat', Arial, sans-serif";
export const FONT_GLOW_SERIF = "'Playfair Display', Georgia, serif";
export const FONT_GLOW_MONO = "'JetBrains Mono', 'Courier New', monospace";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const GLOW_THEMES = {
  gold: { primary: "#E8C36C", soft: "rgba(232,195,108,0.35)", dim: "rgba(232,195,108,0.12)" },
  cyan: { primary: "#8FE3FF", soft: "rgba(143,227,255,0.35)", dim: "rgba(143,227,255,0.12)" }
} as const;
export type GlowAccent = keyof typeof GLOW_THEMES;

/* ------------------------------------------------------------------ */
/*  Background sinematik: hitam pekat + glow radial pusat + grid halus  */
/* ------------------------------------------------------------------ */
export const CinematicBG = ({ accent = "gold" }: { accent?: GlowAccent }) => {
  const frame = useCurrentFrame();
  const c = GLOW_THEMES[accent];
  const pulse = 0.5 + Math.sin(frame / 50) * 0.08;

  return (
    <AbsoluteFill style={{ pointerEvents: "none", backgroundColor: "#07070A" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 70% 45% at 50% 42%, ${c.dim} 0%, transparent 70%)`,
          opacity: pulse
        }}
      />
      <AbsoluteFill
        style={{
          opacity: 0.05,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          maskImage: "radial-gradient(ellipse 70% 60% at 50% 45%, #000 40%, transparent 85%)",
          WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 50% 45%, #000 40%, transparent 85%)"
        }}
      />
      {Array.from({ length: 18 }).map((_, i) => {
        const x = random(`gb-x-${i}`) * 100;
        const speed = 0.08 + random(`gb-s-${i}`) * 0.18;
        const y = ((random(`gb-y-${i}`) * 120 - frame * speed) % 120 + 120) % 120;
        const size = 1.5 + random(`gb-sz-${i}`) * 2.5;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y - 10}%`,
              width: size,
              height: size,
              borderRadius: "50%",
              background: c.primary,
              opacity: 0.25 + 0.25 * Math.sin(frame / 20 + i),
              boxShadow: `0 0 6px ${c.primary}`
            }}
          />
        );
      })}
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.75) 100%)" }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  Teks kata-per-kata: blur-in + rise, glow lembut (bukan hard extrude) */
/* ------------------------------------------------------------------ */
export const GlowWords = ({
  text,
  size,
  accent = "gold",
  color = "#F5F3EE",
  delay = 0,
  stagger = 3,
  font = FONT_GLOW_DISPLAY,
  weight = 800,
  letterSpacing = -0.5,
  maxWidth = 920,
  align = "center",
  glow = true
}: {
  text: string;
  size: number;
  accent?: GlowAccent;
  color?: string;
  delay?: number;
  stagger?: number;
  font?: string;
  weight?: number;
  letterSpacing?: number;
  maxWidth?: number;
  align?: "center" | "left";
  glow?: boolean;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = GLOW_THEMES[accent];
  const words = String(text).split(/\s+/).filter(Boolean);

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: align === "center" ? "center" : "flex-start",
        gap: `0 ${size * 0.24}px`,
        maxWidth,
        lineHeight: 1.08,
        fontFamily: font,
        fontWeight: weight,
        fontSize: size,
        letterSpacing
      }}
    >
      {words.map((w, i) => {
        const f = frame - delay - i * stagger;
        const sp = spring({ frame: f, fps, config: { damping: 16, stiffness: 120, mass: 0.6 } });
        const op = interpolate(f, [0, 10], [0, 1], clamp);
        const blur = Math.max(0, (1 - sp) * 8);
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              color,
              opacity: op,
              transform: `translateY(${(1 - sp) * 26}px)`,
              filter: `blur(${blur}px)`,
              textShadow: glow
                ? `0 0 ${18 + Math.sin(frame / 6) * 6}px ${c.soft}, 0 2px 18px rgba(0,0,0,0.65)`
                : "0 2px 14px rgba(0,0,0,0.6)"
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};

/* Duplikat bayangan di belakang judul (efek "double exposure" khas AE) */
export const GhostEcho = ({ text, size, font = FONT_GLOW_DISPLAY, weight = 800, offset = 6 }: { text: string; size: number; font?: string; weight?: number; offset?: number }) => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 40) * offset;
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: font,
        fontWeight: weight,
        fontSize: size,
        color: "transparent",
        WebkitTextStroke: "1.5px rgba(255,255,255,0.08)",
        transform: `translate(${drift}px, ${Math.abs(drift) * 0.4}px) scale(1.03)`,
        letterSpacing: -0.5,
        whiteSpace: "nowrap",
        pointerEvents: "none"
      }}
    >
      {text}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Pill badge bernomor: "01 · TEORI"                                   */
/* ------------------------------------------------------------------ */
export const GlowPill = ({
  index,
  label,
  accent = "gold",
  active = true,
  delay = 0,
  size = 24
}: {
  index?: number | string;
  label: string;
  accent?: GlowAccent;
  active?: boolean;
  delay?: number;
  size?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = GLOW_THEMES[accent];
  const sp = spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 160, mass: 0.6 } });

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: size * 0.4,
        padding: `${size * 0.42}px ${size * 0.9}px`,
        borderRadius: 999,
        border: `1px solid ${active ? c.primary + "88" : "rgba(255,255,255,0.14)"}`,
        background: active ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.015)",
        boxShadow: active ? `0 0 ${18}px ${c.dim}` : "none",
        opacity: Math.min(1, sp * 1.4),
        transform: `translateY(${(1 - sp) * 10}px) scale(${interpolate(sp, [0, 1], [0.92, 1])})`,
        fontFamily: FONT_GLOW_MONO,
        fontSize: size,
        letterSpacing: 1,
        color: active ? "#F5F3EE" : "rgba(255,255,255,0.45)",
        whiteSpace: "nowrap"
      }}
    >
      <span
        style={{
          width: size * 0.3,
          height: size * 0.3,
          borderRadius: "50%",
          background: active ? c.primary : "rgba(255,255,255,0.3)",
          boxShadow: active ? `0 0 8px ${c.primary}` : "none"
        }}
      />
      {index !== undefined && <span style={{ opacity: 0.6 }}>{String(index).padStart(2, "0")} ·</span>}
      <span style={{ textTransform: "uppercase" }}>{label}</span>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Step number: angka besar outline-glow + eyebrow serif italic        */
/* ------------------------------------------------------------------ */
export const GlowStepNumber = ({
  number,
  eyebrow,
  footnote,
  accent = "cyan",
  delay = 0
}: {
  number: string | number;
  eyebrow?: string;
  footnote?: string;
  accent?: GlowAccent;
  delay?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = GLOW_THEMES[accent];
  const f = frame - delay;
  const sp = spring({ frame: f, fps, config: { damping: 15, stiffness: 140, mass: 0.7 } });
  const op = interpolate(f, [0, 10], [0, 1], clamp);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
      {eyebrow && (
        <div
          style={{
            fontFamily: FONT_GLOW_SERIF,
            fontStyle: "italic",
            fontSize: 44,
            color: "rgba(255,255,255,0.75)",
            opacity: op,
            transform: `translateY(${(1 - sp) * 14}px)`
          }}
        >
          {eyebrow}
        </div>
      )}
      <div
        style={{
          fontFamily: FONT_GLOW_DISPLAY,
          fontWeight: 800,
          fontSize: 220,
          lineHeight: 0.95,
          color: "transparent",
          WebkitTextStroke: `3px ${c.primary}`,
          textShadow: `0 0 36px ${c.soft}`,
          opacity: op,
          transform: `translateY(${(1 - sp) * 20}px) scale(${interpolate(sp, [0, 1], [0.9, 1])})`
        }}
      >
        {number}
      </div>
      {footnote && (
        <div style={{ marginTop: 14, opacity: interpolate(f, [10, 20], [0, 1], clamp) }}>
          <GlowPill label={footnote} accent={accent} delay={delay + 10} size={22} />
        </div>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Kartu data: border tipis + sapuan highlight saat masuk               */
/* ------------------------------------------------------------------ */
export const GlowCard = ({
  label,
  value,
  accent = "cyan",
  delay = 0,
  width = 620
}: {
  label: string;
  value: string;
  accent?: GlowAccent;
  delay?: number;
  width?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = GLOW_THEMES[accent];
  const f = frame - delay;
  const sp = spring({ frame: f, fps, config: { damping: 16, stiffness: 150, mass: 0.7 } });
  const sweep = interpolate(f, [4, 26], [-30, 130], { ...clamp, easing: Easing.out(Easing.cubic) });

  return (
    <div
      style={{
        position: "relative",
        width,
        padding: "28px 32px",
        borderRadius: 14,
        border: `1px solid ${c.primary}55`,
        background: "rgba(10,12,16,0.72)",
        boxShadow: `0 0 30px ${c.dim}, inset 0 1px 0 rgba(255,255,255,0.04)`,
        overflow: "hidden",
        opacity: Math.min(1, sp * 1.4),
        transform: `translateY(${(1 - sp) * 22}px)`
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: `${sweep}%`,
          width: "22%",
          transform: "skewX(-18deg)",
          background: `linear-gradient(90deg, transparent, ${c.soft}, transparent)`,
          pointerEvents: "none"
        }}
      />
      <div
        style={{
          fontFamily: FONT_GLOW_MONO,
          fontSize: 20,
          letterSpacing: 2,
          textTransform: "uppercase",
          color: "rgba(255,255,255,0.55)",
          marginBottom: 10
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: FONT_GLOW_DISPLAY,
          fontWeight: 800,
          fontSize: 56,
          color: c.primary,
          textShadow: `0 0 22px ${c.soft}`
        }}
      >
        {value}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Garis pembatas ber-glow (progress / divider)                        */
/* ------------------------------------------------------------------ */
export const GlowRule = ({ width = 220, accent = "gold", delay = 0 }: { width?: number; accent?: GlowAccent; delay?: number }) => {
  const frame = useCurrentFrame();
  const c = GLOW_THEMES[accent];
  const w = interpolate(frame - delay, [0, 16], [0, width], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <div
      style={{
        height: 2,
        width: w,
        background: `linear-gradient(90deg, transparent, ${c.primary}, transparent)`,
        boxShadow: `0 0 10px ${c.primary}`
      }}
    />
  );
};
