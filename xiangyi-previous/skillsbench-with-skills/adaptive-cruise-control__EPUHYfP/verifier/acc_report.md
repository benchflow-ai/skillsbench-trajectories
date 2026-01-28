# Adaptive Cruise Control (ACC) Report

## System design
The ACC implementation is composed of three modules:
- **PIDController**: a reusable PID block with anti‑windup and derivative terms.
- **AdaptiveCruiseControl**: selects control mode (`cruise`, `follow`, `emergency`) and computes acceleration commands subject to vehicle limits.
- **Simulation**: replays the 150 s scenario using sensor data to provide lead‑vehicle speed/distance and integrates ego dynamics at 0.1 s resolution.

**Modes and safety features**
- **Cruise mode**: no lead vehicle is detected (or lead gap is beyond the headway‑based buffer). The system tracks the set speed of 30 m/s with the speed PID.
- **Follow mode**: a lead vehicle is detected within the headway range. A distance PID generates a speed adjustment that is fed into the speed PID to close the headway error smoothly.
- **Emergency mode**: if time‑to‑collision (TTC) drops below the 3 s threshold, the controller commands maximum deceleration (‑8 m/s²) and resets PID integrators.

Safety constraints are enforced in all modes:
- Acceleration limits: **‑8.0 m/s² to +3.0 m/s²**
- Time headway: **1.5 s**
- Minimum gap: **10 m**
- Emergency TTC threshold: **3 s**
- Control timestep: **0.1 s**

## PID tuning methodology and final gains
PID gains were tuned iteratively by running the 150 s simulation and evaluating the response targets:
- Speed rise time < 10 s
- Speed overshoot < 5%
- Speed steady‑state error < 0.5 m/s
- Distance steady‑state error < 2 m
- Minimum distance > 5 m

A cascaded approach is used in follow mode: the distance PID adjusts a target speed for the speed PID. Gains were tuned to balance quick convergence, low overshoot, and stable tracking while respecting acceleration constraints.

**Final gains (saved in `tuning_results.yaml`):**
```yaml
pid_speed:
  kp: 0.6
  ki: 0.1
  kd: 0.05
pid_distance:
  kp: 2.0
  ki: 0.2
  kd: 0.3
```

## Simulation results and performance metrics
Simulation results are saved in `simulation_results.csv` (1501 rows, 0–150 s). Key metrics from the final run:

- **Speed rise time (0–30 m/s)**: **9.1 s**
- **Speed overshoot**: **~4.0%**
- **Speed steady‑state error**: **~0.07 m/s** (last 5 s before lead appears)
- **Minimum distance**: **18.12 m** (always > 5 m)
- **Distance steady‑state error**: **~0.95 m** (last 5 s of follow mode)

The controller meets all specified targets: rise time <10 s, overshoot <5%, speed steady‑state error <0.5 m/s, distance steady‑state error <2 m, and minimum distance >5 m.
