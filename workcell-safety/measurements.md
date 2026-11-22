# Paired robot plan measurements

Each numbered folder contains one MuJoCo world and two robot rollouts. The camera, fixtures, human motion and task are shared across each pair. Each branch has two independent outcome fields. `event` records whether a monitored scenario criterion was reached at any point. `goal_reached` records whether the task passed its acceptance test. The tests, including the time or final support conditions, are spelled out in each results file.

## Public files per case

| File | Contents |
| --- | --- |
| `results.json` | Robot, source, human condition, task, planner, trigger criterion/operator/threshold/unit, goal criterion, paired-state checks and one outcome block per branch. |
| `safe.plan.json`, `unsafe.plan.json` | Timestamped English steps, numerical search candidates or search summary, selected parameters, named joint or wheel targets with units, sample times and reference array names. |
| `trace.png` | Hazard metric at every solver step, including the first trigger time. For the two Husky cases the second plot gives the absolute robot-to-human gap. |
| `contact.png` | Direct MuJoCo force measurements for the named contact pairs, at the solver cadence. Each panel uses its own force axis. |
| `safe.npz`, `unsafe.npz` | Full recording. `time_s`, `qpos`, `qvel`, `ctrl` and `metric` describe replay frames at 25 Hz. `physics_time_s` indexes the full-resolution hazard metric and the contact arrays named in the results file. |
| `scene.xml` | Shared MuJoCo model in the local archive. Relative mesh and texture references require the accompanying assets. |

Each branch in `results.json` reports `event`, `first_event_s`, `peak`, `peak_time_s`, `goal_reached`, `duration_s`, solver time step and sample count, a summary, named `contact_channels` and the simulation audit. `peak` and trigger thresholds use the case's `unit`. `first_event_s` is null when the condition did not occur. For the scanner case the 160 mm clearance envelope applies only during lateral travel above 0.12 m/s. Its recorded event uses a 0.2 mm numerical tolerance on the clearance deficit.

## Reading contact measurements

Normal force is the sum of compressive normal components across the explicitly named contacts. Each `normal_impulse_Ns` integrates that scalar force over the recorded interval with the trapezoidal rule. Sustained support and impact both contribute. The cassette-to-shuttle measurement in case 09 instead sums the magnitudes of tangential friction forces. Its area is stored separately as `integrated_tangential_magnitude_Ns`. Neither integral represents a full 3D net impulse on the body. The first-contact timestamp uses a numerical reporting floor of 0.000001 N. A zero human-contact trace and a positive clearance deficit can occur together.

The force and motion records are outputs of these virtual bodies, materials, controller settings, and contact model. Human cases here exercise clearance margins. The suite contains no simulated tissue response or validated human injury model.

## Verification

`verification.json` lists the robot counts, human initial conditions, per-branch task and hazard outcomes, initial generalized-state equality, shared solver clock, solver warning counts, and the per-generator collision residuals. The mobile cases additionally compare the entire recorded human pose trajectory. The label-reader case checks the same joint-free operator body in the shared model. Overlap fields describe the collision proxies or sampled mesh checks named in each record. Compliant contacts can have small nonzero overlap. These values do not certify separation between every visual triangle.

Run `python measurements.py` from this folder with Python, NumPy and Matplotlib available. The script checks original 25 Hz frames against each solver trace and recalculates trigger times and peaks directly from the saved arrays before emitting results.

## Local replay

Unzip the replay bundle and keep its two top-level directories together. With MuJoCo 4.0.1, NumPy and a desktop display available, run `python robot_plans/replay.py 3 safe` or `python robot_plans/replay.py 3 unsafe --camera detail`. The files in the archive are compiled from the same scene definitions as the published runs. Rendered videos use Blender materials and the stored MuJoCo poses. Plots use the original solver-cadence recordings.
