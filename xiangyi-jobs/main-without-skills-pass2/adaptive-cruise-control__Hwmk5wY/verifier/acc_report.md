# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### Architecture
The ACC system is designed as a modular control architecture comprising:
- **PID Controller (`pid_controller.py`):** A standard Proportional-Integral-Derivative controller with integral windup protection (clamping) and reset capability.
- **ACC Logic (`acc_system.py`):** The core decision-making unit that implements the ISO 15622-style Min-Select strategy. It calculates two candidate acceleration commands:
    1.  **Cruise Command:** To maintain the set speed (30 m/s).
    2.  **Follow Command:** To maintain a safe time-gap (1.5s) and minimum distance (10m) from the lead vehicle.
    The final command is the minimum of the two (algebraic minimum), ensuring the vehicle never exceeds the set speed while maintaining safety.
- **Simulation Environment (`simulation.py`):** A discrete-time simulator (dt=0.1s) that integrates the vehicle physics and injects lead vehicle data from real-world sensor logs (`sensor_data.csv`). It handles the relative positioning of the lead vehicle by initializing its position upon detection relative to the ego vehicle's current state.

### Modes
1.  **Cruise Mode:** Active when no lead vehicle is detected or when the lead vehicle is far/fast enough that the cruise command is lower (more restrictive) than the follow command.
2.  **Follow Mode:** Active when a lead vehicle is detected and the required braking/coasting to maintain distance results in a lower acceleration command than the cruise command.
3.  **Emergency Mode:** Active when the Time-To-Collision (TTC) drops below 3.0 seconds. Overrides all other logic to apply maximum deceleration (-8.0 m/s^2).

### Safety Features
- **Min-Select Strategy:** Inherently prevents overspeeding even if the lead vehicle exceeds the set limit.
- **Emergency Braking:** Independent check on TTC triggers max braking.
- **Output Clamping:** Acceleration commands are strictly limited to vehicle capabilities [-8.0, 3.0] m/s^2.
- **Integral Anti-Windup:** PID integrators are clamped to [-100, 100] to prevent runway acceleration requests, and unused controllers are reset to prevent state drift.

## 2. PID Tuning Methodology

The PID parameters were tuned iteratively to meet the stringent performance requirements:
- **Rise Time < 10s:** Required a sufficiently high Kp for the speed controller.
- **Overshoot < 5%:** Required eliminating the Integral term (Ki=0) for the speed controller (as the plant is a Type 1 system) and adding Derivative (Kd) damping.
- **Collision Avoidance:** Required a responsive Distance controller.

### Final Gains
The tuning results saved in `tuning_results.yaml` are:

**PID Speed:**
- `kp`: 0.6 (Ensures rapid acceleration to reach 30m/s in < 10s)
- `ki`: 0.0 (Eliminates overshoot and integral windup during saturation)
- `kd`: 0.5 (Provides damping to reduce oscillation near setpoint)

**PID Distance:**
- `kp`: 0.6 (Balanced response to distance errors)
- `ki`: 0.005 (Small integral action to eliminate steady-state distance errors)
- `kd`: 0.6 (Damping for closing rate)

## 3. Simulation Results

The simulation was run for 150 seconds using the provided sensor data.

### Performance Metrics
- **Speed Rise Time (0 to 27 m/s):** 9.8s (Target: < 10s) - *PASSED*
- **Speed Overshoot:** 0.00% (Target: < 5%) - *PASSED*
- **Speed Steady-State Error:** < 0.5 m/s - *PASSED*
- **Distance Steady-State Error:** 0.00 m (Target: < 2m) - *PASSED*
- **Minimum Distance:** 15.96 m (Target: > 5m) - *PASSED*
- **Control Duration:** 150s - *COMPLETED*

### Behavior Analysis
- **0-30s:** The vehicle accelerates smoothly to 30 m/s, reaching the target just under 10 seconds with no overshoot.
- **30s:** The lead vehicle is detected. The system correctly identifies the gap and switches to 'Follow' mode when necessary.
- **90s:** The lead vehicle accelerates significantly (up to ~37 m/s). The system correctly switches back to 'Cruise' mode (limited to 30 m/s) instead of chasing the lead vehicle, demonstrating the effectiveness of the Min-Select strategy.
- **Braking:** The vehicle maintains a safe distance throughout, with the minimum distance never dropping below the safety critical threshold.
