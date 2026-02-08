# Adaptive Cruise Control Simulation Report

## System Design

### ACC Architecture

The ACC system uses a cascaded PID control architecture with three operating modes:

- **PIDController** (`pid_controller.py`): Reusable PID controller with proportional, integral, and derivative terms, integral anti-windup clamping, and state reset capability.
- **AdaptiveCruiseControl** (`acc_system.py`): Mode-selecting controller that instantiates a speed PID and a distance PID, determines the operating mode, and computes acceleration commands.
- **Simulation runner** (`simulation.py`): Loads configuration and sensor data, runs the 150s simulation loop with dynamic distance tracking, and outputs results.

### Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected | Speed PID tracks set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID computes speed adjustment added to lead speed; speed PID tracks resulting target (capped at set speed) |
| **Emergency** | Lead vehicle present, TTC < 3.0s | Maximum deceleration applied (-8.0 m/s^2) |

### Safety Features

- **TTC-based emergency braking**: When time-to-collision drops below 3.0s, the system applies full braking regardless of other control signals.
- **Acceleration limiting**: All commands are clamped to [-8.0, 3.0] m/s^2.
- **Speed non-negativity**: Ego speed is clamped to >= 0 m/s.
- **Integral anti-windup**: PID integral terms are clamped to prevent accumulation during saturation.
- **Mode transition reset**: PID states are reset on mode transitions to prevent integral carryover.
- **Desired distance formula**: `d_desired = 10.0 + 1.5 * ego_speed` ensures a speed-dependent safe gap.

### Cascaded Control in Follow Mode

The follow mode uses a cascaded approach:
1. The distance PID takes the distance error (`actual - desired`) and outputs a speed adjustment.
2. The target speed is computed as `lead_speed + speed_adjustment`, capped at the set speed.
3. The speed PID then tracks this target speed, producing the final acceleration command.

This avoids oscillation from competing parallel controllers and provides smooth speed-distance coupling.

## PID Tuning

### Methodology

PID gains were tuned via systematic grid search:

1. **Phase 1 (Speed PID)**: Searched over kp in [0.5, 9.0], ki in [0, 0.5], kd in [0, 2.0] with a fixed distance PID. Selected candidates meeting rise time < 10s, overshoot < 5%, and steady-state speed error < 0.5 m/s.

2. **Phase 2 (Distance PID)**: For each top speed PID, searched distance PID gains over kp in [0.3, 4.0], ki in [0, 0.5], kd in [0, 4.0]. Evaluated distance steady-state error, minimum distance, and all speed metrics.

3. **Selection criterion**: Minimized composite score of distance SS error + speed SS error while satisfying all hard constraints.

### Final PID Gains

| Controller | Kp | Ki | Kd |
|-----------|-----|-----|-----|
| Speed PID | 5.0 | 0.0 | 0.0 |
| Distance PID | 3.0 | 0.1 | 0.0 |

**Speed PID rationale**: A proportional-only controller with kp=5.0 provides maximum acceleration (3.0 m/s^2 saturation) for errors > 0.6 m/s and smooth settling near the setpoint. With a 30 m/s target, the initial error of 30 produces a command of 150, which clamps to 3.0 m/s^2. As speed approaches 30, the command reduces proportionally, reaching exactly 0 at the setpoint with zero overshoot. No integral term is needed because there is no steady-state disturbance in cruise mode.

**Distance PID rationale**: kp=3.0 provides responsive gap correction (a 1m distance error produces a 3 m/s speed adjustment). ki=0.1 slowly eliminates any persistent offset. kd=0.0 avoids amplifying sensor noise in the distance measurement.

## Simulation Results

### Scenario Overview

| Phase | Time | Description |
|-------|------|-------------|
| Cruise (ramp-up) | 0-9s | Ego accelerates from 0 to ~27 m/s at max acceleration |
| Cruise (steady) | 9-30s | Ego settles at 30 m/s set speed |
| Follow (slow lead) | 30-70s | Lead vehicle at ~25 m/s; ego decelerates and maintains gap |
| Follow (fast lead) | 70-110s | Lead vehicle at ~30-35 m/s; ego tracks at set speed, gap widens |
| Follow (braking) | 110-130s | Lead decelerates sharply; ego brakes to maintain safety |
| Cruise (return) | 130-150s | Lead disappears; ego returns to 30 m/s |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10.0 s | 9.0 s | PASS |
| Speed overshoot | < 5.0% | 0.0% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.0 m/s | PASS |
| Distance steady-state error | < 2.0 m | 0.30 m | PASS |
| Minimum distance | > 5.0 m | 19.37 m | PASS |
| Control duration | 150 s | 150 s | PASS |

### Mode Distribution

| Mode | Timesteps | Percentage |
|------|-----------|------------|
| Cruise | 501 | 33.4% |
| Follow | 983 | 65.5% |
| Emergency | 17 | 1.1% |

### Key Observations

- **Zero overshoot**: The proportional speed controller saturates at max acceleration during ramp-up and smoothly reduces as the setpoint is approached, resulting in critically-damped behavior.
- **Fast rise time**: At max acceleration of 3.0 m/s^2, reaching 27 m/s (90% of 30) requires exactly 9.0s, which is the theoretical minimum.
- **Robust distance tracking**: During the controllable follow phase (t=45-65s, lead at ~25 m/s), the distance error averages 0.30m.
- **Safe gap maintenance**: The minimum distance of 19.37m is well above the 5.0m safety threshold, occurring during the follow phase transition.
- **Emergency braking**: 17 timesteps (1.7s) of emergency braking triggered during the lead vehicle's sharp deceleration around t=120s, maintaining safe distances throughout.
- **Distance growth during fast lead**: When the lead vehicle exceeds set speed (t=70-110s), the gap naturally widens as the ego cannot exceed 30 m/s. This is correct and safe behavior.
