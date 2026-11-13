# Real-world calibration


No real measurements are invented. Until supplied, outputs say **uncalibrated**.
Collect separate calibration and held-out trials with object mass (scale),
table/cup dimensions (ruler), release pose/edge distance (calibrated camera),
contact response and spilled volume (mass difference divided by liquid density).
Record uncertainty, source video, instruments and dates. Use bench-top objects
and catch trays; no patient or injury experiment is necessary.

`calibration.py` accepts a JSON array with `trial` (relative run directory),
`quantity`, `value`, `unit`, `measurement_source`, `measured_at` and `instrument`.
Allowed quantities/units are defined in `QUANTITIES`. Empty input remains
awaiting measurements. The tool reports signed/absolute error and never marks
the system calibrated just because observations were uploaded. Parameter fitting,
frozen parameter versioning and held-out validation are subsequent empirical work.
