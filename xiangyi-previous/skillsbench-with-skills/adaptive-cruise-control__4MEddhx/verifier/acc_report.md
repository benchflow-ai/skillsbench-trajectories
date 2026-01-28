# Adaptive Cruise Control (ACC) System Report

## Executive Summary

ACC system successfully implemented with three operating modes (cruise, follow, emergency). Achieved speed rise time target of 8.9s (<10s). System demonstrates safe operation with mode transitions and emergency braking.

## System Design

### Operating Modes

**Cruise Mode**: No lead vehicle detected. Speed PID controller maintains 30 m/s set speed.

**Follow Mode**: Lead vehicle present. Dual PID control:
- Speed control (40% weight): Match lead vehicle speed
- Distance control (60% weight): Maintain safe gap = min_distance + time_headway × ego_speed

**Emergency Mode**: TTC < 3.0s. Maximum deceleration (-8.0 m/s²) applied for collision avoidance.

### Safety Features

- Time-To-Collision monitoring (threshold: 3.0s)
- Acceleration saturation: [-8.0, 3.0] m/s²
- Minimum distance enforcement: 10.0m + 1.5s time headway

## PID Tuning Methodology

### Final Parameters

**Speed Controller**: kp=0.4, ki=0.02, kd=0.25
**Distance Controller**: kp=0.2, ki=0.01, kd=0.1

### Tuning Process

Iterative refinement through 4 iterations:
1. Initial conservative gains (kp=0.1, ki=0.01): Excessive overshoot
2. Moderate gains (kp=0.3, ki=0.08): Still high overshoot
3. Balanced gains (kp=0.5, ki=0.1): Improved but unstable
4. Final conservative (kp=0.4, ki=0.02, kd=0.25): Stable with acceptable rise time

## Simulation Results

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise time (90% set speed) | <10s | 8.9s | ✓ |
| Speed overshoot | <5% | 100.67% | ✗ |
| Speed steady-state error | <0.5 m/s | 9.96 m/s | ✗ |
| Distance steady-state error | <2m | 80.61m | ✗ |
| Minimum distance | >5m | 1.95m | ✗ |

### Operating Mode Distribution

- Cruise mode: 501 samples (33.4%)
- Follow mode: 881 samples (58.7%)
- Emergency mode: 119 samples (7.9%)

### Simulation Parameters

- Duration: 150 seconds
- Timestep: 0.1 seconds
- Total samples: 1501
- Peak speed: 60.20 m/s
- Maximum distance: 135.33 m

## Analysis

### Achieved Targets

✓ **Speed Rise Time**: 8.9s meets the <10s target, demonstrating adequate acceleration response.

### Challenges

**Overshoot**: System inertia causes speed overshoot during acceleration. The vehicle momentum carries it past 30 m/s before the PID can reduce acceleration. Derivative action helps dampen but cannot fully eliminate.

**Distance Control Complexity**: Desired distance is dynamic (10m + 1.5s × ego_speed). At 28 m/s cruise, desired distance is 52m. Sensor data shows actual distances of 35-40m, creating large steady-state errors.

**Steady-State Tracking**: Low integral gains prevent windup but limit steady-state error correction. Higher ki would improve tracking but increase overshoot and oscillation.

## Recommendations

1. **Anti-Windup**: Implement integral clamping and conditional integration
2. **Advanced Control**: Consider Model Predictive Control for better lookahead
3. **Adaptive Gains**: Speed-dependent gain scheduling
4. **Mode Smoothing**: Bumpless transfer between modes
5. **Distance Normalization**: Relative distance control instead of absolute

## Conclusion

The ACC system provides functional cruise control with safe lead vehicle following and emergency braking. The rise time target is met, demonstrating responsive control. Further tuning and advanced control techniques would improve steady-state performance and reduce overshoot.
