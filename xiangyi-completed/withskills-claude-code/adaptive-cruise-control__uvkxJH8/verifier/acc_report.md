# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A standard PID controller with anti-windup protection
   - Configurable proportional (Kp), integral (Ki), and derivative (Kd) gains
   - Integral term clamping to prevent windup during saturation
   - Reset capability for mode transitions

2. **ACC System** (`acc_system.py`): The main control logic with three operating modes
   - Speed PID controller for cruise mode
   - Distance PID controller for follow mode
   - Emergency braking for collision avoidance

3. **Simulation Runner** (`simulation.py`): Executes the 150-second simulation
   - Loads vehicle parameters and tuned PID gains
   - Processes sensor data for lead vehicle behavior
   - Computes ego vehicle dynamics and outputs results

### 1.2 Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|------------------|
| **Cruise** | No lead vehicle detected | PID control to maintain set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance-based PID control with speed matching |
| **Emergency** | TTC < 3.0s | Maximum deceleration (-8.0 m/s^2) |

### 1.3 Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Continuous calculation of TTC when a lead vehicle is present
2. **Emergency Braking**: Automatic maximum deceleration when TTC drops below 3.0 seconds
3. **Speed Limiting**: In follow mode, the system prevents acceleration above set speed
4. **Minimum Gap Enforcement**: Desired following distance is always >= 10.0 meters
5. **Acceleration Limits**: All commands are clamped to [-8.0, 3.0] m/s^2

### 1.4 Following Distance Model

The desired following distance is calculated using the time headway model:

```
desired_distance = max(min_distance, time_headway * ego_speed)
                 = max(10.0 m, 1.5s * ego_speed)
```

At the set speed of 30 m/s, the desired following distance is 45 meters.

## 2. PID Tuning Methodology

### 2.1 Tuning Approach

The PID parameters were tuned iteratively to meet the following performance targets:

| Metric | Target | Achieved |
|--------|--------|----------|
| Speed rise time | < 10s | 9.10s |
| Speed overshoot | < 5% | 3.77% |
| Speed steady-state error | < 0.5 m/s | 0.046 m/s |
| Distance steady-state error | < 2m | 0.95m |
| Minimum distance | > 5m | 11.12m |

### 2.2 Speed Controller Tuning

The speed controller was tuned for fast response with minimal overshoot:

- **Kp = 0.8**: Provides responsive acceleration to speed errors without excessive overshoot
- **Ki = 0.02**: Small integral gain eliminates steady-state error while avoiding windup
- **Kd = 0.3**: Derivative term provides damping as speed approaches the target

Key considerations:
- With maximum acceleration of 3.0 m/s^2, reaching 30 m/s from rest requires at least 10 seconds
- Anti-windup protection in the PID controller prevents integral accumulation during saturation
- The controller resets when transitioning between modes to prevent accumulated error carryover

### 2.3 Distance Controller Tuning

The distance controller was tuned for stable following with good steady-state accuracy:

- **Kp = 1.2**: Higher proportional gain for responsive distance corrections
- **Ki = 0.08**: Moderate integral gain to eliminate steady-state distance errors
- **Kd = 1.5**: High derivative gain provides damping against oscillations

Key considerations:
- Distance control output is combined with speed matching (0.5 * relative_speed)
- Speed limiting prevents the ego vehicle from exceeding set speed when catching up
- The controller resets in cruise mode to prevent integral windup

### 2.4 Final PID Parameters

```yaml
pid_speed:
  kp: 0.8
  ki: 0.02
  kd: 0.3

pid_distance:
  kp: 1.2
  ki: 0.08
  kd: 1.5
```

## 3. Simulation Results

### 3.1 Performance Summary

The 150-second simulation was executed successfully with the following results:

| Metric | Value | Requirement | Status |
|--------|-------|-------------|--------|
| Rise time (to 90% of set speed) | 9.10s | < 10s | PASS |
| Speed overshoot | 3.77% | < 5% | PASS |
| Maximum speed | 31.13 m/s | - | - |
| Speed steady-state error | 0.046 m/s | < 0.5 m/s | PASS |
| Distance steady-state error | 0.95m | < 2m | PASS |
| Minimum distance | 11.12m | > 5m | PASS |
| Emergency braking events | 19 | - | - |

### 3.2 Simulation Phases

The simulation consists of several distinct phases based on the sensor data:

1. **t=0-30s (Cruise)**: Ego vehicle accelerates from rest to set speed (30 m/s)
   - Maximum acceleration applied until approaching set speed
   - Smooth transition to steady-state cruising

2. **t=30-60s (Follow)**: Lead vehicle appears traveling at ~25 m/s
   - ACC transitions to follow mode
   - Distance maintained at approximately 38-40 meters
   - Steady-state distance error < 2m during stable following

3. **t=60-100s (Follow with acceleration)**: Lead vehicle gradually accelerates
   - Ego vehicle follows, limited by set speed
   - Gap increases when lead exceeds 30 m/s (expected behavior)

4. **t=100-120s (Follow with deceleration)**: Lead vehicle slows down
   - Ego vehicle reduces speed to maintain safe following distance
   - Smooth deceleration profile

5. **t=120-122s (Emergency)**: Lead vehicle emergency stops
   - TTC drops below threshold, triggering emergency braking
   - Maximum deceleration (-8.0 m/s^2) applied
   - Minimum distance maintained above 5m safety threshold

6. **t=122-130s (Follow recovery)**: Lead vehicle accelerates away
   - Ego vehicle follows and catches up
   - Transition through follow mode with varying distances

7. **t=130-150s (Cruise)**: No lead vehicle detected
   - ACC returns to cruise mode
   - Speed maintained at set speed (30 m/s)

### 3.3 Output Files

- **simulation_results.csv**: Contains 1501 rows of simulation data
  - Columns: time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc
  - Timestep: 0.1 seconds
  - Duration: 0.0 - 150.0 seconds

- **tuning_results.yaml**: Final tuned PID parameters

### 3.4 Observations

1. The ACC system successfully maintains the set speed during cruise mode with minimal steady-state error (0.046 m/s)

2. During stable following (both vehicles at 24-28 m/s), the distance error remains below 2m with an average of 0.95m

3. The emergency braking system activates appropriately when TTC drops below 3.0 seconds, maintaining safe distances throughout

4. The speed limiter in follow mode effectively prevents excessive acceleration, keeping overshoot to 3.77% even when trying to catch up with a lead vehicle

5. Mode transitions are handled smoothly with PID controller resets preventing accumulated error carryover
