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

import { LottieFx, Seal, ShapeBurst, SweepRing, TornPaper, type ThemeName as ScrapThemeName } from "./Fx";
import { FONT_IMPACT, FONT_MARKER, GlitchText, KineticText, Kicker, Shine, extrude } from "./Kinetic";
import { CompareInfo, PercentInfo, TimelineInfo, parsePercent, type InfoItem } from "./Infographic";
import { Mascot, POSES, type Pose } from "./Mascot";
import { Triangle } from "@remotion/shapes";
import { CinematicBG, FONT_GLOW_DISPLAY, GhostEcho, GlowPill, GlowRule, GlowStepNumber, GlowWords, GLOW_THEMES, type GlowAccent } from "./GlowFx";

export type ThemeName = ScrapThemeName | "cinematic";
export type MotionCue = {
  type: "year" | "stat" | "keyword" | "question" | "percent" | "compare" | "timeline";
  text: string;
  sub?: string;
  start: number; // detik
  end: number; // detik
  pose?: string; // utama | wow | berfikir | bertanya | terkejut | wink (opsional)
  side?: "left" | "right"; // sisi maskot (opsional)
  items?: InfoItem[]; // data infografis: compare [{label,value}] / timeline [{year,label}]
};

export const THEMES = {
  history: {
    primary: "#F2C879",
    secondary: "#B5651D",
    tint: "rgba(120,70,20,0.35)",
    badge: "ARSIP SEJARAH"
  },
  space: {
    primary: "#6FE7FF",
    secondary: "#8A5CFF",
    tint: "rgba(20,12,80,0.38)",
    badge: "DATA KOSMIK"
  },
  cinematic: {
    primary: "#E8C36C",
    secondary: "#8FE3FF",
    tint: "rgba(0,0,0,0.45)",
    badge: "MODE SINEMATIK"
  }
} as const;

const FONT_DISPLAY = "'Montserrat', 'Impact', 'Arial Black', sans-serif";
const FONT_SUB = "'Poppins', 'Montserrat', Arial, sans-serif";

/* ------------------------------------------------------------------ */
/*  Bracket sudut (HUD / bingkai arsip)                                 */
/* ------------------------------------------------------------------ */
const Corners = ({ color, inset = 28 }: { color: string; inset?: number }) => {
  const frame = useCurrentFrame();
  const o = 0.45 + 0.2 * Math.sin(frame / 14);
  const base = { position: "absolute" as const, width: 72, height: 72, opacity: o };
  const b = `4px solid ${color}`;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ ...base, top: inset + 14, left: inset, borderTop: b, borderLeft: b }} />
      <div style={{ ...base, top: inset + 14, right: inset, borderTop: b, borderRight: b }} />
      <div style={{ ...base, bottom: inset, left: inset, borderBottom: b, borderLeft: b }} />
      <div style={{ ...base, bottom: inset, right: inset, borderBottom: b, borderRight: b }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  Tema SEJARAH: film tua, goresan, debu, penggaris timeline            */
/* ------------------------------------------------------------------ */
const HistoryOverlay = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const t = THEMES.history;
  const tick = Math.floor(frame / 2);
  const flicker = 0.03 + random(`fl-${tick}`) * 0.08;

  const scratches = [0, 1, 2].map((i) => ({
    show: random(`sc-show-${tick}-${i}`) > 0.55,
    x: random(`sc-x-${tick}-${i}`) * width,
    o: 0.12 + random(`sc-o-${tick}-${i}`) * 0.2
  }));

  const ticksMask = "linear-gradient(90deg, transparent, #000 18%, #000 82%, transparent)";

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ backgroundColor: t.tint, mixBlendMode: "multiply" }} />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: flicker }} />

      {scratches.map(
        (s, i) =>
          s.show && (
            <div
              key={i}
              style={{
                position: "absolute",
                left: s.x,
                top: 0,
                width: 2,
                height,
                backgroundColor: "#fff",
                opacity: s.o
              }}
            />
          )
      )}

      {Array.from({ length: 14 }).map((_, i) => {
        const size = 3 + random(`d-size-${i}`) * 6;
        const x = random(`d-x-${i}`) * width + Math.sin(frame / 30 + i) * 20;
        const y = (((random(`d-y-${i}`) * height + frame * (0.4 + random(`d-s-${i}`))) % height) + height) % height;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: t.primary,
              opacity: 0.25 + 0.2 * Math.sin(frame / 10 + i)
            }}
          />
        );
      })}

      {/* penggaris timeline bergeser pelan */}
      <div
        style={{
          position: "absolute",
          top: 30,
          left: 0,
          width: "100%",
          height: 26,
          opacity: 0.6,
          backgroundImage: `repeating-linear-gradient(90deg, ${t.primary} 0 3px, transparent 3px 40px)`,
          backgroundPosition: `${-frame * 1.4}px 0`,
          WebkitMaskImage: ticksMask
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 30,
          left: 0,
          width: "100%",
          height: 12,
          opacity: 0.45,
          backgroundImage: `repeating-linear-gradient(90deg, ${t.primary} 0 2px, transparent 2px 10px)`,
          backgroundPosition: `${-frame * 1.4}px 0`,
          WebkitMaskImage: ticksMask
        }}
      />
      <Corners color={t.primary} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  Tema ANTARIKSA: bintang parallax, cincin orbit, bintang jatuh, scan  */
/* ------------------------------------------------------------------ */
const SpaceOverlay = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const t = THEMES.space;

  // bintang jatuh tiap 170 frame
  const cycle = Math.floor(frame / 170);
  const local = frame % 170;
  const ssP = interpolate(local, [0, 22], [0, 1], { extrapolateRight: "clamp" });
  const ssX = random(`ss-x-${cycle}`) * width * 0.6 + width * 0.4 - ssP * 520;
  const ssY = random(`ss-y-${cycle}`) * height * 0.4 + 120 + ssP * 300;
  const ssO = local < 22 ? Math.sin(ssP * Math.PI) : 0;

  const scanY = ((frame % 160) / 160) * height;
  const rot = frame * 0.18;
  const orbit = (frame / 45) % (Math.PI * 2);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ backgroundColor: t.tint, mixBlendMode: "multiply" }} />

      {Array.from({ length: 40 }).map((_, i) => {
        const layer = i % 3;
        const speed = 0.25 + layer * 0.35;
        const size = 2 + layer;
        const x = random(`st-x-${i}`) * width;
        const y = (random(`st-y-${i}`) * height + frame * speed) % height;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: "#fff",
              boxShadow: `0 0 ${4 + layer * 2}px ${t.primary}`,
              opacity: 0.35 + 0.4 * Math.abs(Math.sin(frame / 18 + i))
            }}
          />
        );
      })}

      {/* cincin orbit */}
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ position: "absolute", inset: 0, opacity: 0.22 }}
      >
        <g transform={`translate(${width / 2} ${height * 0.4})`}>
          <g transform={`rotate(${rot}) scale(1 0.34)`}>
            <circle r={430} fill="none" stroke={t.primary} strokeWidth={3} strokeDasharray="14 18" />
            <circle cx={430 * Math.cos(orbit)} cy={430 * Math.sin(orbit)} r={14} fill={t.primary} />
          </g>
          <g transform={`rotate(${-rot * 0.7 + 60}) scale(1 0.34)`}>
            <circle r={330} fill="none" stroke={t.secondary} strokeWidth={3} strokeDasharray="6 14" />
            <circle cx={330 * Math.cos(-orbit * 1.4)} cy={330 * Math.sin(-orbit * 1.4)} r={10} fill={t.secondary} />
          </g>
        </g>
      </svg>

      {/* bintang jatuh */}
      <div
        style={{
          position: "absolute",
          left: ssX,
          top: ssY,
          width: 280,
          height: 3,
          opacity: ssO,
          transform: "rotate(30deg)",
          transformOrigin: "left center",
          background: `linear-gradient(90deg, #fff, transparent)`
        }}
      />

      {/* garis scan HUD */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: scanY,
          width: "100%",
          height: 110,
          opacity: 0.1,
          background: `linear-gradient(180deg, transparent, ${t.primary}, transparent)`
        }}
      />
      <Corners color={t.primary} />
    </AbsoluteFill>
  );
};

/* tekstur grid kolase (el/grid.png) melayang pelan di atas foto */
const GridTexture = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "screen", opacity: 0.12 }}>
      <Img
        src={staticFile("el/grid_dark.jpg")}
        style={{
          width: "130%",
          height: "130%",
          objectFit: "cover",
          transform: `translate(${-40 + Math.sin(frame / 60) * 30}px, ${-60 + frame * 0.25}px) rotate(${Math.sin(frame / 90) * 2}deg)`
        }}
      />
    </AbsoluteFill>
  );
};

export const ThemeOverlay = ({ theme }: { theme: ThemeName }) => {
  if (theme === "cinematic") return <CinematicBG accent="gold" />;
  return (
    <>
      {theme === "history" ? <HistoryOverlay /> : <SpaceOverlay />}
      <GridTexture />
    </>
  );
};

/* ------------------------------------------------------------------ */
/*  Badge tema kecil di kiri atas                                       */
/* ------------------------------------------------------------------ */
export const ThemeBadge = ({ theme }: { theme: ThemeName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = THEMES[theme];
  const enter = spring({ frame: frame - 70, fps, config: { damping: 15, stiffness: 120 } });
  if (theme === "cinematic") {
    return (
      <AbsoluteFill style={{ pointerEvents: "none", zIndex: 12 }}>
        <div style={{ position: "absolute", top: 80, left: 48, opacity: Math.min(1, enter * 1.3) }}>
          <GlowPill label={t.badge} accent="gold" delay={70} size={22} />
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 12 }}>
      <div
        style={{
          position: "absolute",
          top: 80,
          left: 48,
          opacity: enter * 0.9,
          transform: `translateX(${(1 - enter) * -30}px)`,
          padding: "8px 18px",
          borderLeft: `5px solid ${t.primary}`,
          background: "rgba(0,0,0,0.5)",
          color: t.primary,
          fontFamily: FONT_SUB,
          fontWeight: 700,
          fontSize: 26,
          letterSpacing: 6
        }}
      >
        {t.badge}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  Callout: tahun / angka / kata kunci / pertanyaan                    */
/*  Tiap callout = tipografi bergerak + shapes + Lottie + maskot         */
/* ------------------------------------------------------------------ */
const parseCount = (text: string) => {
  const m = String(text).match(/^(\D*?)(\d{1,3}(?:\.\d{3})+|\d+)(.*)$/);
  if (!m) return null;
  if (/^[.,]\d/.test(m[3])) return null; // desimal -> tampil statis
  return { pre: m[1], num: Number(m[2].replace(/\./g, "")), suf: m[3] };
};

const clamp01 = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const POSE_BY_TYPE: Record<MotionCue["type"], Pose[]> = {
  year: ["wow", "terkejut"],
  stat: ["terkejut", "wow"],
  keyword: ["utama", "wink", "wow"],
  question: ["bertanya", "berfikir"],
  percent: ["wow", "utama"],
  compare: ["berfikir", "utama"],
  timeline: ["berfikir", "wink"]
};

export const pickPose = (cue: MotionCue, index: number): Pose => {
  if (cue.pose && (POSES as string[]).includes(cue.pose)) return cue.pose as Pose;
  const list = POSE_BY_TYPE[cue.type] ?? POSE_BY_TYPE.keyword;
  return list[index % list.length];
};

const longestWord = (text: string) => {
  const ws = String(text).split(/\s+/).filter(Boolean);
  if (!ws.length) return 0;
  return ws.reduce((b, w, i) => (w.length > ws[b].length ? i : b), 0);
};

const KICKER: Record<string, { history: string; space: string }> = {
  year: { history: "TAHUN KEJADIAN", space: "TAHUN PENTING" },
  stat: { history: "FAKTA ANGKA", space: "DATA KOSMIK" },
  keyword: { history: "ISTILAH KUNCI", space: "CATAT INI" },
  question: { history: "RENUNGKAN", space: "BAYANGKAN" }
};

const Callout = ({
  cue,
  theme,
  totalFrames,
  index
}: {
  cue: MotionCue;
  theme: ThemeName;
  totalFrames: number;
  index: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = THEMES[theme];

  // infografis butuh data; kalau tidak lengkap, turun jadi 'keyword'
  const items = Array.isArray(cue.items) ? cue.items : [];
  let ctype: MotionCue["type"] = cue.type;
  if (ctype === "percent" && parsePercent(cue.text) === null) ctype = "keyword";
  if (ctype === "compare" && items.filter((i) => typeof i.value === "number").length < 2) ctype = "keyword";
  if (ctype === "timeline" && items.length < 2) ctype = "keyword";
  const isInfo = ctype === "percent" || ctype === "compare" || ctype === "timeline";

  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 150, mass: 0.7 } });
  const exit = interpolate(frame, [totalFrames - 9, totalFrames], [1, 0], clamp01);
  const count = interpolate(frame, [0, 28], [0, 1], { ...clamp01, easing: Easing.out(Easing.cubic) });
  const sub = interpolate(frame, [10, 22], [0, 1], clamp01);
  const glow = 16 + Math.sin(frame / 5) * 7;
  const side: "left" | "right" = cue.side ?? (index % 2 === 0 ? "right" : "left");
  const pose = pickPose({ ...cue, type: ctype }, index);

  const isNumeric = ctype === "year" || ctype === "stat";
  let main = String(cue.text).toUpperCase();
  if (ctype === "year" && /^\d{3,4}$/.test(main.trim())) {
    main = String(Math.round(parseInt(main, 10) - 80 * (1 - count))); // roll mundur ke tahun
  } else if (ctype === "stat") {
    const pc = parseCount(main);
    if (pc) main = `${pc.pre}${new Intl.NumberFormat("id-ID").format(Math.round(pc.num * count))}${pc.suf}`;
  }

  const numSize = Math.max(96, Math.min(220, 860 / (Math.max(main.length, 3) * 0.54)));
  const kwSize = Math.max(78, Math.min(130, 960 / (Math.max(cue.text.length, 6) * 0.5)));
  const ink = "#14110D";
  const kwW = Math.min(960, Math.max(520, cue.text.length * kwSize * 0.56 + 120));
  const kwLines = Math.max(1, Math.ceil((cue.text.length * kwSize * 0.52) / (kwW - 110)));
  const drawn = interpolate(frame, [1, 18], [0, 1], { ...clamp01, easing: Easing.out(Easing.cubic) }); // progres coretan

  const subTag = cue.sub ? (
    <div
      style={{
        marginTop: 18,
        padding: "6px 22px",
        background: t.primary,
        color: ink,
        fontFamily: FONT_MARKER,
        fontSize: 42,
        letterSpacing: 3,
        textTransform: "uppercase",
        transform: `rotate(-3deg) scale(${interpolate(sub, [0, 1], [0.6, 1])})`,
        opacity: sub,
        boxShadow: "6px 6px 0 rgba(0,0,0,0.7)"
      }}
    >
      {cue.sub}
    </div>
  ) : null;

  const kick = theme === "cinematic" ? undefined : KICKER[ctype]?.[theme];

  /* --------------------------------------------------------------- */
  /*  Gaya SINEMATIK: glow minimal, tanpa maskot/stiker/kertas sobek  */
  /* --------------------------------------------------------------- */
  if (theme === "cinematic") {
    const eyebrowMap: Record<string, string> = {
      year: "TAHUN KEJADIAN",
      stat: "FAKTA ANGKA",
      keyword: "CATAT INI",
      question: "RENUNGKAN"
    };
    const eyebrow = eyebrowMap[ctype];
    const accent: GlowAccent = isNumeric ? "cyan" : "gold";

    return (
      <AbsoluteFill style={{ opacity: exit, zIndex: 14 }}>
        <AbsoluteFill style={{ opacity: pop * 0.8, background: "radial-gradient(ellipse 70% 30% at 50% 32%, rgba(0,0,0,0.6), transparent 75%)" }} />
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: isInfo ? 300 : 420 }}>
          {isInfo ? (
            <div style={{ filter: "drop-shadow(0 10px 24px rgba(0,0,0,0.5))" }}>
              {ctype === "percent" && <PercentInfo t={t} text={cue.text} sub={cue.sub} />}
              {ctype === "compare" && <CompareInfo t={t} items={items} unit={cue.sub} />}
              {ctype === "timeline" && <TimelineInfo t={t} items={items} />}
            </div>
          ) : (
            <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", maxWidth: 940 }}>
              {isNumeric ? (
                <GlowStepNumber number={main} eyebrow={eyebrow} footnote={cue.sub} accent={accent} />
              ) : (
                <>
                  {eyebrow && (
                    <div style={{ marginBottom: 20 }}>
                      <GlowPill index={index + 1} label={eyebrow} accent={accent} delay={0} size={24} />
                    </div>
                  )}
                  <div style={{ position: "relative" }}>
                    <GhostEcho text={String(cue.text).toUpperCase()} size={kwSize * 0.9} />
                    <GlowWords text={cue.text} size={kwSize * 0.9} accent={accent} maxWidth={940} />
                  </div>
                  <div style={{ marginTop: 26 }}>
                    <GlowRule accent={accent} delay={14} width={220} />
                  </div>
                  {cue.sub && (
                    <div style={{ marginTop: 20, fontFamily: FONT_IMPACT, fontSize: 36, letterSpacing: 2, color: "rgba(255,255,255,0.7)", opacity: sub }}>
                      {cue.sub}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ opacity: exit, zIndex: 14 }}>
      {!isInfo && (
        <AbsoluteFill
          style={{
            opacity: pop,
            background: "radial-gradient(ellipse 90% 24% at 50% 26%, rgba(0,0,0,0.62), transparent 78%)"
          }}
        />
      )}

      {/* efek Lottie di belakang teks */}
      <div style={{ position: "absolute", left: 0, top: 70, width: 1080, height: 1080, opacity: 0.95 }}>
        <LottieFx name={isNumeric || isInfo ? "burst" : "rings"} theme={theme} style={{ width: 1080, height: 1080 }} />
      </div>
      <ShapeBurst colors={[t.primary, t.secondary, "#fff"]} count={ctype === "question" ? 8 : 12} radius={400} seed={`cue-${index}`} cy="29%" />

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: isNumeric ? 330 : isInfo ? 300 : 250 }}>
        {isInfo ? (
          <div style={{ filter: "drop-shadow(0 10px 24px rgba(0,0,0,0.5))" }}>
            {ctype === "percent" && <PercentInfo t={t} text={cue.text} sub={cue.sub} />}
            {ctype === "compare" && <CompareInfo t={t} items={items} unit={cue.sub} />}
            {ctype === "timeline" && <TimelineInfo t={t} items={items} />}
          </div>
        ) : (
          <div
            style={{
              position: "relative",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              transform: `scale(${interpolate(pop, [0, 1], [0.55, 1])}) rotate(${interpolate(pop, [0, 1], [-6, 0])}deg)`,
              opacity: Math.min(1, pop * 2),
              filter: `drop-shadow(0 8px 22px rgba(0,0,0,0.8)) drop-shadow(0 0 ${glow}px ${t.primary}66)`
            }}
          >
            {kick && (
              <div style={{ position: "absolute", top: ctype === "keyword" ? -62 : -150, zIndex: 3 }}>
                <Kicker text={kick} bg="#fff" ink={ink} size={34} delay={6} rotate={ctype === "question" ? 3 : -3} />
              </div>
            )}

            {isNumeric && (
              <>
                <div style={{ position: "absolute", left: "50%", top: "50%", transform: `translate(-50%,-56%) rotate(${frame * 0.5}deg)`, opacity: 0.2 }}>
                  <Img src={staticFile("el/grid_white.png")} style={{ width: 640, height: 640 }} />
                </div>
                <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-56%)", opacity: 0.92 }}>
                  <Seal size={Math.min(310, numSize * 1.5)} fill={t.secondary} stroke={t.primary} fill2="rgba(0,0,0,0.65)" spin={frame * 1.4} />
                </div>
                <div style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%,-56%)" }}>
                  <SweepRing radius={Math.min(250, numSize * 1.2)} progress={interpolate(frame, [0, totalFrames], [0, 1], clamp01)} color="#fff" />
                </div>
                <div style={{ position: "relative", padding: "30px 40px" }}>
                  <GlitchText text={main} size={numSize} color="#fff" delay={0} duration={12} shadow={`${extrude("#000", 8, 1.8)}, 0 0 28px ${t.primary}`} />
                  <Shine delay={16} duration={22} />
                  {/* coretan tangan: lingkaran untuk tahun, panah untuk angka */}
                  {ctype === "year" ? (
                    <div style={{ position: "absolute", left: "50%", top: "50%", width: 900, height: 420, transform: "translate(-50%,-50%) scale(1.05)" }}>
                      <LottieFx name="circle" theme={theme} style={{ width: 900, height: 420 }} />
                    </div>
                  ) : (
                    <div style={{ position: "absolute", left: -150, top: 110, width: 420, height: 300, transform: "rotate(8deg)" }}>
                      <LottieFx name="arrow" theme={theme} style={{ width: 420, height: 300 }} />
                    </div>
                  )}
                </div>
                {subTag}
              </>
            )}

            {ctype === "keyword" && (
              <>
                <div style={{ position: "relative", transform: `rotate(${index % 2 ? 2.5 : -2.5}deg)` }}>
                  <TornPaper width={kwW} height={kwLines * kwSize * 1.05 + 76} fill="#F6EDD2" seed={`kw-${index}`} texture="el/paper_tex.jpg" />
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 30px" }}>
                    <KineticText text={cue.text} variant="slam" size={kwSize} color={ink} markerWord={longestWord(cue.text)} markerColor={t.primary} markerInk={ink} stagger={1.5} maxWidth={880} letterSpacing={1} />
                  </div>
                </div>
                <div style={{ position: "relative", width: 760, height: 140, marginTop: -26 }}>
                  <LottieFx name="scribble" theme={theme} style={{ width: 760, height: 140 }} />
                  {/* tangan menulis mengikuti coretan */}
                  <Img
                    src={staticFile("el/pen_hand.png")}
                    style={{
                      position: "absolute",
                      width: 130,
                      left: 40 + drawn * 680 - 104,
                      top: 56,
                      opacity: interpolate(frame, [16, 24], [1, 0], clamp01),
                      transform: "rotate(-6deg)",
                      filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.5))"
                    }}
                  />
                </div>
                {subTag}
              </>
            )}

            {ctype === "question" && (
              <>
                <div style={{ position: "absolute", left: -20, top: -100, transform: `rotate(${frame * 2.4}deg) scale(${1 + Math.sin(frame / 6) * 0.08})` }}>
                  <Seal size={78} fill={t.primary} stroke="#fff" fill2={t.secondary} spin={frame * 3} />
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: FONT_IMPACT,
                      fontSize: 110,
                      color: ink,
                      transform: `rotate(${-frame * 2.4}deg)`
                    }}
                  >
                    ?
                  </div>
                </div>
                <Img
                  src={staticFile("el/torus.png")}
                  style={{ position: "absolute", right: -30, top: -120, width: 140, opacity: 0.9, transform: `rotate(${-frame * 4}deg) scale(${0.9 + Math.sin(frame / 8) * 0.1})` }}
                />
                <div style={{ padding: "40px 26px 0" }}>
                  <KineticText text={cue.text} variant="wave" size={kwSize * 0.92} color="#fff" accent={t.primary} stroke="#000" strokeWidth={5} extrudeColor="#000" ring={t.secondary} ringSize={3} maxWidth={900} stagger={1.5} />
                </div>
                <div style={{ width: 560, marginTop: 10, clipPath: `inset(0 ${(1 - drawn) * 100}% 0 0)` }}>
                  <Img src={staticFile("el/zigzag.svg")} style={{ width: "100%", filter: `drop-shadow(0 0 8px ${t.primary})` }} />
                </div>
                {subTag}
              </>
            )}
          </div>
        )}
      </AbsoluteFill>

      <Mascot pose={pose} side={side} totalFrames={totalFrames} theme={theme} height={isInfo ? 470 : 620} bottom={isInfo ? 500 : 560} />
    </AbsoluteFill>
  );
};

export const CalloutLayer = ({
  cues,
  theme,
  sfx = true
}: {
  cues: MotionCue[];
  theme: ThemeName;
  sfx?: boolean;
}) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cues.map((c, i) => {
        const from = Math.max(0, Math.round(c.start * fps));
        const dur = Math.max(12, Math.round((c.end - c.start) * fps));
        return (
          <Sequence key={`cue-${i}`} from={from} durationInFrames={dur}>
            <Callout cue={c} theme={theme} totalFrames={dur} index={i} />
            {sfx && (
              <>
                <Audio src={staticFile("sfx/pop.wav")} volume={0.55} />
                <Audio src={staticFile("sfx/whoosh.wav")} volume={0.3} />
              </>
            )}
          </Sequence>
        );
      })}
    </>
  );
};

/* ------------------------------------------------------------------ */
/*  HOOK (3 detik pertama): slam typography + maskot menunjuk + megafon  */
/* ------------------------------------------------------------------ */
const pickEmph = (words: string[], preferDigit: boolean) => {
  if (preferDigit) {
    const d = words.findIndex((w) => /\d/.test(w));
    if (d >= 0) return d;
  }
  return words.reduce((b, w, i) => (w.length > words[b].length ? i : b), 0);
};

export const HookScene = ({ text, totalFrames, theme }: { text: string; totalFrames: number; theme: ThemeName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = THEMES[theme];
  const words = String(text).toUpperCase().split(/\s+/).filter(Boolean);
  if (!words.length) return null;

  const emph = pickEmph(words, true);
  const maxWord = Math.max(...words.map((w) => w.length));
  const total = words.join(" ").length;
  const size = Math.max(96, Math.min(190, Math.min(940 / (maxWord * 0.52), 3400 / Math.sqrt(total * 18))));

  const exit = interpolate(frame, [totalFrames - 8, totalFrames], [0, 1], { ...clamp01, easing: Easing.in(Easing.cubic) });
  const scrim = interpolate(frame, [0, 10, totalFrames - 8, totalFrames], [0, 1, 1, 0], clamp01);
  const drift = interpolate(frame, [0, totalFrames], [1, 1.06], clamp01);
  const rule = interpolate(frame, [0, 16], [0, 260], { ...clamp01, easing: Easing.out(Easing.cubic) });
  const mp = spring({ frame: frame - 12, fps, config: { damping: 8, stiffness: 140, mass: 0.7 } });
  const mpShake = Math.sin(frame / 2.2) * 5 * mp;

  if (theme === "cinematic") {
    return (
      <AbsoluteFill style={{ zIndex: 15 }}>
        <AbsoluteFill
          style={{
            opacity: scrim,
            background: "radial-gradient(ellipse at center, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.42) 45%, transparent 78%)"
          }}
        />
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 420 }}>
          <div
            style={{
              textAlign: "center",
              opacity: 1 - exit,
              transform: `scale(${drift * (1 + exit * 0.14)})`,
              filter: exit > 0.02 ? `blur(${exit * 10}px)` : undefined
            }}
          >
            <div style={{ marginBottom: 22 }}>
              <GlowPill label="HOOK" accent="gold" delay={0} size={22} />
            </div>
            <div style={{ position: "relative" }}>
              <GhostEcho text={words.join(" ")} size={size * 0.95} />
              <GlowWords text={words.join(" ")} size={size * 0.95} accent="gold" maxWidth={940} delay={4} stagger={2.4} />
            </div>
            <div style={{ marginTop: 28, display: "flex", justifyContent: "center" }}>
              <GlowRule accent="gold" delay={18} width={rule} />
            </div>
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ zIndex: 15 }}>
      <AbsoluteFill
        style={{
          opacity: scrim,
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.4) 45%, transparent 78%)"
        }}
      />
      <div style={{ position: "absolute", inset: 0, opacity: 0.9 * (1 - exit) }}>
        <LottieFx name="burst" theme={theme} style={{ position: "absolute", left: 0, top: 330, width: 1080, height: 1080 }} />
        <ShapeBurst colors={[t.primary, t.secondary, "#fff", "#FF3B3B"]} count={18} radius={470} seed="hook" cy="46%" />
      </div>

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 420 }}>
        <div
          style={{
            textAlign: "center",
            opacity: 1 - exit,
            transform: `scale(${drift * (1 + exit * 0.18)}) rotate(-2.5deg)`,
            filter: `drop-shadow(0 10px 26px rgba(0,0,0,0.8))${exit > 0.02 ? ` blur(${exit * 10}px)` : ""}`
          }}
        >
          <div
            style={{
              height: 10,
              width: rule,
              margin: "0 auto 30px",
              borderRadius: 10,
              background: `linear-gradient(90deg, ${t.primary}, #FF3B3B)`
            }}
          />
          <div style={{ position: "relative" }}>
          <KineticText
            text={words.join(" ")}
            variant="slam"
            size={size}
            color="#fff"
            markerWord={emph}
            markerColor="#FFE600"
            markerInk="#0A0A0A"
            stagger={1.1}
            delay={2}
            extrudeColor="#000"
            stroke="#000"
            strokeWidth={4}
            maxWidth={960}
            lineHeight={1.02}
            letterSpacing={0}
            ring="#fff"
            ringSize={3}
          />
          <Shine delay={22} duration={22} />
          </div>
        </div>
      </AbsoluteFill>

      {/* megafon kolase (halftone) */}
      <div
        style={{
          position: "absolute",
          left: 34,
          top: 150,
          width: 300,
          opacity: (1 - exit) * Math.min(1, mp),
          transform: `translateX(${(1 - mp) * -260}px) rotate(${-14 + mpShake}deg) scale(${0.85 + mp * 0.15 + Math.max(0, Math.sin(frame / 3)) * 0.04})`,
          filter: "drop-shadow(0 8px 16px rgba(0,0,0,0.6))"
        }}
      >
        <Img src={staticFile("el/megaphone.png")} style={{ width: "100%" }} />
      </div>

      <div style={{ position: "absolute", left: 560, top: 1010, width: 380, height: 270, transform: "scaleX(-1) rotate(-6deg)", opacity: (1 - exit) * Math.min(1, mp) }}>
        <LottieFx name="arrow" theme={theme} style={{ width: 380, height: 270 }} />
      </div>
      <Mascot pose="utama" side="right" totalFrames={totalFrames} theme={theme} height={560} bottom={330} inset={-30} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  OUTRO (3 detik terakhir): CTA wave + tombol subscribe + konfeti      */
/* ------------------------------------------------------------------ */
export const OutroScene = ({ text, totalFrames, theme }: { text: string; totalFrames: number; theme: ThemeName }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = THEMES[theme];
  const words = String(text).toUpperCase().split(/\s+/).filter(Boolean);
  if (!words.length) return null;

  const maxWord = Math.max(...words.map((w) => w.length));
  const size = Math.max(84, Math.min(140, 920 / (maxWord * 0.55)));
  const scrim = interpolate(frame, [0, 10], [0, 1], clamp01);
  const btn = spring({ frame: frame - 22, fps, config: { damping: 8, stiffness: 150, mass: 0.7 } });
  const pulse = 1 + Math.max(0, Math.sin(frame / 5)) * 0.05;

  if (theme === "cinematic") {
    return (
      <AbsoluteFill style={{ zIndex: 15 }}>
        <AbsoluteFill
          style={{
            opacity: scrim,
            background: "radial-gradient(ellipse at center, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.4) 45%, transparent 78%)"
          }}
        />
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 700 }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ position: "relative" }}>
              <GhostEcho text={words.join(" ")} size={size * 0.95} />
              <GlowWords text={words.join(" ")} size={size * 0.95} accent="cyan" maxWidth={940} stagger={2.2} />
            </div>
            <div
              style={{
                margin: "44px auto 0",
                display: "inline-flex",
                alignItems: "center",
                gap: 16,
                padding: "20px 46px",
                borderRadius: 999,
                border: `1px solid ${GLOW_THEMES.cyan.primary}`,
                background: "rgba(255,255,255,0.04)",
                boxShadow: `0 0 30px ${GLOW_THEMES.cyan.dim}`,
                transform: `scale(${interpolate(btn, [0, 1], [0, 1]) * pulse})`,
                opacity: Math.min(1, btn * 2)
              }}
            >
              <Triangle length={30} direction="right" fill={GLOW_THEMES.cyan.primary} cornerRadius={4} />
              <span style={{ fontFamily: FONT_GLOW_DISPLAY, fontWeight: 800, fontSize: 44, letterSpacing: 3, color: "#fff" }}>SUBSCRIBE</span>
            </div>
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill style={{ zIndex: 15 }}>
      <AbsoluteFill
        style={{
          opacity: scrim,
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.38) 45%, transparent 78%)"
        }}
      />
      <LottieFx name="confetti" theme={theme} style={{ position: "absolute", left: 0, top: 250, width: 1080, height: 1080 }} />

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 700 }}>
        <div style={{ textAlign: "center", filter: "drop-shadow(0 10px 24px rgba(0,0,0,0.8))", transform: "rotate(-2deg)" }}>
          <KineticText
            text={words.join(" ")}
            variant="wave"
            size={size}
            color="#fff"
            accent={t.primary}
            stroke="#000"
            strokeWidth={4}
            extrudeColor="#000"
            maxWidth={940}
            stagger={1.6}
            lineHeight={1.05}
          />
          <div
            style={{
              margin: "44px auto 0",
              display: "inline-flex",
              alignItems: "center",
              gap: 20,
              padding: "20px 46px",
              borderRadius: 24,
              background: "#FF1F2D",
              boxShadow: "0 8px 0 #8E0A14, 0 18px 30px rgba(0,0,0,0.6)",
              transform: `scale(${interpolate(btn, [0, 1], [0, 1]) * pulse}) rotate(${(1 - btn) * 8}deg)`,
              opacity: Math.min(1, btn * 2)
            }}
          >
            <Triangle length={46} direction="right" fill="#fff" cornerRadius={5} />
            <span style={{ fontFamily: FONT_IMPACT, fontSize: 64, letterSpacing: 4, color: "#fff" }}>SUBSCRIBE</span>
          </div>
        </div>
      </AbsoluteFill>

      <Mascot pose="wink" side="left" totalFrames={totalFrames} theme={theme} height={600} bottom={380} inset={-20} />
    </AbsoluteFill>
  );
};
