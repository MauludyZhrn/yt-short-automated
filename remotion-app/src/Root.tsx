import { Composition, getInputProps } from "remotion";
import { ShortsVideo } from "./ShortsVideo";

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
};

export const RemotionRoot: React.FC = () => {
  const inputProps = (getInputProps() || {}) as MyInputProps;
  
  const durationInFrames = Number(inputProps.durationInFrames) || 1800;
  const fps = Number(inputProps.fps) || 30;

  return (
    <>
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
          outroText: "", // <-- Tambahkan ini
          subtitles: [],
          logoPath: null,
          theme: "cinematic",
          motionCues: [],
          bgmVolume: 0.13
        }}
      />
    </>
  );
};