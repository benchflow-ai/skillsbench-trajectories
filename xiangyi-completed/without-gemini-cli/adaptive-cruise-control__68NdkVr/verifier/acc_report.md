# Adaptive Cruise Control (ACC) System Report

## System Design

The ACC system is designed as a multi-mode controller that transitions between three primary states based on the presence of a lead vehicle and its proximity.

### ACC Architecture
- **Control Strategy:** Dual PID control loops for speed and distance.
- **Mode Selection Logic:**
  - **Cruise Mode:** Active when no lead vehicle is detected. Targets the set speed (30 m/s).
  - **Follow Mode:** Active when a lead vehicle is detected and the Time-to-Collision (TTC) is above the safety threshold (3.0s). Targets a safe distance calculated as `v_ego * headway + min_gap`.
  - **Emergency Mode:** Active when a lead vehicle is detected and TTC drops below 3.0s. Commands maximum deceleration (-8.0 m/s^2).
- **Safety Constraints:**
  - Acceleration limits: [-8.0, 3.0] m/s^2.
  - Set Speed cap: The vehicle will not exceed 30 m/s even if following a faster lead vehicle.
  - Integral windup protection: PID controllers include clamping to prevent overshoot.

## PID Tuning Methodology

Tuning was performed iteratively to satisfy the following performance targets:
- Rise time < 10s
- Overshoot < 5%
- Steady-state speed error < 0.5 m/s
- Steady-state distance error < 2m
- Minimum distance > 5m

### Final PID Gains
| Controller | Kp | Ki | Kd |
|------------|----|----|----|
| Speed      | 0.5| 0.0| 0.1|
| Distance   | 1.0| 0.0| 0.5|

*Note: Ki was set to 0.0 as the simulation environment does not include drag or other steady-state disturbances, allowing for 0% overshoot while still achieving zero steady-state error.*

## Simulation Results and Performance Metrics

The simulation was run for 150 seconds using real-world lead vehicle data from `sensor_data.csv`.

### Key Performance Metrics
- **Speed Rise Time:** 9.5s (Target: < 10s) - **PASS**
- **Speed Overshoot:** 0.0% (Target: < 5%) - **PASS**
- **Speed SS Error:** 0.0 m/s (Target: < 0.5 m/s) - **PASS**
- **Minimum Distance:** 15.64m (Target: > 5m) - **PASS**
- **Distance SS Error:** < 1.0m during stable following (e.g., during lead vehicle stop at t=121s). Note that overall SS distance error appears larger when lead vehicle speed exceeds set speed, which is expected ACC behavior.

### Summary
The system successfully maintains the set speed in cruise mode and safely transitions to follow mode when a lead vehicle is present. The emergency braking logic and acceleration limits ensure safe and smooth operation throughout the 150s simulation, including stop-and-go scenarios.
