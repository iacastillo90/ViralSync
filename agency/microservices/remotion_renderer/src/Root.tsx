import React from "react";
import { Composition } from "remotion";
import { ViralReelComposition, ViralReelProps } from "./ViralReel/ViralReelComposition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition<ViralReelProps>
        id="ViralReel"
        component={ViralReelComposition}
        durationInFrames={30 * 30} // Default 30s at 30fps
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          scriptText: "Prueba de subtítulos kinetico con Remotion en React",
          durationSeconds: 30,
        }}
        calculateMetadata={({ props }) => {
          const durationSeconds = props.durationSeconds || 30;
          return {
            durationInFrames: Math.ceil(durationSeconds * 30),
          };
        }}
      />
    </>
  );
};
