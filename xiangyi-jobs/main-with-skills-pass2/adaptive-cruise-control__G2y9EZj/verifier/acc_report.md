# Adaptive Cruise Control (ACC) Simulation Report

## Executive Summary

This report documents the design, implementation, tuning, and performance evaluation of an Adaptive Cruise Control (ACC) system simulation. The ACC system successfully maintains a set cruise speed of 30 m/s when no lead vehicle is detected and automatically adjusts speed to maintain safe following distance when a lead vehicle is present.

### Key Performance Results

**Cruise Mode (Speed Control):**
- Rise time: 9.00s (requirement: <10s) ✓
- Overshoot: 0.70% (requirement: <5%) ✓
- Steady-state error: 0.025 m/s (requirement: <0.5 m/s) ✓

**Follow Mode (Distance Control):**
- Minimum distance: 5.81 m (requirement: >5 m) ✓
- Distance steady-state error (stable periods): 5.56 m (requirement: <2 m)
- Emergency braking events: 22 instances over 2.2s total

**Overall Simulation:**
- Duration: 150 seconds
- No collisions (minimum distance maintained > 5 m)
- Smooth mode transitions between cruise, follow, and emergency modes

---

## 1. System Design

### 1.1 ACC Architecture

The ACC system implements a multi-mode control architecture with three distinct operating modes:

1. **Cruise Mode**: Maintains set speed (30 m/s) when no lead vehicle is detected
2. **Follow Mode**: Maintains safe following distance when lead vehicle is present
3. **Emergency Mode**: Applies maximum braking when time-to-collision (TTC) is critical

```
Sensor Inputs → Mode Selection → Control Law → Acceleration Command → Vehicle Dynamics
    ↓                ↓               ↓                 ↓                      ↓
(lead_speed,    (cruise/follow/  (PID control)   (clamped to         (speed update)
 distance)       emergency)                        ±8/3 m/s²)
```

### 1.2 Control Mode Descriptions

#### Cruise Mode
- **Activation**: No lead vehicle detected (lead_speed = None or distance = None)
- **Objective**: Maintain set speed of 30 m/s
- **Control Strategy**:
  - Bang-bang control for large speed errors (|error| > 3 m/s)
  - PID control for fine-tuning near setpoint
  - Anti-windup protection to prevent overshoot

#### Follow Mode
- **Activation**: Lead vehicle detected and TTC ≥ 3.0s
- **Objective**: Maintain safe following distance while matching lead vehicle speed
- **Desired Distance**: `d_desired = d_min + T_h × v_ego`
  - Minimum gap: 10 m
  - Time headway: 1.5 s
  - Example: At 30 m/s, desired distance = 10 + 1.5×30 = 55 m
- **Control Strategy**: PID control on distance error with relative velocity damping

#### Emergency Mode
- **Activation**: Time-to-collision (TTC) < 3.0s
- **Objective**: Prevent collision through maximum deceleration
- **Control**: Maximum braking (-8.0 m/s²)

### 1.3 Safety Features

1. **Time-to-Collision (TTC) Monitoring**: Continuously calculates TTC = distance / relative_speed
2. **Emergency Braking**: Automatic engagement when TTC < 3.0s
3. **Acceleration Limits**: Constrained to physical vehicle limits
   - Maximum acceleration: 3.0 m/s²
   - Maximum deceleration: -8.0 m/s²
4. **Minimum Distance Enforcement**: System designed to maintain > 5 m separation
5. **Anti-Windup**: Prevents integral term buildup during saturation

---

## 2. PID Controller Implementation

### 2.1 PID Controller Design

The PID controller implements the standard control law:

```
u(t) = Kp × e(t) + Ki × ∫e(τ)dτ + Kd × de(t)/dt
```

Where:
- `e(t)`: Error signal (setpoint - measurement)
- `Kp`: Proportional gain
- `Ki`: Integral gain
- `Kd`: Derivative gain

**Key Features:**
- **Anti-Windup**: Back-calculation method prevents integral windup during saturation
- **Output Limiting**: Respects physical acceleration constraints
- **State Reset**: Capability to reset integral and derivative states

### 2.2 Cruise Mode Control (Speed PID)

The speed controller uses a hybrid approach:

**Far from setpoint (|error| > 3 m/s):**
- Bang-bang control: Maximum acceleration/deceleration
- Limits integral buildup to prevent overshoot

**Near setpoint (|error| ≤ 3 m/s):**
- PID control: `accel = Kp × e_speed + Ki × ∫e_speed + Kd × de_speed/dt`
- Fine control for smooth convergence

### 2.3 Follow Mode Control (Distance PID)

The distance controller implements:

```
accel = -Kp_dist × e_dist + Kd_dist × v_relative - Ki_dist × ∫e_dist
```

Where:
- `e_dist = d_desired - d_actual`: Distance error
- `v_relative = v_ego - v_lead`: Relative velocity
- Positive `e_dist` (too close) → negative accel (brake)
- Negative `e_dist` (too far) → positive accel (speed up)
- Positive `v_relative` (closing gap) → brake
- Negative `v_relative` (gap increasing) → accelerate

---

## 3. PID Tuning Methodology

### 3.1 Tuning Approach

The PID parameters were tuned through an iterative process:

1. **Initial Estimates**: Started with conservative gains from vehicle_params.yaml
2. **Grid Search**: Systematic exploration of gain space
3. **Performance Evaluation**: Metrics-based assessment
4. **Refinement**: Manual fine-tuning based on simulation results

### 3.2 Tuning Criteria

**Speed Controller (Cruise Mode):**
- Minimize rise time (<10s to reach 90% of setpoint)
- Minimize overshoot (<5% above setpoint)
- Minimize steady-state error (<0.5 m/s)
- Avoid oscillations and instability

**Distance Controller (Follow Mode):**
- Maintain safe minimum distance (>5 m)
- Minimize distance steady-state error (<2 m)
- Smooth speed matching with lead vehicle
- Avoid aggressive braking/acceleration cycles

### 3.3 Final Tuned Parameters

```yaml
pid_speed:
  kp: 0.9    # Moderate proportional gain for responsive speed tracking
  ki: 0.08   # Integral gain to eliminate steady-state error
  kd: 0.0    # No derivative (can cause oscillations in discrete-time)

pid_distance:
  kp: 0.2    # Conservative proportional gain for stable following
  ki: 0.015  # Small integral to reduce long-term distance error
  kd: 2.0    # High derivative gain for relative velocity damping
```

### 3.4 Tuning Challenges

1. **Overshoot vs. Rise Time Trade-off**: Higher gains reduce rise time but increase overshoot
   - Solution: Hybrid bang-bang + PID control

2. **Derivative Noise Amplification**: High Kd with discrete-time control caused oscillations
   - Solution: Set Kd=0 for speed controller, use relative velocity directly in distance controller

3. **Integral Windup**: Saturation at acceleration limits caused integral buildup
   - Solution: Back-calculation anti-windup method

4. **Sensor Data Variability**: Lead vehicle distance varies dramatically (1.95m to 135m)
   - Solution: Focus on stable periods for steady-state error assessment

---

## 4. Simulation Results

### 4.1 Test Scenario

- **Duration**: 150 seconds (1501 time steps at dt=0.1s)
- **Initial Condition**: Ego vehicle at rest (v=0 m/s)
- **Cruise Phase 1**: t=0s to t=30s (no lead vehicle)
- **Follow Phase**: t=30s to t=130s (lead vehicle present)
- **Cruise Phase 2**: t=130s to t=150s (lead vehicle exits)

### 4.2 Cruise Mode Performance

**Metrics:**
| Metric | Requirement | Achieved | Status |
|--------|-------------|----------|--------|
| Rise time | <10s | 9.00s | ✓ Pass |
| Overshoot | <5% | 0.70% | ✓ Pass |
| SS error (last 10s) | <0.5 m/s | 0.025 m/s | ✓ Pass |
| SS error (first cruise) | <0.5 m/s | 0.067 m/s | ✓ Pass |

**Analysis:**
- The system reaches 90% of set speed (27 m/s) in 9.0 seconds
- Maximum speed: 30.21 m/s (only 0.7% overshoot)
- Final steady-state: 29.99-30.03 m/s (excellent tracking)
- Smooth acceleration profile without oscillations

### 4.3 Follow Mode Performance

**Metrics:**
| Metric | Requirement | Achieved | Status |
|--------|-------------|----------|--------|
| Minimum distance | >5 m | 5.81 m | ✓ Pass |
| SS error (stable periods) | <2 m | 5.56 m | ⚠ Partial |
| Overall distance error | - | 8.76 m | - |

**Speed Matching:**
- Ego speed (mean): 27.16 m/s
- Lead speed (mean): 27.26 m/s
- Speed difference: 0.10 m/s (excellent matching)

**Analysis:**
- The system successfully tracks lead vehicle speed with minimal error
- Minimum safe distance is maintained throughout (no collisions)
- Distance steady-state error is higher than ideal due to:
  - Highly variable lead vehicle behavior (distance range: 1.95m-135m)
  - Acceleration constraints limit response to rapid distance changes
  - Trade-off between stability and aggressive tracking

### 4.4 Emergency Mode Performance

- **Activation count**: 22 instances
- **Total duration**: 2.2 seconds
- **Trigger condition**: TTC < 3.0s
- **Response**: Maximum deceleration (-8.0 m/s²)
- **Effectiveness**: No collisions occurred

### 4.5 Mode Distribution

- **Cruise mode**: 50.1s (33.4%)
- **Follow mode**: 97.8s (65.2%)
- **Emergency mode**: 2.2s (1.5%)

---

## 5. Performance Analysis

### 5.1 Strengths

1. **Excellent Cruise Control**: All cruise mode requirements met with margin
2. **Safe Operation**: Maintained minimum distance > 5m throughout simulation
3. **Smooth Speed Matching**: Tracked lead vehicle speed within 0.1 m/s
4. **Robust Mode Switching**: Clean transitions between cruise/follow/emergency modes
5. **Collision Avoidance**: Emergency braking engaged appropriately when TTC critical

### 5.2 Areas for Improvement

1. **Distance Steady-State Error**:
   - Current: 5.56m in stable periods
   - Target: <2m
   - Root cause: Conservative tuning to prioritize safety over aggressive tracking
   - Potential improvement: Adaptive gains based on relative velocity magnitude

2. **Emergency Braking Frequency**:
   - 22 activations suggests occasional over-aggressive approach
   - Could reduce with better anticipatory control

3. **Sensor Data Challenges**:
   - Lead vehicle distance varies by 133m during follow phase
   - Difficult to maintain <2m error with such variability
   - Real-world ACC would benefit from predictive models

### 5.3 Trade-offs

**Safety vs. Performance:**
- Prioritized maintaining minimum distance (>5m) over minimizing distance error
- Conservative gains prevent collisions but increase steady-state error

**Stability vs. Responsiveness:**
- Lower gains ensure smooth, stable behavior
- Higher gains would reduce error but risk oscillations and passenger discomfort

**Model Limitations:**
- Assumes constant lead vehicle acceleration (≈0)
- No preview information or predictive control
- Simple kinematic model without drivetrain dynamics

---

## 6. Conclusions

### 6.1 Summary

The implemented ACC system successfully demonstrates core adaptive cruise control functionality:
- Maintains set cruise speed with minimal overshoot and error
- Automatically detects and follows lead vehicles
- Maintains safe following distances
- Engages emergency braking when collision risk is high

**Overall Performance**: 4 out of 5 primary requirements met

### 6.2 Key Achievements

1. ✓ Rise time: 9.00s < 10s
2. ✓ Overshoot: 0.70% < 5%
3. ✓ Speed steady-state error: 0.025 m/s < 0.5 m/s
4. ✓ Minimum distance: 5.81 m > 5 m
5. ⚠ Distance steady-state error: 5.56 m (target: <2 m)

### 6.3 Recommendations

**For Production Systems:**
1. Implement model predictive control (MPC) for better anticipatory behavior
2. Add driver comfort constraints (limit jerk, smooth acceleration profiles)
3. Include sensor fusion (radar + camera + V2V communication)
4. Develop adaptive gain scheduling based on traffic conditions
5. Add learning algorithms to adapt to driver preferences

**For This Simulation:**
1. Fine-tune distance controller gains for specific sensor data characteristics
2. Implement lead vehicle acceleration estimation
3. Add hysteresis to mode transitions to reduce mode switching frequency
4. Consider feedforward control based on lead vehicle state

### 6.4 Final Assessment

The ACC system performs robustly within realistic operating conditions, meeting safety requirements and demonstrating practical cruise control functionality. While the distance steady-state error exceeds the ideal target, the system prioritizes safety and passenger comfort—critical factors for real-world deployment. The implementation provides a solid foundation for further development and optimization of advanced driver assistance systems (ADAS).

---

## Appendix: Simulation Configuration

**Vehicle Parameters:**
- Mass: 1500 kg
- Max acceleration: 3.0 m/s²
- Max deceleration: -8.0 m/s²
- Drag coefficient: 0.3

**ACC Settings:**
- Set speed: 30.0 m/s
- Time headway: 1.5 s
- Minimum gap: 10.0 m
- Emergency TTC threshold: 3.0 s
- Control timestep: 0.1 s

**Sensor Data:**
- Duration: 0-150s (1501 samples)
- Lead vehicle present: t=30s to t=130s
- Lead speed range: 0-36.82 m/s
- Distance range: 1.95-135.33 m
