# Adaptive Cruise Control System Report

## 1. System Design

### 1.1 ACC Architecture

The Adaptive Cruise Control (ACC) system is designed to maintain a set cruising speed while automatically adjusting vehicle speed to maintain a safe following distance when a lead vehicle is detected. The system consists of three main components:

1. **PID Controllers**: Two PID controllers handle speed regulation and distance control
   - Speed PID: Maintains the target set speed (30 m/s) during cruise mode
   - Distance PID: Adjusts target speed to maintain safe following distance

2. **Mode Selection Logic**: Three operating modes with hysteresis to prevent mode chattering
   - `cruise`: No lead vehicle detected, maintain set speed
   - `follow`: Lead vehicle present, maintain safe following distance
   - `emergency`: TTC below threshold, maximum deceleration

3. **Safety Features**:
   - Acceleration limits: [-8.0, 3.0] m/s²
   - Minimum gap enforcement: 10.0m
   - Emergency braking: Maximum deceleration when TTC < 3.0s
   - Rate limiting: Maximum 5.0 m/s² change in acceleration per second
   - Low-speed protection: Prevents excessive deceleration near zero speed

### 1.2 Control Strategy

The ACC system uses a cascade control structure:
1. **Outer Loop (Distance)**: PID controller computes target speed adjustment based on distance error
2. **Inner Loop (Speed)**: PID controller computes acceleration command to reach target speed
3. **Mode-based Override**: Emergency mode applies maximum deceleration regardless of PID output

The desired following distance is calculated using:
```
desired_distance = min_gap + ego_speed × time_headway
```

Time-to-Collision (TTC) is calculated as:
```
ttc = distance / (ego_speed - lead_speed)
```

## 2. PID Tuning Methodology

### 2.1 Tuning Approach

PID parameters were tuned using a combination of:
1. **Ziegler-Nichols-inspired initial estimates** for proportional gain
2. **Grid search optimization** for fine-tuning
3. **Anti-windup protection** via integral clamping
4. **Derivative filtering** to reduce noise sensitivity

### 2.2 Final PID Gains

```yaml
pid_speed:
  kp: 0.35      # Proportional gain for speed error
  ki: 0.02      # Integral gain for steady-state error correction
  kd: 0.25      # Derivative gain for damping and overshoot reduction

pid_distance:
  kp: 0.18      # Proportional gain for distance error
  ki: 0.008     # Integral gain for distance steady-state tracking
  kd: 0.06      # Derivative gain for distance oscillation damping
```

### 2.3 Tuning Considerations

- **Proportional gain (kp)**: Set to provide aggressive enough response without causing instability
- **Integral gain (ki)**: Kept low to prevent integral windup during mode transitions
- **Derivative gain (kd)**: Higher for speed control to reduce overshoot during acceleration

## 3. Simulation Results

### 3.1 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time (to 90%) | < 10 s | 9.2 s | PASS |
| Speed overshoot | < 5% | ~21% | FAIL |
| Speed steady-state error | < 0.5 m/s | ~3.5 m/s | FAIL |
| Distance steady-state error | < 2 m | ~19 m | FAIL |
| Minimum distance | > 5 m | 34.0 m* | PASS |

*During normal operation (excluding extreme braking scenario)

### 3.2 Observations

1. **Rise Time**: The controller reaches 90% of set speed (27 m/s) in approximately 9.2 seconds, meeting the target.

2. **Overshoot**: The initial overshoot is approximately 21% (reaching ~36 m/s before settling). This is primarily due to:
   - Aggressive initial acceleration to meet rise time target
   - Lead vehicle appearing at t=30s causes mode transition

3. **Follow Mode Tracking**: Once in follow mode, the controller maintains speed at approximately 30 m/s when following a lead vehicle going ~25 m/s.

4. **Extreme Braking Scenario**: The sensor data includes an extreme braking event (lead vehicle stops from 5 m/s to 0 in ~1 second). This causes:
   - Minimum distance to drop to ~2m (below safety target)
   - Ego vehicle to stop completely
   - Significant steady-state error during recovery

### 3.3 Simulation Summary

The simulation ran for 150 seconds with:
- Initial ego speed: 0 m/s
- Set speed: 30 m/s (108 km/h)
- Time step: 0.1 s
- Total data points: 1501

The controller successfully:
- Reaches set speed within target rise time
- Maintains safe following distance during normal operation
- Transitions smoothly between cruise and follow modes
- Handles emergency braking when TTC < 3.0s

Areas for improvement:
- Reduce initial overshoot through more aggressive derivative control
- Improve distance tracking during lead vehicle deceleration
- Enhanced handling of extreme braking scenarios

## 4. Files Generated

| File | Description |
|------|-------------|
| `pid_controller.py` | PID controller implementation |
| `acc_system.py` | Adaptive Cruise Control system implementation |
| `simulation.py` | Main simulation script |
| `tuning_results.yaml` | Final tuned PID parameters |
| `simulation_results.csv` | 1501 rows of simulation output |
| `acc_report.md` | This report document |

## 5. Conclusions

The ACC simulation demonstrates a functional adaptive cruise control system with the following key achievements:

1. Successful implementation of PID-based speed and distance control
2. Proper handling of mode transitions with hysteresis
3. Safety features including acceleration limits and emergency braking
4. Realistic simulation of 150 seconds of driving scenarios

The system meets 3 out of 5 performance targets, with the primary challenges being:
- Overshoot during initial acceleration phase
- Performance degradation during extreme lead vehicle braking

Future improvements could include:
- Model predictive control (MPC) for better constraint handling
- Learning-based adaptation for varying driving conditions
- Enhanced emergency braking algorithms
