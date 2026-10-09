import { useMemo, type CSSProperties } from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig
} from "remotion";

import { loadFont } from "@remotion/google-fonts/Poppins";
import { ThemeOverlay, ThemeBadge, CalloutLayer, HookScene, OutroScene, type ThemeName, type MotionCue } from "./MotionGraphics";
import { GLOW_THEMES } from "./GlowFx";
loadFont("normal", { weights: ["600", "700", "800"], subsets: ["latin"] }); // hemat request font
import { loadFont as loadMontserrat } from "@remotion/google-fonts/Montserrat";
loadMontserrat("normal", { weights: ["800", "900"], subsets: ["latin"] });

/* ------------------------------------------------------------------ */
/*  Design tokens                                                      */
/* ------------------------------------------------------------------ */
const COLORS = {
  accent: "#FFE600",
  hot: "#FF3B3B",
  white: "#FFFFFF",
  ink: "#0A0A0A"
};

const FONT_DISPLAY = "'Montserrat', 'Impact', 'Arial Black', sans-serif";
const FONT_SUB = "'Poppins', 'Montserrat', Arial, sans-serif";

// Helper pembersih path untuk menangani kejanggalan string dari Python/Windows
const sfxFile = (name: string) => staticFile(`sfx/${name}.wav`);

const cleanPath = (pathStr?: string | null) => {
  if (!pathStr) return "";
  return pathStr.replace(/^public[\/\\]/, "").replace(/\\/g, "/");
};

/* ------------------------------------------------------------------ */
/*  1. Background slide: Ken Burns dengan arah berbeda + crossfade      */
/* ------------------------------------------------------------------ */
// Ken Burns BERANTAI: akhir slide genap == awal slide ganjil (dan sebaliknya) -> tidak ada lompatan zoom saat ganti gambar.
const KB_IN = { s0: 1.06, s1: 1.16, x0: -20, x1: 20, y0: 10, y1: -10 };
const KB_OUT = { s0: 1.16, s1: 1.06, x0: 20, x1: -20, y0: -10, y1: 10 };

type Trans = "none" | "fade" | "iris" | "push" | "zoom";
const TRANSITIONS: Trans[] = ["iris", "push", "zoom", "fade"];

const BgSlide = ({
  src,
  index,
  duration,
  fadeFrames,
  flip = false
}: {
  src: string;
  index: number;
  duration: number;
  fadeFrames: number;
  flip?: boolean;
}) => {
  const frame = useCurrentFrame();
  const kb = index % 2 === 0 ? KB_IN : KB_OUT;
  const trans: Trans = index === 0 ? "none" : TRANSITIONS[(index - 1) % TRANSITIONS.length];

  const p = interpolate(frame, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });

  const scale = interpolate(p, [0, 1], [kb.s0, kb.s1]);
  const x = interpolate(p, [0, 1], [kb.x0, kb.x1]);
  const y = interpolate(p, [0, 1], [kb.y0, kb.y1]);

  // progres transisi masuk 0..1
  const tp = interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic)
  });

  const wrap: CSSProperties = {};
  let inner = "";
  if (trans === "fade") {
    wrap.opacity = tp;
  } else if (trans === "iris") {
    wrap.clipPath = `circle(${tp * 78}% at 50% 52%)`; // bukaan lingkaran
  } else if (trans === "push") {
    wrap.transform = `translateX(${(1 - tp) * 100}%)`; // dorong dari kanan
    wrap.filter = `blur(${(1 - tp) * 5}px)`;
  } else if (trans === "zoom") {
    wrap.opacity = Math.min(1, tp * 1.6);
    inner = `scale(${1 + (1 - tp) * 0.1})`; // zoom-in halus
    wrap.filter = `blur(${(1 - tp) * 6}px)`;
  }

  return (
    <AbsoluteFill style={wrap}>
      <AbsoluteFill
        style={{
          transform: `${inner} translate(${x}px, ${y}px) scale(${scale * (flip ? -1 : 1)}, ${scale})`.trim()
        }}
      >
        <Img
          src={staticFile(cleanPath(src))}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  2. Partikel bokeh melayang (deterministik, aman untuk render)      */
/* ------------------------------------------------------------------ */
const Particles = ({ count = 16 }: { count?: number }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "screen" }}>
      {Array.from({ length: count }).map((_, i) => {
        const size = 8 + random(`size-${i}`) * 26;
        const baseX = random(`x-${i}`) * width;
        const speed = 0.6 + random(`speed-${i}`) * 1.4;
        const startY = random(`y-${i}`) * height;
        const sway = Math.sin(frame / 25 + i) * 30;

        const y = (((startY - frame * speed) % height) + height) % height;
        const twinkle = 0.25 + 0.25 * Math.sin(frame / 12 + i * 2);

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: baseX + sway,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background:
                i % 3 === 0
                  ? `radial-gradient(circle, ${COLORS.accent} 0%, transparent 70%)`
                  : "radial-gradient(circle, #fff 0%, transparent 70%)",
              opacity: twinkle,
              filter: "blur(1px)"
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  3b. Film grain: tekstur sinematik (noise berganti tiap frame)       */
/* ------------------------------------------------------------------ */
const Grain = () => {
  const frame = useCurrentFrame();
  return (
    <svg
      width="100%"
      height="100%"
      style={{ position: "absolute", inset: 0, opacity: 0.1, mixBlendMode: "overlay", pointerEvents: "none" }}
    >
      <filter id="grain-fx">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={frame % 6} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#grain-fx)" />
    </svg>
  );
};

/* ------------------------------------------------------------------ */
/*  4. Subtitle FRASA: karaoke highlight (pengganti pop-in per kata)   */
/*                                                                      */
/*  - Data dari tts.py (satu kata per item) otomatis digabung jadi     */
/*    frasa 2-3 kata; jika main.py sudah mengirim frasa, tetap jalan.  */
/*  - Frasa tampil utuh, kata yang sedang diucapkan disorot.           */
/*  - Ganti gaya lewat prop `subtitleStyle`:                           */
/*      "karaoke" (default) | "slide" | "typewriter"                   */
/* ------------------------------------------------------------------ */
type SubStyle = "karaoke" | "slide" | "typewriter";
type CapWord = { text: string; start: number; end: number; highlight?: boolean };
type CapPage = { start: number; end: number; words: CapWord[] };

const MAX_WORDS_PER_PAGE = 3;
const MAX_CHARS_PER_PAGE = 22;
const PAGE_BREAK_GAP = 0.4; // detik hening -> pindah frasa
const SUB_FONT_SIZE = 56;

// Pecah item yang berisi banyak kata menjadi kata tunggal (proporsional panjang huruf)
const normalizeWords = (subtitles: any[]): CapWord[] => {
  const out: CapWord[] = [];
  for (const s of subtitles ?? []) {
    const raw = String(s?.word ?? s?.text ?? "").trim();
    const start = Number(s?.start);
    const end = Number(s?.end);
    if (!raw || !Number.isFinite(start) || !Number.isFinite(end)) continue;

    const tokens = raw.split(/\s+/).filter(Boolean);
    const safeEnd = Math.max(end, start + 0.05);
    if (tokens.length === 1) {
      out.push({ text: raw, start, end: safeEnd, highlight: !!s.highlight || /\d/.test(raw) });
      continue;
    }
    const total = tokens.reduce((acc, t) => acc + t.length + 1, 0);
    let cursor = start;
    for (const tok of tokens) {
      const d = (safeEnd - start) * ((tok.length + 1) / total);
      out.push({ text: tok, start: cursor, end: cursor + d, highlight: !!s.highlight || /\d/.test(tok) });
      cursor += d;
    }
  }
  return out.sort((x, y) => x.start - y.start);
};

// Kelompokkan kata -> frasa pendek; putus di tanda baca / jeda / batas panjang
const buildPages = (subtitles: any[]): CapPage[] => {
  const words = normalizeWords(subtitles);
  const pages: CapPage[] = [];
  let cur: CapWord[] = [];

  const flush = () => {
    if (!cur.length) return;
    pages.push({ start: cur[0].start, end: cur[cur.length - 1].end, words: cur });
    cur = [];
  };

  words.forEach((w, i) => {
    const chars = cur.reduce((acc, x) => acc + x.text.length + 1, 0) + w.text.length;
    if (cur.length && (cur.length >= MAX_WORDS_PER_PAGE || chars > MAX_CHARS_PER_PAGE)) {
      flush();
    }
    cur.push(w);

    const next = words[i + 1];
    const endsSentence = /[.!?…]["')”’]?$/.test(w.text);
    const endsClause = /[,;:]["')”’]?$/.test(w.text);
    const gap = next ? next.start - w.end : Infinity;
    if (!next || endsSentence || gap > PAGE_BREAK_GAP || (endsClause && cur.length >= 2)) {
      flush();
    }
  });
  flush();

  // Tutup celah kecil antar frasa (anti-kedip), beri hold singkat jika jedanya panjang
  pages.forEach((p, i) => {
    const next = pages[i + 1];
    if (next && next.start - p.end < 0.3) p.end = next.start;
    else p.end += 0.12;
  });
  return pages;
};

const CaptionPage = ({
  page,
  fromFrame,
  duration,
  variant
}: {
  page: CapPage;
  fromFrame: number;
  duration: number;
  variant: SubStyle;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Waktu absolut (detik) pada frame ini -> dipakai untuk menyorot kata yang sedang diucapkan
  const t = (fromFrame + frame) / fps;

  // Frasa masuk halus (fade + naik sedikit), keluar cepat. Tanpa efek membal/pop.
  const enter = interpolate(frame, [0, 5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic)
  });
  const exit = interpolate(frame, [duration - 4, duration], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp"
  });

  let activeIdx = -1;
  page.words.forEach((w, i) => {
    if (t >= w.start) activeIdx = i;
  });

  const baseText: CSSProperties = {
    display: "inline-block",
    fontSize: SUB_FONT_SIZE,
    fontWeight: 800,
    fontFamily: FONT_SUB,
    textTransform: "uppercase",
    letterSpacing: 1,
    lineHeight: 1.1
  };
  const outline: CSSProperties = {
    WebkitTextStroke: "3px rgba(0,0,0,0.9)",
    paintOrder: "stroke fill",
    textShadow: "0 4px 12px rgba(0,0,0,0.7)"
  };

  const renderWord = (w: CapWord, i: number) => {
    const started = i <= activeIdx;
    const isActive = i === activeIdx;
    const local = t - w.start; // detik sejak kata mulai diucapkan

    /* ---------- GAYA 1: KARAOKE (default) ---------- */
    if (variant === "karaoke") {
      const pillColor = w.highlight ? COLORS.hot : COLORS.accent;
      const pillIn = spring({
        frame: Math.max(0, local) * fps,
        fps,
        config: { damping: 9, stiffness: 300, mass: 0.45 }
      });
      const scale = isActive ? interpolate(pillIn, [0, 1], [0.82, 1.1]) : 1;
      const tilt = isActive ? interpolate(pillIn, [0, 1], [-4, w.highlight ? 1.5 : -1]) : 0;
      return (
        <span
          key={i}
          style={{
            ...baseText,
            padding: "2px 14px",
            borderRadius: 16,
            color: isActive ? (w.highlight ? COLORS.white : COLORS.ink) : COLORS.white,
            background: isActive
              ? w.highlight
                ? "linear-gradient(180deg,#FF6A5A 0%,#E01E1E 100%)"
                : "linear-gradient(180deg,#FFF27A 0%,#FFD400 100%)"
              : "transparent",
            opacity: started ? 1 : 0.55,
            transform: `scale(${scale}) rotate(${tilt}deg)`,
            boxShadow: isActive
              ? `0 6px 0 ${w.highlight ? "#8E0F0F" : "#B89400"}, 0 16px 26px ${pillColor}77, inset 0 2px 0 rgba(255,255,255,0.55)`
              : "none",
            ...(isActive ? { textShadow: "none" } : outline)
          }}
        >
          {w.text}
        </span>
      );
    }

    /* ---------- GAYA 2: SLIDE (kata naik dari dalam mask) ---------- */
    if (variant === "slide") {
      const p = interpolate(local, [-0.04, 0.14], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic)
      });
      return (
        <span
          key={i}
          style={{ display: "inline-block", overflow: "hidden", padding: "6px 4px" }}
        >
          <span
            style={{
              ...baseText,
              ...outline,
              color: isActive ? (w.highlight ? COLORS.hot : COLORS.accent) : COLORS.white,
              opacity: p,
              transform: `translateY(${(1 - p) * 110}%)`
            }}
          >
            {w.text}
          </span>
        </span>
      );
    }

    /* ---------- GAYA 3: TYPEWRITER (huruf muncul berurutan) ---------- */
    const span = Math.max(0.08, (w.end - w.start) * 0.85);
    const prog = interpolate(local, [0, span], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    });
    const shown = w.text.slice(0, Math.ceil(w.text.length * prog));
    return (
      <span key={i} style={{ position: "relative", display: "inline-block" }}>
        <span style={{ ...baseText, opacity: 0 }}>{w.text}</span>
        <span
          style={{
            ...baseText,
            ...outline,
            position: "absolute",
            left: 0,
            top: 0,
            whiteSpace: "nowrap",
            color: isActive ? (w.highlight ? COLORS.hot : COLORS.accent) : COLORS.white
          }}
        >
          {shown}
        </span>
      </span>
    );
  };

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 420,
        opacity: enter * exit
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: "6px 12px",
          maxWidth: "90%",
          transform: `translateY(${(1 - enter) * 16}px)`
        }}
      >
        {page.words.map(renderWord)}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  5. Watermark teks "MorbMyth": transparan, di bawah subtitle        */
/* ------------------------------------------------------------------ */
const Watermark = ({ text, theme = "space" }: { text: string; theme?: ThemeName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({
    frame: frame - 10,
    fps,
    config: { damping: 15, stiffness: 120 }
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 330,
        zIndex: 10,
        pointerEvents: "none"
      }}
    >
      <span
        style={{
          opacity: enter * 0.4,
          transform: `translateY(${(1 - enter) * 12}px)`,
          color: COLORS.white,
          fontSize: 32,
          fontWeight: 700,
          fontFamily: FONT_SUB,
          letterSpacing: 8,
          textShadow: "0 2px 8px rgba(0,0,0,0.5)"
        }}
      >
        {text}
      </span>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  6. Progress bar di atas (retention hook khas Shorts/Reels)          */
/* ------------------------------------------------------------------ */
const ProgressBar = ({ theme = "space" }: { theme?: ThemeName }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const progress = interpolate(frame, [0, durationInFrames], [0, 100], {
    extrapolateRight: "clamp"
  });
  const cinematic = theme === "cinematic";
  const barColor = cinematic ? GLOW_THEMES.gold.primary : COLORS.accent;
  const barColor2 = cinematic ? GLOW_THEMES.cyan.primary : COLORS.hot;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: cinematic ? 4 : 10,
        backgroundColor: "rgba(255,255,255,0.1)",
        zIndex: 20
      }}
    >
      <div
        style={{
          width: `${progress}%`,
          height: "100%",
          background: `linear-gradient(90deg, ${barColor}, ${barColor2})`,
          boxShadow: `0 0 14px ${barColor}`
        }}
      />
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Komposisi utama                                                    */
/* ------------------------------------------------------------------ */
export const ShortsVideo = ({
  audioPath,
  bgMusicPath,
  bgImages = [],
  titleText,
  outroText,
  subtitles = [],
  subtitleStyle = "karaoke",
  theme = "space",
  motionCues = [],
  bgmVolume = 0.13,
  sfxEnabled = true
}: any) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Kata -> frasa (dihitung sekali, bukan tiap frame)
  const captionPages = useMemo(() => buildPages(subtitles), [subtitles]);
  const captionVariant: SubStyle =
    subtitleStyle === "slide" || subtitleStyle === "typewriter" ? subtitleStyle : "karaoke";

  const CARD_FRAMES = Math.round(fps * 3); // durasi hook & outro
  const bgmVol: number = Number(bgmVolume) || 0.13;
  const themeName: ThemeName = theme === "history" ? "history" : theme === "cinematic" ? "cinematic" : "space";
  const cinematic = themeName === "cinematic";
  const cues: MotionCue[] = Array.isArray(motionCues) ? motionCues : [];

  // Punch-in di detik pertama (hook): zoom keras lalu settle
  const punch = interpolate(frame, [0, 22], [1.16, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic)
  });
  const hookFlash = interpolate(frame, [0, 7], [0.55, 0], {
    extrapolateRight: "clamp"
  });
  const FADE_FRAMES = Math.round(fps * 0.35); // durasi transisi antar background (iris/push/zoom/fade)

  // Multi background: tiap gambar dapat slot, sedikit overlap untuk crossfade
  const numImages = bgImages.length || 1;
  const maxFramesPerImage = Math.round(fps * 8); // gambar sedikit -> tiap slot panjang, gerak kamera pelan
  const rawFramesPerImage = Math.ceil(durationInFrames / numImages);
  const framesPerImage = Math.min(rawFramesPerImage, maxFramesPerImage);

  const totalSlots = Math.ceil(durationInFrames / framesPerImage);

  // Camera shake halus + flash tipis saat pergantian background
  const shakeX = Math.sin(frame / 23) * 2.5;
  const shakeY = Math.cos(frame / 29) * 2.5;

  const flash = Array.from({ length: totalSlots }).reduce<number>((acc, _, i) => {
    if (i === 0) return acc;
    const cutFrame = i * framesPerImage;
    return Math.max(
      acc,
      interpolate(frame, [cutFrame, cutFrame + 6], [0.22, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp"
      })
    );
  }, 0);

  // Dorongan kamera halus tiap callout muncul (ease in-out, bukan hentakan)
  let cueBump = 0;
  for (const c of cues) {
    const d = frame - Math.round(c.start * fps);
    if (d >= 0 && d < 26) cueBump = Math.max(cueBump, Math.sin((d / 26) * Math.PI) * 0.022);
  }
  const camScale = 1.02 * punch * (1 + cueBump);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {/* --- AUDIO LAYERS --- */}
      {audioPath && <Audio src={staticFile(cleanPath(audioPath))} />}
      {bgMusicPath && (
        <Audio
          src={staticFile(cleanPath(bgMusicPath))}
          volume={(f) =>
            interpolate(
              f,
              [0, fps, durationInFrames - fps * 1.5, durationInFrames],
              [0, bgmVol, bgmVol, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            )
          }
        />
      )}

      {/* --- SFX: impact di hook, whoosh tiap cut & outro (file di public/sfx) --- */}
      {sfxEnabled && (
        <>
          <Sequence layout="none" durationInFrames={Math.round(fps * 1)}>
            <Audio src={sfxFile("impact")} volume={0.9} />
            <Audio src={sfxFile("whoosh")} volume={0.5} />
          </Sequence>
          {Array.from({ length: Math.max(0, totalSlots - 1) }).map((_, k) => (
            <Sequence
              key={`sfx-cut-${k}`}
              layout="none"
              from={(k + 1) * framesPerImage}
              durationInFrames={Math.round(fps * 0.7)}
            >
              <Audio src={sfxFile("whoosh")} volume={0.22} />
            </Sequence>
          ))}
          {outroText && (
            <Sequence
              layout="none"
              from={Math.max(0, durationInFrames - CARD_FRAMES)}
              durationInFrames={Math.round(fps * 0.7)}
            >
              <Audio src={sfxFile("whoosh")} volume={0.5} />
            </Sequence>
          )}
        </>
      )}

      {/* --- BACKGROUND SLIDESHOW (Ken Burns + crossfade) --- */}
      <AbsoluteFill
        style={{
          transform: `translate(${shakeX}px, ${shakeY}px) scale(${camScale})`,
          filter: cinematic
            ? "contrast(1.12) saturate(0.55) brightness(0.62) grayscale(0.15)"
            : "contrast(1.1) saturate(1.15) brightness(0.97)"
        }}
      >
        {Array.from({ length: totalSlots }).map((_, i) => {
          // Jika jumlah gambar kurang dari total slot, gambar akan di-loop berulang secara halus
          const imgIndex = i % numImages;
          const img = bgImages[imgIndex];
          const from = i === 0 ? 0 : i * framesPerImage - FADE_FRAMES;
          const dur = framesPerImage + (i === 0 ? 0 : FADE_FRAMES);
          return (
            <Sequence
              key={`bg-slot-${i}`}
              from={Math.max(0, from)}
              durationInFrames={dur}
            >
              <BgSlide
                src={img}
                index={i}
                flip={Math.floor(i / numImages) % 2 === 1}
                duration={dur}
                fadeFrames={FADE_FRAMES}
              />
            </Sequence>
          );
        })}
      </AbsoluteFill>

      {/* --- COLOR GRADE: gradient gelap atas/bawah + vignette --- */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.12) 35%, rgba(0,0,0,0.18) 60%, rgba(0,0,0,0.65) 100%)"
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.55) 100%)"
        }}
      />

      {/* --- TEMA NICHE (sejarah / antariksa) --- */}
      <ThemeOverlay theme={themeName} />

      {/* --- PARTIKEL --- */}
      {!cinematic && <Particles />}

      {/* --- FILM GRAIN --- */}
      <Grain />

      {/* --- LIGHT LEAK + FLASH TIPIS SAAT GANTI GAMBAR --- */}
      <AbsoluteFill
        style={{
          opacity: Math.min(1, flash * 3.2),
          mixBlendMode: "screen",
          background:
            "radial-gradient(circle at 85% 12%, rgba(255,170,70,0.85), transparent 55%), radial-gradient(circle at 10% 90%, rgba(255,70,120,0.55), transparent 50%)"
        }}
      />
      <AbsoluteFill
        style={{ backgroundColor: "#fff", opacity: flash, mixBlendMode: "overlay" }}
      />

      {/* --- FLASH HOOK DI FRAME AWAL --- */}
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: hookFlash }} />

      {/* --- BADGE TEMA + CALLOUT MOTION GRAPHIC --- */}
      <ThemeBadge theme={themeName} />
      <CalloutLayer cues={cues} theme={themeName} sfx={sfxEnabled} />

      {/* --- WATERMARK TEKS --- */}
      <Watermark text="MorbMyth" theme={themeName} />

      {/* --- HOOK TYPOGRAPHY (3 DETIK PERTAMA) --- */}
      {titleText && (
        <Sequence durationInFrames={CARD_FRAMES}>
          <HookScene text={titleText} totalFrames={CARD_FRAMES} theme={themeName} />
        </Sequence>
      )}

      {/* --- SUBTITLE FRASA (karaoke / slide / typewriter) --- */}
      {captionPages.map((p, i) => {
        const from = Math.max(0, Math.round(p.start * fps));
        const dur = Math.max(6, Math.round((p.end - p.start) * fps));
        return (
          <Sequence key={`cap-${i}`} from={from} durationInFrames={dur}>
            <CaptionPage
              page={p}
              fromFrame={from}
              duration={dur}
              variant={captionVariant}
            />
          </Sequence>
        );
      })}

      {/* --- OUTRO TYPOGRAPHY (3 DETIK TERAKHIR) --- */}
      {outroText && (
        <Sequence
          from={Math.max(0, durationInFrames - CARD_FRAMES)}
          durationInFrames={CARD_FRAMES}
        >
          <OutroScene text={outroText} totalFrames={CARD_FRAMES} theme={themeName} />
        </Sequence>
      )}

      {/* --- PROGRESS BAR --- */}
      <ProgressBar theme={themeName} />
    </AbsoluteFill>
  );
};