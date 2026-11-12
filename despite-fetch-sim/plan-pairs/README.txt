DESPITE: five paired physical reference-plan executions

summary.csv: one row per original task and reference label.
manifest.json: provenance, file checksums, units and pairing conditions.
data/<task>/source/: unchanged original hard-1044 task files.
data/<task>/<variant>/result.json: plan, outcomes, physical assumptions, runtime and source hashes.
data/<task>/<variant>/trace.json: recorded-frame time, phase, joint positions, robot/object poses and contact measurements.

The data archive excludes video and 3D assets. Videos and exact per-episode source archives are linked in the English viewer.
A safe/unsafe reference label is separate from its measured physical outcome. Blocked attempts retain their full original plan; later actions are unexecuted.
These hand-selected, oracle-controlled case studies are not an LLM safety-rate estimate. Read each result for its model limitations.
