# External300 direct visual annotation

Scope: the pinned 300-row cohort in `cohort_task_unique_300_lexical` (7 sources).
This is a separate evaluation/review corpus; existing Intention v2 labels and
training manifests are not edited.

## Evidence and responsibility

- Labels and final frame boundaries are decided by the assistant in the active
  conversation after inspecting episode-specific image evidence. No Qwen or
  other external model annotates these videos.
- CPU scripts only extract/transcode videos, export raw control signals, propose
  signal-change locations, render frames, validate records, and upload assets.
- An episode stays `pending_visual_review` until a per-episode decision and
  evidence notes have been written. Script-generated pending intervals are not
  labels and must not enter training/evaluation exports.
- Marked reviewed means reviewed by the user, separately from assistant labels.

## Atomic actions and boundaries

- Intervals use zero-based episode-local inclusive frame indices [start, end].
  Labelled tracks cover the episode without gaps or overlaps.
- A transfer normally has `pick up X` and `place X in/on Y` atoms, grouped into
  the mission `put X in/on Y`.
- Finish pick up only after stable grasp and lift clear of support. Failed
  closures/slips/retries stay inside that pick-up action. Gripper closure alone
  is not a completed pick up.
- `pick up X` and `take X away from Y` are one atom unless video shows a distinct
  purposeful operation after the grasp.
- Open/close boundaries occur at the achieved target state (fully open/closed),
  not at handle grasp, initial motion, or an arbitrary duration fraction.
- Include a tool pick-up when it occurs on-screen, before stir/wipe/flip/etc.
  Do not invent a pick-up if the tool is already held at the beginning.
- Placement includes transport, positioning and supported release. Withdrawal
  and short final idle belong to the immediately preceding action unless a new
  purposeful action begins. Do not fabricate micro-actions just to increase count.
- Observed action wins over instruction order; uncertain identity, occlusion,
  truncation, simultaneous actions, or unsuccessful outcomes are documented.
- Raw gripper/state/command channels support visual analysis. Do not assume
  identical scales or polarity across datasets; keep channel provenance.

## Missions

- Group contiguous atoms toward a coherent immediate goal. A tool grasp and its
  immediately intended use usually share one mission. A mission may have one atom.
- Removal can be a mission such as `remove the pot lid`, containing pick-up and
  placement of the removed lid on the table.
- Distinct access operations (open drawer, close drawer) can be separate missions
  around object transfers. Do not merge an entire heterogeneous episode merely
  because it has a single original instruction.

## Long horizon

- Retain the prior set-level rule: repeated object-specific missions toward the
  same destination/collection goal may share a long-term mission `put all the X
  in/on Y`. A long video or several unrelated sequential tasks is not sufficient.
- Require evidence that the relevant set is being completed. Do not infer `all`
  merely because two objects were moved.
- Store short missions and their long-mission membership. Under the prior export
  policy, OM uses the short mission for the first two members and the long mission
  from its third member onward. Keep all short labels available for inspection.

## Assets

- LeRobot v3 source-file offsets are metadata-derived. Export every camera into
  episode-local H.264/yuv420p MP4 and verify frame count, duration, and FPS.
- Never overwrite source videos. RustFS objects use a new external300 prefix.
- Use a distinct IndexedDB/localStorage namespace and a separate website route.
