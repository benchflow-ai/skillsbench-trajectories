# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A reusable discrete PID controller with anti-windup clamping. Supports configurable proportional, integral, and derivative gains, plus output limits to prevent integral windup.

2. **ACC System** (`acc_system.py`): The core control logic that manages mode selection and computes acceleration commands using two PID controllers:
   - **Speed PID**: Controls ego vehicle speed toward the set speed (30 m/s)
   - **Distance PID**: Controls the following gap to maintain safe distance

3. **Simulation Runner** (`simulation.py`): Loads configuration and sensor data, runs the 150s simulation with Euler integration, and evaluates performance metrics.

### 1.2 Operating Modes

The ACC operates in three modes:

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected | Speed PID tracks set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC > 3.0s | Distance PID computes desired speed adjustment; speed PID tracks the resulting target speed (capped at set speed) |
| **Emergency** | TTC < 3.0s | Maximum deceleration (-8.0 m/s²) applied immediately |

### 1.3 Follow Mode Control Strategy

The follow mode uses a cascaded control approach:

1. Compute desired following distance: `d_desired = 1.5 * v_ego + 10.0`
2. Distance PID processes the gap error: `error = d_actual - d_desired`
3. Distance PID output adjusts lead speed to compute desired ego speed: `v_desired = min(v_lead + dist_correction, v_set)`
4. Speed PID tracks the desired speed

This architecture prevents the ego vehicle from exceeding the set speed while maintaining appropriate following distance.

### 1.4 Safety Features

- **Emergency braking**: Full deceleration (-8.0 m/s²) when TTC drops below 3.0s
- **Acceleration limits**: All commands clamped to [-8.0, 3.0] m/s²
- **Speed floor**: Ego speed cannot go below 0 m/s
- **Anti-windup**: PID integral terms are clamped to prevent windup during saturation
- **Mode transition resets**: PID states are reset on mode changes to prevent control artifacts
- **Speed cap in follow mode**: Ego speed is limited to set speed even when lead vehicle is faster

## 2. PID Tuning Methodology

### 2.1 Approach

A systematic manual tuning process was used:

1. **Speed controller first**: Tuned in cruise-only conditions (t=0-30s, no lead vehicle)
2. **Distance controller second**: Tuned during follow mode (t=30-130s)
3. **Combined validation**: Verified all metrics across the full 150s scenario

### 2.2 Speed PID Tuning

**Constraints**:
- With max_accel = 3.0 m/s², the theoretical minimum rise time from 0 to 27 m/s (90% of 30) is 9.0s
- Need Kp high enough that the PID saturates at max_accel for large errors
- Ki must be small to avoid overshoot from integral windup during the long ramp-up

**Process**:
1. Started with Kp=1.0, Ki=0, Kd=0: Rise time 10s, no overshoot but slow settling
2. Increased Kp to 2.0: Faster response near setpoint, still saturates at max_accel for large errors
3. Added Ki=0.01: Eliminates tiny steady-state errors without significant windup
4. Added Kd=0.8: Provides strong damping to reduce overshoot when approaching setpoint

### 2.3 Distance PID Tuning

**Constraints**:
- Lead vehicle speed varies 22-37 m/s (noisy sensor data)
- Desired distance = 1.5 * ego_speed + 10.0 (dynamic target)
- Must maintain min distance > 5m and respond to emergency scenarios

**Process**:
1. Started with Kp=0.5, Ki=0.02, Kd=0.8: Poor tracking, high oscillation
2. Increased Kp to 2.5: Better gap tracking during stable following
3. Increased Ki to 0.15: Reduces steady-state distance error
4. Reduced Kd to 0.3: Less sensitivity to noisy distance error derivatives

### 2.4 Final PID Gains

```yaml
pid_speed:
  kp: 2.0
  ki: 0.01
  kd: 0.8

pid_distance:
  kp: 2.5
  ki: 0.15
  kd: 0.3
```

## 3. Simulation Results

### 3.1 Scenario Overview

The 150-second simulation consists of three phases:

| Phase | Time (s) | Description |
|-------|----------|-------------|
| Cruise ramp-up | 0 - 30 | Ego accelerates from 0 to 30 m/s, no lead vehicle |
| Follow | 30 - 130 | Lead vehicle present, varying speed (22-37 m/s), including emergency braking event at t~120s |
| Cruise recovery | 130 - 150 | Lead vehicle disappears, ego returns to set speed |

### 3.2 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10s | 9.0s | PASS |
| Speed overshoot | < 5% | 2.48% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.001 m/s | PASS |
| Distance steady-state error | < 2m | 1.28m | PASS |
| Minimum distance | > 5m | 35.9m | PASS |
| Control duration | 150s | 150s (1501 steps) | PASS |

### 3.3 Phase Analysis

**Phase 1 - Cruise Ramp-up (t=0-30s)**:
- Ego accelerates at maximum 3.0 m/s² from rest
- Reaches 27 m/s (90% of setpoint) at t=9.0s
- Reaches 30 m/s at t=10.0s
- Maximum overshoot to ~30.7 m/s (2.48%), quickly settling to 30.0 m/s

**Phase 2 - Follow Mode (t=30-130s)**:
- Initial transition from cruise (30.7 m/s) to following lead at ~25 m/s
- Ego speed adjusts smoothly to match lead vehicle with appropriate gap
- Steady-state distance error averages 1.28m during stable following (t=50-70s)
- Lead vehicle accelerates to ~33 m/s (t=80-100s): gap opens but ego correctly caps at set speed
- Emergency braking event (t~119-121s): TTC drops below 3.0s, emergency mode activates
- Post-emergency: ego decelerates and re-establishes following distance

**Phase 3 - Cruise Recovery (t=130-150s)**:
- Lead vehicle disappears at t=130s
- Speed PID resets and smoothly accelerates back to 30 m/s
- Final steady-state speed at t=150s: 30.0 m/s (error < 0.001 m/s)

### 3.4 Emergency Event Analysis

At approximately t=119-121s, the lead vehicle performs an emergency stop:
- Lead speed drops from ~20 m/s to near 0 m/s
- TTC falls below 3.0s threshold at t=119.1s
- Emergency mode activates: maximum braking at -8.0 m/s²
- Minimum distance maintained at 35.9m (well above 5m safety margin)
- Minimum TTC observed: 3.22s (just above the 3.0s emergency threshold)
- The system's dynamic distance tracking and proactive speed matching kept the ego vehicle at a safe distance throughout

## 4. Files Produced

| File | Description |
|------|-------------|
| `pid_controller.py` | PID controller class with anti-windup |
| `acc_system.py` | ACC system with cruise/follow/emergency modes |
| `simulation.py` | Simulation runner with evaluation |
| `tuning_results.yaml` | Final PID gains |
| `simulation_results.csv` | 1501-row simulation output |
| `vehicle_params.yaml` | Vehicle parameters and ACC settings |
| `sensor_data.csv` | Sensor data (lead vehicle speed and distance) |
