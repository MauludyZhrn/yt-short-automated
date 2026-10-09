import React from "react";
import { Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Circle, Pie, Star } from "@remotion/shapes";
import { FONT_IMPACT, FONT_MARKER, Kicker } from "./Kinetic";

export type InfoItem = { label?: string; value?: number; year?: string };
export type InfoTheme = { primary: string; secondary: string };

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const INK = "#14110D";
const nf = new Intl.NumberFormat("id-ID");

/** Panel kaca gelap bergrid + selotip, dasar semua infografis. */
export const InfoPanel = ({
  t,
  title,
  height,
  children,
  scrap
}: {
  t: InfoTheme;
  title?: string;
  height: number;
  children: React.ReactNode;
  scrap?: "photo" | "text";
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 13, stiffness: 130, mass: 0.8 } });
  return (
    <div
      style={{
        position: "relative",
        width: 940,
        height,
        transform: `translateY(${(1 - enter) * -80}px) scale(${0.8 + enter * 0.2}) rotate(${(1 - enter) * -4 + Math.sin(frame / 40) * 0.4}deg)`,
        opacity: Math.min(1, enter * 2)
      }}
    >
      {scrap && (
        <Img
          src={staticFile(scrap === "photo" ? "el/paper_photo.png" : "el/paper_text.png")}
          style={{
            position: "absolute",
            width: scrap === "photo" ? 330 : 150,
            right: scrap === "photo" ? -70 : -36,
            top: scrap === "photo" ? -86 : -70,
            transform: `rotate(${scrap === "photo" ? 9 : 14}deg)`,
            filter: "drop-shadow(0 8px 14px rgba(0,0,0,0.55))"
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: 30,
          overflow: "hidden",
          border: `5px solid ${t.primary}`,
          boxShadow: `0 0 0 4px rgba(0,0,0,0.6), 0 24px 44px rgba(0,0,0,0.65), 0 0 36px ${t.primary}55`,
          background: `linear-gradient(180deg, rgba(8,8,16,0.82), rgba(8,8,16,0.94)), url(${staticFile("el/grid_dark.jpg")}) center/cover`
        }}
      />
      <div style={{ position: "absolute", top: -16, left: 40, width: 110, height: 32, background: "rgba(255,230,120,0.8)", transform: "rotate(-9deg)" }} />
      {title && (
        <div style={{ position: "absolute", top: -34, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <Kicker text={title} bg={t.primary} ink={INK} size={40} />
        </div>
      )}
      <div style={{ position: "absolute", inset: 0 }}>{children}</div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  PERCENT: donut animasi + angka hitung naik                           */
/* ------------------------------------------------------------------ */
export const parsePercent = (text: string): number | null => {
  const m = String(text).match(/(\d+(?:[.,]\d+)?)/);
  if (!m) return null;
  const v = parseFloat(m[1].replace(",", "."));
  return Number.isFinite(v) && v >= 0 && v <= 100 ? v : null;
};

export const PercentInfo = ({ t, text, sub, title }: { t: InfoTheme; text: string; sub?: string; title?: string }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pct = parsePercent(text) ?? 0;
  const p = spring({ frame: frame - 10, fps, config: { damping: 22, stiffness: 55, mass: 1 } });
  const R = 190;
  return (
    <InfoPanel t={t} title={title ?? "PERSENTASE"} height={610} scrap="text">
      <div style={{ position: "absolute", left: 0, right: 0, top: 70, display: "flex", justifyContent: "center" }}>
        <div style={{ position: "relative", width: R * 2 + 60, height: R * 2 + 60 }}>
          <div style={{ position: "absolute", left: 30, top: 30 }}>
            <Circle radius={R} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth={46} />
          </div>
          <div style={{ position: "absolute", left: 30, top: 30, filter: `drop-shadow(0 0 16px ${t.primary})` }}>
            <Pie radius={R} progress={(pct / 100) * p} closePath={false} rotation={-Math.PI / 2} fill="none" stroke={t.primary} strokeWidth={46} strokeLinecap="round" />
          </div>
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ fontFamily: FONT_IMPACT, fontSize: 150, color: "#fff", textShadow: `0 0 26px ${t.primary}, 5px 6px 0 #000` }}>
              {Math.round(pct * p)}
              <span style={{ fontSize: 80, color: t.primary }}>%</span>
            </div>
          </div>
        </div>
      </div>
      {sub && (
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, textAlign: "center", fontFamily: FONT_MARKER, fontSize: 46, color: "#fff", letterSpacing: 2, textTransform: "uppercase" }}>
          {sub}
        </div>
      )}
    </InfoPanel>
  );
};

/* ------------------------------------------------------------------ */
/*  COMPARE: batang horizontal bertingkat, pemenang ditandai bintang     */
/* ------------------------------------------------------------------ */
export const CompareInfo = ({ t, items, unit, title }: { t: InfoTheme; items: InfoItem[]; unit?: string; title?: string }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rows = items.slice(0, 3);
  const max = Math.max(...rows.map((r) => r.value ?? 0), 1);
  const rowH = 150;
  const height = 130 + rows.length * rowH;
  const winner = rows.reduce((b, r, i) => ((r.value ?? 0) > (rows[b].value ?? 0) ? i : b), 0);
  const BAR_W = 760;
  return (
    <InfoPanel t={t} title={title ?? "PERBANDINGAN"} height={height} scrap="photo">
      {rows.map((r, i) => {
        const sp = spring({ frame: frame - 8 - i * 9, fps, config: { damping: 18, stiffness: 80, mass: 0.9 } });
        const w = Math.max(18, ((r.value ?? 0) / max) * BAR_W * sp);
        const win = i === winner;
        const col = win ? t.primary : "rgba(255,255,255,0.78)";
        return (
          <div key={i} style={{ position: "absolute", left: 60, right: 60, top: 78 + i * rowH }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 8 }}>
              <span style={{ fontFamily: FONT_IMPACT, fontSize: 54, color: "#fff", letterSpacing: 1, textTransform: "uppercase" }}>{r.label}</span>
              <span style={{ fontFamily: FONT_IMPACT, fontSize: 54, color: col }}>
                {nf.format(Math.round((r.value ?? 0) * sp))}
                {unit ? <span style={{ fontSize: 30, marginLeft: 8 }}>{unit}</span> : null}
              </span>
            </div>
            <div style={{ position: "relative", height: 46, borderRadius: 23, background: "rgba(255,255,255,0.1)" }}>
              <div
                style={{
                  width: w,
                  height: 46,
                  borderRadius: 23,
                  background: win ? `linear-gradient(90deg, ${t.secondary}, ${t.primary})` : "linear-gradient(90deg,#9aa0ad,#e8eaf0)",
                  boxShadow: win ? `0 0 22px ${t.primary}99` : "none"
                }}
              />
              {win && (
                <div style={{ position: "absolute", left: w - 34, top: -26, transform: `rotate(${frame * 3}deg) scale(${sp})` }}>
                  <Star points={5} innerRadius={20} outerRadius={42} fill="#FFE600" stroke={INK} strokeWidth={5} cornerRadius={4} />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </InfoPanel>
  );
};

/* ------------------------------------------------------------------ */
/*  TIMELINE: garis waktu tergambar, titik muncul berurutan              */
/* ------------------------------------------------------------------ */
export const TimelineInfo = ({ t, items, title }: { t: InfoTheme; items: InfoItem[]; title?: string }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pts = items.slice(0, 4);
  const n = pts.length;
  const line = interpolate(frame, [6, 14 + n * 12], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const W = 940 - 320;
  return (
    <InfoPanel t={t} title={title ?? "LINIMASA"} height={560}>
      <div style={{ position: "absolute", left: 160, top: 280, width: W, height: 10, borderRadius: 5, background: "rgba(255,255,255,0.12)" }} />
      <div style={{ position: "absolute", left: 160, top: 280, width: W * line, height: 10, borderRadius: 5, background: `linear-gradient(90deg, ${t.secondary}, ${t.primary})`, boxShadow: `0 0 18px ${t.primary}` }} />
      {pts.map((p, i) => {
        const x = 160 + (n === 1 ? W / 2 : (i / (n - 1)) * W);
        const sp = spring({ frame: frame - 12 - i * 12, fps, config: { damping: 9, stiffness: 160, mass: 0.7 } });
        const up = i % 2 === 0;
        return (
          <div key={i} style={{ position: "absolute", left: x, top: 285, width: 0, height: 0 }}>
            <div style={{ position: "absolute", left: -26, top: -26, transform: `scale(${sp})` }}>
              <Circle radius={26} fill={t.primary} stroke="#fff" strokeWidth={8} />
            </div>
            <div
              style={{
                position: "absolute",
                left: -150,
                width: 300,
                textAlign: "center",
                [up ? "bottom" : "top"]: up ? 52 : 52,
                opacity: Math.min(1, sp * 1.5),
                transform: `translateY(${(1 - sp) * (up ? 30 : -30)}px)`
              }}
            >
              <div style={{ fontFamily: FONT_IMPACT, fontSize: 92, color: "#fff", textShadow: `0 0 20px ${t.primary}, 4px 5px 0 #000`, lineHeight: 1 }}>{p.year ?? ""}</div>
              <div style={{ fontFamily: FONT_MARKER, fontSize: 34, color: t.primary, textTransform: "uppercase", letterSpacing: 1, lineHeight: 1.15, marginTop: 6 }}>{p.label ?? ""}</div>
            </div>
          </div>
        );
      })}
    </InfoPanel>
  );
};
