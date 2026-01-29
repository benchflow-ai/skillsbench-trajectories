# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The Adaptive Cruise Control system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A general-purpose PID controller with anti-windup protection
2. **ACC System** (`acc_system.py`): The main control logic that manages modes and computes acceleration commands
3. **Simulation** (`simulation.py`): Vehicle dynamics simulation using sensor data

### 1.2 Operating Modes

The ACC system operates in three modes:

| Mode | Condition | Control Strategy |
|------|-----------|------------------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID controller |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Maintain safe following distance using distance PID controller |
| **Emergency** | TTC < 3.0s | Apply maximum braking (-8.0 m/s^2) |

### 1.3 Distance Control Model

The desired following distance is computed using the time headway model:

```
desired_distance = time_headway * ego_speed + min_gap
                 = 1.5 * ego_speed + 10.0 m
```

At 30 m/s, this gives a desired following distance of 55 meters.

### 1.4 Safety Features

1. **Time-to-Collision (TTC) Monitoring**: Continuous calculation of collision risk
2. **Emergency Braking**: Automatic maximum deceleration when TTC < 3.0s
3. **Anti-Windup Protection**: Prevents integral accumulation during actuator saturation
4. **Controller Reset on Mode Transitions**: Prevents undesirable transients when switching modes
5. **Acceleration Limits**: All commands clamped to [-8.0, 3.0] m/s^2

## 2. PID Tuning Methodology

### 2.1 Approach

The PID gains were tuned using a grid search optimization over the following ranges:

- **Kp**: (0, 10) - open interval
- **Ki**: [0, 5) - half-open interval
- **Kd**: [0, 5) - half-open interval

The optimization targeted the following performance metrics:
- Rise time < 10s
- Speed overshoot < 5%
- Speed steady-state error < 0.5 m/s
- Distance steady-state error < 2m
- Minimum distance > 5m

### 2.2 Anti-Windup Implementation

A critical aspect of the tuning was implementing anti-windup in the PID controller. Without anti-windup, the integral term accumulated excessively during the initial acceleration phase (when the controller was saturated at max acceleration), causing significant overshoot.

The anti-windup logic prevents integral updates when:
- Output is saturated high AND error is positive (would increase saturation)
- Output is saturated low AND error is negative (would increase saturation)

### 2.3 Final PID Gains

**Speed Controller:**
| Parameter | Value |
|-----------|-------|
| Kp | 1.5 |
| Ki | 0.05 |
| Kd | 0.2 |

**Distance Controller:**
| Parameter | Value |
|-----------|-------|
| Kp | 0.7 |
| Ki | 0.1 |
| Kd | 0.3 |

### 2.4 Gain Selection Rationale

**Speed Controller:**
- Higher Kp (1.5) for quick response to speed errors
- Low Ki (0.05) to eliminate steady-state error without oscillation
- Moderate Kd (0.2) for damping to reduce overshoot

**Distance Controller:**
- Moderate Kp (0.7) for responsive but stable following
- Higher Ki (0.1) than speed controller to ensure distance tracking
- Higher Kd (0.3) to anticipate distance changes and smooth following

## 3. Simulation Results

### 3.1 Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Duration | 150 seconds |
| Timestep | 0.1 seconds |
| Initial speed | 0 m/s |
| Set speed | 30 m/s |
| Max acceleration | 3.0 m/s^2 |
| Max deceleration | -8.0 m/s^2 |
| Time headway | 1.5 s |
| Minimum gap | 10.0 m |
| Emergency TTC threshold | 3.0 s |

### 3.2 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise time | < 10s | 9.00s | PASS |
| Speed overshoot | < 5% | 0.17% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.033 m/s | PASS |
| Distance steady-state error | < 2m | 1.72m | PASS |
| Minimum distance | > 5m | 18.15m | PASS |

### 3.3 Mode Distribution

| Mode | Timesteps | Percentage |
|------|-----------|------------|
| Cruise | 501 | 33.4% |
| Follow | 983 | 65.5% |
| Emergency | 17 | 1.1% |

### 3.4 Simulation Phases

1. **Initial Acceleration (t=0-10s)**: Vehicle accelerates from rest at maximum acceleration (3.0 m/s^2), reaching 27 m/s at t=9s and 30 m/s at t=10s.

2. **Cruise Stabilization (t=10-30s)**: Speed controller maintains set speed with minimal steady-state error (0.033 m/s).

3. **Follow Mode Engagement (t=30-120s)**: Lead vehicle detected at 52.1m. ACC transitions to follow mode, adjusting speed to maintain safe following distance.

4. **Emergency Braking (t=120-121.7s)**: Lead vehicle decelerates rapidly. When TTC drops below 3.0s, emergency braking is triggered. Maximum deceleration applied for 1.7 seconds.

5. **Recovery (t=121.7-130s)**: TTC returns above threshold, system transitions back to follow mode. Both vehicles accelerate.

6. **Return to Cruise (t=130-150s)**: Lead vehicle disappears. System returns to cruise mode, stabilizing at set speed.

### 3.5 Emergency Event Analysis

One emergency braking event occurred:
- **Start time**: 120.0s
- **End time**: 121.7s
- **Duration**: 1.7s
- **Minimum distance achieved**: 18.15m

The emergency braking system successfully prevented collision while maintaining distance above the 5m safety threshold.

## 4. Conclusions

The Adaptive Cruise Control system successfully meets all performance requirements:

1. **Speed Control**: Fast rise time (9s) with minimal overshoot (0.17%) and excellent steady-state accuracy (0.033 m/s error).

2. **Distance Control**: Maintains safe following distance with average error of 1.72m, well within the 2m target.

3. **Safety**: Emergency braking activates appropriately when TTC < 3s, maintaining minimum distance of 18.15m (well above 5m safety limit).

4. **Robustness**: Anti-windup protection prevents controller saturation issues, enabling smooth transitions between operating modes.

The implemented ACC system demonstrates reliable performance across all tested scenarios, including normal cruise, vehicle following, and emergency braking situations.
