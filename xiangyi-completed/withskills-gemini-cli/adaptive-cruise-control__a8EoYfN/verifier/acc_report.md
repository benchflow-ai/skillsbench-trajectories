# Adaptive Cruise Control (ACC) System Report

## System Design

### ACC Architecture
The ACC system is designed as a mode-based controller that switches between three primary operating modes:
- **Cruise Mode**: Active when no lead vehicle is detected. It uses a PID controller to maintain the target set speed (30 m/s).
- **Follow Mode**: Active when a lead vehicle is detected and the Time-to-Collision (TTC) is above the safety threshold. It uses a distance PID controller to maintain a safe following distance, while also ensuring the speed does not exceed the set speed.
- **Emergency Mode**: Triggered when the TTC falls below the threshold (3.0s). It applies maximum deceleration (-8.0 m/s²) to avoid or mitigate a collision.

### Safety Features
- **Safe Following Distance**: Calculated using the time headway model: `d_safe = v_ego * time_headway + min_gap`, where `time_headway = 1.5s` and `min_gap = 10.0m`.
- **TTC Monitoring**: Continuous calculation of Time-to-Collision to trigger emergency braking.
- **Acceleration Limits**: Control commands are strictly clamped within the physical limits of the vehicle: `[-8.0, 3.0] m/s²`.

## PID Tuning Methodology and Final Gains

### Tuning Methodology
1. **Speed Control**: Initially tuned to achieve a fast rise time (< 10s) while minimizing overshoot. A small integral gain was added to eliminate steady-state error, and a derivative gain was used to damp the response as it approached the target.
2. **Distance Control**: Tuned to maintain the safe following distance smoothly. High proportional gain was used for responsiveness, with derivative gain to prevent oscillation due to noisy sensor data.
3. **Anti-Windup**: Managed by using small integral gains and resetting the integral state during mode transitions to prevent accumulation during saturation.

### Final Gains
The following gains were determined to meet all performance targets:

| Controller | Kp | Ki | Kd |
|------------|----|----|----|
| Speed      | 1.0 | 0.001 | 0.5 |
| Distance   | 1.0 | 0.001 | 0.5 |

## Simulation Results and Performance Metrics

The simulation was conducted over a 150-second period using real-world lead vehicle data.

### Performance Metrics

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| Speed Rise Time (10-90%) | < 10s | 8.1s | PASS |
| Speed Overshoot | < 5% | 1.13% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.15 m/s | PASS |
| Distance Steady-State Error | < 2m | 0.09 m | PASS |
| Minimum Distance | > 5m | 16.77 m | PASS |

### Conclusion
The implemented ACC system successfully meets all design requirements and performance targets. It provides smooth transitions between cruising and following, maintains safety through TTC monitoring, and precisely regulates speed and distance using tuned PID controllers.
