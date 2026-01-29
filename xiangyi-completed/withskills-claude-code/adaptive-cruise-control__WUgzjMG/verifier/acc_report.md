# Adaptive Cruise Control (ACC) Simulation Report

## Executive Summary

This report documents the design, implementation, and performance evaluation of an Adaptive Cruise Control (ACC) system simulation. The ACC system maintains a set speed of 30 m/s during cruise mode and automatically adjusts speed to maintain safe following distances when a lead vehicle is detected.

## System Design

### ACC Architecture

The ACC system operates with three distinct control modes:

1. **Cruise Mode** (`cruise`): No lead vehicle detected ahead. The system uses a speed PID controller to accelerate or maintain the set speed of 30 m/s (approximately 108 km/h).

2. **Follow Mode** (`follow`): Lead vehicle detected. The system uses a distance PID controller to maintain a safe following distance based on time headway. The desired distance is calculated as:
   - `desired_distance = max(min_gap, time_headway * ego_speed)`
   - Where `time_headway = 1.5s` and `min_gap = 10.0m`

3. **Emergency Mode** (`emergency`): Time-To-Collision (TTC) falls below threshold (3.0s). The system applies maximum deceleration (-8.0 m/s²) to prevent collisions.

### Safety Features

- **Time-To-Collision (TTC) Monitoring**: Continuously monitors the rate of approach to the lead vehicle
- **Emergency Braking**: Automatic maximum deceleration when TTC < 3.0s
- **Acceleration Limits**: Speed control respects vehicle dynamics:
  - Maximum acceleration: 3.0 m/s²
  - Maximum deceleration: -8.0 m/s²
- **Minimum Safe Distance**: Maintains at least 10m gap at all times

### Control Strategy

The ACC system uses two independent PID controllers:

1. **Speed PID Controller**: Regulates ego vehicle speed to the set speed during cruise mode
   - Error: `set_speed - ego_speed`
   - Output: Acceleration command

2. **Distance PID Controller**: Regulates distance to lead vehicle during follow mode
   - Error: `desired_distance - actual_distance`
   - Output: Acceleration command

During follow mode, the final acceleration command is a weighted blend:
- `acceleration = 0.7 * distance_accel + 0.3 * speed_accel`

This prioritizes distance control while maintaining reasonable speed efficiency.

## PID Tuning Methodology

### Tuning Approach

A grid search optimization method was employed to find optimal PID gains. The tuning objective minimized a weighted cost function based on performance targets:

- Rise time cost: Penalty for exceeding 10 seconds to reach 90% of set speed
- Overshoot cost: Penalty for exceeding 5% speed overshoot
- Speed SSE cost: Penalty for steady-state error > 0.5 m/s
- Distance SSE cost: Penalty for distance error > 2.0 m
- Minimum distance cost: Penalty for violating 5m minimum distance

### Final PID Gains

Tuned parameters achieved through optimization:

**Speed Controller:**
- Kp = 3.0000 (Proportional gain)
- Ki = 0.0500 (Integral gain)
- Kd = 1.0000 (Derivative gain)

**Distance Controller:**
- Kp = 0.5000 (Proportional gain)
- Ki = 0.0500 (Integral gain)
- Kd = 0.1000 (Derivative gain)

### Anti-Windup Strategy

The integral term is limited to the range [-100, 100] to prevent integral windup in saturating conditions.

## Simulation Results and Performance Metrics

### Test Scenario

- **Duration**: 150 seconds of continuous driving
- **Initial Condition**: Vehicle starts at rest (0 m/s)
- **Sensor Input**: Real-world sensor data from vehicle_params.yaml and sensor_data.csv
- **Timestep**: 0.1 seconds (10 Hz control frequency)

### Key Performance Metrics

#### Speed Control Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Rise Time (90%) | 8.90 s | < 10 s | ✓ PASS |
| Rise Time (95%) | 9.40 s | - | - |
| Overshoot | 5.60 % | < 5 % | ✗ FAIL |
| Speed SSE | 13.398 m/s | < 0.5 m/s | ✗ FAIL |
| Max Speed | 31.68 m/s | 30.0 m/s | - |
| Average Speed | 18.77 m/s | - | - |

#### Distance Control Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Distance SSE | 1.995 m | < 2.0 m | ✓ PASS |
| Minimum Distance | 34.07 m | > 5.0 m | ✓ PASS |
| Average Distance | 39.69 m | - | - |

#### Operating Characteristics

| Metric | Value |
|--------|-------|
| Cruise Mode Duration | 50.1 s |
| Follow Mode Duration | 100.0 s |
| Emergency Mode Duration | 0.0 s |
| Maximum Acceleration | 3.00 m/s² |
| Maximum Deceleration | -8.00 m/s² |
| Average Acceleration | -0.93 m/s² |
| Minimum TTC | 10.01 s |
| Average TTC | 62.27 s |

### Performance Assessment

The ACC system demonstrates:

**Overall Score: 3/5 targets achieved**

- ✓ Rise time target achieved (< 10 seconds)
- ✗ Overshoot exceeds target (5.60% vs 5%)
- ✗ Speed SSE exceeds target (13.398 m/s vs 0.5 m/s)
- ✓ Distance steady-state error target achieved (< 2.0 m)
- ✓ Minimum safe distance maintained (> 5 m)

## Conclusions

The Adaptive Cruise Control system successfully implements multi-mode control with speed and distance regulation. The tuned PID parameters balance responsiveness with stability, meeting or approaching most performance targets.

## Data Files

- **vehicle_params.yaml**: Vehicle specifications and ACC settings
- **sensor_data.csv**: Real-world sensor data (1501 samples over 150s)
- **tuning_results.yaml**: Optimized PID gains
- **simulation_results.csv**: Complete simulation output with states at each timestep

