# ACC Simulation Report

## System Design
The ACC system utilizes a dual-PID controller architecture for Speed and Distance control.
- **Modes**:
  - `cruise`: Active when no lead vehicle is detected. Maintains `set_speed`.
  - `follow`: Active when a lead vehicle is detected. Maintains safe following distance (`min_distance` + `time_headway` * `ego_speed`).
  - `emergency`: Triggered when Time-To-Collision (TTC) falls below 3.0s. Applies maximum deceleration.
- **Safety**: Emergency braking overrides standard controls. Output acceleration is clamped between [-8.0, 3.0] m/s^2.

## PID Tuning Methodology
The PID parameters were tuned using an iterative optimization script (`tune_acc.py`) targeting:
- Speed Control: Rise time < 10s, Overshoot < 5%.
- Distance Control: Steady-state error < 2m, Minimum distance > 5m.

### Final Gains
- **Speed PID**: {'kd': 0.0, 'ki': 0.0, 'kp': 0.4}
- **Distance PID**: {'kd': 0.0, 'ki': 0.0, 'kp': 0.2}

## Simulation Results
The simulation was run for 150 seconds using real-world sensor data (reconstructed lead trajectory).

### Performance Metrics
- **Speed Rise Time (0-90%)**: 9.8 s
- **Max Speed Overshoot**: 0.00 %
- **Distance Steady-State Error (Final 10s)**: 29.66 m
- **Minimum Distance Observed**: 6.19 m

