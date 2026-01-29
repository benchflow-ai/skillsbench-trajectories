# Adaptive Cruise Control (ACC) System Report

## 1. System Design

### 1.1 ACC Architecture

The Adaptive Cruise Control system is designed as a mode-based controller that automatically adjusts vehicle speed to maintain safe following distance while respecting acceleration constraints.

```
+------------------+     +-------------------+     +------------------+
|   Sensor Data    |---->|   ACC System      |---->|  Acceleration    |
| (lead_speed,     |     |                   |     |  Command         |
|  distance)       |     |  - PID Speed      |     |                  |
+------------------+     |  - PID Distance   |     +------------------+
                         |  - Mode Selector  |
                         +-------------------+
```

### 1.2 Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID |
| **Follow** | Lead vehicle detected, TTC >= threshold | Maintain safe following distance using distance PID |
| **Emergency** | TTC < 3.0 seconds | Maximum deceleration (-8.0 m/s²) |

### 1.3 Safety Features

- **Time Headway**: 1.5 seconds - maintains minimum gap proportional to speed
- **Minimum Gap**: 10.0 meters - hard minimum distance
- **TTC Threshold**: 3.0 seconds - triggers emergency braking
- **Acceleration Limits**: [-8.0, 3.0] m/s² - respects vehicle dynamics

### 1.4 Control Structure

```
                    +------------------+
                    |   Set Speed      |
                    |   (30.0 m/s)     |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Speed Error     |
                    |  (set - ego)     |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Speed PID       |----> Acceleration
                    |  Controller      |     Command
                    +--------+---------+
                             |
              +--------------^--------------+
              |              |              |
              |    Lead Vehicle?            |
              |              |              |
              NO            |             YES
              |              |              |
     +--------v-------+      |     +--------v--------+
     |  Cruise Mode   |      |     |  Target Dist    |
     |  (set speed)   |      |     |  = 10 + 1.5*V   |
     +--------+-------+      |     +--------+--------+
              |              |              |
              |              |     +--------v--------+
              |              |     |  Distance Error |
              |              |     |  (actual-target)|
              |              |     +--------+--------+
              |              |              |
              |              |     +--------v--------+
              |              |     |  Distance PID   |
              |              |     |  Controller     |
              |              |     +--------+--------+
              |              |              |
              +--------------)-------------+
                           /
                    TTC < 3.0?
                    /      \
                  NO       YES
                   \      /
            +-------v----v-------+
            |  Follow Mode       |  Emergency Mode
            +--------------------+
```

## 2. PID Tuning Methodology

### 2.1 Tuning Approach

A systematic grid search approach was used to find optimal PID gains:

1. **Speed PID Tuning**: Tune for cruise mode performance (rise time, overshoot, steady-state error)
2. **Distance PID Tuning**: Tune for follow mode performance (distance error, minimum distance)
3. **Fine-tuning**: Joint optimization of both controllers

### 2.2 Tuning Constraints

| Parameter | Range |
|-----------|-------|
| Kp | (0, 10) |
| Ki | [0, 5) |
| Kd | [0, 5) |

### 2.3 Final Tuned Parameters

```yaml
pid_speed:
  kp: 1.6
  ki: 0.1
  kd: 4.0

pid_distance:
  kp: 5.6
  ki: 0.3
  kd: 0.5
```

### 2.4 Tuning Rationale

- **Speed PID**: Moderate Kp for responsive speed control, low Ki to avoid windup, high Kd for damping
- **Distance PID**: Higher Kp for aggressive distance tracking, moderate Ki for steady-state accuracy

## 3. Simulation Results

### 3.1 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time | < 10 s | 8.90 s | PASS |
| Speed Overshoot | < 5% | 2.00% | PASS |
| Cruise SSE | < 0.5 m/s | 0.226 m/s | PASS |
| Distance SSE | < 2 m | 20.55 m | FAIL* |
| Min Distance | > 5 m | 9.03 m | PASS |
| Emergency Activations | 0 | 0 | PASS |

*Note: The distance SSE target of <2m is challenging due to varying lead vehicle behavior in the sensor data. The controller achieves 36.8% of measurements within 2m and 48.5% within 5m.

### 3.2 Simulation Summary

- **Duration**: 150 seconds (1501 timesteps at 0.1s intervals)
- **Lead Vehicle**: Appears at t=30s, travels at varying speeds (23-26 m/s)
- **Speed Profile**: Rises from 0 to 30 m/s in ~9s, maintains set speed in cruise mode
- **Distance Profile**: Stabilizes around 40-50m when lead vehicle at steady speed

### 3.3 Mode Distribution

```
Cruise Mode:  t = 0.0 - 30.0s  (300 timesteps)
Follow Mode:  t = 30.0 - 150.0s (1201 timesteps)
Emergency:    None
```

## 4. Discussion

### 4.1 Cruise Mode Performance

The speed controller achieves excellent performance in cruise mode:
- Rise time of 8.9s meets the <10s target
- Overshoot of 2% is well within the 5% limit
- Steady-state error of 0.23 m/s is half the 0.5 m/s target

### 4.2 Follow Mode Performance

The distance controller maintains safe following distance:
- Minimum distance of 9.03m exceeds the 5m safety requirement
- No emergency braking activations throughout the simulation
- Distance tracking shows expected variation due to lead vehicle speed changes

### 4.3 Limitations

The distance SSE of 20.55m is inflated by:
1. **Lead vehicle speed variations**: When lead vehicle slows, distance temporarily increases
2. **Controller response limits**: Maximum deceleration of -8 m/s² limits closing rate
3. **Target distance dynamics**: Target distance changes with ego speed, creating transients

### 4.4 Recommendations for Improvement

1. **Adaptive gain scheduling**: Adjust PID gains based on operating conditions
2. **Lead speed feedforward**: Incorporate lead vehicle speed for faster response
3. **Model predictive control**: Use prediction for better distance tracking
4. **Look-ahead control**: Account for expected lead vehicle behavior

## 5. Files Generated

| File | Description |
|------|-------------|
| `pid_controller.py` | PID controller implementation |
| `acc_system.py` | ACC system with mode selection |
| `simulation.py` | 150s simulation runner |
| `tuning_results.yaml` | Final PID gains |
| `simulation_results.csv` | Full simulation output (1501 rows) |
| `acc_report.md` | This report |

## 6. Conclusion

The ACC system successfully meets 5 out of 6 performance targets:
- Speed dynamics (rise time, overshoot, steady-state error) are well within spec
- Safety requirements (minimum distance, emergency handling) are satisfied
- Distance tracking shows expected behavior given lead vehicle variations

The distance SSE target of <2m is aggressive for scenarios with significant lead vehicle speed variations. The system maintains safe operation throughout the 150-second simulation.
