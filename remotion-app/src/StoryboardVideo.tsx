import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Captions, ProgressBar, buildPages, type CapWord } from "./Captions";
import { InfographicByType, type InfoItem } from "./InfographicAnim";
import { KineticType, type Verb } from "./KineticType";
import { Flash, LightLeak, TRANSITION_SEC, transitionFor, type TransitionName } from "./Transitions";
import { SAFE, shotAt, type Shot } from "./Timeline";

/**
 * StoryboardVideo.tsx — komposisi baru yang membaca `storyboard` dari input_props.json.
 *
 * Dibuat oleh scripts/storyboard_compile.py. Komposisi lama (ShortsVideo.tsx) tetap ada
 * dan tidak perlu diubah: daftarkan komposisi ini sebagai "StoryboardComposition" di Root.tsx,
 * lalu ganti argumen `render` di remotion_bridge.py bila ingin memakai pipeline baru.
 *
 * Semua angka waktu berasal dari storyboard (aturan P2). Tidak ada angka frame telanjang.
 */

export type Cue = {
  type: "year" | "stat" | "keyword" | "question" | "percent" | "compare" | "timeline";
  text: string;
  sub?: string;
  start: number;
  end: number;
  verb?: string;
  pose?: string;
  side?: "left" | "right";
  items?: InfoItem[];
};

type Props = {
  // baru
  storyboard?: { shots?: Shot[]; meta?: Record<string, unknown> };
  beats?: { beatTimes?: number[]; beatStrengths?: number[] } | null;
  safeArea?: { top?: number; bottom?: number };
  subtitleStyle?: "karaoke" | "slide" | "typewriter";
  // lama (kompatibel mundur)
  audioPath?: string;
  bgMusicPath?: string | null;
  bgImages?: string[];
  titleText?: string;
  outroText?: string;
  subtitles?: CapWord[];
  logoPath?: string | null;
  theme?: "history" | "space" | "cinematic";
  motionCues?: Cue[];
  bgmVolume?: number;
  sfxEnabled?: boolean;
};

const THEMES = {
  history: { primary: "#F2C879", secondary: "#B5651D", badge: "ARSIP SEJARAH" },
  space: { primary: "#6FE7FF", secondary: "#8A5CFF", badge: "DATA KOSMIK" },
  cinematic: { primary: "#E8C36C", secondary: "#8FE3FF", badge: "MODE SINEMATIK" },
} as const;

const cleanPath = (p?: string | null) => (p ? String(p).replace(/^public\//, "").replace(/^\.?\//, "") : "");

const VERB_MAP: Record<string, Verb> = {
  slam: "slam", wave: "wave", mask: "mask", type: "type", pop: "pop",
  countup: "countup", draw: "draw", glitch: "glitch", wipe: "wipe", float: "float",
};

/* ------------------------------------------------------------------ */
/*  Latar: Ken Burns per slot                                          */
/* ------------------------------------------------------------------ */
const BgSlide: React.FC<{ src?: string; index: number; duration: number }> = ({ src, index, duration }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, duration], [0, 1], { extrapolateRight: "clamp" });
  const dir = index % 4;
  const scale = 1 + p * 0.06;
  const tx = dir === 0 ? p * -30 : dir === 1 ? p * 30 : 0;
  const ty = dir === 2 ? p * -30 : dir === 3 ? p * 30 : 0;
  if (!src) return <AbsoluteFill style={{ backgroundColor: "#05060c" }} />;
  return (
    <AbsoluteFill style={{ backgroundColor: "#05060c" }}>
      <Img
        src={staticFile(cleanPath(src))}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translate(${tx}px, ${ty}px)`,
        }}
      />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  Satu callout: infografis atau tipografi                            */
/* ------------------------------------------------------------------ */
const Callout: React.FC<{ cue: Cue; theme: keyof typeof THEMES; index: number; durationFrames: number }> = ({
  cue,
  theme,
  index,
  durationFrames,
}) => {
  const t = THEMES[theme];
  const verb = VERB_MAP[cue.verb ?? ""] ?? (cue.type === "year" ? "slam" : cue.type === "question" ? "wave" : "pop");
  const info = cue.type === "percent" || cue.type === "compare" || cue.type === "timeline";

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 240 }}>
      {info ? (
        <InfographicByType t={t} type={cue.type} text={cue.text} sub={cue.sub} items={cue.items} />
      ) : (
        <KineticType
          text={cue.text}
          verb={verb}
          size={cue.type === "year" || cue.type === "stat" ? 150 : 110}
          color="#fff"
          accent={t.primary}
          extrudeColor="rgba(0,0,0,0.85)"
          seed={`cue-${index}`}
          markerWord={verb === "wipe" ? 0 : undefined}
        />
      )}
      {cue.sub && !info ? (
        <div
          style={{
            marginTop: 18,
            fontFamily: "'Permanent Marker', 'Poppins', cursive",
            fontSize: 46,
            color: t.primary,
            textTransform: "uppercase",
            letterSpacing: 2,
          }}
        >
          {cue.sub}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/*  Komposisi                                                          */
/* ------------------------------------------------------------------ */
export const StoryboardVideo: React.FC<Props> = (props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const shots: Shot[] = props.storyboard?.shots ?? [];
  const themeName: keyof typeof THEMES =
    props.theme === "history" ? "history" : props.theme === "cinematic" ? "cinematic" : "space";
  const t = THEMES[themeName];
  const bgImages = props.bgImages ?? [];
  const cues: Cue[] = props.motionCues ?? [];
  const bgmVol = Number(props.bgmVolume) || 0.15;
  const safeBottom = props.safeArea?.bottom ?? SAFE.bottom;

  const active = shotAt(shots, frame);
  const activeIdx = shots.findIndex((s) => s === active);

  // latar mengikuti shot aktif; tanpa storyboard, gilir gambar tiap 8 detik
  const slot = active?.visual?.slot ?? Math.floor(frame / (fps * 8)) % Math.max(1, bgImages.length);
  const bgSrc = bgImages[(slot ?? 0) % Math.max(1, bgImages.length)];

  // punch-in di hook + dorongan halus saat callout masuk (maks +0.022)
  const punch = interpolate(frame, [0, 22], [1.16, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  let cueBump = 0;
  for (const c of cues) {
    const d = frame - Math.round(c.start * fps);
    if (d >= 0 && d < 26) cueBump = Math.max(cueBump, Math.sin((d / 26) * Math.PI) * 0.022);
  }
  const prevEnergy = activeIdx > 0 ? shots[activeIdx - 1]?.energy : undefined;
  const trans: TransitionName = active?.transitionIn ?? transitionFor(prevEnergy, active?.energy);

  const pages = React.useMemo(() => buildPages(props.subtitles ?? []), [props.subtitles]);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {/* ---- AUDIO ---- */}
      {props.audioPath ? <Audio src={staticFile(cleanPath(props.audioPath))} /> : null}
      {props.bgMusicPath ? (
        <Audio
          src={staticFile(cleanPath(props.bgMusicPath))}
          volume={(f) =>
            interpolate(f, [0, fps, durationInFrames - fps * 1.5, durationInFrames], [0, bgmVol, bgmVol, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      ) : null}

      {/* ---- LATAR ---- */}
      <AbsoluteFill
        style={{
          transform: `translate(${Math.sin(frame / 23) * 2.5}px, ${Math.cos(frame / 29) * 2.5}px) scale(${punch * (1 + cueBump)})`,
          filter: themeName === "cinematic"
            ? "contrast(1.12) saturate(0.55) brightness(0.62) grayscale(0.15)"
            : "contrast(1.1) saturate(1.15) brightness(0.97)",
        }}
      >
        <BgSlide src={bgSrc} index={slot ?? 0} duration={Math.max(1, active?.durationFrames ?? fps * 8)} />
      </AbsoluteFill>

      {/* ---- COLOR GRADE ---- */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.12) 35%, rgba(0,0,0,0.18) 60%, rgba(0,0,0,0.65) 100%)",
        }}
      />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.55) 100%)" }} />

      {/* ---- TRANSISI antar shot ---- */}
      {shots.map((s, i) =>
        i === 0 ? null : (
          <React.Fragment key={`tr-${s.id}`}>
            {trans === "cut" ? <Flash at={s.from} /> : null}
            {trans === "dissolve" ? <LightLeak at={s.from - Math.round(TRANSITION_SEC.dissolve * fps)} /> : null}
          </React.Fragment>
        )
      )}

      {/* ---- CALLOUT / INFOGRAFIS ---- */}
      {cues.map((c, i) => {
        const from = Math.max(0, Math.round(c.start * fps));
        const dur = Math.max(12, Math.round((c.end - c.start) * fps));
        return (
          <Sequence key={`cue-${i}`} from={from} durationInFrames={dur}>
            <Callout cue={c} theme={themeName} index={i} durationFrames={dur} />
          </Sequence>
        );
      })}

      {/* ---- HOOK CARD (3 detik pertama) ---- */}
      {props.titleText ? (
        <Sequence durationInFrames={Math.round(fps * 3)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 380 }}>
            <KineticType
              text={props.titleText}
              verb="slam"
              size={150}
              color="#fff"
              accent={t.primary}
              extrudeColor="rgba(0,0,0,0.9)"
              seed="hook"
            />
          </AbsoluteFill>
        </Sequence>
      ) : null}

      {/* ---- CAPTION ---- */}
      {props.subtitles?.length ? (
        <Captions
          words={props.subtitles}
          pages={pages}
          style={props.subtitleStyle ?? "karaoke"}
          size={100}
          activeColor={t.primary}
          bottomOffset={safeBottom + 40}
        />
      ) : null}

      {/* ---- OUTRO CARD ---- */}
      {props.outroText ? (
        <Sequence from={Math.max(0, durationInFrames - Math.round(fps * 3))} durationInFrames={Math.round(fps * 3)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingBottom: 380 }}>
            <KineticType
              text={props.outroText}
              verb="wave"
              size={110}
              color="#fff"
              accent={t.primary}
              extrudeColor="rgba(0,0,0,0.9)"
              seed="outro"
            />
          </AbsoluteFill>
        </Sequence>
      ) : null}

      {/* ---- BADGE, LOGO, PROGRESS ---- */}
      <div
        style={{
          position: "absolute",
          top: SAFE.top - 120,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            padding: "8px 22px",
            border: `3px solid ${t.primary}`,
            borderRadius: 999,
            color: t.primary,
            fontFamily: "'Anton', Impact, sans-serif",
            fontSize: 34,
            letterSpacing: 4,
            background: "rgba(0,0,0,0.45)",
            opacity: 0.85,
          }}
        >
          {t.badge}
        </div>
      </div>
      {props.logoPath ? (
        <Img
          src={staticFile(cleanPath(props.logoPath))}
          style={{ position: "absolute", top: SAFE.top - 130, right: 40, width: 130, opacity: 0.9 }}
        />
      ) : null}
      <ProgressBar color={t.primary} bottom={safeBottom + 10} />
    </AbsoluteFill>
  );
};
