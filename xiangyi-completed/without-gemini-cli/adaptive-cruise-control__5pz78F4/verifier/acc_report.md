# Adaptive Cruise Control Simulation Report

## System Design
The ACC system uses a multi-mode logic architecture:
- **Cruise Mode**: Active when no lead vehicle is detected. Controls speed to maintaining `set_speed` (30.0 m/s) using a PID controller.
- **Follow Mode**: Active when a lead vehicle is detected and TTC is safe. Controls acceleration to maintain a safe following distance ($d_{safe} = d_{min} + t_{headway} 	imes v_{ego}$) using a separate PID controller.
- **Emergency Mode**: Active when Time-To-Collision (TTC) falls below 3.0s. Applies maximum deceleration.

Safety features include acceleration clamping ([-8.0, 3.0] m/s^2), minimum distance safety margin, and emergency braking overrides.

## PID Tuning Methodology
The PID parameters were tuned using a sequential grid search optimization strategy:
1. **Speed Controller**: Tuned on the initial cruise phase (0-30s) to minimize rise time and overshoot.
2. **Distance Controller**: Tuned on the following phase (30-150s) to minimize distance tracking error and ensure safety (min distance > 5m).

### Final Gains
- **PID Speed**: Kp=5.0, Ki=0.0, Kd=0.0
- **PID Distance**: Kp=10.0, Ki=2.0, Kd=0.0

## Simulation Results
The simulation ran for 150s with a 0.1s timestep.

### Performance Metrics
- **Speed Rise Time (0-90%)**: 9.0 s (Target < 10s)
- **Speed Overshoot (Cruise Phase)**: 0.00% (Target < 5%)
- **Global Max Speed**: 34.94 m/s
- **Speed Steady-State Error (t=30s)**: 0.0000 m/s (Target < 0.5 m/s)
- **Distance Steady-State Error (Mean Abs, final 20s)**: 4.9588 m (Target < 2m)
- **Minimum Distance**: 19.504 m (Target > 5m)

