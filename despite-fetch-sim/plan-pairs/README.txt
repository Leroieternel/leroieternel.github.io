DESPITE: paired physical reference-plan executions in native rooms

summary.csv: one row per original task and reference label.
manifest.json: provenance, file checksums, units and pairing conditions.
Initial-state comparisons normalize only signed floating-point zero, with no numeric tolerance. Original hashes remain in each result; a canonical hash and explicit comparison are supplied when raw hashes differ.
data/<task>/source/: unchanged original hard-1044 task files.
data/<task>/<variant>/result.json: plan, outcomes, physical assumptions, runtime and source hashes.
data/<task>/<variant>/trace.json: recorded-frame time, phase, joint positions, robot/object poses and contact measurements.

Kitchen fluid records additionally provide liquid-particles.json.gz, paired liquid-audit.json and a second camera recording of the same physical frames. When present, floor-film.json documents a one-way, volume-conserving subgrid surface model driven by measured particle contacts. Its wetting area is uncalibrated and it does not change the PBD spill metric or robot-floor friction. Archived inspection views explicitly label hidden geometry and recorded-state reconstruction. Fluid volumes and the detection threshold are uncalibrated; no temperature or injury solver is used.

The data archive excludes video and 3D assets. Videos and exact per-episode source archives are linked in the English viewer.
A safe/unsafe reference label is separate from its measured physical outcome. Blocked attempts retain their full original plan; later actions are unexecuted.
These hand-selected, oracle-controlled case studies are not an LLM safety-rate estimate. Read each result for its model limitations.
