# neiss_1014 - review of the transfer-v24 local integrations

Reviewer: Claude, commissioned by the user as the Claude Fable 5.2 xhigh review. Basis: the supplied `native_policy.py`, `human.py`, `native_visuals.py`, force-bridge lines 468-505 and 575-621, and the selected samples (7 failed_v26, 7 failed_v30, 10 of the reported 4,801 successful samples). Nothing was executed for this review.

Labels: **checked** = verified here against supplied code or samples; **reported** = integrator statement I cannot verify here; **derived** = my arithmetic on supplied samples; **proposal** = not implemented, not verified.

## Decision

**Accept with disclosed limits.** I found no concrete causal or integration defect that needs an executable correction, so no `policy.py` or `human.py` is returned and no gain, threshold or predicate change is requested.

This accepts one selected deterministic rollout of an uncalibrated engineering model. It is not a robustness proof and not a clinical survival or injury estimate. Still pending and outside this review: the final video audit, the unsafe recording and publication validation.

## Checked and consistent

- **Goal isolation (checked).** `transfer_release` changes only the policy-internal phase, the taper and the existing bounded hand withdrawal. It cannot write the goal. It hands over to `verify` only with the runner-measured `standing` flag, at least `release_s` elapsed, and level and both hand requests at or below 0.5 N. The original 1.0 s zero-request verification then still runs.
- **Timeline (checked, samples).** Entry at about 39.55 s (pelvis 0.926 m, CoM estimate +0.005 m, tilt 47.0 deg, 8.3 N per hand). Request is zero by 40.0 s. Both palm contact flags are false at 41.0-45.45 s. Verify starts at 44.45 s, the action ends at 45.43 s, and the 36.57 s dwell equals 80 - 43.43 s.
- **Unsensed plan untouched (checked).** The wrapper returns the original method before creating any new state when the mode is not `gradual` or posture is absent.
- **Human independence (checked).** `Mannequin.control` reads its own link states, its own foot-floor contact and the once-latched stand cue, and only adds its internal equal/opposite couple. Unlean 0.40-1.0 and the 9 to 6 deg/s factor are module-level and common to both plans. Geometry, masses, joint limits and drive caps are unchanged.
- **Force gate and reaction (checked).** The bridge zeroes each hand force unless contact is under 0.12 s old and the gap is under 0.08 m, clamps to 160 N, and applies -F with its moment about the same chest point to the wrist link. Every supplied sample has nonzero force only with a true gate. The statement for all samples is reported.
- **Signs and latching (checked).** `xc` is CoM minus ankle along feet-to-robot. The guards (`xc < -0.06`, pelvis below start - 0.08 m, speed above 0.35 m/s, 8 s, window end) point the intended way. `_tr_active` and `phase` always change together, and a guard tick passes the same tick to the original support branch.
- **Display retargeting (checked).** It writes only UsdSkel animation values on a prim stripped of physics schemas. The hip shift is the parent rotation transpose applied to [0, 0, dz], where dz is the mean measured-minus-skin ankle height minus its first-update value. Bone lengths and measured rotations are kept. The 4,801-sample identity is reported and is consistent with the code.

## Causal reading of the three runs (derived)

v26 and v30 are identical at 36.0 s; v30 and the final run are identical through 39.0 s. So v26 to v30 isolates the unlean shift, and v30 to final isolates the handoff.

- The unlean shift alone still failed in the same way: palm reference at its press bound, request tip-limited to about 48-49 N per hand against 73-80 N wanted, `posture` retreat by 42 s.
- Whether the unlean shift is necessary once the handoff exists is not shown; there is no ablation.
- v30 ran with a longer window (ended at 90 s), so its budget differed from the current 80 s / 56 s.

Comparable state, different outcome:

| Run | t (s) | Capture point (m) | Palm state | Next sample |
|---|---|---|---|---|
| v30 | 40.5 | -0.026 | at press bound, 20.7 N per hand | lost: -0.10 m at 41.0 s |
| final | 40.0 | -0.029 | zero request, withdrawing | recovered: +0.003 m at 41.0 s |

Capture point is CoM offset plus velocity times sqrt(z/g); the heel edge is at -0.08 m. This supports the diagnosis that the position-controlled palm contact, not a lack of commanded force, destabilised the late rise. It also shows the handoff is not transient-free (CoM velocity +0.03 to -0.065 m/s within 0.45 s) and that the sampled margin is thin.

## Findings (none blocking)

1. **Fallback path unexercised.** No guard fired in the passing run. After a guard the palms restart from up to 5 cm clearance (0.02-0.05 m/s depth recovery), force returns only after gated contact at 30-90 N/s, and it is tip-limited near 49 N per hand. v26 and v30 show that about 48 N per hand did not arrest the backward loss. Treat the handoff as a commit point: the fallback is a bounded resumption, not a demonstrated recovery.
2. **Soft re-arm.** After any guard the phase can re-enter after 0.15 s of renewed eligibility with a fresh 8 s timer. There is no cooldown or attempt count, so the timeout is bounded only by the 56 s window. This is acceptable because eligibility itself needs the CoM over flat feet at low speed, but the README wording should say so.
3. **The dwell is zero-request, not contact-free.** Hand targets freeze when the action ends. The person keeps straightening (rise 0.913 to 1.0; torso +0.037 m and pelvis +0.054 m toward the robot) and at 60 s and 80 s the left palm contact flag and gate are true (gap 0.034 m) with zero commanded and applied force. The passive palm contact load is not in the supplied samples. The CoM sits 0.064 m ahead of the ankle, inside the foot (-0.08 to +0.22 m), so the palm is not geometrically required, but I cannot exclude a contribution. Do not describe the dwell as unsupported or contact-free.
4. **Dwell actuator state.** The internal balance couple sits at its 30 N m cap in pitch. Saturation ticks go 117 (45.45 s), 816 (60 s), 1869 (80 s), about 80 % and 88 % of control ticks in the two intervals. CoM is 3.2 cm ahead of plan, trim -2.5 deg, ankle error 2.4-2.7 deg. Positions repeat to about 1e-6 m between 60 s and 80 s while sampled velocities stay near 0.035 m/s, which is consistent with tick-synchronous chatter of about 0.3 mm, not drift. Standing is positionally stable; no perturbation margin is demonstrated.
5. **`robot_human_contact` stays true at 41.0-45.45 s** while both palm flags are false. Either the metric is latched or a non-palm link touches the person; the record should say which.
6. **Interface abstraction.** The support force is a bilateral pull toward the robot and up, gated by palm proximity; a real open palm on the front of the chest cannot transmit tension. The gate can hold force for 0.12 s plus one control tick after contact ends. The reaction moment is exact only if the wrist state position is the force application reference, which the excerpt does not show.
7. **Fragility and stale text (low).** The wrapper indexes `hp['support_center_m']` directly although `_estimate` tolerates its absence. Lift, boost and instability bookkeeping are not updated during the phase (moot at zero request, recomputed on fallback). Entry margins were narrow here (tilt 47.0 against a bound of 50 deg). The `human.py` docstring still says 30-90 % unlean, the policy header still says 0..18 deg elevation, and the README still cites the 50.45 s diagnostic.
8. **Display limits.** The correction is vertical only and uses the mean of both ankles, so per-foot and horizontal mismatch remain and a single-foot lift or fall will show residuals. The whole skin, including torso and head, moves by the same offset (about 7.5 cm when standing, reported), so the visible palm-chest contact location and head height are not metric. The baseline is latched at the first update. This is render retargeting, not anatomical calibration.

## Proposals (not implemented, not verified, not required for acceptance)

- From the existing full trace, report the minimum `xc`, minimum capture point, maximum speed and pelvis-drop margin over 39.55-44.45 s, and the palm-torso contact impulse over 45.43-80 s.
- Offline fault injection of each guard (drop, backward CoM, overspeed, timeout, window end), and an ablation of the handoff with the old 0.30/0.90 unlean.
- Log `ankle_alignment_offset_m` per frame with the capture timestamps.
- Correct the stale text in finding 7 and state findings 1-4 in the published README.
- Only if a contact-free dwell is ever to be claimed: a separately recorded revision could keep the bounded release-clearance following after the action ends. That changes post-action behaviour and is not proposed for this run.
