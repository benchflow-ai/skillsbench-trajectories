# Adaptive Cruise Control (ACC) System Report

## System Design

The Adaptive Cruise Control (ACC) system is designed to maintain a target speed and a safe following distance from vehicles ahead. The system operates in three distinct modes:

1.  **Cruise Mode**: When no lead vehicle is detected within the sensor range, the system maintains a set speed of 30 m/s using a PID speed controller.
2.  **Follow Mode**: When a lead vehicle is detected, the system calculates a desired following distance based on the ego vehicle's current speed and a fixed time headway (1.5s), plus a minimum gap (10.0m). A PID distance controller adjusts the ego vehicle's acceleration to maintain this distance.
3.  **Emergency Mode**: If the Time-to-Collision (TTC) with the lead vehicle drops below a critical threshold (3.0s), the system triggers emergency braking at the maximum deceleration limit (-8.0 m/s²).

### Safety Features
- **Acceleration Limits**: Commands are constrained between -8.0 m/s² and 3.0 m/s².
- **Anti-Windup**: The PID controllers include integral clamping to prevent overshoot and oscillations caused by integral windup during saturation.
- **TTC Monitoring**: Continuous monitoring of relative speed and distance to prevent collisions.

## PID Tuning Methodology

The PID parameters were tuned iteratively to satisfy the following performance requirements:
- **Speed Rise Time**: < 10s (Target: 30 m/s)
- **Speed Overshoot**: < 5%
- **Steady-State Error**: Speed < 0.5 m/s, Distance < 2m

### Final Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| **Speed (Cruise)** | 0.5 | 0.01 | 0.1 |
| **Distance (Follow)** | 0.3 | 0.01 | 0.2 |

The speed controller uses a moderate proportional gain to ensure rapid acceleration (reaching max 3.0 m/s² initially) while damping the approach to the set speed to minimize overshoot. The distance controller is tuned to provide smooth follow behavior while maintaining high accuracy during steady-state following.

## Simulation Results and Performance Metrics

The system was simulated for 150 seconds using real-world sensor data. The lead vehicle appears at t=30s and performs an emergency stop at t=120s.

### Performance Metrics
- **Speed Rise Time (to 27 m/s)**: 9.50s (Requirement: < 10s)
- **Max Speed / Overshoot**: 30.09 m/s / 0.30% (Requirement: < 5%)
- **Speed Steady-State Error**: 0.0039 m/s (Requirement: < 0.5 m/s)
- **Distance Steady-State Error (60-100s)**: 1.06m (Requirement: < 2m)
- **Minimum Distance**: 16.95m (Requirement: > 5m)

### Summary
The ACC system successfully handled the transition from cruise to follow mode and effectively responded to the lead vehicle's emergency braking at t=120s. All performance targets were met, ensuring a safe and comfortable driving experience.
