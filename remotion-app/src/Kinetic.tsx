import React from "react";
import { Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadMarker } from "@remotion/google-fonts/PermanentMarker";

loadAnton();
loadMarker();

export const FONT_IMPACT = "'Anton', 'Montserrat', 'Impact', 'Arial Black', sans-serif";
export const FONT_MARKER = "'Permanent Marker', 'Poppins', cursive";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Bayangan keras bertumpuk (extrude 3D ala CapCut). */
export const extrude = (color: string, depth = 8, step = 1.6) =>
  Array.from({ length: depth }, (_, i) => `${((i + 1) * step * 0.6).toFixed(1)}px ${((i + 1) * step).toFixed(1)}px 0 ${color}`).join(", ");

export type KVariant = "slam" | "wave" | "mask" | "type";

type Props = {
  text: string;
  variant?: KVariant;
  size: number;
  color?: string;
  accent?: string;          // warna kata penekanan
  markerWord?: number;      // indeks kata yang diberi marker wipe
  markerColor?: string;
  markerInk?: string;       // warna teks di atas marker
  delay?: number;           // frame
  stagger?: number;         // frame antar huruf
  shadow?: string;          // textShadow CSS
  stroke?: string;          // warna outline
  strokeWidth?: number;
  maxWidth?: number;
  font?: string;
  letterSpacing?: number;
  lineHeight?: number;
  align?: "center" | "left";
  extrudeColor?: string;
  ring?: string;            // cincin luar ala sticker (mis. putih)
  ringSize?: number;
};

/**
 * Tipografi bergerak per huruf:
 *  slam  : huruf jatuh dari besar + blur, menghantam (hook / angka)
 *  wave  : huruf memantul naik lalu bergelombang pelan (pertanyaan / CTA)
 *  mask  : kata naik dari dalam mask (editorial)
 *  type  : mesin tik dengan kursor
 */
export const KineticText = ({
  text,
  variant = "slam",
  size,
  color = "#fff",
  accent,
  markerWord,
  markerColor = "#FFE600",
  markerInk = "#0A0A0A",
  delay = 0,
  stagger = 2,
  shadow,
  stroke,
  strokeWidth = 0,
  maxWidth = 940,
  font = FONT_IMPACT,
  letterSpacing = 1,
  lineHeight = 1.0,
  align = "center",
  extrudeColor,
  ring,
  ringSize = 4
}: Props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = String(text).split(/\s+/).filter(Boolean);

  const ringShadow = ring
    ? Array.from({ length: 8 }, (_, i) => {
        const a = (i / 8) * Math.PI * 2;
        return `${(Math.cos(a) * ringSize).toFixed(1)}px ${(Math.sin(a) * ringSize).toFixed(1)}px 0 ${ring}`;
      }).join(", ")
    : "";
  const textShadow =
    [ringShadow, extrudeColor ? extrude(extrudeColor, 7, 1.7) : "", shadow ?? ""].filter(Boolean).join(", ") || undefined;
  let gi = 0;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: align === "center" ? "center" : "flex-start",
        alignItems: "baseline",
        maxWidth,
        gap: `0 ${size * 0.22}px`,
        lineHeight,
        fontFamily: font,
        fontSize: size,
        letterSpacing,
        textTransform: "uppercase"
      }}
    >
      {words.map((w, wi) => {
        const isMarker = markerWord === wi;
        const wordStart = gi;
        const chars = Array.from(w);
        const wipe = isMarker
          ? interpolate(frame - delay, [6 + wordStart * stagger, 20 + wordStart * stagger], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) })
          : 0;
        const inkColor = isMarker && wipe > 0.4 ? markerInk : accent && wi === words.length - 1 ? accent : color;

        const letters = chars.map((ch, ci) => {
          const g = gi++;
          const f = frame - delay - g * stagger;
          let style: React.CSSProperties = {};

          if (variant === "slam") {
            const sp = spring({ frame: f, fps, config: { damping: 11, stiffness: 210, mass: 0.6 } });
            const jitter = (random(`k-${g}-${text}`) - 0.5) * 36;
            style = {
              opacity: interpolate(f, [0, 3], [0, 1], clamp),
              transform: `translateY(${(1 - sp) * -70}px) scale(${interpolate(sp, [0, 1], [2.8, 1])}) rotate(${(1 - sp) * jitter}deg)`,
              filter: sp < 0.98 ? `blur(${(1 - sp) * 12}px)` : undefined
            };
          } else if (variant === "wave") {
            const sp = spring({ frame: f, fps, config: { damping: 9, stiffness: 160, mass: 0.7 } });
            const live = Math.max(0, Math.min(1, sp));
            style = {
              opacity: interpolate(f, [0, 3], [0, 1], clamp),
              transform: `translateY(${(1 - sp) * 110 + Math.sin((frame - g * 3) / 6) * 7 * live}px) rotate(${(1 - sp) * 14 + Math.sin((frame - g * 2) / 9) * 1.6 * live}deg)`
            };
          } else if (variant === "mask") {
            const sp = spring({ frame: f, fps, config: { damping: 20, stiffness: 190, mass: 0.6 } });
            style = { transform: `translateY(${Math.max(0, 1 - sp) * 118}%)` };
          } else {
            style = { opacity: f >= 0 ? 1 : 0 };
          }

          return (
            <span
              key={ci}
              style={{
                display: "inline-block",
                whiteSpace: "pre",
                color: inkColor,
                textShadow: isMarker && wipe > 0.4 ? "none" : textShadow,
                WebkitTextStroke: stroke && strokeWidth ? `${strokeWidth}px ${stroke}` : undefined,
                paintOrder: "stroke fill",
                ...style
              }}
            >
              {ch}
            </span>
          );
        });

        return (
          <span
            key={wi}
            style={{
              position: "relative",
              display: "inline-block",
              whiteSpace: "nowrap",
              overflow: variant === "mask" || isMarker ? "hidden" : "visible",
              padding: variant === "mask" || isMarker ? "0.06em 0.1em" : "0.02em 0",
              margin: isMarker ? "0 0.04em" : undefined
            }}
          >
            {isMarker && (
              <span
                style={{
                  position: "absolute",
                  inset: "0.08em 0 0.02em",
                  background: markerColor,
                  transform: `scaleX(${wipe}) skewX(-8deg)`,
                  transformOrigin: "left center"
                }}
              />
            )}
            <span style={{ position: "relative" }}>{letters}</span>
            {variant === "type" && wi === words.length - 1 && frame - delay > 0 && Math.floor(frame / 8) % 2 === 0 && (
              <span style={{ color }}>|</span>
            )}
          </span>
        );
      })}
    </div>
  );
};

/** Teks glitch RGB-split: dipakai saat angka/tahun menghantam layar. */
export const GlitchText = ({
  text,
  size,
  color = "#fff",
  delay = 0,
  duration = 14,
  font = FONT_IMPACT,
  shadow,
  letterSpacing = 2
}: {
  text: string;
  size: number;
  color?: string;
  delay?: number;
  duration?: number;
  font?: string;
  shadow?: string;
  letterSpacing?: number;
}) => {
  const frame = useCurrentFrame();
  const f = frame - delay;
  const amp = f < 0 ? 0 : interpolate(f, [0, duration], [1, 0], clamp);
  const dx = (random(`gx-${frame}`) - 0.5) * 34 * amp;
  const dy = (random(`gy-${frame}`) - 0.5) * 10 * amp;
  const slice = random(`gs-${frame}`);
  const base: React.CSSProperties = {
    fontFamily: font,
    fontSize: size,
    letterSpacing,
    textTransform: "uppercase",
    whiteSpace: "nowrap",
    lineHeight: 1
  };
  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      {amp > 0.02 && (
        <>
          <div style={{ ...base, position: "absolute", left: dx, top: dy, color: "#00E5FF", mixBlendMode: "screen", opacity: 0.85 }}>{text}</div>
          <div style={{ ...base, position: "absolute", left: -dx, top: -dy, color: "#FF2E88", mixBlendMode: "screen", opacity: 0.85 }}>{text}</div>
        </>
      )}
      <div
        style={{
          ...base,
          position: "relative",
          color,
          textShadow: shadow,
          clipPath:
            amp > 0.3 && slice > 0.55
              ? `inset(${Math.floor(slice * 60)}% 0 ${Math.floor((1 - slice) * 40)}% 0)`
              : undefined
        }}
      >
        {text}
      </div>
    </div>
  );
};

/** Label ala selotip/stiker tulisan tangan di atas teks utama. */
export const Kicker = ({
  text,
  bg = "#FFE600",
  ink = "#14110D",
  size = 40,
  delay = 0,
  rotate = -3
}: {
  text: string;
  bg?: string;
  ink?: string;
  size?: number;
  delay?: number;
  rotate?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = spring({ frame: frame - delay, fps, config: { damping: 10, stiffness: 190, mass: 0.6 } });
  return (
    <div
      style={{
        display: "inline-block",
        padding: "6px 24px",
        background: bg,
        color: ink,
        fontFamily: FONT_MARKER,
        fontSize: size,
        letterSpacing: 3,
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        boxShadow: "6px 6px 0 rgba(0,0,0,0.75)",
        transform: `rotate(${rotate * sp}deg) scale(${sp})`,
        opacity: Math.min(1, sp * 2)
      }}
    >
      {text}
    </div>
  );
};

/** Kilau cahaya miring yang menyapu blok teks (dibungkus overflow hidden). */
export const Shine = ({ delay = 14, duration = 20, repeat = 0 }: { delay?: number; duration?: number; repeat?: number }) => {
  const frame = useCurrentFrame();
  const f = repeat ? (frame - delay) % repeat : frame - delay;
  const x = interpolate(f, [0, duration], [-35, 125], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  if (frame < delay) return null;
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", borderRadius: 12 }}>
      <div
        style={{
          position: "absolute",
          top: "-20%",
          bottom: "-20%",
          left: `${x}%`,
          width: "20%",
          transform: "skewX(-18deg)",
          background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.85), transparent)",
          mixBlendMode: "overlay"
        }}
      />
    </div>
  );
};
