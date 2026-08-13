import React from "react";
import { Audio, OffthreadVideo } from "remotion";
import { FloatingProductCard } from "./FloatingProductCard";
import { KineticSubtitles } from "./KineticSubtitles";

export interface ViralReelProps {
  videoClips?: string[];
  audioUrl?: string;
  scriptText: string;
  productImageUrl?: string;
  durationSeconds: number;
}

export const ViralReelComposition: React.FC<ViralReelProps> = ({
  videoClips = [],
  audioUrl,
  scriptText,
  productImageUrl,
  durationSeconds,
}) => {
  const bgVideo = videoClips.length > 0 ? videoClips[0] : null;

  return (
    <div
      style={{
        width: 1080,
        height: 1920,
        backgroundColor: "#090d16",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* 1. Offthread Background Video Clip */}
      {bgVideo && (
        <OffthreadVideo
          src={bgVideo}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            position: "absolute",
            top: 0,
            left: 0,
          }}
        />
      )}

      {/* Subtle dark gradient overlay for text contrast */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(9, 13, 22, 0.4) 0%, rgba(9, 13, 22, 0.1) 40%, rgba(9, 13, 22, 0.7) 100%)",
          zIndex: 10,
        }}
      />

      {/* 2. Edge-TTS Speech Audio Narration */}
      {audioUrl && <Audio src={audioUrl} />}

      {/* 3. Floating Product Card Badge */}
      <FloatingProductCard productImageUrl={productImageUrl} />

      {/* 4. Kinetic CapCut / Instagram Subtitles */}
      <KineticSubtitles
        scriptText={scriptText}
        durationSeconds={durationSeconds}
      />
    </div>
  );
};
