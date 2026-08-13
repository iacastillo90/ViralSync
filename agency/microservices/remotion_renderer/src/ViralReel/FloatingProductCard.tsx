import React from "react";
import { Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface FloatingProductCardProps {
  productImageUrl?: string;
}

export const FloatingProductCard: React.FC<FloatingProductCardProps> = ({
  productImageUrl,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!productImageUrl) return null;

  // Spring entry animation for product card
  const springProgress = spring({
    fps,
    frame,
    config: { damping: 14, mass: 0.5 },
  });

  const scale = interpolate(springProgress, [0, 1], [0.5, 1]);
  const opacity = interpolate(springProgress, [0, 1], [0, 1]);

  // Subtle continuous levitation pulse
  const floatY = Math.sin(frame / 15) * 8;

  return (
    <div
      style={{
        position: "absolute",
        top: 240 + floatY,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: 40,
        transform: `scale(${scale})`,
        opacity,
      }}
    >
      <div
        style={{
          width: 380,
          height: 380,
          borderRadius: 40,
          backgroundColor: "rgba(15, 23, 42, 0.90)",
          border: "4px solid rgba(250, 204, 21, 0.9)",
          boxShadow: "0 25px 50px rgba(0, 0, 0, 0.65), 0 0 30px rgba(250, 204, 21, 0.3)",
          overflow: "hidden",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: 20,
        }}
      >
        <Img
          src={productImageUrl}
          style={{
            maxWidth: "100%",
            maxHeight: "100%",
            objectFit: "contain",
            borderRadius: 24,
          }}
        />
      </div>
    </div>
  );
};
