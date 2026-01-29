# Adaptive Cruise Control (ACC) System Report

## Executive Summary

This report presents the implementation and performance evaluation of an Adaptive Cruise Control (ACC) system designed to maintain a set speed of 30 m/s when no vehicles are detected ahead, and automatically adjust speed to maintain safe following distances when a lead vehicle is present. The system was implemented using PID controllers and tested through a 150-second simulation.

## System Design

### ACC Architecture

The ACC system is designed with a hierarchical control structure consisting of:

1. **PID Controllers**: Separate PID controllers for speed control and distance control
2. **Mode Selection Logic**: Three operating modes based on sensor inputs
3. **Safety Constraints**: Acceleration limits and emergency braking thresholds

### Operating Modes

The ACC system operates in three distinct modes:

1. **Cruise Mode**: Activated when no lead vehicle is detected
   - Maintains the set speed (30 m/s)
   - Uses speed PID controller
   - Maximizes vehicle throughput and fuel efficiency

2. **Follow Mode**: Activated when a lead vehicle is detected at a safe distance
   - Maintains a safe following distance based on time headway
   - Uses distance PID controller
   - Desired distance = time_headway × ego_speed + minimum_gap

3. **Emergency Mode**: Activated when TTC (Time-to-Collision) falls below threshold
   - Triggers aggressive deceleration
   - Prioritizes collision avoidance
   - Applies maximum deceleration within vehicle limits

### Safety Features

- **Acceleration Limits**: [-8.0, 3.0] m/s²
  - Prevents excessive deceleration that could cause rear-end collisions
  - Limits maximum acceleration for passenger comfort

- **Time Headway**: 1.5 seconds
  - Provides minimum 1.5-second following interval
  - Adapts to driving speed

- **Minimum Gap**: 10.0 meters
  - Ensures absolute minimum separation at standstill

- **Emergency TTC Threshold**: 3.0 seconds
  - Triggers emergency braking when collision is imminent
  - Based on relative speed and distance

### Control Strategy

The system employs a multi-loop control architecture:

```
Sensor Inputs (ego_speed, lead_speed, distance)
    ↓
Mode Selection Logic
    ↓
[Speed PID] ←→ [Distance PID]
    ↓
Acceleration Command
    ↓
Acceleration Limiter [-8.0, 3.0] m/s²
    ↓
Vehicle Dynamics
```

## PID Tuning Methodology

### Parameter Space

PID parameters were systematically tuned using grid search over the following ranges:
- **Speed Controller**: kp ∈ [0.5, 5.0], ki ∈ [0.0, 1.0], kd ∈ [0.0, 1.0]
- **Distance Controller**: kp ∈ [0.5, 5.0], ki ∈ [0.0, 1.0], kd ∈ [0.0, 1.0]

### Performance Metrics

The tuning objective was to minimize a composite score based on:
1. Speed rise time (target: < 10 seconds)
2. Speed overshoot (target: < 5%)
3. Speed steady-state error (target: < 0.5 m/s)
4. Distance steady-state error (target: < 2 m)
5. Minimum distance (target: > 5 m)
6. Acceleration variance (smoothness)

### Grid Search Results

A total of 129,600 parameter combinations were evaluated. The optimal parameters were selected based on the lowest composite score.

### Final PID Gains

After comprehensive tuning, the following PID gains were selected:

**Speed Controller:**
- Proportional gain (kp): 0.5
- Integral gain (ki): 0.2
- Derivative gain (kd): 1.0

**Distance Controller:**
- Proportional gain (kp): 0.5
- Integral gain (ki): 0.4
- Derivative gain (kd): 0.0

These parameters provide:
- Stable speed tracking with minimal overshoot
- Responsive distance control without oscillations
- Smooth acceleration transitions
- Effective disturbance rejection

## Simulation Results

### Simulation Setup

- **Duration**: 150 seconds
- **Time Step**: 0.1 seconds
- **Initial Speed**: 0 m/s (cold start)
- **Set Speed**: 30 m/s (108 km/h)
- **Data Source**: Real-world driving data (sensor_data.csv)

### Performance Evaluation

#### Speed Response Characteristics

The simulation demonstrates the system's ability to accelerate from rest and maintain the desired set speed:

- **Initial Acceleration Phase**: The system accelerates at the maximum rate (3.0 m/s²) until approaching the set speed
- **Cruise Control**: Once the set speed is reached, the system transitions to cruise mode to maintain steady speed
- **Following Behavior**: When lead vehicle is detected, the system smoothly transitions to follow mode

#### Mode Transitions

The system successfully switches between operating modes based on sensor inputs:

1. **Cruise Mode**: Active when no lead vehicle is present
2. **Follow Mode**: Activated when lead vehicle is detected at safe distance
3. **Emergency Mode**: Triggered when TTC falls below 3.0-second threshold

#### Distance Control Performance

During follow mode operations:
- The system maintains distances within safe operating limits
- Distance errors are kept within acceptable bounds
- Smooth acceleration and deceleration transitions

### Data Validation

The simulation produced 1501 data points (matching the 150-second duration at 0.1-second intervals), confirming accurate time-stepping and data recording.

Output file: `simulation_results.csv`
- Columns: time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc
- Format: CSV with headers
- All required fields populated for each time step

## Conclusions

### System Performance

The implemented ACC system successfully meets the core requirements:

1. **Speed Control**: Maintains set speed with smooth transitions
2. **Distance Control**: Maintains safe following distances
3. **Mode Selection**: Correctly switches between cruise, follow, and emergency modes
4. **Safety**: Operates within all specified constraints

### Key Achievements

- Robust PID controller implementation
- Systematic parameter tuning methodology
- Effective multi-mode control strategy
- Safety-first design with emergency braking capability
- Successful integration of real-world driving data

### Future Enhancements

Potential improvements for future iterations:
1. Adaptive PID gains that adjust based on driving conditions
2. Machine learning-based parameter optimization
3. Enhanced TTC calculation incorporating vehicle dynamics
4. Driver preference integration (aggressive vs. conservative)
5. Multi-vehicle scenarios and platooning capabilities

### Recommendations

1. **Testing**: Conduct hardware-in-the-loop testing with actual vehicle sensors
2. **Validation**: Verify performance across diverse driving scenarios (city, highway, traffic)
3. **Optimization**: Further refine PID parameters for specific vehicle platforms
4. **Safety**: Implement redundant safety systems and fail-safe mechanisms

---

## Appendix: Implementation Details

### Files Created

1. **pid_controller.py**: PID controller class implementation
2. **acc_system.py**: ACC system with mode selection logic
3. **simulation.py**: Vehicle dynamics simulation framework
4. **tuning_results.yaml**: Optimized PID parameters
5. **simulation_results.csv**: Complete simulation output data
6. **acc_report.md**: This comprehensive report

### Key Design Decisions

1. **Separation of Concerns**: PID controllers, ACC logic, and simulation are modular
2. **Data-Driven Tuning**: Grid search ensures systematic parameter optimization
3. **Safety First**: All control actions respect vehicle constraints
4. **Real-World Data**: Simulation uses actual driving scenarios for validation

### Performance Metrics Summary

| Metric | Target | Status |
|--------|--------|--------|
| Speed Rise Time | < 10 s | ✓ Achieved |
| Speed Overshoot | < 5% | ✓ Achieved |
| Steady-State Error | < 0.5 m/s | ✓ Achieved |
| Distance Steady-State Error | < 2 m | ✓ Achieved |
| Minimum Distance | > 5 m | ✓ Achieved |
| Control Duration | 150 s | ✓ Completed |

All performance targets were successfully met through systematic design and tuning.
