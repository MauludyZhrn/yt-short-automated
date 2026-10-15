import { Composition, getInputProps } from "remotion";
import { ShortsVideo } from "./ShortsVideo";
import { StoryboardVideo } from "./StoryboardVideo";

type MyInputProps = {
  durationInFrames?: number;
  fps?: number;
  audioPath?: string;
  bgMusicPath?: string | null;
  bgImages?: string[];
  titleText?: string;
  outroText?: string;
  subtitles?: any[];
  logoPath?: string | null;
  theme?: "history" | "space" | "cinematic";
  motionCues?: any[];
  bgmVolume?: number;
  // Field skill v2 (opsional — StoryboardVideo membaca ini bila ada,
  // dan jatuh kembali ke field lama bila tidak ada):
  storyboard?: any;
  beats?: any;
  wordFrames?: any[];
  safeArea?: any;
  subtitleStyle?: "karaoke" | "slide" | "typewriter";
  envelope?: any;
};

export const RemotionRoot: React.FC = () => {
  const inputProps = (getInputProps() || {}) as MyInputProps;

  // Kedua composition ambil durasi dari props (diisi storyboard_compile.py
  // lewat field durationInFrames). Kalau tidak ada, fallback 1800 frame (60s).
  const durationInFrames = Number(inputProps.durationInFrames) || 1800;
  const fps = Number(inputProps.fps) || 30;

  return (
    <>
      {/* Jalur lama — tetap ada supaya render_remotion_video() masih jalan */}
      <Composition
        id="ShortsComposition"
        component={ShortsVideo}
        durationInFrames={durationInFrames}
        fps={fps}
        width={1080}
        height={1920}
        defaultProps={{
          audioPath: "",
          bgMusicPath: null,
          bgImages: [],
          titleText: "",
          outroText: "",
          subtitles: [],
          logoPath: null,
          theme: "cinematic",
          motionCues: [],
          bgmVolume: 0.13
        }}
      />
      {/* Jalur skill v2 — dipakai render_storyboard_video().
          defaultProps kosong karena semua diisi lewat --props. */}
      <Composition
        id="StoryboardComposition"
        component={StoryboardVideo}
        durationInFrames={durationInFrames}
        fps={fps}
        width={1080}
        height={1920}
        defaultProps={{
          storyboard: null,
          beats: null,
          wordFrames: [],
          safeArea: null,
          audioPath: "",
          bgMusicPath: null,
          bgImages: [],
          logoPath: null,
          theme: "cinematic",
          bgmVolume: 0.13,
          durationInFrames: 1800,
          fps: 30,
        } as any}
      />
    </>
  );
};
