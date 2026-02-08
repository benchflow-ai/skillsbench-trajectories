# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system is composed of three core modules:

1. **PIDController** (`pid_controller.py`) — A general-purpose PID controller with clamping anti-windup. The integral term is bounded to [-10, 10] to prevent excessive windup during long saturation periods (e.g., the initial 0→30 m/s ramp where the output is clamped at max acceleration for ~10 seconds).

2. **AdaptiveCruiseControl** (`acc_system.py`) — The main ACC logic that selects operating modes and coordinates two PID controllers:
   - **Speed PID**: Controls ego vehicle speed toward the set speed (30 m/s) or lead vehicle speed.
   - **Distance PID**: Controls the gap to the lead vehicle toward the desired following distance.

3. **Simulation Runner** (`simulation.py`) — Reads tuned PID gains from `tuning_results.yaml`, loads lead vehicle data from `sensor_data.csv`, and runs the 150-second simulation.

### Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected (`lead_speed` is None) | Speed PID targets set speed (30 m/s). Distance PID is reset. |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Blended speed and distance control. When too close (error < -5m), braking is prioritized. When far enough (error > 10m), speed control dominates. |
| **Emergency** | Lead vehicle present, TTC < 3.0s and closing | Maximum deceleration applied (-8.0 m/s²). |

### Desired Following Distance

The desired following distance is computed as:

```
d_desired = time_headway * ego_speed + min_distance
           = 1.5 * ego_speed + 10.0
```

At the set speed of 30 m/s, this gives a desired gap of 55 m.

### Safety Features

- **Time-to-Collision (TTC) monitoring**: Computed as `distance / (ego_speed - lead_speed)` when closing. Emergency braking triggers when TTC < 3.0s.
- **Acceleration limits**: All commands clamped to [-8.0, 3.0] m/s².
- **Anti-windup**: PID integral clamped to prevent runaway accumulation during saturation.
- **Speed floor**: Ego speed cannot go below 0 m/s.
- **Distance floor**: Simulated distance cannot go below 0 m.

## 2. PID Tuning Methodology

### Approach

A grid search was performed over candidate PID gain combinations, evaluating each against the full 150-second simulation scenario. The simulation uses lead vehicle speed data from `sensor_data.csv` and dynamically simulates the ego vehicle speed and following distance.

### Search Space

| Parameter | Range | Description |
|-----------|-------|-------------|
| Speed kp | 0.5 – 2.0 | Proportional gain for speed error |
| Speed ki | 0.02 – 0.05 | Integral gain for speed steady-state error |
| Speed kd | 0.0 – 0.1 | Derivative gain for speed damping |
| Distance kp | 0.2 – 0.5 | Proportional gain for distance error |
| Distance ki | 0.005 – 0.02 | Integral gain for distance steady-state error |
| Distance kd | 0.3 – 1.0 | Derivative gain for distance damping |

### Evaluation Criteria

Each combination was tested against:
- Rise time < 10s (time to reach 27 m/s)
- Speed overshoot < 5%
- Speed steady-state error < 0.5 m/s (measured at t=20–30s)
- Distance steady-state error < 2 m (measured at t=40–50s)
- Minimum distance > 5 m

Passing combinations were ranked by a weighted score favoring low overshoot, low steady-state errors, and high minimum distance.

### Final Tuned Gains

| Controller | kp | ki | kd |
|-----------|-----|------|------|
| Speed PID | 1.0 | 0.02 | 0.0 |
| Distance PID | 0.5 | 0.02 | 0.5 |

**Speed PID rationale**: kp=1.0 provides proportional control that saturates at max acceleration (3.0 m/s²) for errors above 3.0, giving a natural ramp. ki=0.02 provides a small integral correction to eliminate steady-state error without excessive windup. kd=0.0 is sufficient because the system dynamics are simple and derivative action is not needed for speed control.

**Distance PID rationale**: kp=0.5 provides responsive gap control. kd=0.5 adds damping based on the rate of change of distance error, helping smooth transitions when the lead vehicle speed fluctuates. ki=0.02 eliminates residual distance error.

## 3. Simulation Results

### Scenario Timeline

| Phase | Time | Description |
|-------|------|-------------|
| Cruise ramp-up | 0.0 – 9.0s | Ego vehicle accelerates from 0 to 27 m/s (90% of set speed) |
| Cruise steady-state | 9.0 – 30.0s | Ego vehicle maintains ~30 m/s, no lead vehicle |
| Follow mode | 30.0 – 130.0s | Lead vehicle detected at 52.1m, ACC adjusts speed to follow |
| Return to cruise | 130.0 – 150.0s | Lead vehicle disappears, ego returns to 30 m/s cruise |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise time (0→27 m/s) | < 10.0s | 9.0s | PASS |
| Speed overshoot | < 5.0% | 0.63% | PASS |
| Max cruise speed | — | 30.19 m/s | — |
| Speed steady-state error | < 0.5 m/s | 0.16 m/s | PASS |
| Distance steady-state error | < 2.0 m | 1.22 m | PASS |
| Minimum distance | > 5.0 m | 47.23 m | PASS |
| Simulation duration | 150.0s | 150.0s | PASS |
| Data points | 1501 | 1501 | PASS |

### Key Observations

1. **Cruise phase (0–30s)**: The ego vehicle ramps smoothly from 0 to 30 m/s in 9 seconds with minimal overshoot (0.63%). The anti-windup mechanism prevents the integral from accumulating excessively during the saturation period, keeping overshoot well below the 5% threshold.

2. **Follow phase (30–130s)**: Upon detecting the lead vehicle at 52.1m, the ACC transitions to follow mode and reduces speed to match the lead vehicle (~25 m/s initially). The distance controller maintains the gap near the desired following distance with a mean absolute error of 1.22m.

3. **Cruise return (130–150s)**: After the lead vehicle disappears, the PID controllers are reset and the ACC smoothly returns to 30 m/s cruise.

4. **Safety margin**: The minimum distance throughout the simulation is 47.23m, well above the 5m safety threshold. No emergency braking events were triggered because the ACC maintained adequate following distance throughout.

### Output Files

- `simulation_results.csv`: 1501 rows with columns `time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc`
- `tuning_results.yaml`: Final PID gains for both speed and distance controllers
