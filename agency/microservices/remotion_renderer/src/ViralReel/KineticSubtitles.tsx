import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface KineticSubtitlesProps {
  scriptText: string;
  durationSeconds: number;
}

export const KineticSubtitles: React.FC<KineticSubtitlesProps> = ({
  scriptText,
  durationSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const words = (scriptText || "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return null;

  const totalFrames = Math.max(durationSeconds * fps, 1);
  const progress = Math.min(Math.max(frame / totalFrames, 0), 1);
  const activeIdx = Math.min(
    Math.floor(progress * words.length),
    words.length - 1
  );

  // Group words into lines of 4
  const wordsPerLine = 4;
  const lines: { startIdx: number; lineWords: string[] }[] = [];
  for (let i = 0; i < words.length; i += wordsPerLine) {
    lines.push({ startIdx: i, lineWords: words.slice(i, i + wordsPerLine) });
  }

  // Find active line
  let activeLineIdx = 0;
  lines.forEach((line, idx) => {
    if (activeIdx >= line.startIdx && activeIdx < line.startIdx + line.lineWords.length) {
      activeLineIdx = idx;
    }
  });

  const visibleLines = lines.slice(
    Math.max(0, activeLineIdx - 1),
    Math.min(lines.length, activeLineIdx + 2)
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 220,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 40px",
        zIndex: 50,
      }}
    >
      <div
        style={{
          backgroundColor: "rgba(15, 23, 42, 0.88)",
          backdropFilter: "blur(12px)",
          border: "3.5px solid rgba(250, 204, 21, 0.95)",
          borderRadius: 32,
          padding: "24px 36px",
          maxWidth: 960,
          width: "100%",
          boxShadow: "0 20px 45px rgba(0, 0, 0, 0.6), inset 0 2px 4px rgba(255, 255, 255, 0.15)",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          alignItems: "center",
        }}
      >
        {visibleLines.map((line) => (
          <div
            key={line.startIdx}
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "center",
              gap: 16,
            }}
          >
            {line.lineWords.map((word, wIdx) => {
              const globalWordIdx = line.startIdx + wIdx;
              const isActive = globalWordIdx === activeIdx;
              const isPast = globalWordIdx < activeIdx;

              // Pop-in spring animation for the active word
              const springScale = isActive
                ? spring({
                    fps,
                    frame: frame % Math.max(Math.floor(totalFrames / words.length), 1),
                    config: { damping: 12, mass: 0.4 },
                  })
                : 1;

              const scale = isActive ? interpolate(springScale, [0, 1], [0.95, 1.15]) : 1;

              return (
                <span
                  key={wIdx}
                  style={{
                    fontFamily: "'Inter', 'SF Pro Display', system-ui, sans-serif",
                    fontSize: 48,
                    fontWeight: 900,
                    letterSpacing: "-0.02em",
                    transform: `scale(${scale})`,
                    transition: "all 0.15s ease-out",
                    color: isActive
                      ? "#facc15"
                      : isPast
                      ? "#ffffff"
                      : "rgba(255, 255, 255, 0.65)",
                    textShadow: isActive
                      ? "0 0 20px rgba(250, 204, 21, 0.8), -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000"
                      : "-2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000",
                  }}
                >
                  {word}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};
