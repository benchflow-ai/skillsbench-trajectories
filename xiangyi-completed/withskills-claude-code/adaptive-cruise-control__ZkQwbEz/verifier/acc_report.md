# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PIDController** (`pid_controller.py`): A standard PID controller with anti-windup protection
   - Proportional, Integral, and Derivative control terms
   - Configurable output limits for anti-windup
   - Reset functionality for mode transitions

2. **AdaptiveCruiseControl** (`acc_system.py`): The main ACC logic
   - Dual PID controllers: one for speed control, one for distance control
   - Mode selection based on sensor inputs and safety thresholds
   - Acceleration limiting near setpoint to prevent overshoot

3. **Simulation** (`simulation.py`): Vehicle dynamics simulation
   - Reads lead vehicle data from sensor_data.csv
   - Computes ego vehicle response to ACC commands
   - Tracks positions to compute actual following distance

### 1.2 Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID |
| **Follow** | Lead vehicle present, TTC > 3s | Maintain safe following distance using combined speed/distance control |
| **Emergency** | TTC < 3.0s | Apply maximum braking (-8.0 m/s^2) |

### 1.3 Safety Features

- **Time-To-Collision (TTC) Monitoring**: Emergency braking triggers when TTC < 3.0s
- **Safe Following Distance**: Dynamic gap = 10m + 1.5s * speed
- **Acceleration Limits**: Hard limits of [-8.0, 3.0] m/s^2
- **Overshoot Prevention**: Acceleration limiting when approaching set speed
- **Anti-windup**: PID integral term clamping to prevent saturation effects

## 2. PID Tuning Methodology

### 2.1 Approach

The tuning followed a systematic approach:

1. **Speed Controller**: Tuned for fast rise time with minimal overshoot
   - High Kp (1.5) for aggressive acceleration during ramp-up
   - Moderate Ki (0.2) for zero steady-state error
   - Low Kd (0.1) for basic damping

2. **Distance Controller**: Tuned for stable car-following
   - Moderate Kp (0.5) for responsive gap control
   - Low Ki (0.02) to avoid oscillation
   - Higher Kd (0.3) for smooth approach to target distance

### 2.2 Final Tuned Gains

```yaml
pid_speed:
  kp: 1.5
  ki: 0.2
  kd: 0.1

pid_distance:
  kp: 0.5
  ki: 0.02
  kd: 0.3
```

### 2.3 Key Tuning Insights

- **Acceleration Limiting**: Near the set speed (within 1.5 m/s), acceleration is progressively limited to prevent overshoot caused by integral windup
- **Mode Transitions**: Controllers are reset when switching between modes to prevent integral term carryover
- **Anti-windup Protection**: PID outputs are clamped to vehicle acceleration limits

## 3. Simulation Results

### 3.1 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time (90%) | < 10s | 9.0s | PASS |
| Speed Overshoot | < 5% | 0.13% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.01 m/s | PASS |
| Distance Steady-State Error | < 2m | 0.73m | PASS |
| Minimum Distance | > 5m | 13.84m | PASS |
| Control Duration | 150s | 150s | PASS |

### 3.2 Scenario Coverage

The simulation covers the following scenarios from the sensor data:

1. **Initial Acceleration (t=0-10s)**: Vehicle accelerates from 0 to 30 m/s
2. **Cruise Control (t=10-30s)**: Maintains set speed with no lead vehicle
3. **Vehicle Following (t=30-120s)**: Lead vehicle appears, ACC maintains safe distance
4. **Emergency Braking (t=120-122s)**: Lead vehicle decelerates rapidly, ACC applies emergency braking
5. **Recovery (t=122-126s)**: Lead vehicle accelerates, ACC resumes following
6. **Return to Cruise (t=130-150s)**: Lead vehicle disappears, ACC returns to set speed

### 3.3 Mode Distribution

- Cruise mode: 501 timesteps (33.4%)
- Follow mode: 982 timesteps (65.4%)
- Emergency mode: 18 timesteps (1.2%)

## 4. Configuration Summary

### 4.1 Vehicle Parameters
- Mass: 1500 kg
- Max acceleration: 3.0 m/s^2
- Max deceleration: -8.0 m/s^2

### 4.2 ACC Settings
- Set speed: 30.0 m/s
- Time headway: 1.5 s
- Minimum distance: 10.0 m
- Emergency TTC threshold: 3.0 s

### 4.3 Simulation Parameters
- Timestep: 0.1 s
- Duration: 150 s
- Total samples: 1501

## 5. Files Produced

| File | Description |
|------|-------------|
| `pid_controller.py` | PID controller implementation with anti-windup |
| `acc_system.py` | ACC system with cruise, follow, and emergency modes |
| `simulation.py` | Vehicle simulation driver |
| `tuning_results.yaml` | Final tuned PID parameters |
| `simulation_results.csv` | 1501-row output with all simulation data |
| `acc_report.md` | This report |

## 6. Conclusion

The ACC system successfully meets all specified performance targets. The combination of dual PID controllers with mode-based switching, anti-windup protection, and acceleration limiting near the setpoint provides robust speed control with minimal overshoot while maintaining safe following distances in car-following scenarios.
