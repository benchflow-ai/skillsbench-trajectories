# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A reusable PID controller with anti-windup integral clamping. Provides proportional, integral, and derivative control with configurable gains.

2. **ACC System** (`acc_system.py`): The main control logic that selects operating modes and computes acceleration commands using two PID controllers (speed and distance).

3. **Simulation** (`simulation.py`): Runs the 150-second vehicle simulation, reading lead vehicle data from sensor_data.csv and PID gains from tuning_results.yaml. Tracks ego and lead vehicle positions to compute dynamic inter-vehicle distance.

### Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected (`lead_speed` is None) | Speed PID maintains set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID maintains safe following gap |
| **Emergency** | TTC < 3.0s (time-to-collision threshold) | Maximum braking applied (-8.0 m/s^2) |

### Safety Features

- **Time-to-Collision (TTC) monitoring**: Continuously computed as `distance / (ego_speed - lead_speed)` when closing. Emergency braking triggers when TTC < 3.0s.
- **Acceleration clamping**: All commands limited to [-8.0, 3.0] m/s^2.
- **Anti-windup**: Integral term clamped to prevent controller saturation.
- **Speed non-negativity**: Ego speed cannot go below 0 m/s.
- **Dynamic distance tracking**: Lead vehicle position tracked from sensor speed data, providing realistic gap evolution.
- **Soft speed limiting**: In follow mode, acceleration is limited when exceeding set speed with non-negative distance error.

## 2. PID Tuning Methodology

### Speed Controller Tuning

**Objective**: Reach 30 m/s from 0 with rise time < 10s, overshoot < 5%, and steady-state error < 0.5 m/s.

**Challenge**: With max acceleration of 3.0 m/s^2, the theoretical minimum rise time to 27 m/s (90% of 30) is 9.0s. The PID must command near-maximum acceleration throughout the ramp while avoiding overshoot near the setpoint.

**Approach**:
1. Started with moderate Kp (1.0) and observed overshoot due to integral windup during the 9s ramp.
2. Increased Kp to 3.0 so the proportional term alone reaches 3.0 m/s^2 at error = 1.0 m/s, ensuring smooth approach.
3. Set Ki = 0.01 (very small) to eliminate steady-state error without causing windup during the long ramp.
4. Set Kd = 0.5 to dampen any overshoot at the setpoint transition.

**Final Speed PID Gains**:
```
Kp = 3.0, Ki = 0.01, Kd = 0.5
```

### Distance Controller Tuning

**Objective**: Maintain safe following distance with steady-state error < 2m and minimum distance > 5m.

**Desired distance formula**: `d_desired = 1.5 * ego_speed + 10.0` (time headway * speed + minimum gap).

**Approach**:
1. Started with Kp = 0.3 and observed slow response to distance changes.
2. Increased Kp to 0.8 for responsive gap tracking while avoiding oscillation.
3. Set Ki = 0.05 to eliminate steady-state distance offset.
4. Set Kd = 0.8 to provide damping and smooth approach to the desired gap.
5. Verified that during the critical braking event (t=120s), the combination of emergency braking and distance PID maintains minimum distance > 5m.

**Final Distance PID Gains**:
```
Kp = 0.8, Ki = 0.05, Kd = 0.8
```

### Tuning Trade-offs

- Higher distance Kp improves gap tracking but can cause oscillation in follow mode.
- Higher distance Kd improves damping but makes the system slower to react to sudden changes.
- The integral term (Ki) is critical for eliminating steady-state distance error but must be kept small to avoid windup during mode transitions.

## 3. Simulation Results

### Scenario Overview

The 150-second simulation covers three phases:
- **t=0-30s**: No lead vehicle. Ego accelerates from 0 to 30 m/s (cruise mode).
- **t=30-130s**: Lead vehicle present with varying speed (~25-35 m/s) and a critical braking event at t=120s. Modes: follow and emergency.
- **t=130-150s**: Lead vehicle disappears. Ego returns to cruise mode at 30 m/s.

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10.0 s | 9.0 s | PASS |
| Speed overshoot | < 5.0% | 1.67% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.015 m/s | PASS |
| Distance steady-state error | < 2.0 m | 0.54 m | PASS |
| Minimum distance | > 5.0 m | 8.61 m | PASS |

### Additional Metrics

- **Maximum cruise speed**: 30.50 m/s (1.67% above setpoint)
- **Minimum TTC**: 1.16 s (during the emergency braking event recovery)
- **Mode distribution**: Cruise: 501 steps, Follow: 981 steps, Emergency: 19 steps

### Critical Event Analysis (t=120-122s)

The most challenging scenario occurs at t=120s when the lead vehicle brakes sharply (speed drops from ~20 m/s to near 0). The ACC system:

1. Detects TTC < 3.0s and enters emergency mode.
2. Applies maximum braking (-8.0 m/s^2) for 19 timesteps (1.9s).
3. Maintains minimum distance of 8.61m (above 5m threshold).
4. Transitions back to follow mode at t=121.9s as distance stabilizes.
5. Gradually re-accelerates under distance PID control.

### Mode Transitions

| Time | Transition | Trigger |
|------|-----------|---------|
| t=0.0s | Start -> Cruise | Initial state |
| t=30.0s | Cruise -> Follow | Lead vehicle detected at 52.1m |
| t=120.0s | Follow -> Emergency | TTC drops below 3.0s threshold |
| t=121.9s | Emergency -> Follow | TTC recovers above threshold |
| t=130.0s | Follow -> Cruise | Lead vehicle no longer detected |

## 4. Conclusions

The ACC system successfully meets all performance targets across the 150-second simulation. The dual PID architecture (speed + distance) provides effective control in both cruise and follow modes, while the TTC-based emergency braking ensures safety during critical events. The tuned PID gains balance responsiveness with stability, achieving sub-meter distance tracking error and minimal speed overshoot.
