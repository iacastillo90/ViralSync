# video-scene-render-contract Specification

## Purpose

Additive per-scene render protocol on the renderer `RenderRequest` (`microservices/renderer/app.py:43`). The renderer MAY receive `scenes[]` — the storyboard already produced by `video_prompt_crew` (`video_storyboard` in state) — so scene work is consumed instead of discarded. Payloads without `scenes[]` MUST render byte-identically to today (flat `script_text` + keyword b-roll), keeping the renderer deploy-safe.

## Requirements

### Requirement: REQ-VSR-01 — Additive `scenes[]` protocol on RenderRequest

The system MUST accept an optional `scenes` field on `RenderRequest`, each scene carrying `block` and `text` (required) and optional `tts_voice`, `visual_prompt`, `duration_s`. Absent `scenes` MUST NOT break existing clients.

#### Scenario: VSR-01-1 — full scenes payload accepted

- GIVEN a render request with 4 scenes (block/text + optional voice, prompt, duration)
- WHEN the renderer validates
- THEN it accepts the payload and renders per scene

#### Scenario: VSR-01-2 — absent scenes keeps old contract

- GIVEN a render request with no `scenes` field (legacy payload)
- WHEN the renderer validates
- THEN it accepts it and uses the flat `script_text` path

### Requirement: REQ-VSR-02 — Flat `script_text` fallback is byte-identical

The system MUST render legacy payloads (no `scenes`) exactly as before: single TTS pass over `script_text`, keyword b-roll, MoviePy 9:16 compose at the existing cap. `scenes` MUST be optional.

#### Scenario: VSR-02-1 — legacy payload renders unchanged

- GIVEN a payload identical to the current renderer's input (`title`, `script_text`, `keywords`, `tenant_id`)
- WHEN it is rendered after the change
- THEN the output video, narration, and duration match pre-change behavior

### Requirement: REQ-VSR-03 — Per-scene TTS semantics

The system MUST synthesize narration per scene: each scene's `text` with its `tts_voice` when present, else `DEFAULT_VOICE` (`app.py:40`). Audio MUST concatenate in scene order.

#### Scenario: VSR-03-1 — distinct voice per scene

- GIVEN scenes with different `tts_voice` values
- WHEN the renderer generates audio
- THEN each scene's narration uses its declared voice
- AND audio is concatenated in scene order

#### Scenario: VSR-03-2 — missing tts_voice uses default

- GIVEN a scene without `tts_voice`
- WHEN the renderer generates audio
- THEN that scene uses `DEFAULT_VOICE`

### Requirement: REQ-VSR-04 — Per-scene b-roll semantics

The system MUST source b-roll per scene: `visual_prompt` present drives that scene's clip search; absent falls back to the payload `keywords`. Clips MUST compose in scene order.

#### Scenario: VSR-04-1 — visual_prompt drives scene clips

- GIVEN a scene with `visual_prompt`
- WHEN the b-roll for that scene is resolved
- THEN clip search uses keywords derived from `visual_prompt`

#### Scenario: VSR-04-2 — no visual_prompt falls back

- GIVEN a scene without `visual_prompt`
- WHEN the b-roll for that scene is resolved
- THEN clip search uses the payload `keywords`

### Requirement: REQ-VSR-05 — Per-scene duration semantics

The system MUST honor `duration_s` when provided; scenes without it MUST use their TTS-derived natural duration. Total render MUST NOT exceed the existing `max_duration_seconds` cap unless the payload explicitly requests more.

#### Scenario: VSR-05-1 — explicit duration honored

- GIVEN a scene with `duration_s: 12.0`
- WHEN the scene is composed
- THEN the scene holds 12 seconds in the final timeline

#### Scenario: VSR-05-2 — natural duration when absent

- GIVEN a scene without `duration_s`
- WHEN the scene is composed
- THEN its duration equals its TTS length

### Requirement: REQ-VSR-06 — Malformed scenes validation

The system MUST reject (4xx, never silently render) requests where `scenes` holds an object missing `block` or `text`, or whose `text` is not a non-empty string. Unknown extra keys MUST be ignored (forward compatibility); `scenes: []` MUST behave as the flat fallback.

#### Scenario: VSR-06-1 — invalid scene rejected

- GIVEN a request whose scene lacks `text`
- WHEN the renderer validates
- THEN it responds 4xx naming the invalid scene
- AND it does NOT render a fallback video

#### Scenario: VSR-06-2 — empty scenes behaves as flat

- GIVEN `scenes: []`
- WHEN the renderer renders
- THEN it uses the flat path

#### Scenario: VSR-06-3 — unknown keys ignored

- GIVEN a scene with an extra unrecognized key
- WHEN the renderer validates
- THEN it accepts the scene and ignores the unknown key