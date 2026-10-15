import React from "react";
import { Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadMarker } from "@remotion/google-fonts/PermanentMarker";

loadAnton();
loadMarker();

/**
 * KineticType.tsx — tipografi bergerak yang digerakkan oleh KATA KERJA.
 *
 * LLM/penulis storyboard tidak menulis parameter animasi; mereka menulis:
 *   {"text": "400 ORANG MENARI", "verb": "slam"}
 * Tabel di bawah menerjemahkannya. Kalau sebuah elemen tidak punya kata kerja,
 * berarti elemen itu belum selesai didesain.
 *
 * slam    : huruf jatuh dari besar + blur, menghantam (hook, tahun, angka)
 * wave    : memantul naik lalu bergelombang (pertanyaan, CTA)
 * mask    : naik dari dalam mask (editorial)
 * type    : mesin tik + kursor
 * pop     : kata penekanan (overshoot)
 * countup : angka berhitung, wajib tabular-nums
 * draw    : garis bawah/stabilo yang ditarik
 * glitch  : RGB split memudar (angka kontras)
 * wipe    : marker stabilo menyapu kata
 * float   : drift halus, tanpa masuk/keluar (badge, sumber)
 */

export const FONT_IMPACT = "'Anton', 'Montserrat', 'Impact', 'Arial Black', sans-serif";
export const FONT_MARKER = "'Permanent Marker', 'Poppins', cursive";

export type Verb =
  | "slam"
  | "wave"
  | "mask"
  | "type"
  | "pop"
  | "countup"
  | "draw"
  | "glitch"
  | "wipe"
  | "float";

export const VERBS: Verb[] = [
  "slam", "wave", "mask", "type", "pop", "countup", "draw", "glitch", "wipe", "float",
];

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Bayangan bertumpuk (extrude ala CapCut). Untuk hook, bukan untuk caption. */
export const extrude = (color: string, depth = 8, step = 1.6) =>
  Array.from({ length: depth }, (_, i) =>
    `${((i + 1) * step * 0.6).toFixed(1)}px ${((i + 1) * step).toFixed(1)}px 0 ${color}`
  ).join(", ");

/** Paket waktu: masuk <= 0.6s, HOLD >= 0.8s, keluar lewat transisi (bukan animasi sendiri). */
export const textEnvelope = (durationFrames: number, fps = 30) => {
  const inF = Math.min(Math.round(0.6 * fps), Math.round(durationFrames * 0.35));
  const holdMin = Math.round(0.8 * fps);
  const holdF = Math.max(holdMin, durationFrames - inF);
  return { inF, holdF, needsMoreTime: durationFrames < inF + holdMin };
};

type Props = {
  text: string;
  verb?: Verb;
  size: number;
  color?: string;
  accent?: string;
  delay?: number;
  stagger?: number;          // frame antar huruf (maks 2 — lihat catatan di references/05)
  shadow?: string;
  stroke?: string;
  strokeWidth?: number;
  maxWidth?: number;
  font?: string;
  align?: "center" | "left";
  extrudeColor?: string;
  seed?: string;
  /** untuk countup: nilai akhir & satuan */
  value?: number;
  suffix?: string;
  /** untuk wipe/draw: warna marker */
  markerColor?: string;
  markerWord?: number;
  lineHeight?: number;
};

export const KineticType: React.FC<Props> = ({
  text,
  verb = "pop",
  size,
  color = "#fff",
  accent,
  delay = 0,
  stagger = 2,
  shadow,
  stroke,
  strokeWidth = 0,
  maxWidth = 940,
  font = FONT_IMPACT,
  align = "center",
  extrudeColor,
  seed = "kt",
  value,
  suffix = "",
  markerColor = "#FFE600",
  markerWord,
  lineHeight = 1.0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - delay;
  const words = String(text).split(/\s+/).filter(Boolean);

  const base: React.CSSProperties = {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: align === "center" ? "center" : "flex-start",
    alignItems: "baseline",
    maxWidth,
    gap: `0 ${size * 0.22}px`,
    lineHeight,
    fontFamily: font,
    fontSize: size,
    letterSpacing: 1,
    textTransform: "uppercase",
  };

  // ---------------------------------------------------------------- countup
  if (verb === "countup") {
    const parsed = parseFloat(String(text).replace(/[^\d.,-]/g, "").replace(",", "."));
    const target = value ?? (Number.isFinite(parsed) ? parsed : 0);
    const p = interpolate(f, [0, Math.round(0.9 * fps)], [0, 1], {
      ...clamp,
      easing: Easing.out(Easing.cubic),
    });
    const pulse = f > Math.round(0.9 * fps) ? interpolate(f, [Math.round(0.9 * fps), Math.round(0.9 * fps) + 3], [1.04, 1], clamp) : 1;
    return (
      <div
        style={{
          ...base,
          fontVariantNumeric: "tabular-nums",
          transform: `scale(${pulse})`,
        }}
      >
        <span style={{ color, textShadow: shadow ?? extrude(extrudeColor ?? "#000", 6, 1.7) }}>
          {Math.round(target * p).toLocaleString("id-ID")}
        </span>
        {suffix ? (
          <span style={{ color: accent ?? color, fontSize: size * 0.53, marginLeft: size * 0.12 }}>{suffix}</span>
        ) : null}
      </div>
    );
  }

  // ---------------------------------------------------------------- glitch
  if (verb === "glitch") {
    const amp = f < 0 ? 0 : interpolate(f, [0, 14], [1, 0], clamp);
    const dx = (random(`${seed}-gx-${Math.floor(frame / 2)}`) - 0.5) * 34 * amp;
    const dy = (random(`${seed}-gy-${Math.floor(frame / 2)}`) - 0.5) * 10 * amp;
    const shared: React.CSSProperties = { ...base, display: "block", whiteSpace: "nowrap" };
    return (
      <div style={{ position: "relative", display: "inline-block" }}>
        {amp > 0.02 ? (
          <>
            <div style={{ ...shared, position: "absolute", left: dx, top: dy, color: "#00E5FF", mixBlendMode: "screen", opacity: 0.85 }}>{text}</div>
            <div style={{ ...shared, position: "absolute", left: -dx, top: -dy, color: "#FF2E88", mixBlendMode: "screen", opacity: 0.85 }}>{text}</div>
          </>
        ) : null}
        <div style={{ ...shared, position: "relative", color, textShadow: shadow }}>{text}</div>
      </div>
    );
  }

  // ---------------------------------------------------------------- float
  if (verb === "float") {
    const y = Math.sin(frame / 22) * 5;
    const rot = Math.sin(frame / 34) * 0.5;
    return (
      <div style={{ ...base, transform: `translateY(${y}px) rotate(${rot}deg)`, color, textShadow: shadow, opacity: 0.9 }}>
        {words.map((w, wi) => (
          <span key={wi} style={{ display: "inline-block", whiteSpace: "nowrap" }}>{w}</span>
        ))}
      </div>
    );
  }

  // ------------------------------------------------- per-huruf: slam/wave/mask/type/pop/draw/wipe
  let gi = 0;
  return (
    <div style={base}>
      {words.map((w, wi) => {
        const wordStart = gi;
        const isMarker = markerWord === wi;
        const wipe = isMarker
          ? interpolate(f, [6 + wordStart * stagger, 20 + wordStart * stagger], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) })
          : 0;
        const inkColor = isMarker && wipe > 0.4 ? "#0A0A0A" : accent && wi === words.length - 1 ? accent : color;

        const letters = Array.from(w).map((ch, ci) => {
          const g = gi++;
          const lf = f - g * stagger;
          let style: React.CSSProperties = {};

          if (verb === "slam") {
            const sp = spring({ frame: lf, fps, config: { damping: 11, stiffness: 210, mass: 0.6 } });
            const jitter = (random(`${seed}-${g}`) - 0.5) * 36;
            style = {
              opacity: interpolate(lf, [0, 3], [0, 1], clamp),
              transform: `translateY(${(1 - sp) * -70}px) scale(${interpolate(sp, [0, 1], [2.8, 1])}) rotate(${(1 - sp) * jitter}deg)`,
              filter: sp < 0.98 ? `blur(${(1 - sp) * 12}px)` : undefined,
            };
          } else if (verb === "pop") {
            const sp = spring({ frame: lf, fps, config: { damping: 8, stiffness: 220, mass: 0.5 } });
            style = {
              opacity: interpolate(lf, [0, 2], [0, 1], clamp),
              transform: `scale(${interpolate(sp, [0, 1], [0.6, 1])}) translateY(${(1 - sp) * 24}px)`,
            };
          } else if (verb === "wave") {
            const sp = spring({ frame: lf, fps, config: { damping: 9, stiffness: 160, mass: 0.7 } });
            const live = Math.max(0, Math.min(1, sp));
            style = {
              opacity: interpolate(lf, [0, 3], [0, 1], clamp),
              transform: `translateY(${(1 - sp) * 110 + Math.sin((frame - g * 3) / 6) * 7 * live}px) rotate(${(1 - sp) * 14 + Math.sin((frame - g * 2) / 9) * 1.6 * live}deg)`,
            };
          } else if (verb === "mask") {
            const sp = spring({ frame: lf, fps, config: { damping: 20, stiffness: 190, mass: 0.6 } });
            style = { transform: `translateY(${Math.max(0, 1 - sp) * 118}%)` };
          } else if (verb === "type") {
            style = { opacity: lf >= 0 ? 1 : 0 };
          } else if (verb === "draw") {
            const sp = spring({ frame: lf, fps, config: { damping: 14, stiffness: 150, mass: 0.7 } });
            style = { opacity: interpolate(lf, [0, 3], [0, 1], clamp), transform: `translateY(${(1 - sp) * 30}px)` };
          } else {
            style = { opacity: lf >= 0 ? 1 : 0 };
          }

          return (
            <span
              key={ci}
              style={{
                display: "inline-block",
                whiteSpace: "pre",
                color: inkColor,
                textShadow: isMarker && wipe > 0.4 ? "none" : (shadow ?? (extrudeColor ? extrude(extrudeColor, 7, 1.7) : undefined)),
                WebkitTextStroke: stroke && strokeWidth ? `${strokeWidth}px ${stroke}` : undefined,
                paintOrder: "stroke fill",
                ...style,
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
              overflow: verb === "mask" || isMarker ? "hidden" : "visible",
              padding: verb === "mask" || isMarker ? "0.06em 0.1em" : "0.02em 0",
            }}
          >
            {isMarker ? (
              <span
                style={{
                  position: "absolute",
                  inset: "0.08em 0 0.02em",
                  background: markerColor,
                  transform: `scaleX(${wipe}) skewX(-8deg)`,
                  transformOrigin: "left center",
                }}
              />
            ) : null}
            <span style={{ position: "relative" }}>{letters}</span>
            {verb === "draw" ? <Underline delay={delay + wordStart * stagger} color={markerColor} width={size * 0.9} /> : null}
            {verb === "type" && wi === words.length - 1 && f > 0 && Math.floor(frame / 8) % 2 === 0 ? (
              <span style={{ color }}>|</span>
            ) : null}
          </span>
        );
      })}
    </div>
  );
};

/** Garis bawah yang ditarik (verb: draw). Waktu tarik 12–18 frame. */
export const Underline: React.FC<{ delay?: number; color?: string; width?: number; thickness?: number }> = ({
  delay = 0,
  color = "#FFE600",
  width = 200,
  thickness = 8,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = interpolate(frame - delay, [0, Math.round(0.55 * fps)], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <span
      style={{
        position: "absolute",
        left: 0,
        bottom: -thickness,
        height: thickness,
        width: width * p,
        background: color,
        borderRadius: thickness / 2,
      }}
    />
  );
};

/** Stiker kicker (judul kecil di atas panel infografis). */
export const Kicker: React.FC<{ text: string; bg?: string; ink?: string; size?: number; delay?: number; rotate?: number }> = ({
  text,
  bg = "#FFE600",
  ink = "#14110D",
  size = 40,
  delay = 0,
  rotate = -3,
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
        opacity: Math.min(1, sp * 2),
      }}
    >
      {text}
    </div>
  );
};
