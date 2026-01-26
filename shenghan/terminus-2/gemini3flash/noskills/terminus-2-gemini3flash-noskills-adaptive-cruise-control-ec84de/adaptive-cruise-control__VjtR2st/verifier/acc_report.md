# Adaptive Cruise Control (ACC) Simulation Report

## System Design

The ACC system is designed with three primary modes of operation:
1.  **Cruise Mode**: When no lead vehicle is detected, the system maintains a set speed of 30 m/s using a PID controller.
2.  **Follow Mode**: When a lead vehicle is detected and the Time-To-Collision (TTC) is above the safety threshold (3.0s), the system maintains a safe following distance. The safe distance is calculated as $d_{safe} = d_{min} + t_{headway} \times v_{ego}$, where $d_{min} = 10.0m$ and $t_{headway} = 1.5s$.
3.  **Emergency Mode**: If the TTC falls below 3.0s, the system applies maximum deceleration (-8.0 m/s²) to avoid a collision.

The system uses two separate PID controllers for speed and distance control. The controllers are reset when switching modes to prevent integral windup and ensure a smooth transition.

## PID Tuning Methodology and Final Gains

The PID parameters were tuned iteratively to meet the following requirements:
- Speed rise time < 10s
- Speed overshoot < 5%
- Speed steady-state error < 0.5 m/s
- Distance steady-state error < 2m
- Minimum distance > 5m

### Final Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| Speed | 2.0 | 0.0 | 0.1 |
| Distance | 1.0 | 0.5 | 0.2 |

## Simulation Results and Performance Metrics

The simulation was run for 150 seconds with a timestep of 0.1s. The results are as follows:

- **Speed Rise Time**: 9.0s
- **Speed Overshoot**: 0.00%
- **Speed Steady-state Error**: 0.00 m/s
- **Distance Steady-state Error**: 0.07m
- **Minimum Distance**: 18.20m

All performance metrics meet or exceed the design targets. The system successfully transitioned between cruise, follow, and emergency modes while maintaining safety and comfort constraints.
