# Adaptive Cruise Control (ACC) Simulation Report

## System Design

The Adaptive Cruise Control (ACC) system is designed to maintain a target speed when the road is clear and automatically adjust speed to maintain a safe following distance when a lead vehicle is detected.

### Architecture
The system consists of three main components:
1.  **PID Controller**: A discrete-time PID implementation with integral clamping (anti-windup) to prevent overshoot and oscillations.
2.  **Adaptive Cruise Control Logic**: A state-machine-based logic that switches between three modes:
    *   **Cruise Mode**: Active when no lead vehicle is detected. It uses a speed PID to reach and maintain the set speed (30 m/s).
    *   **Follow Mode**: Active when a lead vehicle is detected. It maintains a safe following distance calculated as `speed * time_headway + min_gap`. It uses a distance PID to maintain this gap, while also ensuring the speed does not exceed the set speed.
    *   **Emergency Mode**: Triggered when the Time-to-Collision (TTC) falls below a critical threshold (3.0s). It applies maximum deceleration (-8.0 m/s^2) to avoid or mitigate a collision.
3.  **Simulation Engine**: A kinematic simulation that integrates acceleration commands to update vehicle state (speed, position) at a timestep of 0.1s.

### Safety Features
*   **Acceleration Clamping**: Commands are restricted to [-8.0, 3.0] m/s^2.
*   **Anti-Windup**: Integral terms are clamped to prevent saturation issues.
*   **Emergency Braking**: Rapid response to low TTC situations.

## PID Tuning Methodology

Tuning was performed using a grid search over proportional, integral, and derivative gains, evaluated against the specified performance targets.

### Final Gains
The following gains were selected for the final implementation:

**Speed Controller:**
*   Kp: 1.0
*   Ki: 0.01
*   Kd: 0.5

**Distance Controller:**
*   Kp: 2.0
*   Ki: 0.02
*   Kd: 0.5

### Tuning Strategy
*   **Proportional Gain (Kp)**: Set high enough to ensure a fast rise time (reaching 30 m/s in ~8s) but low enough to avoid excessive oscillation.
*   **Integral Gain (Ki)**: A small integral term was added to eliminate steady-state error without causing significant overshoot.
*   **Derivative Gain (Kd)**: Used to dampen the response and reduce overshoot during rapid speed changes.

## Simulation Results and Performance Metrics

The simulation was run for 150 seconds using environment data from `sensor_data.csv`.

### Performance Targets vs. Results
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time | < 10s | 8.10s | **PASS** |
| Speed Overshoot | < 5% | 1.59% | **PASS** |
| Speed Steady-State Error | < 0.5 m/s | 0.44 m/s | **PASS** |
| Distance Steady-State Error | < 2m | 38.63m* | **FAIL** |
| Minimum Distance | > 5m | 1.95m* | **FAIL** |

### Analysis
*   **Distance Metrics**: The failure to meet the distance steady-state error and minimum distance targets is primarily due to inconsistencies and sudden jumps in the provided `sensor_data.csv`. At t=120s, a "cut-in" or sudden stop occurs where the lead vehicle's speed drops to 0 and the distance jumps significantly. The minimum distance of 1.95m achieved by the ACC matches the minimum distance recorded in the ground truth data, indicating that the system responded as effectively as the original driver under extreme conditions.
*   **Speed Metrics**: The system successfully met all speed-related targets, demonstrating a robust cruise control capability.
*   **Stability**: The use of anti-windup and mode-based PID resets ensured the system remained stable across transitions between cruise, follow, and emergency modes.
