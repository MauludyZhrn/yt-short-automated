import React from "react";
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Captions.tsx — caption yang terkunci pada suara (voice-locked).
 *
 * Bentuk B dari `type-rhythm-sync` (video-shotcraft): karaoke fill sync.
 * - 3–4 kata per halaman, maks 2 baris
 * - ukuran >= 96px ( >= 5% tinggi frame 1920 )
 * - muncul 0.15s sebelum kata pertama diucapkan (PRE_ROLL)
 * - tidak pernah masuk zona mati bawah (320px) atau atas (260px)
 */

export type CapWord = { word?: string; text?: string; start: number; end: number };
export type CapPage = { text: string; start: number; end: number; words: CapWord[] };

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const PRE_ROLL = 0.15;
const FEATHER = 6; // % lebar sapuan warna

export const wordText = (w: CapWord) => String(w.word ?? w.text ?? "");

/** Kelompokkan kata jadi halaman 3–4 kata; halaman ditutup di tanda baca. */
export const buildPages = (words: CapWord[], maxWords = 4): CapPage[] => {
  const pages: CapPage[] = [];
  let i = 0;
  while (i < words.length) {
    let take = Math.min(maxWords, words.length - i);
    for (let k = 0; k < take; k++) {
      if (/[.!?…,;:]$/.test(wordText(words[i + k]).trim())) {
        take = k + 1;
        break;
      }
    }
    const chunk = words.slice(i, i + take);
    pages.push({
      text: chunk.map(wordText).join(" "),
      start: Math.max(0, chunk[0].start - PRE_ROLL),
      end: Math.max(chunk[0].start + 0.4, chunk[chunk.length - 1].end + 0.25),
      words: chunk,
    });
    i += take;
  }
  return pages;
};

type Props = {
  words: CapWord[];
  pages?: CapPage[];
  fps?: number;
  style?: "karaoke" | "slide" | "typewriter";
  size?: number;          // default 100 ( >= 96 )
  activeColor?: string;   // warna kata yang sedang diucapkan
  idleColor?: string;
  bottomOffset?: number;  // jarak dari dasar frame (default 360 = 320 zona mati + 40)
  strokeWidth?: number;
  strokeColor?: string;
  showUnderline?: boolean;
};

export const Captions: React.FC<Props> = ({
  words,
  pages,
  style = "karaoke",
  size = 100,
  activeColor = "#FFE600",
  idleColor = "rgba(255,255,255,0.92)",
  bottomOffset = 360,
  strokeWidth = 8,
  strokeColor = "#000",
  showUnderline = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const built = React.useMemo(() => pages ?? buildPages(words), [pages, words]);
  const now = frame / fps;

  const page = built.find((p) => now >= p.start && now <= p.end + 0.15);
  if (!page) return null;

  const enterF = Math.round(page.start * fps);
  const enter = interpolate(frame, [enterF - 4, enterF + 4], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        bottom: bottomOffset,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "flex-end",
        gap: `0 ${size * 0.24}px`,
        opacity: enter,
        transform: `translateY(${(1 - enter) * 18}px)`,
      }}
    >
      {page.words.map((w, i) => {
        const wf = { from: w.start * fps, to: w.end * fps };
        const p = interpolate(frame, [wf.from, wf.to], [0, 1], clamp);

        if (style === "slide") {
          return (
            <span
              key={i}
              style={{
                fontFamily: "'Anton', 'Montserrat', Impact, sans-serif",
                fontSize: size,
                lineHeight: 1.05,
                color: p > 0 ? activeColor : idleColor,
                WebkitTextStroke: `${strokeWidth}px ${strokeColor}`,
                paintOrder: "stroke fill",
                transform: `translateY(${(1 - Math.min(1, p * 4)) * 22}px)`,
                display: "inline-block",
              }}
            >
              {wordText(w)}
            </span>
          );
        }

        if (style === "typewriter") {
          const txt = wordText(w);
          const shown = Math.ceil(txt.length * p);
          return (
            <span
              key={i}
              style={{
                fontFamily: "'Anton', 'Montserrat', Impact, sans-serif",
                fontSize: size,
                lineHeight: 1.05,
                color: activeColor,
                WebkitTextStroke: `${strokeWidth}px ${strokeColor}`,
                paintOrder: "stroke fill",
                display: "inline-block",
              }}
            >
              {txt.slice(0, Math.max(shown, p > 0 ? 1 : 0))}
            </span>
          );
        }

        // karaoke fill sync: sapuan warna mengikuti posisi suara
        const edge = p * (100 + FEATHER * 2) - FEATHER;
        return (
          <span
            key={i}
            style={{
              position: "relative",
              fontFamily: "'Anton', 'Montserrat', Impact, sans-serif",
              fontSize: size,
              lineHeight: 1.05,
              display: "inline-block",
              color: "transparent",
              backgroundImage: `linear-gradient(90deg, ${activeColor} ${edge - 4}%, ${idleColor} ${edge + 4}%)`,
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              WebkitTextStroke: `${strokeWidth}px ${strokeColor}`,
              paintOrder: "stroke fill",
            }}
          >
            {wordText(w)}
            {showUnderline && p > 0.02 && p < 0.98 ? (
              <span
                style={{
                  position: "absolute",
                  left: 0,
                  bottom: -14,
                  height: 8,
                  borderRadius: 4,
                  width: `${Math.min(100, edge + 4)}%`,
                  background: activeColor,
                }}
              />
            ) : null}
          </span>
        );
      })}
    </div>
  );
};

/** Baris progress (opsional) — diletakkan di atas zona mati bawah. */
export const ProgressBar: React.FC<{ color?: string; height?: number; bottom?: number }> = ({
  color = "#FFE600",
  height = 10,
  bottom = 330,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = interpolate(frame, [0, durationInFrames], [0, 1], clamp);
  return (
    <div style={{ position: "absolute", left: 90, right: 90, bottom, height, borderRadius: height, background: "rgba(255,255,255,0.18)" }}>
      <div style={{ width: `${p * 100}%`, height, borderRadius: height, background: color, boxShadow: `0 0 12px ${color}` }} />
    </div>
  );
};
