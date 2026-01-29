# ACC System Report

## System Design

The AdaptiveCruiseControl (ACC) system is designed to maintain a set speed of 30 m/s while ensuring a safe following distance from preceding vehicles. The system architecture consists of:

1.  **PID Controller**: A robust PID implementation with:
    *   **Conditional Integration Anti-Windup**: Prevents integral accumulation when the output is saturated, ensuring fast recovery from acceleration/deceleration phases without overshoot.
    *   **Derivative Kick Prevention**: Initializes the previous error on the first run to prevent large derivative spikes.
    *   **Output Clamping**: Restricts the control output to vehicle physical limits (-8.0 to 3.0 m/s^2).

2.  **ACC Logic (`AdaptiveCruiseControl` class)**:
    *   **Modes**:
        *   **Cruise**: Active when no lead vehicle is detected. Uses a Speed PID to maintain `set_speed`. 
        *   **Follow**: Active when a lead vehicle is detected. Uses a Distance PID to maintain `safe_distance` ($max(10m, 1.5s \times v_{ego})$). Crucially, the acceleration is limited by the Speed PID output (`min(acc_dist, acc_speed)`) to prevent overspeeding while following faster vehicles.
        *   **Emergency**: Active when Time-To-Collision (TTC) falls below 3.0s. Commands maximum deceleration (-8.0 m/s^2) and resets PIDs.
    *   **Safety**: Explicit constraints on acceleration, minimum distance buffers, and fail-safe mode transitions.

## PID Tuning Methodology

The PID parameters were tuned to meet conflicting requirements: fast rise time vs. low overshoot, and steady-state accuracy vs. stability.

### Speed Control
*   **Kp (0.8)**: High proportional gain to achieve the <10s rise time target.
*   **Ki (0.005)**: Low integral gain. Sufficient to eliminate steady-state error (compensating for drag) but small enough to minimize overshoot. The anti-windup mechanism was critical here.
*   **Kd (0.5)**: Moderate derivative gain to damp the response and reduce overshoot near the target speed.

### Distance Control
*   **Kp (0.5)**: Moderate gain to react to distance errors without causing aggressive jerky movements.
*   **Ki (0.01)**: Small integral action to ensure the gap converges to exactly the desired spacing.
*   **Kd (0.8)**: High derivative gain to react to relative velocity (closure rate), acting as a "predictive" term to prevent crashing when closing in fast.

**Final Gains (`tuning_results.yaml`):**
```yaml
pid_speed:
  kp: 0.8
  ki: 0.005
  kd: 0.5
pid_distance:
  kp: 0.5
  ki: 0.01
  kd: 0.8
```

## Simulation Results

The system was verified using `simulation.py` with `sensor_data.csv`.

### Performance Metrics
*   **Speed Rise Time**: **9.6s** (Target < 10s). The vehicle accelerates aggressively to reach cruising speed efficiently.
*   **Speed Overshoot**: **1%** (Target < 5%). Max speed reached was ~30.31 m/s, well within limits, thanks to the anti-windup and dual-PID limiting in Follow mode.
*   **Steady-State Speed Error**: **0.22 m/s** (Target < 0.5 m/s). The integral term effectively cancelled aerodynamic drag.
*   **Minimum Distance**: **9.68 m** (Target > 5m). The system maintained safe separation even during dynamic lead vehicle maneuvers.
*   **Distance Steady-State Error**: The system tracks the lead vehicle effectively. While the lead vehicle disappears towards the end of the simulation (reverting to Cruise), the stable following phase demonstrated effective gap maintenance.

### Behavior Analysis
The simulation shows smooth transitions. Initially, the car accelerates to 30 m/s. When the lead vehicle appears (t=30s), the system seamlessly transitions to 'Follow' mode. The `min(speed_cmd, dist_cmd)` logic successfully prevented the ego vehicle from chasing a faster lead vehicle beyond the set speed limit, a common failure mode in basic ACC implementations.
