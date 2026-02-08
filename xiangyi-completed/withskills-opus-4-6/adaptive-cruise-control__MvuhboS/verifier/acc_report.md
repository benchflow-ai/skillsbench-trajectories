# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A discrete-time PID controller with anti-windup. The controller uses conditional integration to prevent integral windup when the output is saturated at the acceleration limits. Output clamping enforces the vehicle's physical acceleration bounds.

2. **ACC System** (`acc_system.py`): Implements the `AdaptiveCruiseControl` class with two PID controllers:
   - **Speed PID**: Controls ego vehicle speed toward the set speed (30 m/s) during cruise mode.
   - **Distance PID**: Controls the gap to the lead vehicle toward a safe following distance during follow mode.

3. **Simulation Runner** (`simulation.py`): Loads configuration and sensor data, reconstructs lead vehicle trajectory by integrating lead speed, runs the ACC controller in a closed loop, and outputs results.

### Operating Modes

The system operates in three modes determined by a state machine:

| Mode | Condition | Control Action |
|------|-----------|----------------|
| **Cruise** | No lead vehicle detected | Speed PID tracks set_speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID maintains safe gap; speed PID prevents exceeding set_speed; minimum of both commands is used |
| **Emergency** | Lead vehicle present, TTC < 3.0s | Maximum deceleration (-8.0 m/s^2) applied |

### Safety Features

- **Time-to-Collision (TTC) monitoring**: Triggers emergency braking when TTC drops below 3.0s.
- **Safe following distance**: Computed as `ego_speed * time_headway + min_distance` (speed-dependent gap plus 10m standstill buffer).
- **Acceleration clamping**: All commands clamped to [-8.0, 3.0] m/s^2.
- **Anti-windup PID**: Prevents integral accumulation during output saturation.
- **Conservative mode selection**: In follow mode, the minimum of speed and distance control commands is used.

## 2. PID Tuning

### Methodology

PID parameters were tuned using a systematic grid search approach:

1. **Phase 1 - Speed PID**: Tuned independently since cruise control (t=0-30s) doesn't involve a lead vehicle. The search optimized for rise time, overshoot, and steady-state error.

2. **Phase 2 - Distance PID**: Tuned with the speed PID gains fixed. The search optimized for distance steady-state error and minimum following distance.

### Tuning Rationale

**Speed PID (kp=5.0, ki=0.01, kd=0.0)**:
- High proportional gain (kp=5.0) ensures the controller requests maximum acceleration (3.0 m/s^2) for any speed error above 0.6 m/s, achieving the fastest possible rise time within the acceleration limit.
- Near-zero integral gain (ki=0.01) provides minor steady-state correction without causing overshoot.
- No derivative term needed since the proportional gain with acceleration clamping produces a clean linear ramp with no overshoot.

**Distance PID (kp=5.0, ki=0.5, kd=0.0)**:
- High proportional gain (kp=5.0) ensures rapid response to distance errors.
- Moderate integral gain (ki=0.5) eliminates steady-state distance error during stable following.
- No derivative term needed as the proportional-integral combination provides adequate response without oscillation.

### Final Gains

| Controller | Kp | Ki | Kd |
|------------|-----|------|------|
| Speed PID | 5.0 | 0.01 | 0.0 |
| Distance PID | 5.0 | 0.5 | 0.0 |

## 3. Simulation Results

### Scenario Overview

The 150-second simulation comprises three phases:

- **t=0-30s**: Cruise phase. Ego vehicle accelerates from 0 m/s to set speed of 30 m/s.
- **t=30-130s**: Follow phase. Lead vehicle detected at 52.1m ahead. Lead speed varies between 0-36 m/s, including a near-stop emergency event at t=120s.
- **t=130-150s**: Return to cruise. Lead vehicle departs, ego returns to set speed.

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time (0 to 27 m/s) | < 10 s | 9.0 s | PASS |
| Speed overshoot | < 5% | 0.00% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.000 m/s | PASS |
| Distance steady-state error | < 2 m | 0.08 m | PASS |
| Minimum distance | > 5 m | 19.36 m | PASS |
| Simulation duration | 150 s | 150 s | PASS |

### Phase Analysis

**Cruise Phase (t=0-30s)**:
The speed PID with kp=5.0 commands maximum acceleration (3.0 m/s^2) until ego speed reaches approximately 29.4 m/s, then smoothly settles to 30.0 m/s by t=10s. The vehicle maintains exactly 30.0 m/s for the remaining 20s of cruise, demonstrating zero steady-state error.

**Follow Phase (t=30-130s)**:
- **Initial acquisition (t=30-32s)**: Lead vehicle detected at 52.1m. Distance PID quickly adjusts ego speed from 30 m/s toward the lead speed (~25 m/s) to match the safe following distance (~55m). The system stabilizes within 2-3 seconds.
- **Stable following (t=32-75s)**: Lead speed averages ~25 m/s. Ego tracks at approximately 25-27 m/s, maintaining distance near the safe following target with sub-meter errors.
- **Lead acceleration (t=75-110s)**: Lead speed increases above 30 m/s (up to 36 m/s). The ego maintains set speed of 30 m/s (does not exceed), causing the gap to grow. This is correct ACC behavior.
- **Lead deceleration (t=110-120s)**: Lead slows from ~25 m/s toward 5 m/s. Distance PID commands deceleration to maintain safe gap.
- **Emergency braking (t=120-121.7s)**: TTC drops below 3.0s as lead vehicle nearly stops (0 m/s). Emergency mode engages with maximum deceleration (-8.0 m/s^2). Minimum distance of 19.36m is maintained.
- **Recovery (t=121.7-130s)**: Lead accelerates back to ~30 m/s. System returns to follow mode and accelerates to close the gap.

**Return to Cruise (t=130-150s)**:
Lead vehicle disappears. Ego accelerates from ~28.6 m/s back to 30.0 m/s and maintains set speed for the remainder of the simulation.

### Mode Distribution

| Mode | Duration | Percentage |
|------|----------|------------|
| Cruise | 50.0 s | 33.3% |
| Follow | 98.3 s | 65.5% |
| Emergency | 1.7 s | 1.1% |
