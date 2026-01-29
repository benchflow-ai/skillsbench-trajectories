# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A discrete PID controller implementing the control law:
   ```
   u(t) = Kp * e(t) + Ki * integral(e) + Kd * de/dt
   ```

2. **ACC System** (`acc_system.py`): The main control logic that:
   - Selects operating mode based on sensor inputs
   - Computes acceleration commands using appropriate PID controller
   - Enforces vehicle constraints and safety limits

3. **Simulation** (`simulation.py`): Runs the 150s simulation using:
   - Lead vehicle behavior from sensor_data.csv
   - PID gains from tuning_results.yaml
   - Vehicle parameters from vehicle_params.yaml

### 1.2 Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) using speed PID |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Maintain safe following distance using distance PID |
| **Emergency** | TTC < 3.0s | Apply maximum braking (-8.0 m/s^2) |

### 1.3 Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Continuous calculation of TTC when closing on lead vehicle
2. **Emergency Braking**: Automatic maximum deceleration when TTC < 3.0s threshold
3. **Speed Limiting**: ACC never exceeds set speed, even when following a faster lead vehicle
4. **Acceleration Limits**: All commands clamped to [-8.0, 3.0] m/s^2
5. **Safe Following Distance**: Target = max(10.0m, 1.5s * ego_speed)

## 2. PID Tuning Methodology

### 2.1 Speed Controller

The speed PID controller maintains the set speed during cruise mode.

**Tuning approach:**
- Started with Kp to achieve desired rise time
- Added small Ki to eliminate steady-state error
- Added Kd to reduce overshoot

**Constraints considered:**
- Rise time < 10s (with max accel 3.0 m/s^2, theoretical minimum = 30/3 = 10s)
- Overshoot < 5%
- Steady-state error < 0.5 m/s

### 2.2 Distance Controller

The distance PID controller maintains safe following distance in follow mode.

**Tuning approach:**
- Balanced Kp for responsive tracking without oscillation
- Moderate Ki for steady-state accuracy
- Kd for damping and anticipating distance changes

**Constraints considered:**
- Steady-state error < 2m
- Minimum distance > 5m during emergency scenarios
- Stable response to lead vehicle speed variations

### 2.3 Final PID Gains

```yaml
pid_speed:
  kp: 1.5
  ki: 0.01
  kd: 0.5

pid_distance:
  kp: 1.1
  ki: 0.08
  kd: 1.3
```

## 3. Simulation Results

### 3.1 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed Rise Time | < 10s | 9.00s | PASS |
| Speed Overshoot | < 5% | 3.28% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.021 m/s | PASS |
| Distance Steady-State Error | < 2m | 1.98m | PASS |
| Minimum Distance | > 5m | 8.06m | PASS |

### 3.2 Scenario Analysis

The simulation covers several challenging scenarios from the sensor data:

1. **Initial Cruise (0-30s)**: Vehicle accelerates from 0 to 30 m/s
   - Achieved 90% of set speed in 9.0s
   - Minimal overshoot (3.28%)

2. **Follow Mode (30-60s)**: Lead vehicle at ~25 m/s
   - Controller maintains safe following distance
   - Distance error typically < 2m

3. **High-Speed Following (60-100s)**: Lead vehicle at ~30 m/s
   - Speed limited at set speed
   - Distance increases when lead exceeds set speed (by design)

4. **Lead Deceleration (100-120s)**: Lead vehicle slows from 30 to 20 m/s
   - Controller successfully tracks slowing lead
   - Maintains safe distance throughout

5. **Emergency Scenario (120-122s)**: Sudden lead vehicle braking
   - Emergency mode activated when TTC < 3.0s
   - Maximum braking applied
   - Minimum distance maintained at 8.06m (> 5m requirement)

6. **Recovery (122-130s)**: Lead vehicle accelerates again
   - Controller smoothly resumes follow mode
   - Distance maintained throughout recovery

7. **Return to Cruise (130-150s)**: Lead vehicle leaves
   - Smooth transition back to cruise mode
   - Speed returns to 30 m/s set speed

### 3.3 Mode Distribution

The simulation included the following mode distribution:
- Cruise mode: Initial acceleration (0-30s) and final phase (130-150s)
- Follow mode: Main following period (30-130s)
- Emergency mode: Brief periods during sudden lead braking events

## 4. Conclusions

The ACC system successfully meets all performance targets:

1. **Speed Control**: The speed PID provides fast response (9.0s rise time) with minimal overshoot (3.28%) and excellent steady-state tracking (0.021 m/s error).

2. **Distance Control**: The distance PID maintains the safe following distance with steady-state error of 1.98m, meeting the <2m requirement.

3. **Safety**: The emergency braking system ensures minimum distance remains above 5m (achieved 8.06m) even during sudden lead vehicle braking.

4. **Robustness**: The system handles various scenarios including lead vehicle speed variations, emergency braking, and mode transitions smoothly.

The tuned PID parameters provide a good balance between responsive tracking and stability, meeting all specified requirements while maintaining safety margins.
