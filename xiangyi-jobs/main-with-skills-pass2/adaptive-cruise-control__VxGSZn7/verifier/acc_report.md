# Adaptive Cruise Control (ACC) System Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PIDController** (`pid_controller.py`): A general-purpose PID controller class that provides proportional, integral, and derivative control.

2. **AdaptiveCruiseControl** (`acc_system.py`): The core ACC logic that manages vehicle speed and following distance using two PID controllers.

3. **Simulation** (`simulation.py`): The vehicle dynamics simulation that integrates sensor data with the ACC controller.

### 1.2 Operating Modes

The ACC system operates in three distinct modes:

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintains set speed (30 m/s) using speed PID controller |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Maintains safe following distance based on time headway |
| **Emergency** | TTC < 3.0s | Applies maximum braking (-8.0 m/s^2) |

### 1.3 Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Continuously calculates TTC when a lead vehicle is present. Emergency braking activates when TTC < 3.0 seconds.

2. **Speed-Dependent Following Distance**: Safe distance calculated as:
   ```
   desired_distance = min_distance + time_headway * ego_speed
                    = 10.0 m + 1.5s * ego_speed
   ```

3. **Acceleration Limits**: All commands clamped to [-8.0, +3.0] m/s^2.

4. **Overshoot Prevention**: Proportional acceleration reduction when approaching set speed.

5. **Minimum Gap Enforcement**: 10.0 m minimum following distance built into the control law.

## 2. PID Tuning Methodology

### 2.1 Approach

PID gains were tuned to meet the following performance requirements:

| Metric | Target | Achieved |
|--------|--------|----------|
| Speed rise time (to 90%) | < 10s | 9.0s |
| Speed overshoot | < 5% | 0.17% |
| Speed steady-state error | < 0.5 m/s | 0.0 m/s |
| Distance steady-state error | < 2m | 0.57m avg |
| Minimum distance | > 5m | 5.47m |

### 2.2 Tuning Process

1. **Speed Controller**: Tuned for fast response with minimal overshoot. High proportional gain (Kp=2.5) ensures quick response. Moderate integral gain (Ki=0.15) eliminates steady-state error. Derivative gain (Kd=0.3) dampens oscillations.

2. **Distance Controller**: Tuned for smooth following with safety priority. Moderate proportional gain (Kp=0.8) provides responsive distance correction. Low integral gain (Ki=0.05) prevents overshoot. Higher derivative gain (Kd=1.2) provides damping for rapid distance changes.

### 2.3 Final Gains

```yaml
pid_speed:
  kp: 2.5
  ki: 0.15
  kd: 0.3

pid_distance:
  kp: 0.8
  ki: 0.05
  kd: 1.2
```

## 3. Simulation Results

### 3.1 Test Scenario Overview

The 150-second simulation covers several driving scenarios:

| Time Range | Scenario |
|------------|----------|
| 0-30s | Free cruising (acceleration from 0 to 30 m/s) |
| 30-60s | Following slower lead vehicle (~25 m/s) |
| 60-75s | Lead vehicle accelerating to match set speed |
| 75-120s | Following at cruise speed with lead vehicle variations |
| 120-122s | Emergency braking (lead vehicle sudden deceleration) |
| 122-130s | Recovery and following |
| 130-150s | Return to cruise mode |

### 3.2 Performance Metrics

#### Speed Control
- **Rise Time (0 to 27 m/s)**: 9.0 seconds
- **Maximum Speed**: 30.05 m/s
- **Overshoot**: 0.17%
- **Steady-State Error**: 0.0 m/s

#### Distance Control
- **Steady-State Error**: 0.57m average during stable following
- **Minimum Distance**: 5.47m (during emergency recovery at t=122.0s)

### 3.3 Mode Distribution

| Mode | Count | Percentage |
|------|-------|------------|
| Cruise | 501 | 33.4% |
| Follow | 980 | 65.3% |
| Emergency | 20 | 1.3% |

### 3.4 Emergency Braking Performance

At t=120s, the lead vehicle suddenly decelerates from ~20 m/s to near-zero. The ACC system:
1. Detects TTC < 3.0s and enters emergency mode
2. Applies maximum braking (-8.0 m/s^2)
3. Reduces speed from 22.4 m/s to 6.4 m/s over 2 seconds
4. Maintains minimum distance of 5.47m (above 5m threshold)
5. Smoothly transitions back to follow mode

## 4. Conclusions

The implemented ACC system successfully meets all performance requirements:

1. Fast speed response with minimal overshoot ensures driver comfort
2. Accurate distance control maintains safe following gaps
3. Emergency braking provides collision avoidance capability
4. Smooth mode transitions prevent jerky vehicle behavior

The PID control approach with separate speed and distance controllers provides a robust and tunable solution for adaptive cruise control applications.
