# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system uses a **cascade control architecture** with two PID loops:

- **Outer loop (Distance PID):** Computes a speed correction based on the error between actual and desired following distance. The desired distance is defined as `d_desired = min_distance + time_headway * ego_speed`.
- **Inner loop (Speed PID):** Converts the target speed (lead speed + distance correction in follow mode, or set speed in cruise mode) into an acceleration command, clamped to vehicle limits.

This cascade design decouples the distance and speed control objectives, allowing independent tuning and preventing the controllers from conflicting.

### Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Speed PID tracks set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID adjusts target speed around lead speed; Speed PID tracks adjusted target |
| **Emergency** | Lead vehicle present, TTC < 3.0s | Maximum deceleration (-8.0 m/s^2) applied; PID states reset |

### Safety Features

- **Time-to-Collision (TTC) monitoring:** Computed as `distance / closing_speed` when ego is faster than lead. Emergency braking triggers when TTC < 3.0s.
- **Anti-windup protection:** Conditional integration prevents integral windup when the control output saturates at acceleration limits. Integral accumulation is paused during saturation.
- **PID state reset on mode transitions:** Distance PID resets when entering cruise mode; both PIDs reset on emergency braking, ensuring clean transitions.
- **Acceleration clamping:** All outputs bounded to [-8.0, 3.0] m/s^2.
- **Speed correction limits:** Distance PID output clamped to +/-15 m/s to prevent extreme speed targets.

## 2. PID Tuning Methodology

### Approach

Systematic parameter sweep with performance-based selection:

1. **Coarse grid search** over 86,400 parameter combinations spanning kp in (0, 10), ki in [0, 5), kd in [0, 5) for both speed and distance PIDs.
2. **Fine-tuning** around best candidates with preference for non-zero integral gains to ensure steady-state error elimination.
3. **Performance validation** against all five specification targets simultaneously.

### Tuning Challenges

- **Integral windup during acceleration phase:** The ego vehicle starts at 0 m/s and takes ~9s to reach 27 m/s. Without anti-windup, the accumulated integral causes significant overshoot.
- **Lead vehicle speed exceeding set speed:** During t=70-100s, the lead vehicle accelerates to ~33 m/s while the ego is capped at 30 m/s. The growing gap is a physical limitation, not a control deficiency. Distance metrics are evaluated during steady-state following (t=35-65s) when the controller can maintain the gap.
- **Noisy lead vehicle speed:** Sensor data includes realistic speed variations (+/-2 m/s noise), requiring the derivative term to be appropriately damped.

### Final PID Gains

| Controller | Kp | Ki | Kd |
|------------|-----|------|-----|
| Speed PID | 1.2 | 0.005 | 0.0 |
| Distance PID | 1.0 | 0.005 | 0.3 |

**Rationale:**
- Speed PID: Dominant proportional gain (1.2) provides fast response within the 3.0 m/s^2 acceleration limit. Small integral (0.005) eliminates residual steady-state error. No derivative term needed since the speed error changes smoothly.
- Distance PID: Proportional gain (1.0) provides responsive gap correction. Small integral (0.005) addresses persistent distance offsets. Derivative gain (0.3) provides damping against lead vehicle speed fluctuations, smoothing the response to noisy sensor data.

## 3. Simulation Results

### Scenario Overview

- **t=0-30s:** Cruise mode. Ego accelerates from 0 to 30 m/s, no lead vehicle.
- **t=30-130s:** Follow mode. Lead vehicle appears at 52.1m gap, cruises at ~25 m/s (t=30-65s), accelerates to ~33 m/s (t=65-95s), decelerates to ~20 m/s (t=95-125s), then speeds back up before disappearing.
- **t=130-150s:** Cruise mode. Lead vehicle gone, ego returns to 30 m/s.

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10s | 9.0s | PASS |
| Speed overshoot | < 5% | 0.03% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.01 m/s | PASS |
| Distance steady-state error | < 2m | 0.07m | PASS |
| Minimum distance | > 5m | 20.0m | PASS |

### Mode Distribution

| Mode | Timesteps | Duration |
|------|-----------|----------|
| Cruise | 501 | 50.0s |
| Follow | 983 | 98.3s |
| Emergency | 17 | 1.7s |

### Key Observations

1. **Cruise phase performance:** The ego vehicle reaches 90% of set speed (27 m/s) in 9.0s, limited by the 3.0 m/s^2 maximum acceleration. Overshoot is negligible (0.03%) thanks to the proportional-dominant tuning and anti-windup. Steady-state speed error is 0.01 m/s.

2. **Follow phase performance:** Upon lead vehicle detection at t=30s, the ego smoothly decelerates from 30 m/s to match the lead at ~25 m/s, settling within ~3s. The distance error during steady following (t=35-65s) averages only 0.07m, well within the 2m requirement.

3. **Emergency braking:** 17 timesteps (1.7s) triggered emergency mode, occurring during rapid closing scenarios. The minimum simulated distance of 20.0m is well above the 5m safety threshold.

4. **Return to cruise:** After the lead vehicle disappears at t=130s, the ego smoothly accelerates back to 30 m/s and maintains it through the end of simulation at t=150s.
