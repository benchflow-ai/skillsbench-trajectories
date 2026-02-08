# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system is implemented as a cascaded control architecture with three main components:

1. **PID Controller** (`pid_controller.py`) - A general-purpose PID controller with anti-windup clamping, used for both speed and distance control loops.

2. **ACC System** (`acc_system.py`) - The main control logic that selects operating modes and coordinates the speed and distance PID controllers in a cascaded configuration.

3. **Simulation** (`simulation.py`) - The simulation harness that reads vehicle parameters and sensor data, runs the ACC controller at each timestep, and tracks the ego vehicle's speed and gap distance dynamically.

### 1.2 Control Architecture

The ACC uses a cascaded control strategy:

- **Outer loop (Distance PID)**: Computes a speed correction based on the distance error (actual distance minus desired following distance).
- **Inner loop (Speed PID)**: Tracks the target speed, which is set to either the cruise set speed (in cruise mode) or the lead vehicle speed plus the distance correction (in follow mode).

The desired following distance is computed as:

```
desired_distance = min_distance + time_headway * ego_speed
                 = 10.0 + 1.5 * ego_speed
```

### 1.3 Operating Modes

The system operates in three modes:

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Speed PID tracks the set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Cascaded distance-speed control maintains safe following distance |
| **Emergency** | TTC < 3.0s and closing | Maximum deceleration (-8.0 m/s^2) applied |

### 1.4 Safety Features

- **Time-to-Collision (TTC) monitoring**: Continuously computed when a lead vehicle is present. Emergency braking activates when TTC < 3.0s.
- **Acceleration limits**: All commands are clamped to [-8.0, 3.0] m/s^2.
- **Speed non-negativity**: Ego speed is clamped to >= 0 m/s.
- **Anti-windup**: PID integral terms are prevented from accumulating when the output is saturated.
- **Controller reset**: Distance PID is reset when transitioning to cruise mode; both controllers are reset on emergency braking to prevent integral windup from carrying over.
- **Set speed cap**: In follow mode, the target speed is capped at the set speed (30 m/s) to prevent exceeding the driver's desired maximum.

## 2. PID Tuning Methodology

### 2.1 Approach

PID gains were tuned manually using an iterative approach guided by the performance requirements:

1. **Speed PID**: Tuned first in isolation during the cruise phase (t=0-30s, no lead vehicle).
2. **Distance PID**: Tuned second during the follow phase (t=30-120s) while keeping speed PID gains fixed.
3. **Validation**: Full 150s simulation run to verify all targets are met simultaneously.

### 2.2 Speed PID Tuning

**Target**: Rise time < 10s, overshoot < 5%, steady-state error < 0.5 m/s.

- **kp = 1.5**: Provides strong proportional response. At maximum error (30 m/s), the output saturates at the 3.0 m/s^2 limit, ensuring maximum acceleration during the initial ramp. As the error decreases below 2 m/s, the proportional term transitions to fine control.
- **ki = 0.15**: Eliminates steady-state error. Moderate value avoids integral windup while ensuring convergence.
- **kd = 0.3**: Provides damping to reduce overshoot as the speed approaches the setpoint.

### 2.3 Distance PID Tuning

**Target**: Distance steady-state error < 2m, minimum distance > 5m.

The distance PID outputs a speed correction that is added to the lead vehicle speed to produce the target speed for the inner speed loop.

- **kp = 0.8**: Converts distance error (meters) to speed correction (m/s). A 5m distance error produces a 4 m/s speed correction, which is responsive without being overly aggressive.
- **ki = 0.4**: Higher integral gain to ensure the distance error converges to zero during steady-state following. Important for tracking when lead vehicle speed changes gradually.
- **kd = 1.5**: Provides damping against the noisy distance measurements and prevents oscillation in the gap-closing response.

### 2.4 Final Gains

```yaml
pid_speed:
  kp: 1.5
  ki: 0.15
  kd: 0.3

pid_distance:
  kp: 0.8
  ki: 0.4
  kd: 1.5
```

## 3. Simulation Results

### 3.1 Scenario Overview

The 150-second simulation covers multiple operating phases:

| Time (s) | Phase | Description |
|-----------|-------|-------------|
| 0 - 30 | Cruise ramp-up | Ego accelerates from 0 to 30 m/s with no lead vehicle |
| 30 - 120 | Following | Lead vehicle detected at ~25 m/s, gradually accelerating to ~35 m/s |
| 120 - 122 | Emergency braking | Lead vehicle decelerates rapidly to 0 m/s |
| 122 - 130 | Recovery following | Both vehicles accelerate; lead vehicle pulls away |
| 130 - 150 | Cruise recovery | Lead vehicle disappears; ego recovers to 30 m/s |

### 3.2 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10 s | 9.0 s | PASS |
| Speed overshoot | < 5% | 0.51% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.05 m/s | PASS |
| Distance steady-state error | < 2 m | 0.49 m | PASS |
| Minimum distance | > 5 m | 24.95 m | PASS |

### 3.3 Phase Analysis

**Cruise Phase (t=0-30s)**: The ego vehicle accelerates at the maximum rate (3.0 m/s^2) until approaching the set speed, where the PID controller smoothly transitions to fine control. The speed reaches 90% of set speed (27.0 m/s) at t=9.0s. Overshoot is minimal at 0.51%.

**Following Phase (t=30-120s)**: When the lead vehicle is detected at t=30s with distance ~52m and speed ~25 m/s, the ACC transitions to follow mode. The ego vehicle decelerates to match the lead vehicle speed and converges to the desired following distance. During steady-state following (t=45-75s), the average distance error is 0.49m.

**Emergency Phase (t=120-122s)**: The lead vehicle decelerates abruptly. The ACC detects the low TTC and triggers emergency braking at -8.0 m/s^2. The minimum distance of 24.95m is maintained well above the 5m safety threshold, demonstrating effective emergency response.

**Recovery Phase (t=130-150s)**: After the lead vehicle disappears, the ACC switches back to cruise mode and accelerates back to the 30 m/s set speed.

### 3.4 Key Observations

- The cascaded control architecture (distance -> speed) provides smooth and stable following behavior.
- The TTC-based emergency braking activates reliably when the lead vehicle decelerates suddenly.
- During periods when the lead vehicle exceeds the set speed (t=80-90s), the ACC correctly limits ego speed to 30 m/s, allowing the gap to grow naturally. This is the expected behavior.
- The anti-windup mechanism prevents integral accumulation during saturation, ensuring smooth transitions between modes.
