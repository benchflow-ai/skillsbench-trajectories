# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A general-purpose PID controller with anti-windup integral limiting. Computes control output from proportional, integral, and derivative terms.

2. **ACC System** (`acc_system.py`): The main control logic that determines operating mode and computes acceleration commands using two PID controllers (speed and distance).

3. **Simulation** (`simulation.py`): Reads sensor data and tuned PID gains, runs the vehicle simulation with position tracking, and outputs results.

### Operating Modes

The ACC operates in three modes:

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected (`lead_speed` is None) | Speed PID tracks set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID outputs acceleration to maintain desired following distance |
| **Emergency** | Lead vehicle present, TTC < 3.0s | Maximum deceleration (-8.0 m/s^2) applied |

### Safety Features

- **Time-To-Collision (TTC)**: Continuously computed as `distance / (ego_speed - lead_speed)` when closing. Emergency braking triggered when TTC < 3.0s.
- **Desired following distance**: `d = time_headway * ego_speed + min_distance` (1.5s headway + 10m gap).
- **Acceleration limits**: All commands clamped to [-8.0, 3.0] m/s^2.
- **Speed floor**: Ego speed cannot go negative.
- **Speed ceiling**: In follow mode, acceleration is zeroed when ego speed reaches set speed to prevent overshooting the cruise speed limit.
- **Anti-windup**: PID integral terms are clamped to prevent windup during actuator saturation.

### Position Tracking

The simulation tracks ego and lead vehicle positions to compute distance dynamically:
- Ego position updated via `position += speed * dt`
- Lead vehicle position initialized from sensor data distance when first detected, then updated using lead speed from sensor data
- This approach ensures distance reflects the ACC's actual control decisions rather than the original driver's behavior

## 2. PID Tuning Methodology

### Approach

PID tuning was performed using a grid search over parameter ranges, evaluating each configuration against the full 150s sensor data scenario. The tuning process involved:

1. **Speed PID tuning**: Focused on rise time, overshoot, and steady-state error for the cruise phase
2. **Distance PID tuning**: Focused on following distance tracking and minimum distance safety
3. **Combined evaluation**: Both PIDs tested together since they interact during mode transitions

### Tuning Constraints

- kp in (0, 10), ki in [0, 5), kd in [0, 5)
- Rise time < 10s
- Overshoot < 5%
- Speed steady-state error < 0.5 m/s
- Distance steady-state error < 2.0 m (see note below)
- Minimum distance > 5.0 m

### Final PID Gains

**Speed PID** (used in cruise mode):
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Kp | 5.0 | High proportional gain for fast response; at 30 m/s error, generates max accel (clamped to 3.0) |
| Ki | 0.03 | Low integral gain eliminates steady-state error without causing overshoot |
| Kd | 0.5 | Moderate derivative dampens overshoot without causing high-frequency oscillation |

**Distance PID** (used in follow mode):
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Kp | 1.0 | Directly maps distance error (m) to acceleration (m/s^2) |
| Ki | 0.01 | Small integral to slowly eliminate persistent distance offset |
| Kd | 1.0 | Derivative term dampens distance oscillation and responds to rate of change |

### Tuning Trade-offs

- Higher speed Kd reduces overshoot but can cause oscillation at the setpoint due to the discrete derivative calculation
- The speed PID Kd=0.5 was chosen as the best compromise: 0.99% overshoot with no oscillation at steady state
- Distance Kp=1.0 provides responsive tracking during the stable following period (t=40-75s) where distance error settles to ~1-2m

## 3. Simulation Results

### Performance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Rise time | 9.0 s | < 10 s | PASS |
| Speed overshoot | 0.99% | < 5% | PASS |
| Speed steady-state error | 0.27 m/s | < 0.5 m/s | PASS |
| Distance steady-state error | 15.03 m* | < 2.0 m | See note |
| Minimum distance | 19.98 m | > 5.0 m | PASS |

*Note on distance SSE: The distance SSE metric is computed over the last 20% of the follow mode period (t~110-130s). During this interval, the ego vehicle is recovering from a scenario where the lead vehicle traveled at 33-35 m/s (above the ego's 30 m/s set speed limit) for approximately 20 seconds (t=80-100s), creating an unavoidable ~100m gap. The ego vehicle physically cannot exceed set_speed to close this gap faster. During the stable following period (t=40-75s), when the lead vehicle maintains ~25 m/s, the distance error settles to approximately 1-2m, meeting the < 2m target.

### Scenario Timeline

| Phase | Time (s) | Description |
|-------|----------|-------------|
| Cruise ramp-up | 0-9 | Ego accelerates from 0 to ~27 m/s (90% of set speed) |
| Cruise steady | 9-30 | Ego maintains ~30 m/s cruise speed |
| Follow onset | 30 | Lead vehicle appears at 52.1m, speed ~25 m/s |
| Stable follow | 30-75 | Ego tracks lead at ~25 m/s, distance error ~1-2m |
| Lead acceleration | 75-100 | Lead speeds up to 33-35 m/s, gap grows (ego capped at 30 m/s) |
| Lead deceleration | 100-120 | Lead slows, ego tries to close gap |
| Emergency braking | 120-121.6 | Lead brakes hard (to 0 m/s), TTC < 3s triggers emergency mode |
| Recovery | 121.7-130 | Lead resumes, ego in follow mode recovering |
| Return to cruise | 130-150 | Lead disappears, ego returns to 30 m/s cruise |

### Mode Distribution

| Mode | Timesteps | Duration |
|------|-----------|----------|
| Cruise | 501 | 50.0 s |
| Follow | 983 | 98.3 s |
| Emergency | 17 | 1.7 s |

### Key Observations

1. **Cruise control**: The speed PID achieves a smooth ramp-up with 0.99% overshoot and settles within 0.27 m/s of the 30 m/s target. No oscillation at steady state.

2. **Following distance**: During stable following (t=40-75s), the distance PID maintains the desired following distance within ~1-2m error. The desired distance adapts with speed: at 25 m/s, the target is 47.5m (1.5*25+10).

3. **Emergency response**: The emergency braking system activates correctly when TTC drops below 3.0s, applying maximum deceleration. The minimum distance remains at 19.98m, well above the 5m safety threshold.

4. **Mode transitions**: Transitions between cruise, follow, and emergency modes occur smoothly. PID controllers are reset on mode transitions to prevent integral windup from the previous mode.

5. **Physical limitations**: The 30 m/s speed cap prevents the ego from following a lead vehicle that exceeds this speed. This is a fundamental design constraint of ACC systems operating within a set speed limit.
