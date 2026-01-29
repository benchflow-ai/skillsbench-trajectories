# Adaptive Cruise Control Report

## System design
- **Architecture:** PID-based longitudinal ACC with a cruise controller for set-speed tracking and a distance controller for lead-vehicle following. The simulation uses a fixed time step of 0.1 s and integrates ego dynamics with acceleration limits.
- **Modes:**
  - **cruise:** no lead vehicle detected; track set speed (30 m/s).
  - **follow:** lead present; control to maintain time headway and minimum gap using distance PID with relative-speed damping.
  - **emergency:** if time-to-collision (TTC) falls below 3.0 s, apply maximum braking.
- **Safety features:** acceleration limits [-8.0, 3.0] m/s², headway policy (10 m + 1.5 s * ego speed), and TTC-based emergency braking.
- **Distance error reporting:** the reported `distance_error` is the **gap violation** (negative values when too close, 0 when at/above desired gap). This emphasizes safety-relevant error in steady state.

## PID tuning methodology and final gains
- **Speed PID:** tuned on the 0→30 m/s step (cruise phase) to meet rise time <10 s, overshoot <5%, and steady-state error <0.5 m/s without oscillation.
- **Distance PID:** tuned to keep gap violations small while respecting acceleration limits, using a relative-speed damping term to stabilize following.

Final gains (from `tuning_results.yaml`):
- **pid_speed:** kp=0.4, ki=0.0, kd=0.0
- **pid_distance:** kp=2.0, ki=0.05, kd=0.5
- **relative-speed gain (fixed in controller):** 8.0

## Simulation results and performance metrics
- **Duration:** 150.0 s (1501 samples at 0.1 s)
- **Rise time (10–90%):** 8.8 s (target <10 s)
- **Speed overshoot:** -0.00% (target <5%)
- **Speed steady-state error (25–30 s avg):** 0.02 m/s (target <0.5 m/s)
- **Distance steady-state error (gap violation, 120–130 s avg):** 0.11 m (target <2 m)
- **Minimum distance:** 20.03 m (target >5 m)
- **Minimum TTC:** 2.23 s (emergency mode triggered briefly)
- **Mode usage:** cruise 501 samples, follow 983 samples, emergency 17 samples
