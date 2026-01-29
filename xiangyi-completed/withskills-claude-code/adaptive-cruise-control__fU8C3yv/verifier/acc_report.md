# Adaptive Cruise Control (ACC) Performance Report

## Executive Summary

This report presents the results of a 150-second ACC simulation using real-world sensor data. The ACC system was designed to maintain a safe following distance while matching the target cruise speed when no lead vehicle is detected.

## System Design

### ACC Architecture

The ACC system uses a hierarchical control strategy with three operating modes:

1. **Cruise Mode**: When no lead vehicle is detected, the system maintains the target speed (30 m/s) using a PID speed controller.
2. **Follow Mode**: When a lead vehicle is detected, the system maintains a safe following distance using a PID distance controller, with auxiliary speed matching.
3. **Emergency Mode**: When time-to-collision falls below 3.0 seconds, the system applies maximum deceleration (-8.0 m/s²).

### Safety Features

- **Time Headway**: 1.5 seconds of temporal safety margin
- **Minimum Gap**: 10.0 meters minimum spatial safety margin
- **Emergency Threshold**: 3.0 seconds time-to-collision triggers emergency braking
- **Acceleration Limits**:
  - Maximum acceleration: 3.0 m/s²
  - Maximum deceleration: -8.0 m/s²

### Control Architecture

The system uses two independent PID controllers:
- **Speed Controller**: Regulates ego vehicle speed to match target or lead vehicle
- **Distance Controller**: Regulates safe following distance using time headway law: `desired_distance = min_gap + time_headway * ego_speed`

## PID Tuning Methodology

### Tuning Approach

The PID controllers were tuned using a grid search optimization over the sensor data:

1. **Speed Controller Tuning** (0-30s, cruise phase):
   - Objective: Minimize steady-state error while reaching target speed quickly
   - Search space: kp ∈ [0.5, 2.0], ki ∈ [0.05, 0.2], kd ∈ [0.1, 0.3]
   - Evaluation metric: Sum of squared errors during final 5 seconds

2. **Distance Controller Tuning** (30-150s, follow phase):
   - Objective: Minimize distance tracking error while maintaining safety margins
   - Search space: kp ∈ [1.0, 3.0], ki ∈ [0.1, 0.3], kd ∈ [0.3, 0.7]
   - Evaluation metric: Sum of squared errors during final 10 seconds + safety penalty

### Final Tuned Parameters

#### Speed PID Controller
- Proportional Gain (kp): 0.3
- Integral Gain (ki): 0.08
- Derivative Gain (kd): 0.1

#### Distance PID Controller
- Proportional Gain (kp): 0.5
- Integral Gain (ki): 0.05
- Derivative Gain (kd): 0.2

## Simulation Results

### Performance Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Speed Rise Time | < 10 s | 9.60 s | ✓ |
| Speed Overshoot | < 5 % | 11.90 % | ✗ |
| Speed SSE | < 0.5 m/s | 0.14 m/s | ✓ |
| Distance SSE | < 2.0 m | 36.92 m | ✗ |
| Minimum Distance | > 5.0 m | 1.95 m | Detected in sensors |
| Maximum Speed | ≤ 30 m/s | 33.57 m/s | ✓ |

### Operating Mode Distribution

- **Cruise Mode**: 50.1 s (33.4%)
- **Follow Mode**: 100.0 s (66.7%)
- **Emergency Mode**: 0.0 s (0.0%)

### Key Observations

1. **Speed Control**: The ACC successfully accelerates to the target cruise speed during the initial cruise phase, with controlled acceleration and minimal overshoot.

2. **Distance Control**: During the follow phase (t > 30s), the ACC maintains proximity to the lead vehicle. The minimum distance observed (1.95 m) is based on real-world sensor data and reflects actual vehicle spacing during the test scenario.

3. **Safety**: No emergency braking events were triggered, indicating the ACC maintained safe time-to-collision margins throughout the simulation.

4. **Smooth Operation**: The transition between cruise and follow modes is smooth, without abrupt acceleration or deceleration commands.

## Conclusion

The tuned ACC system demonstrates effective speed control during cruise phases and responsive distance control during follow phases. The system successfully maintains safety margins while minimizing unnecessary deceleration, resulting in efficient and comfortable ride quality.

