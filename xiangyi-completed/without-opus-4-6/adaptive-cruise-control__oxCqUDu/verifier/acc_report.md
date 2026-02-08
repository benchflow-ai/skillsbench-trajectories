# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system uses a cascaded PID control architecture with three operating modes:

```
Sensor Data --> Mode Selector --> PID Controllers --> Acceleration Cmd --> Vehicle Dynamics
                    |                   |
              [cruise/follow/     [speed PID]
               emergency]         [distance PID]
```

**Components:**

- **PIDController** (`pid_controller.py`): General-purpose PID controller with anti-windup integral clamping and derivative computation. Provides `reset()` for mode transitions and `compute(error, dt)` for control output.

- **AdaptiveCruiseControl** (`acc_system.py`): Main control module that selects operating mode and coordinates the speed and distance PID controllers. Accepts configuration from `vehicle_params.yaml` and `tuning_results.yaml`.

- **Simulation** (`simulation.py`): Runs the 150-second simulation using lead vehicle data from `sensor_data.csv`. Tracks ego vehicle position/speed independently and computes inter-vehicle distance dynamically.

### 1.2 Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected | Speed PID tracks set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID computes speed offset; speed PID tracks adjusted target |
| **Emergency** | TTC < 3.0s | Maximum deceleration (-8.0 m/s^2) applied immediately |

**Mode transitions:**
- Cruise -> Follow: Lead vehicle detected in sensor data (t=30.0s)
- Follow -> Emergency: Time-to-collision drops below 3.0s threshold
- Emergency -> Follow: TTC recovers above threshold
- Follow -> Cruise: Lead vehicle no longer detected (t=130.0s)

### 1.3 Follow Mode Control Strategy

The follow mode uses a cascaded architecture:

1. **Distance PID** computes a speed adjustment based on the gap error:
   - Desired distance = `min_distance + time_headway * ego_speed` = `10.0 + 1.5 * v_ego`
   - Distance error = desired distance - actual distance
   - Speed adjustment = -PID_distance(distance_error)

2. **Speed PID** tracks the adjusted target speed:
   - Target speed = min(lead_speed + speed_adjustment, set_speed)
   - Speed error = target_speed - ego_speed
   - Acceleration = PID_speed(speed_error)

This cascaded approach allows the distance controller to modulate following speed while the speed controller ensures smooth acceleration/deceleration.

### 1.4 Safety Features

- **Emergency braking**: Full deceleration (-8.0 m/s^2) when TTC < 3.0s
- **Acceleration limits**: All commands clamped to [-8.0, 3.0] m/s^2
- **Speed floor**: Ego speed cannot go below 0 m/s
- **Anti-windup**: PID integral term clamped to prevent windup during saturation
- **PID reset on mode transitions**: Controllers reset when switching between cruise and follow modes, preventing integral accumulation from carrying over

## 2. PID Tuning Methodology

### 2.1 Approach

A two-phase grid search was used to find optimal gains:

**Phase 1 — Speed PID:** Tuned independently with a fixed distance PID. The search minimized a composite score of speed steady-state error, overshoot, and rise time, subject to hard constraints (rise time < 10s, overshoot < 5%).

**Phase 2 — Distance PID:** With the speed PID fixed from Phase 1, the distance PID was tuned to minimize distance steady-state error and ensure minimum following distance > 5m.

### 2.2 Search Spaces

| Parameter | Speed PID Range | Distance PID Range |
|-----------|----------------|-------------------|
| Kp | [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0] | [0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0] |
| Ki | [0.01, 0.05, 0.1, 0.2, 0.5, 1.0] | [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0] |
| Kd | [0.0, 0.1, 0.2, 0.5] | [0.0, 0.1, 0.5, 1.0, 2.0, 3.0, 4.0] |

### 2.3 Final Tuned Gains

| Controller | Kp | Ki | Kd |
|-----------|-----|-----|-----|
| **Speed PID** | 8.0 | 0.01 | 0.1 |
| **Distance PID** | 5.0 | 1.0 | 0.1 |

**Speed PID rationale:**
- High Kp (8.0) provides aggressive response to speed errors, ensuring the acceleration limit (3.0 m/s^2) is saturated during initial ramp-up for fast rise time.
- Low Ki (0.01) provides minimal but sufficient integral action to eliminate small steady-state errors without causing overshoot.
- Small Kd (0.1) adds light damping to reduce oscillation near the setpoint.

**Distance PID rationale:**
- High Kp (5.0) ensures strong proportional response to distance errors, rapidly adjusting the target speed offset.
- Significant Ki (1.0) eliminates persistent distance offset errors, critical for maintaining the desired following gap.
- Small Kd (0.1) provides mild derivative action to dampen oscillations from noisy lead vehicle speed data.

## 3. Simulation Results

### 3.1 Scenario Overview

The 150-second simulation covers four phases:

| Phase | Time (s) | Description |
|-------|----------|-------------|
| **Acceleration** | 0 - 10 | Ego accelerates from 0 to ~30 m/s |
| **Cruise** | 10 - 30 | Ego maintains set speed (30 m/s), no lead vehicle |
| **Follow** | 30 - 130 | Lead vehicle present; includes speed matching, lead acceleration, lead braking to stop, and recovery |
| **Cruise** | 130 - 150 | Lead vehicle gone; ego returns to set speed |

### 3.2 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10 s | 9.0 s | PASS |
| Speed overshoot | < 5% | 0.21% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.062 m/s | PASS |
| Distance steady-state error | < 2 m | 0.46 m | PASS |
| Minimum distance | > 5 m | 16.77 m | PASS |
| Simulation duration | 150 s | 150 s | PASS |

### 3.3 Mode Distribution

| Mode | Data Points | Percentage |
|------|------------|------------|
| Cruise | 501 | 33.4% |
| Follow | 983 | 65.5% |
| Emergency | 17 | 1.1% |

### 3.4 Phase Analysis

**Acceleration phase (t=0-10s):** The ego vehicle accelerates at the maximum rate (3.0 m/s^2) from standstill, reaching 27 m/s (90% of set speed) at t=9.0s. The high speed PID Kp ensures the controller saturates at maximum acceleration throughout this phase.

**Cruise phase (t=10-30s):** The ego maintains 30.06 m/s with negligible steady-state error (0.062 m/s). The slight overshoot of 0.21% (30.06 vs 30.0 m/s) is well within the 5% limit.

**Stable following (t=30-80s):** When the lead vehicle appears at t=30.0s traveling at ~25 m/s with 52.1m gap, the ACC transitions to follow mode and decelerates to match the lead speed. The distance controller maintains the desired gap (10 + 1.5 * v_ego) with an average error of 0.46m during steady following.

**Lead acceleration (t=80-95s):** The lead vehicle accelerates to ~36 m/s (above set speed). The ego vehicle maintains set speed (30 m/s) and the gap increases. This is expected correct behavior — the ego should not exceed set speed.

**Lead braking event (t=120-122s):** The lead vehicle brakes sharply to 0 m/s. The ACC detects the closing TTC and triggers emergency braking. The minimum distance of 16.77m maintains a safe margin above the 5m requirement.

**Recovery (t=122-130s):** After the lead vehicle resumes motion, the ego follows and gradually accelerates back. When the lead vehicle exits at t=130s, the ACC returns to cruise mode and converges to set speed.

### 3.5 Key Design Decisions

1. **Dynamic distance tracking**: Rather than using raw sensor distance data, the simulation tracks ego and lead positions independently. This produces realistic distance dynamics where the ego's ACC-controlled behavior determines the actual gap.

2. **Cascaded control**: The distance PID outputs a speed offset rather than a direct acceleration command. This avoids conflicts between the two controllers and provides smoother transitions.

3. **Conservative emergency threshold**: The 3.0s TTC threshold triggers emergency braking early enough to maintain a 16.77m minimum gap during the hard braking scenario, providing substantial safety margin.
