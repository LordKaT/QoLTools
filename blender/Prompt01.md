SYSTEM ROLE:
You are a senior Blender Python developer.
Target Blender 4.5 ONLY (not 3.x).
Use the Video Sequence Editor (VSE) API for Blender 4.5.
Do not invent operators/properties.

LANGUAGE:
Python

SCENE ASSUMPTIONS:
Single scene, single VSE timeline.
Treat “Frame 0” in this spec as scene.frame_start.

INPUT STRIPS (MUST EXIST):
- Original movie strip (video) on channel 5 (call it ORIG_V)
- Original sound strip (audio) on channel 4 (call it ORIG_A)
These represent the same source and must remain in sync.

MARKERS:
- Read all timeline markers, sort by frame ascending.
- Marker count MUST be even. If odd: halt with error.
- Pair markers by order:
  START_1 = markers[0], END_1 = markers[1], ...
- Each segment range is half-open: keep [START_N, END_N)
- Validate START_N < END_N for all pairs. Else halt.

PHASE 1 — EXTRACT SEGMENTS (SPLIT/TRIM ONLY, NO RE-IMPORT):
A) Split rules:
- For every boundary frame in {START_1, END_1, START_2, END_2, ...}:
  - Split ORIG_V at that frame ONLY if ORIG_V.frame_final_start < frame < ORIG_V.frame_final_end
  - Split ORIG_A at that frame ONLY if ORIG_A.frame_final_start < frame < ORIG_A.frame_final_end
- Splitting must preserve all existing strip properties.

B) Keep/delete rules:
- After splitting, the timeline will contain multiple slices of ORIG_V and ORIG_A.
- For each N:
  - Identify the slice whose frame range exactly matches [START_N, END_N).
  - Rename that slice pair:
    - video strip: VIDEO_{N}_V (must be on channel 5)
    - audio strip: VIDEO_{N}_A (must be on channel 4)
- Delete every other slice of the original video/audio that is NOT one of those exact kept ranges.
- After Phase 1, NO remaining “original” slices are allowed; only VIDEO_{N}_V and VIDEO_{N}_A pairs remain.

C) Compaction rule (remove gaps deterministically):
- Repack segments so VIDEO_1 starts at scene.frame_start.
- Place segments back-to-back in increasing N:
  - VIDEO_{N+1}_V/A start exactly at end of VIDEO_N_V/A.
- Video and audio for each N must move together and retain identical frame ranges.

PHASE 2 — INSERT RESPONSES AND SHIFT SUBSEQUENT SEGMENTS:
- Responses are files: RESPONSE_1.wav ... RESPONSE_N.wav on disk.
- Insert responses on audio channel 3 only.
- For each N from 1..N in order:
  1) Let seg_end = VIDEO_{N}_V.frame_final_end (current timeline, after compaction and any prior shifts).
  2) Insert RESPONSE_N.wav at seg_end on channel 3, name it RESPONSE_{N}.
  3) Compute response duration in frames as resp_len_frames.
  4) Shift ALL strips belonging to segments (VIDEO_{K}_V and VIDEO_{K}_A for K > N) forward by resp_len_frames.
     - Shift video+audio together for each K.
     - Do NOT shift VIDEO_{N}_V/A.
     - Do NOT shift earlier responses already inserted.

FINAL GUARANTEES:
- Timeline begins with VIDEO_1 (VIDEO_1_V on ch5 + VIDEO_1_A on ch4) at scene.frame_start.
- For every N: VIDEO_N is immediately followed by RESPONSE_N on channel 3.
- Final strip in time is RESPONSE_N.
- No leftover original slices exist.
- No video/audio desync is permitted: for every N, VIDEO_{N}_V and VIDEO_{N}_A must share identical start/end frames.
- Any missing RESPONSE_N.wav file: halt with error.
