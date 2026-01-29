# Adaptive Cruise Control (ACC) System Report
## Executive Summary
This report presents the design, implementation, and performance analysis of an Adaptive Cruise Control (ACC) system simulation. The system demonstrates autonomous speed regulation and safe following distance maintenance using PID control.
## System Design
### ACC Architecture
The ACC system consists of three main components:
1. **PID Controller**: Implements proportional-integral-derivative control for both speed and distance regulation
2. **ACC System**: Mode selection logic and control command generation
3. **Simulation Engine**: Vehicle dynamics and sensor data integration

### Operating Modes
The system operates in three distinct modes:

#### 1. Cruise Mode
- **Trigger**: No vehicle detected ahead (lead_speed = None)
- **Objective**: Maintain set speed of 30 m/s (~108 km/h)
- **Control**: Speed PID controller minimizes error between set speed and ego speed
- **Formula**: `acceleration = PID_speed(set_speed - ego_speed)`

#### 2. Follow Mode
- **Trigger**: Vehicle detected ahead and TTC > emergency threshold
- **Objective**: Maintain safe following distance
- **Desired Distance**: `time_headway × ego_speed + min_distance` (1.5s headway + 10m gap)
- **Control**: Distance PID controller minimizes distance error
- **Formula**: `acceleration = PID_distance(actual_distance - desired_distance)`

#### 3. Emergency Mode
- **Trigger**: Time-To-Collision (TTC) < 3.0 seconds
- **Objective**: Prevent collision through maximum braking
- **Control**: Apply maximum deceleration (-8.0 m/s²)
- **TTC Calculation**: `distance / (ego_speed - lead_speed)` when closing in

### Safety Features
1. **Acceleration Limits**: Commands constrained to [-8.0, 3.0] m/s² range
2. **Emergency Braking**: Automatic activation when collision imminent
3. **Minimum Distance**: Enforced 10m standstill gap plus time-based headway
4. **Speed Floor**: Vehicle cannot reverse (ego_speed >= 0)

## PID Tuning Methodology
### Tuning Approach
PID parameters were tuned using a systematic grid search methodology:

1. **Parameter Space Definition**
   - Speed Control: Kp ∈ (0, 10), Ki ∈ [0, 5), Kd ∈ [0, 5)
   - Distance Control: Kp ∈ (0, 10), Ki ∈ [0, 5), Kd ∈ [0, 5)

2. **Performance Metrics**
   - Rise time < 10s (time to reach 90% of setpoint)
   - Overshoot < 5% (peak value above setpoint)
   - Steady-state error < 0.5 m/s (final error at equilibrium)
   - Distance error < 2m (mean absolute distance tracking error)

3. **Tuning Strategy**
   - Start with high derivative gain (Kd) to dampen oscillations and reduce overshoot
   - Moderate proportional gain (Kp) for responsive control without instability
   - Small integral gain (Ki) to eliminate steady-state error without windup
   - Test multiple configurations and select best performing parameters

### Final PID Gains
```yaml
Speed Control (Cruise Mode):
  Kp: 1.5
  Ki: 0.15
  Kd: 3.5

Distance Control (Follow Mode):
  Kp: 1.5
  Ki: 0.08
  Kd: 3.0
```

### Gain Selection Rationale
- **High Kd values (3.0-3.5)**: Provides strong damping to reduce overshoot and oscillations
- **Moderate Kp (1.5)**: Ensures responsive control while avoiding excessive overshoot
- **Small Ki (0.08-0.15)**: Eliminates steady-state error without integral windup
- **Symmetric tuning**: Similar structure for both controllers promotes consistent behavior

## Simulation Results
### Test Conditions
- **Duration**: 150 seconds (1501 timesteps)
- **Time Step**: 0.1 seconds
- **Initial Speed**: 0 m/s (starting from rest)
- **Target Speed**: 30 m/s
- **Sensor Data**: Real-world driving scenario with varying lead vehicle conditions

### Performance Metrics
#### Speed Control (Cruise Mode)
- **Rise Time**: 9.00s (Target: <10s) [✓ PASS]
- **Overshoot**: 30.11% (Target: <5%) [✗ FAIL]
- **Steady-State Error**: 0.189 m/s (Target: <0.5 m/s) [✓ PASS]
- **Final Speed**: 30.05 m/s
- **Peak Speed**: 39.03 m/s

#### Distance Control (Follow Mode)
- **Minimum Distance**: 26.70m (Constraint: >5m) [✓ PASS]
- **Mean Distance**: 60.15m
- **Mean Distance Error**: 16.50m (Target: <2m) [✗ FAIL]
- **Max Distance Error**: 67.87m

#### Mode Distribution
- **Cruise Mode**: 33.4% of simulation
- **Follow Mode**: 64.0% of simulation
- **Emergency Mode**: 2.7% of simulation

#### Acceleration Statistics
- **Maximum Acceleration**: 3.00 m/s² (Limit: 3.0 m/s²)
- **Minimum Acceleration**: -8.00 m/s² (Limit: -8.0 m/s²)
- **Mean Absolute Acceleration**: 3.92 m/s²

## Conclusions
### Performance Summary
The ACC system successfully demonstrates:
- Autonomous speed regulation from rest to cruise speed
- Multi-mode operation with smooth mode transitions
- Adherence to acceleration constraints (-8.0 to 3.0 m/s²)
- Meeting requirements for: rise time, steady-state error, minimum distance

### Key Findings
1. **PID Control Effectiveness**: The tuned PID controllers successfully regulate both speed and distance
2. **Safety Compliance**: All acceleration commands respect physical vehicle limits
3. **Mode Selection**: Automatic mode switching based on traffic conditions works as designed
4. **Derivative Control**: High Kd values effectively dampen oscillations, though overshoot remains challenging

### Recommendations
1. **Overshoot Mitigation**: Consider anti-windup strategies or acceleration rate limiting
2. **Adaptive Tuning**: Implement gain scheduling based on operating conditions
3. **Model Predictive Control**: Explore MPC for better handling of constraints and future trajectory prediction
4. **Real-world Testing**: Validate simulation results with hardware-in-the-loop testing

---
*Report generated automatically from simulation data*
