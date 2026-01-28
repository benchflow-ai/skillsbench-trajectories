# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### Architecture
The ACC system is designed as a hierarchical controller:
1.  **Sensor Interface**: Processes lead vehicle data (speed, distance) from `sensor_data.csv`.
2.  **State Machine**: Determines the operating mode (`cruise`, `follow`, `emergency`) based on sensor inputs and time-to-collision (TTC).
3.  **Control Loop**:
    *   Calculates `accel_cruise` using a PID controller targeting `set_speed`.
    *   Calculates `accel_follow` using a PID controller targeting `desired_distance` (Constant Time Headway policy).
    *   **Arbitration**: Selects the minimum acceleration (`min(accel_cruise, accel_follow)`) to ensure the vehicle never exceeds the set speed, while maintaining safety.
    *   **Safety Override**: If TTC < `emergency_threshold`, triggers max deceleration.

### Modes
*   **Cruise**: Active when no lead vehicle is detected or when the lead vehicle is faster/farther than the set speed allows. Maintains `set_speed` (30 m/s).
*   **Follow**: Active when a lead vehicle is slower or closer than the cruise setting requires. Maintains `desired_distance = min_distance + time_headway * ego_speed`.
*   **Emergency**: Active when `TTC < 3.0s` and closing speed is positive. Applies maximum braking (`-8.0 m/s^2`).

## 2. PID Tuning Methodology

A grid search approach was used to tune the PID parameters for both Speed and Distance controllers.
*   **Speed Controller**: Tuned on a step response from 0 to 30 m/s. 
    *   Metric: Minimized rise time (<10s) and overshoot (<5%).
    *   Result: `Kp=2.0, Ki=0.0, Kd=0.0`. (High proportional gain for fast rise, no integral needed as drag was handled by the plant implicitly/ideally).
*   **Distance Controller**: Tuned on a synthetic following scenario.
    *   Metric: Minimized steady-state distance error and prevented safety violations (distance < 5m).
    *   Result: `Kp=1.0, Ki=0.0, Kd=0.5`. (Balanced response with damping `Kd` to reduce oscillations).

### Final Gains
```yaml
pid_speed:
  kp: 2.0
  ki: 0.0
  kd: 0.0

pid_distance:
  kp: 1.0
  ki: 0.0
  kd: 0.5
```

## 3. Simulation Results

The simulation was run for 150s using real-world sensor data.

### Performance Metrics
*   **Speed Rise Time (0-27 m/s)**: 9.0 s (Target: < 10s) - *PASSED*
*   **Speed Overshoot**: 0.00% (Target: < 5%) - *PASSED*
    *   Achieved by using the `min(cruise, follow)` logic, preventing the ego vehicle from chasing a speeding lead vehicle above the set limit.
*   **Minimum Following Distance**: 17.20 m (Target: > 5m) - *PASSED*
*   **Mean Distance Error (Steady State)**: 0.97 m (Target: < 2m) - *PASSED*
*   **Control Duration**: 150s - *Completed*

### Analysis
The system successfully navigated the scenario. The ego vehicle accelerated smoothly to 30 m/s. Upon detecting the lead vehicle (t=30s), it transitioned to 'follow' mode seamlessly. The improved simulation logic ensured correct relative positioning, and the ISO-style arbitration logic prevented dangerous overspeeding while maintaining a safe gap.
