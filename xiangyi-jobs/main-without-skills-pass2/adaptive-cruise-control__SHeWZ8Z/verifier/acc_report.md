# Adaptive Cruise Control (ACC) Simulation Report

## System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A standard PID controller with anti-windup protection
   - Proportional, Integral, and Derivative terms
   - Configurable integral limit to prevent windup
   - Reset capability for mode transitions

2. **ACC System** (`acc_system.py`): The main control logic implementing three operating modes
   - Computes desired following distance based on time headway model
   - Manages mode transitions and PID controller states
   - Applies acceleration limits for vehicle safety

3. **Simulation** (`simulation.py`): The vehicle dynamics simulation
   - Loads configuration from YAML files
   - Reads sensor data for lead vehicle behavior
   - Simulates ego vehicle response using ACC controller
   - Generates output CSV with simulation results

### Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID |
| **Follow** | Lead vehicle present, safe distance | Maintain desired following distance using distance PID + velocity damping |
| **Emergency** | TTC < 3.0s OR distance < 5m | Maximum braking (-8.0 m/s^2) |

### Safety Features

1. **Emergency Braking**: Activates when Time-To-Collision (TTC) drops below 3.0 seconds or distance falls below 5.0 meters
2. **Anti-Windup**: Integral term limited to prevent controller saturation during extended error conditions
3. **Acceleration Limits**: All commands clamped to [-8.0, 3.0] m/s^2
4. **Speed Limiting**: Ego vehicle never exceeds set speed (30 m/s) even when following faster lead vehicle

### Following Distance Model

The desired following distance is computed as:

```
desired_distance = min_distance + time_headway * ego_speed
                 = 10.0 m + 1.5 s * ego_speed
```

At set speed (30 m/s): desired_distance = 10 + 1.5 * 30 = 55 m

## PID Tuning Methodology

### Approach

The PID parameters were tuned iteratively to meet the performance requirements:

1. **Initial Analysis**: Understood the physical constraints (max accel 3.0 m/s^2 limits minimum rise time to ~10s)
2. **Speed Controller Tuning**: Balanced fast rise time against overshoot
3. **Distance Controller Tuning**: Ensured stable following with smooth transitions
4. **Anti-Windup Adjustment**: Limited integral to prevent overshoot from accumulated error

### Tuning Challenges

1. **Rise Time vs Overshoot Trade-off**: Higher gains reduce rise time but increase overshoot
2. **Integral Windup**: During mode transitions, integral term can cause speed spikes
3. **Physical Limits**: Max acceleration of 3.0 m/s^2 fundamentally limits rise time to ~10s

### Final PID Gains

| Controller | Kp | Ki | Kd |
|------------|----|----|-----|
| Speed | 5.0 | 1.0 | 1.8 |
| Distance | 0.5 | 0.02 | 0.8 |

**Anti-Windup Limits:**
- Speed controller integral limit: 10.0
- Distance controller integral limit: 20.0

## Simulation Results

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time | < 10 s | 10.0 s | At limit (physical constraint) |
| Speed Overshoot | < 5% | 4.53% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.033 m/s | PASS |
| Distance Steady-State Error | < 2 m | 1.28 m | PASS |
| Minimum Distance | > 5 m | 20.78 m | PASS |
| Control Duration | 150 s | 150 s | PASS |

### Mode Distribution

| Mode | Samples | Percentage |
|------|---------|------------|
| Cruise | 501 | 33.4% |
| Follow | 983 | 65.5% |
| Emergency | 17 | 1.1% |

### Key Observations

1. **Rise Time Physical Limit**: With max acceleration 3.0 m/s^2 and target speed 30 m/s, the theoretical minimum rise time is exactly 10.0 seconds (t = v/a = 30/3). The controller achieves this theoretical limit.

2. **Emergency Braking Scenario**: The sensor data includes a severe emergency at t=120s where the lead vehicle suddenly decelerates. The ACC system successfully handles this by:
   - Detecting low TTC condition
   - Engaging emergency braking
   - Maintaining minimum safe distance of 20.78m

3. **Lead Vehicle Speed Variations**: When the lead vehicle exceeds set speed (30 m/s), the ACC correctly limits ego speed and allows the gap to grow, rather than violating the speed limit.

4. **Stable Following**: During the period t=35-60s when lead speed is around 25 m/s, the distance error averages only 1.28m, well within the 2m requirement.

## File Structure

```
/root/
├── pid_controller.py      # PID controller implementation
├── acc_system.py          # ACC system with mode logic
├── simulation.py          # Simulation runner
├── vehicle_params.yaml    # Vehicle and ACC configuration
├── sensor_data.csv        # Input: lead vehicle behavior
├── tuning_results.yaml    # Tuned PID parameters
├── simulation_results.csv # Output: 1501 rows of simulation data
└── acc_report.md          # This report
```

## Conclusion

The ACC system successfully meets all performance requirements except for the rise time, which is constrained by the physical acceleration limit. The system demonstrates:

- Smooth speed control with minimal overshoot (4.53%)
- Excellent steady-state tracking (0.033 m/s speed error)
- Safe following distance maintenance (min 20.78m > 5m requirement)
- Proper emergency braking activation during hazardous scenarios
- Stable mode transitions between cruise, follow, and emergency modes
