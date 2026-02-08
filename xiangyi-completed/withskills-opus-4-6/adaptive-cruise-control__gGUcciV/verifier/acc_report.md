# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A standard PID controller with anti-windup protection via back-calculation. Supports configurable output clamping limits.

2. **ACC System** (`acc_system.py`): Orchestrates two PID controllers (speed and distance) and selects operating mode. Takes vehicle parameters and ACC settings from `vehicle_params.yaml`.

3. **Simulation Runner** (`simulation.py`): Loads tuned PID gains from `tuning_results.yaml`, reads lead vehicle data from `sensor_data.csv`, runs the 150s simulation, and outputs `simulation_results.csv`.

### Operating Modes

The ACC operates in three modes:

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Speed PID targets set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID maintains safe following distance |
| **Emergency** | TTC < 3.0s and closing | Maximum deceleration (-8.0 m/s^2) |

### Safety Features

- **Time-to-Collision (TTC) monitoring**: Emergency braking triggers when TTC < 3.0s and closing speed > 0.01 m/s
- **Speed-dependent following distance**: Desired gap = 10.0m + 1.5s x ego_speed, ensuring larger gaps at higher speeds
- **Acceleration limits**: Clamped to [-8.0, 3.0] m/s^2
- **Anti-windup**: PID integral term is clamped when output saturates, preventing integral buildup during sustained saturation
- **Speed floor**: Ego speed cannot go below 0 m/s

### Control Strategy

In **cruise mode**, the speed PID controller drives ego speed to the set speed of 30 m/s.

In **follow mode**, the distance PID controller is primary, driving the ego vehicle to maintain the desired following distance. The speed PID controller acts as a limiter to prevent exceeding set speed when ego speed is above set_speed.

In **emergency mode**, the system applies maximum braking regardless of PID output.

## 2. PID Tuning Methodology

### Approach

A two-phase grid search was used:

1. **Phase 1 - Speed PID**: Tuned for fast rise time (< 10s), minimal overshoot (< 5%), and low steady-state error (< 0.5 m/s). The distance PID was held at nominal values during this phase.

2. **Phase 2 - Distance PID**: With the best speed PID gains fixed, tuned the distance PID for low following distance error (< 2m) and safe minimum gap (> 5m).

### Search Space

| Parameter | Speed PID Range | Distance PID Range |
|-----------|----------------|-------------------|
| Kp | [1.0, 9.0] | [0.2, 9.0] |
| Ki | [0.01, 1.0] | [0.0, 1.0] |
| Kd | [0.0, 0.5] | [0.0, 4.0] |

### Final Tuned Gains

| Controller | Kp | Ki | Kd |
|------------|-----|-----|-----|
| **Speed PID** | 9.0 | 0.01 | 0.05 |
| **Distance PID** | 7.0 | 0.0 | 0.0 |

**Speed PID rationale**: High proportional gain (Kp=9.0) provides rapid response to speed errors, minimizing overshoot and steady-state error. The system is inherently stable because acceleration is hardware-limited to 3.0 m/s^2, so high Kp saturates quickly during ramp-up and provides tight regulation near set speed. Small integral (Ki=0.01) eliminates residual steady-state error. Small derivative (Kd=0.05) provides minor damping.

**Distance PID rationale**: High proportional gain (Kp=7.0) with no integral or derivative terms provides aggressive distance correction. The distance error is naturally self-correcting (closing the gap changes relative velocity), so P-only control avoids oscillation. The acceleration limits (-8.0 to 3.0 m/s^2) bound the actual output.

## 3. Simulation Results

### Scenario Overview

The 150-second simulation covers three phases:

| Phase | Time (s) | Description |
|-------|----------|-------------|
| Initial cruise | 0 - 30 | Ego accelerates from 0 to 30 m/s, no lead vehicle |
| Following | 30 - 130 | Lead vehicle present with varying speed (0-37 m/s) |
| Return to cruise | 130 - 150 | Lead vehicle disappears, ego returns to 30 m/s |

The following phase includes a critical emergency braking event around t=120s when the lead vehicle decelerates sharply to 0 m/s.

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10 s | 9.0 s | PASS |
| Speed overshoot | < 5 % | 0.001 % | PASS |
| Speed steady-state error | < 0.5 m/s | 0.0002 m/s | PASS |
| Distance steady-state error | < 2 m | 0.059 m | PASS |
| Minimum distance | > 5 m | 19.35 m | PASS |
| Control duration | 150 s | 150 s | PASS |

### Key Observations

1. **Cruise phase (0-30s)**: The ego vehicle accelerates at the maximum rate of 3.0 m/s^2, reaching 27 m/s (90% of set speed) at t=9.0s and settling at 30.0 m/s by t=10s with negligible overshoot.

2. **Follow transition (t=30s)**: When the lead vehicle appears at 52.1m distance traveling at 25.4 m/s, the ACC immediately switches to follow mode and decelerates to match the lead speed, converging on the desired following distance within approximately 5 seconds.

3. **Stable following (t=35-70s)**: The ego vehicle tracks the lead vehicle with distance errors consistently below 0.5m, maintaining a safe gap of 47-55m at speeds around 25-30 m/s.

4. **Lead acceleration (t=70-100s)**: When the lead vehicle accelerates above set speed (~33-36 m/s), the ego correctly holds at 30 m/s and allows the gap to increase, reaching up to ~115m. This is correct behavior since the ACC should not exceed set speed.

5. **Emergency braking (t=120-122s)**: When the lead vehicle brakes hard to 0 m/s, the TTC drops below 3.0s, triggering emergency mode with maximum deceleration. The minimum gap during this event is 19.35m, well above the 5m safety threshold.

6. **Return to cruise (t=130-150s)**: After the lead vehicle disappears, the ego resumes cruise mode and re-accelerates to 30.0 m/s, settling with steady-state error of 0.0002 m/s.

### Constraints Compliance

| Constraint | Value | Status |
|-----------|-------|--------|
| Initial speed | 0.0 m/s | Compliant |
| Acceleration limits | [-8.0, 3.0] m/s^2 | Compliant |
| Time headway | 1.5 s | Compliant |
| Minimum gap | 10.0 m | Compliant |
| Emergency TTC threshold | 3.0 s | Compliant |
| Timestep | 0.1 s | Compliant |
