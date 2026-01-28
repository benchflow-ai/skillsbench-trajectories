# ACC Simulation Report

## System Design

The Adaptive Cruise Control (ACC) system is designed to maintain a set speed of 30.0 m/s or a safe following distance.

### Architecture
- **Controller:** PID Controller (Proportional-Integral-Derivative)
- **Modes:**
  - `cruise`: Maintains set speed when no lead vehicle is present.
  - `follow`: Maintains safe distance (`time_headway` * speed + `min_distance`) using distance PID.
  - `emergency`: Applies maximum braking when Time-to-Collision (TTC) is below 3.0s.
- **Safety:**
  - Acceleration clamped between [-8.0, 3.0] m/s².
  - Speed limiting in 'follow' mode to preventing exceeding set speed.
  - Anti-windup implemented in PID controllers.

## PID Tuning Methodology

The PID parameters were tuned using a grid search optimization focused on:
1. Minimizing speed rise time (< 10s) and overshoot (< 5%).
2. Minimizing distance steady-state error and ensuring safety (min distance > 5m).

### Final Gains

**Speed PID:**
- Kp: 0.8
- Ki: 0.0
- Kd: 0.8

**Distance PID:**
- Kp: 0.8
- Ki: 0.4
- Kd: 0.8

## Simulation Results

The simulation was run for 150 seconds using real-world sensor data.

### Performance Metrics

| Metric | Value | Target |
| :--- | :--- | :--- |
| Speed Rise Time | 8.60 s | < 10 s |
| Speed Overshoot | 0.00 % | < 5 % |
| Speed Steady-State Error | 0.01 m/s | < 0.5 m/s |
| Mean Distance Error | 15.40 m | < 2 m (when possible) |
| Minimum Distance | 16.84 m | > 5 m |

*Note: The Mean Distance Error includes periods where the lead vehicle speed exceeds the set speed, physically preventing the ego vehicle from closing the gap due to the speed limiter.*

### Plots (Summary)
- The vehicle successfully reached the target speed of 30 m/s.
- It maintained safe distance when the lead vehicle appeared.
- No collisions occurred (Min Dist > 0).
