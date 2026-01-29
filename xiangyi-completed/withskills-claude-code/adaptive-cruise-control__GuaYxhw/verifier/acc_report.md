# Adaptive Cruise Control (ACC) System Report

## System Design

### ACC Architecture

The ACC system implements a cascaded control architecture with three operating modes:

1. **Cruise Mode**: Activated when no lead vehicle is detected. Uses a PID speed controller to maintain the set speed of 30 m/s.

2. **Follow Mode**: Activated when a lead vehicle is detected. Uses a distance PID controller to compute speed adjustments, combined with proportional speed matching to smoothly follow the lead vehicle while maintaining safe distance.

3. **Emergency Mode**: Activated when Time-To-Collision (TTC) falls below 3.0 seconds. Applies maximum braking (-8.0 m/s^2) until the situation is safe.

### Control Flow

```
Sensor Data -> Mode Selection -> Controller -> Acceleration Command -> Vehicle Dynamics
                    |
                    v
            [Cruise] -> Speed PID -> Target: set_speed (30 m/s)
            [Follow] -> Distance PID + Speed Matching -> Target: safe following distance
            [Emergency] -> Maximum Braking -> Target: avoid collision
```

### Safety Features

1. **Time-To-Collision Monitoring**: Continuously calculates TTC and triggers emergency braking when TTC < 3.0s
2. **Minimum Distance Protection**: Applies additional braking when distance falls below minimum gap (10m)
3. **Speed Limiting**: Never exceeds set speed even when lead vehicle is faster
4. **Acceleration Clamping**: All commands clamped to vehicle limits [-8.0, 3.0] m/s^2
5. **Controller Reset on Mode Transitions**: Prevents integral windup when switching modes

## PID Tuning Methodology

### Speed Controller

The speed controller maintains the target speed in cruise mode and assists with speed matching in follow mode.

**Tuning approach:**
- Started with proportional-only control to establish baseline response
- Added derivative term to dampen overshoot
- Added small integral term to eliminate steady-state error
- Reduced integral limit (anti-windup) to prevent windup during transitions

**Final gains:**
- Kp = 0.5: Provides responsive acceleration/deceleration
- Ki = 0.012: Small integral for steady-state accuracy without excessive windup
- Kd = 0.35: Dampens oscillations and reduces overshoot

### Distance Controller

The distance controller maintains safe following distance in follow mode.

**Tuning approach:**
- Used lower gains than speed controller to avoid oscillations
- Higher derivative term to react quickly to closing distance
- Moderate integral to reduce steady-state distance error
- Combined with 0.3x proportional speed matching for smooth following

**Final gains:**
- Kp = 0.15: Moderate response to distance errors
- Ki = 0.012: Sufficient integral to reduce steady-state error
- Kd = 0.2: Provides damping and quick response to rate changes

### Key Tuning Insights

1. **Anti-windup is critical**: Integral windup during long cruise periods caused significant overshoot. Clamping integral to +/-50 and resetting on mode transitions resolved this.

2. **Speed matching aids stability**: Adding 30% proportional speed matching (tracking lead vehicle speed) significantly reduced oscillations in follow mode.

3. **Cascaded control works well**: Using distance error to adjust target speed, then using speed controller to track that target, provides stable two-stage control.

## Simulation Results

### Performance Metrics Summary

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed Rise Time | < 10s | 9.5s | PASS |
| Speed Overshoot | < 5% | 3.5% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.04 m/s | PASS |
| Distance Steady-State Error | < 2m | 1.27m | PASS |
| Minimum Distance | > 5m | 9.03m | PASS |

### Scenario Analysis

**Phase 1 (t=0-30s): Initial Cruise**
- Vehicle accelerates from 0 to 30 m/s
- Achieves 90% of target speed (27 m/s) at t=9.5s
- Settles to steady cruise with minimal overshoot (3.5%)

**Phase 2 (t=30-60s): Stable Following**
- Lead vehicle detected at 52m distance, traveling at ~25 m/s
- ACC transitions to follow mode
- Ego vehicle decelerates to match lead speed
- Maintains average distance error of 1.27m in stable period

**Phase 3 (t=60-100s): Lead Accelerating**
- Lead vehicle accelerates beyond set speed (30+ m/s)
- ACC maintains set speed, allowing gap to increase
- Correct behavior: ACC doesn't exceed set speed

**Phase 4 (t=100-120s): Lead Decelerating**
- Lead vehicle decelerates
- ACC gradually closes gap while maintaining safe distance

**Phase 5 (t=120-122s): Emergency Braking**
- Lead vehicle performs hard braking (deceleration from ~20 to 0 m/s)
- TTC drops below threshold, triggering emergency mode
- Maximum braking applied
- Minimum distance maintained at 9.03m (above 5m requirement)

**Phase 6 (t=122-130s): Recovery**
- Lead vehicle accelerates again
- ACC exits emergency mode, resumes following
- Smooth transition to cruise when lead disappears at t=130s

**Phase 7 (t=130-150s): Return to Cruise**
- No lead vehicle detected
- ACC accelerates back to set speed
- Settles at 30 m/s for remainder of simulation

### Control Duration

Total simulation duration: 150 seconds (1501 timesteps at 0.1s intervals)

## Files Generated

1. **pid_controller.py**: PID controller class with anti-windup
2. **acc_system.py**: ACC system with three operating modes
3. **simulation.py**: Simulation runner and analysis functions
4. **tuning_results.yaml**: Final tuned PID gains
5. **simulation_results.csv**: 1501 rows of simulation output
6. **acc_report.md**: This report

## Conclusions

The ACC system successfully meets all performance targets:
- Fast response (rise time < 10s) while maintaining low overshoot (< 5%)
- Accurate speed control (steady-state error < 0.5 m/s)
- Stable distance following (steady-state error < 2m)
- Safe emergency response (minimum distance > 5m)

The cascaded control architecture with mode-based operation provides a robust and safe adaptive cruise control system suitable for real-world driving scenarios.
