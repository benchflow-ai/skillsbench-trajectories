# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The Adaptive Cruise Control system consists of three main components:

1. **PID Controller** (`pid_controller.py`)
   - Implements a standard PID controller with anti-windup protection
   - Features derivative filtering to reduce noise sensitivity
   - Supports output limiting for saturation handling

2. **ACC System** (`acc_system.py`)
   - Manages speed and distance control modes
   - Computes desired following distance based on time headway
   - Calculates Time-To-Collision (TTC) for safety monitoring

3. **Simulation** (`simulation.py`)
   - Integrates vehicle dynamics with ACC controller
   - Uses sensor data for lead vehicle behavior
   - Generates performance metrics and results

### 1.2 Operating Modes

The ACC system operates in three modes:

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID |
| **Follow** | Lead vehicle present, TTC > 3s | Maintain safe following distance using distance PID |
| **Emergency** | TTC < 3s | Apply maximum braking (-8.0 m/s²) |

### 1.3 Safety Features

1. **Time-To-Collision (TTC) Monitoring**
   - Continuously calculates TTC when lead vehicle present
   - Triggers emergency braking when TTC < 3.0 seconds

2. **Safe Following Distance**
   - Desired distance = min_gap + time_headway × ego_speed
   - min_gap = 10.0 m, time_headway = 1.5 s
   - At 30 m/s: desired distance = 10 + 1.5×30 = 55 m

3. **Acceleration Limits**
   - Maximum acceleration: 3.0 m/s²
   - Maximum deceleration: -8.0 m/s²

4. **Anti-Windup Protection**
   - Prevents integral accumulation during saturation
   - Resets controllers on mode transitions

## 2. PID Tuning Methodology

### 2.1 Speed Controller

**Objectives:**
- Rise time < 10 seconds
- Overshoot < 5%
- Steady-state error < 0.5 m/s

**Tuning Process:**

1. Started with moderate Kp to achieve required rise time
2. Added derivative gain (Kd) to dampen response near setpoint
3. Used minimal integral gain (Ki) to avoid windup during acceleration phase
4. Implemented conditional integration (anti-windup) to prevent overshoot

**Final Gains:**
```yaml
pid_speed:
  kp: 0.6   # Proportional: adequate response without excessive overshoot
  ki: 0.008 # Integral: minimal to prevent windup, sufficient for SS accuracy
  kd: 0.4   # Derivative: dampens approach to setpoint
```

### 2.2 Distance Controller

**Objectives:**
- Steady-state error < 2 m
- Minimum distance > 5 m

**Tuning Process:**

1. High Kp for responsive gap control
2. Significant Ki to eliminate steady-state error
3. Low Kd to avoid oscillation from distance measurement noise
4. Blended with speed controller output for smooth transitions

**Final Gains:**
```yaml
pid_distance:
  kp: 4.0  # Proportional: aggressive gap tracking
  ki: 0.8  # Integral: eliminates steady-state error
  kd: 0.1  # Derivative: minimal to avoid noise amplification
```

## 3. Simulation Results

### 3.1 Test Scenario

- **Duration:** 150 seconds
- **Initial conditions:** Ego vehicle at rest (0 m/s)
- **Phase 1 (0-30s):** Cruise mode - accelerate to set speed
- **Phase 2 (30-130s):** Follow mode - lead vehicle present at ~25-30 m/s
- **Phase 3 (130-150s):** Cruise mode - lead vehicle departed

### 3.2 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time (to 90% of 30 m/s) | < 10 s | 9.8 s | ✅ PASS |
| Speed Overshoot | < 5% | 0.66% | ✅ PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.198 m/s | ✅ PASS |
| Distance Steady-State Error | < 2 m | 1.96 m | ✅ PASS |
| Minimum Following Distance | > 5 m | 19.58 m | ✅ PASS |

### 3.3 Mode Distribution

- **Cruise mode:** 0-30s (initial acceleration) and 130-150s (final cruise)
- **Follow mode:** 30-130s (following lead vehicle)
- **Emergency mode:** Not triggered (TTC always > 3s threshold)

### 3.4 Key Observations

1. **Smooth Acceleration:** The vehicle accelerates at maximum rate (3.0 m/s²) initially, then smoothly transitions to maintain set speed with minimal overshoot.

2. **Effective Following:** When lead vehicle appears, the ACC smoothly transitions to follow mode and maintains appropriate following distance.

3. **Safe Operation:** Minimum distance of 19.58 m maintained throughout, well above the 5 m safety threshold.

4. **Stable Tracking:** Distance steady-state error of 1.96 m indicates good gap maintenance during follow mode.

## 4. Conclusions

The implemented ACC system successfully meets all performance targets:

1. **Speed Control:** Fast response (9.8s rise time) with excellent stability (0.66% overshoot) and accuracy (0.198 m/s SS error).

2. **Distance Control:** Maintains safe following distance with acceptable steady-state error (1.96 m).

3. **Safety:** Large safety margins maintained throughout simulation with minimum distance of 19.58 m.

The anti-windup mechanism in the PID controller was crucial for preventing overshoot during the initial acceleration phase while still achieving the required rise time.
