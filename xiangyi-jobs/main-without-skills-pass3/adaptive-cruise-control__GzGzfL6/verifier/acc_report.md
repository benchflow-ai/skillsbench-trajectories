# Adaptive Cruise Control (ACC) Simulation Report

## Executive Summary

This report documents the implementation and evaluation of an Adaptive Cruise Control (ACC) system simulation. The system successfully meets all specified performance targets:

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed Rise Time | < 10s | 9.40s | PASS |
| Speed Overshoot | < 5% | 0.89% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.004 m/s | PASS |
| Distance Steady-State Error | < 2m | 1.48m | PASS |
| Minimum Distance | > 5m | 12.16m | PASS |

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A reusable PID controller with anti-windup support
2. **ACC System** (`acc_system.py`): The core ACC logic with three operating modes
3. **Simulation** (`simulation.py`): The vehicle dynamics simulation using sensor data

### 1.2 Operating Modes

The ACC system operates in three modes:

#### Cruise Mode
- **Triggered when**: No lead vehicle detected (lead_speed is None)
- **Behavior**: Accelerates/decelerates to maintain set speed (30 m/s)
- **Control**: PID-based speed control with soft approach near target to minimize overshoot

#### Follow Mode
- **Triggered when**: Lead vehicle detected and TTC >= 3.0s
- **Behavior**: Maintains safe following distance based on time headway model
- **Control**: Combined speed matching and distance control with adaptive weighting
- **Desired Distance**: `d = 10m + 1.5s * ego_speed`

#### Emergency Mode
- **Triggered when**: TTC (Time-To-Collision) < 3.0s
- **Behavior**: Maximum deceleration (-8.0 m/s^2) to avoid collision
- **Safety**: Controllers are reset to prevent windup during emergency

### 1.3 Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Continuously calculates TTC and triggers emergency braking when TTC < 3.0s

2. **Acceleration Limits**: All commands are clamped to vehicle limits:
   - Maximum acceleration: 3.0 m/s^2
   - Maximum deceleration: -8.0 m/s^2

3. **Set Speed Limiter**: Prevents acceleration when at or above set speed (30 m/s)

4. **Distance-Based Safety**: When too close to lead vehicle:
   - Limits maximum allowed acceleration based on proximity
   - Forces deceleration when distance error exceeds -5m

5. **Anti-Windup**: PID controllers include integral clamping to prevent windup during saturation

## 2. PID Tuning Methodology

### 2.1 Approach

The tuning process followed these principles:

1. **Speed Controller First**: Tune for cruise mode performance (rise time, overshoot, steady-state error)
2. **Distance Controller Second**: Tune for following mode performance while maintaining stability
3. **Iterative Refinement**: Adjust both controllers to balance responsiveness and safety

### 2.2 Speed Controller Tuning

**Objective**: Fast rise time (<10s), minimal overshoot (<5%), negligible steady-state error

**Approach**:
- Started with moderate Kp for responsiveness
- Added small Ki to eliminate steady-state error
- Used Kd for damping to prevent overshoot
- Implemented soft approach near set speed to reduce overshoot

**Final Gains**:
```yaml
pid_speed:
  kp: 0.8   # Proportional gain for quick response
  ki: 0.03  # Integral gain for zero steady-state error
  kd: 0.5   # Derivative gain for overshoot damping
```

### 2.3 Distance Controller Tuning

**Objective**: Small steady-state distance error (<2m), smooth following, no oscillation

**Approach**:
- Moderate Kp for responsive gap correction
- Higher Ki to ensure distance error converges
- Moderate Kd to smooth transitions
- Adaptive control weighting based on distance error magnitude

**Final Gains**:
```yaml
pid_distance:
  kp: 0.5   # Proportional gain for gap correction
  ki: 0.04  # Integral gain for steady-state accuracy
  kd: 0.35  # Derivative gain for smooth control
```

### 2.4 Control Law Design

The follow mode uses an adaptive blending of speed matching and distance control:

```
if |distance_error| < 5m:
    accel = 0.7 * speed_match + 0.3 * distance_correction
else:
    accel = 0.4 * speed_match + 0.6 * distance_correction
```

This approach:
- Prioritizes speed matching when close to desired distance (stability)
- Emphasizes distance correction when gap is large (responsiveness)

## 3. Simulation Results

### 3.1 Performance Metrics Summary

| Metric | Requirement | Achieved | Margin |
|--------|-------------|----------|--------|
| Speed Rise Time | < 10s | 9.40s | 0.6s |
| Speed Overshoot | < 5% | 0.89% | 4.11% |
| Speed SS Error | < 0.5 m/s | 0.004 m/s | 0.496 m/s |
| Distance SS Error | < 2m | 1.48m | 0.52m |
| Minimum Distance | > 5m | 12.16m | 7.16m |

### 3.2 Simulation Scenario

The 150-second simulation covers multiple scenarios from the sensor data:

1. **t=0-30s (Cruise)**: Vehicle accelerates from rest to set speed (30 m/s)
2. **t=30-75s (Follow)**: Lead vehicle detected, ACC maintains safe following distance
3. **t=75-100s (Follow)**: Lead vehicle speeds vary (some exceed set speed)
4. **t=100-120s (Follow)**: Lead vehicle gradually decelerates
5. **t=120-122s (Emergency)**: Lead vehicle emergency brakes, ACC responds with max deceleration
6. **t=122-130s (Follow)**: Recovery and re-establishment of safe following
7. **t=130-150s (Cruise)**: Lead vehicle disappears, ACC returns to set speed

### 3.3 Emergency Events

18 emergency braking events occurred at t=120.0-121.7s when the lead vehicle performed an emergency stop (speed dropped from ~20 m/s to 0 in ~2 seconds). The ACC system:
- Detected the impending collision via TTC calculation
- Applied maximum deceleration (-8.0 m/s^2)
- Maintained minimum distance of 12.16m (well above 5m safety threshold)
- Successfully avoided collision

## 4. Key Design Decisions

### 4.1 Time Headway Model

The desired following distance uses a linear time headway model:

```
d_desired = d_min + t_headway * v_ego
d_desired = 10m + 1.5s * v_ego
```

At 30 m/s, this gives a desired distance of 55m, providing approximately 1.8s of reaction time.

### 4.2 Soft Speed Approach

To minimize overshoot when approaching set speed:

```python
if speed_error > 0 and time_to_target < 2.0:
    scale = speed_error / (2.0 * max_acceleration)
    accel_cmd = min(accel_cmd, max_acceleration * scale)
```

This gradually reduces acceleration as the vehicle approaches set speed.

### 4.3 Position-Based Distance Tracking

The simulation tracks vehicle positions independently:
- Lead vehicle position updated based on sensor-reported lead speed
- Ego vehicle position updated based on simulated speed
- Distance computed as difference between positions

This approach provides realistic dynamics where the ACC controller's actions affect the actual following distance.

## 5. Conclusions

The implemented ACC system successfully meets all specified performance requirements:

1. **Speed Control**: Fast response (9.4s rise time) with minimal overshoot (0.89%) and excellent steady-state accuracy (0.004 m/s error)

2. **Distance Control**: Maintains following distance within 1.48m of target during steady-state following

3. **Safety**: Emergency braking maintains minimum distance of 12.16m, well above the 5m safety threshold

4. **Robustness**: Handles various scenarios including lead vehicle speed variations, emergency braking, and vehicle appearance/disappearance

The PID-based control approach with adaptive weighting provides a good balance between responsiveness and stability, while the safety features ensure collision avoidance even in challenging scenarios.
