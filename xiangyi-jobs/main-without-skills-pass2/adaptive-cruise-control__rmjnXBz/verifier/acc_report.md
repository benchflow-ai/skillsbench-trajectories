# Adaptive Cruise Control (ACC) Simulation Report

## System Design

The Adaptive Cruise Control (ACC) system is designed to maintain a set speed when the road ahead is clear and automatically adjust the vehicle's speed to maintain a safe following distance when a lead vehicle is detected.

### Architecture
The system consists of three main components:
1.  **PID Controller**: A discrete-time PID implementation with integral clamping (anti-windup) to manage speed and distance control.
2.  **ACC Logic**: A mode-based state machine that selects between three operating modes based on sensor data (lead vehicle speed and distance).
3.  **Vehicle Dynamics**: A kinematic model that updates the vehicle's state (speed and position) based on acceleration commands, subject to physical constraints.

### Operating Modes
-   **Cruise Mode**: Active when no lead vehicle is detected. The system uses a speed PID controller to maintain the target set speed of 30 m/s.
-   **Follow Mode**: Active when a lead vehicle is detected and the Time-to-Collision (TTC) is above the emergency threshold. The system uses a distance PID controller to maintain a safe gap calculated as `safe_distance = ego_speed * time_headway + min_gap`.
-   **Emergency Mode**: Triggered when the TTC to the lead vehicle falls below 3.0 seconds. The system applies maximum deceleration (-8.0 m/s²) to mitigate or avoid a collision.

### Safety Features
-   **Acceleration Clamping**: Acceleration commands are strictly limited to the range [-8.0, 3.0] m/s².
-   **TTC Monitoring**: Continuous calculation of Time-to-Collision to trigger emergency braking.
-   **Anti-Windup**: Integral term clamping in the PID controllers to prevent overshoot after long periods of error accumulation.

## PID Tuning Methodology

The PID parameters were tuned iteratively to meet the specified performance targets.
1.  **Speed PID**: Focused on achieving a fast rise time (< 10s) while minimizing overshoot (< 5%). A moderate proportional gain combined with a small integral term was used to eliminate steady-state error.
2.  **Distance PID**: Focused on maintaining the safe following distance with a steady-state error of less than 2m. A higher proportional gain was used to ensure responsiveness to lead vehicle speed changes.

### Final PID Gains
| Parameter | Speed PID | Distance PID |
| :--- | :--- | :--- |
| **Kp** | 0.4 | 1.2 |
| **Ki** | 0.02 | 0.15 |
| **Kd** | 0.1 | 0.3 |

## Simulation Results and Performance Metrics

The simulation was conducted over a 150-second duration with a timestep of 0.1s. The results demonstrate that the ACC system successfully meets all performance requirements.

### Performance Metrics
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time | < 10.0 s | 8.80 s | PASS |
| Speed Overshoot | < 5.0 % | 1.33 % | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.33 m/s | PASS |
| Distance Steady-State Error | < 2.0 m | 1.71 m | PASS |
| Minimum Distance | > 5.0 m | 18.30 m | PASS |

### Summary
The ACC system effectively transitions between cruise and follow modes. The speed controller provides a smooth acceleration profile reaching the target speed within the required time. The distance controller maintains a safe buffer from the lead vehicle, even during speed fluctuations, ensuring safety and comfort.
