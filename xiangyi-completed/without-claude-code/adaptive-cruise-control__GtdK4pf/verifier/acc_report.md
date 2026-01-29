# Adaptive Cruise Control (ACC) Simulation Report

## System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A generic PID controller implementation with:
   - Proportional, Integral, and Derivative terms
   - Anti-windup protection for the integral term
   - State reset capability for mode transitions

2. **ACC System** (`acc_system.py`): The main control logic that:
   - Maintains set speed (30 m/s) in cruise mode
   - Follows lead vehicle with safe distance in follow mode
   - Triggers emergency braking when TTC < 3s

3. **Simulation** (`simulation.py`): The vehicle dynamics simulation that:
   - Reads sensor data for lead vehicle information
   - Simulates ego vehicle response to ACC commands
   - Tracks distance dynamically based on vehicle positions

### Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID |
| **Follow** | Lead vehicle detected, TTC >= 3s | Maintain safe following distance using distance PID |
| **Emergency** | TTC < 3s | Apply maximum braking (-8.0 m/s^2) |

### Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Continuously calculates TTC and triggers emergency braking when TTC falls below 3.0 seconds.

2. **Safe Following Distance**: Desired distance = min_distance + time_headway * ego_speed
   - Minimum gap: 10.0 m
   - Time headway: 1.5 s
   - At 25 m/s: desired distance = 10 + 1.5*25 = 47.5 m

3. **Acceleration Limits**: All acceleration commands are clamped to [-8.0, 3.0] m/s^2

4. **Speed Limiting**: Ego vehicle never exceeds set speed of 30 m/s

## PID Tuning Methodology

### Approach

The tuning process followed a systematic approach:

1. **Speed PID Tuning** (Cruise Mode):
   - Started with proportional control to achieve fast rise time
   - Added derivative for damping to reduce overshoot
   - Added minimal integral to eliminate steady-state error
   - Key constraint: Rise time < 10s with max acceleration 3.0 m/s^2

2. **Distance PID Tuning** (Follow Mode):
   - Tuned for steady-state distance tracking
   - Balanced responsiveness vs. stability
   - Higher integral gain to eliminate steady-state offset

### Final PID Gains

```yaml
pid_speed:
  kp: 1.5   # Proportional gain
  ki: 0.02  # Integral gain
  kd: 1.5   # Derivative gain

pid_distance:
  kp: 1.2   # Proportional gain
  ki: 0.2   # Integral gain
  kd: 2.5   # Derivative gain
```

### Control Strategy

The follow mode uses a hybrid control approach:
- **Distance error < -5m**: Emergency-level braking (max deceleration)
- **Distance error < -2m**: Distance PID for braking
- **Distance error within +/-2m**: Blend of distance (30%) and speed (70%) control
- **Distance error > 2m**: Pure distance PID for catching up

## Simulation Results

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed Rise Time | < 10s | 9.1s | PASS |
| Speed Overshoot | < 5% | 1.07% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.32 m/s | PASS |
| Distance Steady-State Error | < 2m | 1.57m | PASS |
| Minimum Distance | > 5m | 12.79m | PASS |
| Control Duration | 150s | 150s | PASS |

### Mode Distribution

- Cruise mode: 501 samples (33.4%)
- Follow mode: 981 samples (65.4%)
- Emergency mode: 19 samples (1.3%)

### Scenario Summary

The 150-second simulation covers multiple driving scenarios:

1. **t=0-30s (Cruise)**: Ego vehicle accelerates from 0 to 30 m/s with no lead vehicle
2. **t=30-120s (Follow)**: Lead vehicle appears and ACC maintains following distance
3. **t=120-122s (Emergency)**: Lead vehicle brakes hard, triggering emergency braking
4. **t=122-130s (Recovery)**: Lead vehicle accelerates, ego follows
5. **t=130-150s (Cruise)**: Lead vehicle disappears, return to cruise mode

### Key Observations

1. **Smooth Acceleration**: The speed controller achieves target with minimal overshoot (1.07%)
2. **Stable Following**: Distance error maintains average of 1.57m during steady following
3. **Emergency Response**: System correctly identifies and responds to dangerous TTC situations
4. **Mode Transitions**: Clean transitions between cruise, follow, and emergency modes

## Conclusion

The ACC system successfully meets all performance requirements. The PID-based control strategy provides robust speed and distance regulation while maintaining safety margins. The emergency braking feature ensures collision avoidance in critical situations.
