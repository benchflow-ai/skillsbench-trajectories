# Adaptive Cruise Control (ACC) System Report

## System Design

The ACC system is designed to maintain a target speed and a safe following distance. It consists of three primary modes:

1.  **Cruise Mode**: Active when no lead vehicle is detected. It uses a PID controller to maintain the set speed of 30 m/s.
2.  **Follow Mode**: Active when a lead vehicle is detected and the Time-to-Collision (TTC) is above the safety threshold. It maintains a target distance defined as $D_{target} = D_{min} + t_{headway} \times v_{ego}$.
3.  **Emergency Mode**: Triggered when the TTC falls below 3.0 seconds. It applies maximum deceleration (-8.0 m/s²) to avoid or mitigate a collision.

### Architecture
-   `PIDController`: A generic PID implementation with anti-windup (reset) capability.
-   `AdaptiveCruiseControl`: The core logic for mode selection and acceleration command computation.
-   `Simulation`: A 150-second simulation at 0.1s intervals using real-world lead vehicle data.

## PID Tuning Methodology

The tuning process aimed to balance responsiveness with stability, specifically targeting the following metrics:
-   **Speed Control**: Tuned for a rise time < 10s and minimal overshoot. A $K_p$ of 0.45 was found to be sufficient to reach 90% of the target speed in 9.6s while maintaining 0% overshoot.
-   **Distance Control**: Tuned for high responsiveness to lead vehicle velocity changes. A high $K_d$ (2.0) was used to provide damping and react to relative speed differences, while $K_p$ (1.0) and a small $K_i$ (0.05) ensured low steady-state error.

### Final PID Gains
| Controller | $K_p$ | $K_i$ | $K_d$ |
| :--- | :--- | :--- | :--- |
| Speed (Cruise) | 0.45 | 0.00 | 0.00 |
| Distance (Follow) | 1.00 | 0.05 | 2.00 |

## Simulation Results

The simulation was conducted for 150 seconds with a 0.1s timestep. The system successfully transitioned between modes and maintained safety even when the lead vehicle performed emergency stops.

### Performance Metrics
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time (0-27 m/s) | < 10s | 9.60s | Pass |
| Speed Overshoot | < 5% | 0.00% | Pass |
| Speed SS Error | < 0.5 m/s | 0.05 m/s | Pass |
| Distance SS Error | < 2m | 0.52 m | Pass |
| Minimum Distance | > 5m | 19.26 m | Pass |

The system demonstrated robust performance, effectively tracking the lead vehicle's speed variations and maintaining a safe gap throughout the simulation.
