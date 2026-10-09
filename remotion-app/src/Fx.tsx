import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  cancelRender,
  continueRender,
  delayRender,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from "remotion";
import { Lottie, type LottieAnimationData } from "@remotion/lottie";
import { Arrow, Circle, Pie, Polygon, Spark, Star, Triangle } from "@remotion/shapes";

export type ThemeName = "history" | "space";
export type FxName = "burst" | "rings" | "confetti" | "twinkle" | "scribble" | "circle" | "arrow";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/* ------------------------------------------------------------------ */
/*  Lottie (file di public/lottie/<nama>_a.json = sejarah, _b = space)  */
/* ------------------------------------------------------------------ */
const lottieCache = new Map<string, LottieAnimationData>();

export const LottieFx = ({
  name,
  theme,
  style,
  playbackRate = 1,
  loop = false
}: {
  name: FxName;
  theme: ThemeName;
  style?: React.CSSProperties;
  playbackRate?: number;
  loop?: boolean;
}) => {
  const file = `${name}_${theme === "history" ? "a" : "b"}`;
  const [data, setData] = useState<LottieAnimationData | null>(() => lottieCache.get(file) ?? null);
  const [handle] = useState(() => (lottieCache.has(file) ? null : delayRender(`lottie ${file}`)));

  useEffect(() => {
    if (handle === null) return;
    const cached = lottieCache.get(file);
    if (cached) {
      setData(cached);
      continueRender(handle);
      return;
    }
    fetch(staticFile(`lottie/${file}.json`))
      .then((r) => r.json())
      .then((j) => {
        lottieCache.set(file, j);
        setData(j);
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [file, handle]);

  if (!data) return null;
  return <Lottie animationData={data} loop={loop} playbackRate={playbackRate} style={style} />;
};

/* ------------------------------------------------------------------ */
/*  @remotion/shapes: semburan bentuk geometri (ala shape-burst AE)      */
/* ------------------------------------------------------------------ */
const Centered = ({ size, children }: { size: number; children: React.ReactNode }) => (
  <div
    style={{
      position: "absolute",
      left: -size,
      top: -size,
      width: size * 2,
      height: size * 2,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}
  >
    {children}
  </div>
);

export const ShapeBurst = ({
  colors,
  count = 14,
  radius = 420,
  seed = "sb",
  delay = 0,
  cx = "50%",
  cy = "50%"
}: {
  colors: string[];
  count?: number;
  radius?: number;
  seed?: string;
  delay?: number;
  cx?: string;
  cy?: string;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - delay;
  if (f < 0) return null;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: count }).map((_, i) => {
        const a = (i / count) * Math.PI * 2 + random(`${seed}-a-${i}`) * 0.5;
        const dist = radius * (0.5 + random(`${seed}-d-${i}`) * 0.6);
        const lag = Math.floor(random(`${seed}-l-${i}`) * 4);
        const p = spring({ frame: f - lag, fps, config: { damping: 15, stiffness: 85, mass: 0.8 } });
        const fade = interpolate(f, [20, 52], [1, 0], clamp);
        const size = 12 + random(`${seed}-s-${i}`) * 22;
        const rot = f * (3 + random(`${seed}-r-${i}`) * 7) * (i % 2 ? 1 : -1);
        const x = Math.cos(a) * dist * p;
        const y = Math.sin(a) * dist * p + f * f * 0.05; // sedikit gravitasi
        const color = colors[i % colors.length];
        const kind = i % 5;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: cx,
              top: cy,
              opacity: fade * Math.min(1, p * 3),
              transform: `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${0.4 + p * 0.6})`
            }}
          >
            <Centered size={size}>
              {kind === 0 && <Star points={5} innerRadius={size * 0.5} outerRadius={size} fill={color} cornerRadius={2} />}
              {kind === 1 && <Circle radius={size * 0.6} fill={color} />}
              {kind === 2 && <Triangle length={size * 1.6} direction="up" fill={color} cornerRadius={2} />}
              {kind === 3 && <Spark width={size * 1.7} height={size * 1.7} fill={color} />}
              {kind === 4 && <Polygon points={6} radius={size * 0.9} fill="none" stroke={color} strokeWidth={4} />}
            </Centered>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/* Segel bintang berputar (sticker "burst") */
export const Seal = ({
  size,
  fill,
  stroke,
  fill2,
  spin = 0
}: {
  size: number;
  fill: string;
  stroke: string;
  fill2?: string;
  spin?: number;
}) => (
  <div style={{ position: "relative", width: size * 2, height: size * 2 }}>
    <div style={{ position: "absolute", inset: 0, transform: `rotate(${-spin * 0.6}deg)` }}>
      <Star points={14} innerRadius={size * 0.84} outerRadius={size} fill={fill2 ?? stroke} cornerRadius={6} />
    </div>
    <div style={{ position: "absolute", inset: 0, transform: `rotate(${spin}deg)` }}>
      <Star points={18} innerRadius={size * 0.9} outerRadius={size * 0.98} fill={fill} stroke={stroke} strokeWidth={6} cornerRadius={4} />
    </div>
  </div>
);

/* Cincin progres (Pie) yang menyapu seiring durasi callout */
export const SweepRing = ({
  radius,
  progress,
  color,
  track = "rgba(255,255,255,0.12)"
}: {
  radius: number;
  progress: number;
  color: string;
  track?: string;
}) => (
  <div style={{ position: "relative", width: radius * 2, height: radius * 2 }}>
    <div style={{ position: "absolute", inset: 0 }}>
      <Circle radius={radius} fill="none" stroke={track} strokeWidth={10} />
    </div>
    <div style={{ position: "absolute", inset: 0 }}>
      <Pie radius={radius} progress={progress} closePath={false} rotation={-Math.PI / 2} fill="none" stroke={color} strokeWidth={10} />
    </div>
  </div>
);

/* Panah goyang (tunjuk ke teks / karakter) */
export const WigglyArrow = ({ color, frame, length = 150 }: { color: string; frame: number; length?: number }) => (
  <div style={{ transform: `translateX(${Math.sin(frame / 3) * 10}px)` }}>
    <Arrow length={length} headWidth={90} headLength={60} shaftWidth={34} direction="right" fill={color} stroke="#000" strokeWidth={5} cornerRadius={6} />
  </div>
);

/* ------------------------------------------------------------------ */
/*  Kertas sobek (kolase CapCut) - tepi acak deterministik               */
/* ------------------------------------------------------------------ */
export const TornPaper = ({
  width,
  height,
  fill = "#F6EDD2",
  seed = "tp",
  rough = 10,
  tape = true,
  tapeColor = "rgba(255,230,120,0.75)",
  texture
}: {
  width: number;
  height: number;
  fill?: string;
  seed?: string;
  rough?: number;
  tape?: boolean;
  tapeColor?: string;
  texture?: string; // path staticFile, mis. "el/paper_tex.jpg"
}) => {
  const pts = useMemo(() => {
    const out: string[] = [];
    const step = 22;
    for (let x = 0; x <= width; x += step) out.push(`${x},${random(`${seed}-t-${x}`) * rough}`);
    for (let y = 0; y <= height; y += step) out.push(`${width - random(`${seed}-r-${y}`) * rough * 0.6},${y}`);
    for (let x = width; x >= 0; x -= step) out.push(`${x},${height - random(`${seed}-b-${x}`) * rough}`);
    for (let y = height; y >= 0; y -= step) out.push(`${random(`${seed}-l-${y}`) * rough * 0.6},${y}`);
    return out.join(" ");
  }, [width, height, seed, rough]);

  return (
    <div style={{ position: "relative", width, height, filter: "drop-shadow(0 10px 18px rgba(0,0,0,0.55))" }}>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <defs>
          <clipPath id={`tp-${seed}`}>
            <polygon points={pts} />
          </clipPath>
        </defs>
        <polygon points={pts} fill={fill} />
        {texture && (
          <image
            href={staticFile(texture)}
            width={width}
            height={height}
            preserveAspectRatio="xMidYMid slice"
            clipPath={`url(#tp-${seed})`}
            opacity={0.9}
            style={{ mixBlendMode: "multiply" }}
          />
        )}
        <polygon points={pts} fill="none" stroke="rgba(0,0,0,0.12)" strokeWidth={2} />
      </svg>
      {tape && (
        <>
          <div style={{ position: "absolute", top: -14, left: 24, width: 96, height: 30, background: tapeColor, transform: "rotate(-14deg)" }} />
          <div style={{ position: "absolute", bottom: -14, right: 24, width: 96, height: 30, background: tapeColor, transform: "rotate(-10deg)" }} />
        </>
      )}
    </div>
  );
};
