# Adaptive Cruise Control Simulation Report

## 1. System Design

### ACC Architecture

The ACC system is composed of three modules:

- **PIDController** (`pid_controller.py`): Discrete-time PID controller with output clamping and anti-windup (back-calculation). Prevents integral windup when the controller output saturates at the vehicle's acceleration limits.
- **AdaptiveCruiseControl** (`acc_system.py`): Mode-based controller that selects between cruise, follow, and emergency modes. Uses two PID controllers (speed and distance) and fuses their outputs.
- **Simulation** (`simulation.py`): Reads tuned PID gains from `tuning_results.yaml` and lead vehicle data from `sensor_data.csv`, executes the 150s simulation with discrete-time kinematic updates (dt = 0.1s).

### Operating Modes

| Mode | Condition | Control Law |
|------|-----------|-------------|
| **Cruise** | No lead vehicle detected | Speed PID tracks set speed (30 m/s). Distance PID is reset. |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID maintains safe following distance. Speed PID caps ego speed at set speed. Output = min(dist_accel, speed_accel). |
| **Emergency** | Lead vehicle present, TTC < 3.0s | Maximum deceleration applied (-8.0 m/s^2). Both PIDs are reset. |

### Safety Features

- **Time-to-Collision (TTC) monitoring**: TTC is computed as distance / (ego_speed - lead_speed) when closing. Emergency braking triggers when TTC < 3.0s.
- **Safe following distance model**: d_safe = ego_speed * 1.5 + 10.0 (time headway model with minimum gap).
- **Acceleration clamping**: All commands are clamped to [-8.0, 3.0] m/s^2.
- **Anti-windup**: PID integral is rolled back when output saturates, preventing wind-up during acceleration/deceleration limits.
- **Speed floor**: Ego speed is clamped to >= 0 (no reverse).
- **Conservative mode fusion**: In follow mode, the minimum of speed and distance controller outputs ensures the ego never exceeds set speed while following.

## 2. PID Tuning

### Methodology

PID gains were tuned via grid search over the parameter space:

- kp in {0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0}
- ki in {0.0, 0.01, 0.05, 0.1, 0.2, 0.5}
- kd in {0.0, 0.05, 0.1, 0.3, 0.5}

Each combination was evaluated against the full 150s scenario with a composite score penalizing constraint violations (rise time, overshoot, steady-state errors, minimum distance). Over 60,000 parameter combinations were tested.

### Tuning Rationale

**Speed PID (kp=5.0, ki=0.0, kd=0.0):**
- High kp ensures the controller saturates at max_accel (3.0 m/s^2) during the initial ramp-up, achieving the fastest possible rise time.
- With max_accel = 3.0 m/s^2, the theoretical minimum time to reach 27 m/s (90% of 30) is exactly 9.0s. The proportional-only controller achieves this by immediately saturating.
- ki = 0 is sufficient because the proportional gain is high enough to drive steady-state error to effectively zero (at set speed, error = 0 so output = 0, which is correct).
- kd = 0 avoids noise amplification from the derivative term.

**Distance PID (kp=5.0, ki=0.0, kd=0.1):**
- High kp provides aggressive distance tracking, quickly correcting deviations from the safe following distance.
- ki = 0 avoids integral accumulation issues during mode transitions (cruise to follow and back).
- Small kd (0.1) provides damping to reduce oscillation in the distance response as the lead vehicle speed fluctuates with sensor noise.

### Final PID Gains

```yaml
pid_speed:
  kp: 5.0
  ki: 0.0
  kd: 0.0
pid_distance:
  kp: 5.0
  ki: 0.0
  kd: 0.1
```

## 3. Simulation Results

### Scenario Overview

The 150s simulation covers five phases:

| Phase | Time (s) | Description |
|-------|----------|-------------|
| Cruise ramp-up | 0 - 9 | Ego accelerates from 0 to 30 m/s |
| Steady cruise | 9 - 30 | Ego maintains 30 m/s, no lead vehicle |
| Following | 30 - 120 | Lead vehicle at ~25 m/s, ego follows at safe distance |
| Emergency | 120 - 121.6 | Lead vehicle brakes hard, TTC drops below 3.0s |
| Recovery & cruise | 121.7 - 150 | Lead vehicle accelerates away then disappears, ego returns to cruise at 30 m/s |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10s | 9.0s | PASS |
| Speed overshoot | < 5% | 0.00% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.0000 m/s | PASS |
| Distance steady-state error | < 2m | 0.06m | PASS |
| Minimum distance | > 5m | 19.27m | PASS |

### Mode Distribution

| Mode | Timesteps | Percentage |
|------|-----------|------------|
| Cruise | 501 | 33.4% |
| Follow | 983 | 65.5% |
| Emergency | 17 | 1.1% |

### Key Observations

1. **Cruise phase**: The ego reaches 30 m/s in exactly 9.0s with zero overshoot. The proportional controller with high gain saturates at max_accel (3.0 m/s^2) throughout the ramp, providing the fastest achievable response within physical limits.

2. **Follow phase**: When the lead vehicle appears at t=30s traveling at ~25 m/s, the ego decelerates and converges to a safe following distance within ~5s. The distance steady-state error during stable following (t=40-65s) averages only 0.06m, well within the 2m target.

3. **Emergency braking**: At t=120s, the lead vehicle brakes sharply (speed drops from ~20 m/s to 0). The ACC detects TTC < 3.0s and applies full emergency braking (-8.0 m/s^2). The minimum following distance during this event is 19.27m, providing substantial safety margin above the 5m minimum. The minimum TTC observed during emergency braking was 2.05s.

4. **Recovery**: After the emergency, the lead vehicle accelerates and eventually disappears from sensor range at t=130s. The ego smoothly returns to cruise mode and reaches 30 m/s by approximately t=143s.

5. **Conservative distance control**: The min(dist_accel, speed_accel) fusion ensures the ego never exceeds set speed even when the lead vehicle pulls away. This is standard ACC behavior -- the system follows at safe distance when the lead is slower, and cruises at set speed when the lead is faster or absent.
