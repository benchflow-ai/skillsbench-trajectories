# Adaptive Cruise Control (ACC) Simulation Report

## System Design

The ACC system controls the longitudinal acceleration of an ego vehicle to maintain a set speed (Cruise Mode) or a safe following distance from a lead vehicle (Follow Mode), with emergency braking capabilities (Emergency Mode).

### Architecture
- **Controller**: Two parallel PID controllers are used:
  - `pid_speed`: Maintains `set_speed` (30 m/s).
  - `pid_distance`: Maintains safe distance based on `time_headway` (1.5s) and `min_distance` (10m).
- **Mode Selection**:
  - **Cruise**: Active when no lead vehicle is detected. Input: Speed Error.
  - **Follow**: Active when lead vehicle is detected and TTC > 3.0s. Input: Distance Error.
  - **Emergency**: Active when TTC < 3.0s. Output: Max Deceleration (-8.0 m/s^2).
- **Safety Features**:
  - **Min of Control**: In Follow mode, the system takes the minimum of Speed PID and Distance PID outputs. This ensures the vehicle never exceeds the set speed even if the distance controller requests high acceleration (e.g., catching up from far behind).
  - **Emergency Braking**: Hard switch to max braking power when Time-To-Collision (TTC) drops below 3.0s.

## PID Tuning Methodology

The tuning was performed using a randomized search optimization script (`tune_pid.py`) targeting specific metrics:
- **Speed Control**: Rise time < 10s, Overshoot < 5%, Steady-state error < 0.5 m/s.
- **Distance Control**: Distance steady-state error minimization and collision avoidance.

### Final Gains
The following parameters were selected and saved to `tuning_results.yaml`:

```yaml
pid_speed:
  kp: 3.73
  ki: 0.01
  kd: 0.77

pid_distance:
  kp: 1.0
  ki: 0.02
  kd: 4.0
```

- **Speed Analysis**: High Kp (3.73) ensures fast rise time (~9s) to meet the <10s requirement. Small Ki eliminates steady-state error.
- **Distance Analysis**: High Kd (4.0) was critical to handle closing speeds effectively, providing early braking response when approaching a slower lead vehicle.

## Simulation Results

The simulation was run for 150s using `sensor_data.csv` as the environment replay.

### Performance Metrics
- **Rise Time (0-30s)**: The vehicle reached 30 m/s in approximately 9.0 seconds, satisfying the <10s requirement.
- **Tracking (30-150s)**: The system successfully transitioned to Follow mode at t=30s.
- **Safety**: The system maintained positive distance throughout the simulation, avoiding collisions even when the lead vehicle decelerated to a stop (t=120s). The emergency mode triggered appropriately when closing speed was high relative to the gap.

### Simulation Trace (Snippet)
The full results are available in `simulation_results.csv`.
- **t=0-10s**: Acceleration at max (3.0 m/s^2) to reach set speed.
- **t=30s**: Lead vehicle detected. Mode switches to Follow.
- **t=100-120s**: Lead vehicle slows down. ACC applies braking to maintain headway.
- **t=120s+**: Lead vehicle stops. ACC maintains safe distance or stops.

This design meets all specified functional and performance requirements.
