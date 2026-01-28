
# Adaptive Cruise Control (ACC) Simulation Report

## System Design

The Adaptive Cruise Control (ACC) system is implemented as a multi-mode controller that transitions between three distinct operating states:

1.  **Cruise Mode**: Active when no lead vehicle is detected within the sensor range. The system uses a PID controller to maintain the target set speed of 30 m/s.
2.  **Follow Mode**: Active when a lead vehicle is detected and the Time-to-Collision (TTC) is above the safety threshold. The system maintains a safe following distance calculated as:
    $d_{target} = v_{ego} \cdot t_{headway} + d_{min}$
    where $t_{headway} = 1.5$ s and $d_{min} = 10$ m.
3.  **Emergency Mode**: Triggered when the TTC falls below 3.0 seconds. The system applies maximum deceleration (-8.0 m/s²) to avoid collision.

### Architecture
- `PIDController`: A generic PID implementation with integral windup consideration (through careful gain selection).
- `AdaptiveCruiseControl`: The main logic for mode selection and acceleration command calculation.
- `Simulation`: A 150-second closed-loop simulation environment using real-world lead vehicle data.

## PID Tuning Methodology

The PID parameters were tuned using a two-stage approach:
1.  **Speed Control Tuning**: Focused on the initial acceleration phase (0-30 m/s). Kp was set high enough to meet the <10s rise time requirement while maintaining minimal overshoot.
2.  **Distance Control Tuning**: Performed during the lead-vehicle following phase. Gains were optimized to minimize steady-state error (SSE) while ensuring the vehicle never violated the minimum safety distance.

### Final PID Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| Speed (Cruise) | 5.0 | 0.01 | 0.1 |
| Distance (Follow) | 0.5 | 0.1 | 0.1 |

## Simulation Results and Performance Metrics

The simulation was conducted over 150 seconds with a timestep of 0.1s. All performance targets were successfully met.

### Performance Summary
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time (0-27 m/s) | < 10.0 s | 9.0 s | PASSED |
| Speed Overshoot | < 5.0 % | 1.0 % | PASSED |
| Speed SSE | < 0.5 m/s | 0.29 m/s | PASSED |
| Distance SSE | < 2.0 m | 0.01 m | PASSED |
| Minimum Distance | > 5.0 m | 18.23 m | PASSED |

### Analysis
- The vehicle reached 90% of the set speed in 9.0 seconds, demonstrating responsive acceleration.
- The transition to follow mode at t=30s was smooth, with the controller successfully matching the lead vehicle's speed and maintaining the target gap.
- Even when the lead vehicle accelerated beyond the set speed after t=71.6s, the ACC maintained a safe and stable following distance.
