import React from "react";
import { AbsoluteFill, Img, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { LottieFx, Seal, ShapeBurst, type ThemeName } from "./Fx";

export type Pose = "utama" | "wow" | "berfikir" | "bertanya" | "terkejut" | "wink";
export const POSES: Pose[] = ["utama", "wow", "berfikir", "bertanya", "terkejut", "wink"];

const FILE: Record<Pose, string> = {
  utama: "char/pose_utama.png",
  wow: "char/pose_wow.png",
  berfikir: "char/pose_berfikir.png",
  bertanya: "char/pose_bertanya.png",
  terkejut: "char/pose_terkejut.png",
  wink: "char/pose_wink.png"
};

// pose yang menunjuk ke kiri layar -> di-flip bila berdiri di sisi kiri agar menunjuk ke tengah
const FLIP_ON_LEFT: Partial<Record<Pose, boolean>> = { utama: true };

const REACT_SHAKE: Partial<Record<Pose, number>> = { terkejut: 1, wow: 0.6 };

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Maskot ala sticker CapCut: masuk membal, idle bob + squash, keluar menyamping. */
export const Mascot = ({
  pose,
  side = "right",
  totalFrames,
  height = 640,
  bottom = 560,
  theme,
  halo = true,
  inset = -30
}: {
  pose: Pose;
  side?: "left" | "right";
  totalFrames: number;
  height?: number;
  bottom?: number;
  theme: ThemeName;
  halo?: boolean;
  inset?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dir = side === "left" ? -1 : 1;
  const accent = theme === "history" ? { a: "#F2C879", b: "#B5651D" } : { a: "#6FE7FF", b: "#8A5CFF" };

  const enter = spring({ frame: frame - 2, fps, config: { damping: 9, stiffness: 120, mass: 0.9 } });
  const exit = interpolate(frame, [totalFrames - 10, totalFrames], [0, 1], { ...clamp, easing: (t) => t * t });
  const bob = Math.sin(frame / 7) * 9;
  const squash = 1 + Math.sin(frame / 7 + Math.PI) * 0.018;

  const shakeAmp = (REACT_SHAKE[pose] ?? 0) * interpolate(frame, [4, 20], [1, 0], clamp);
  const sx = (random(`ms-x-${frame}`) - 0.5) * 16 * shakeAmp;
  const sy = (random(`ms-y-${frame}`) - 0.5) * 10 * shakeAmp;

  const offY = (1 - enter) * height * 1.15;
  const offX = exit * dir * (height * 0.8);
  const tilt = (1 - enter) * dir * 22 + Math.sin(frame / 11) * 1.8 * dir;
  const flip = side === "left" && FLIP_ON_LEFT[pose] ? -1 : 1;

  const outline = [
    "drop-shadow(5px 0 0 #fff)",
    "drop-shadow(-5px 0 0 #fff)",
    "drop-shadow(0 5px 0 #fff)",
    "drop-shadow(0 -5px 0 #fff)",
    "drop-shadow(0 14px 22px rgba(0,0,0,0.55))"
  ].join(" ");

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 16 }}>
      <div
        style={{
          position: "absolute",
          bottom,
          [side]: inset,
          height,
          width: height,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          transform: `translate(${offX + sx}px, ${offY + sy}px)`
        }}
      >
        {halo && (
          <>
            <div style={{ position: "absolute", left: "50%", top: "52%", transform: `translate(-50%,-50%) scale(${0.4 + enter * 0.6})`, opacity: 0.9 * (1 - exit) }}>
              <Seal size={height * 0.46} fill={accent.b} stroke={accent.a} fill2="rgba(255,255,255,0.9)" spin={frame * 1.6} />
            </div>
            <ShapeBurst colors={[accent.a, accent.b, "#ffffff"]} count={10} radius={height * 0.55} seed={`m-${pose}-${side}`} delay={3} cx="50%" cy="50%" />
            <div style={{ position: "absolute", left: "50%", top: "40%", width: height, height: height, transform: "translate(-50%,-50%)" }}>
              <LottieFx name="twinkle" theme={theme} style={{ width: "100%", height: "100%" }} />
            </div>
          </>
        )}
        <Img
          src={staticFile(FILE[pose])}
          style={{
            position: "relative",
            height: "100%",
            width: "auto",
            transformOrigin: "50% 100%",
            transform: `translateY(${bob}px) rotate(${tilt}deg) scale(${flip * (0.55 + enter * 0.45)}, ${(0.55 + enter * 0.45) * squash})`,
            filter: outline
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
