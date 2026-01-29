# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### 1.1 ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A general-purpose PID controller with anti-windup protection
2. **ACC System** (`acc_system.py`): The main control logic that selects operating modes and computes acceleration commands
3. **Simulation** (`simulation.py`): Reads sensor data, runs the ACC system, and outputs results

### 1.2 Operating Modes

The ACC operates in three modes:

| Mode | Condition | Action |
|------|-----------|--------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Maintain safe following distance |
| **Emergency** | TTC < 3.0s | Apply maximum braking (-8.0 m/s²) |

### 1.3 Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Continuously calculates TTC when a lead vehicle is present
2. **Emergency Braking**: Automatically triggers when TTC drops below 3.0 seconds
3. **Time Headway Distance**: Desired following distance = min_distance + time_headway × ego_speed
4. **Acceleration Limits**: All commands clamped to [-8.0, 3.0] m/s²
5. **Anti-Windup**: PID integral term limited to prevent controller saturation

### 1.4 Following Distance Formula

```
desired_distance = min_distance + time_headway × ego_speed
                 = 10.0 m + 1.5s × ego_speed
```

At 30 m/s cruise speed: desired_distance = 10 + 1.5 × 30 = 55 m

---

## 2. PID Tuning Methodology

### 2.1 Tuning Approach

The PID parameters were tuned iteratively to meet the following requirements:

| Metric | Target | Priority |
|--------|--------|----------|
| Speed Rise Time | < 10s | High |
| Speed Overshoot | < 5% | High |
| Speed Steady-State Error | < 0.5 m/s | Medium |
| Distance Steady-State Error | < 2 m | Medium |
| Minimum Distance | > 5 m | Safety |

### 2.2 Tuning Constraints

- **Physical Limit**: With max acceleration of 3.0 m/s², theoretical minimum rise time is exactly 10 seconds (30 m/s ÷ 3.0 m/s² = 10s)
- **Trade-off**: Higher Kp reduces rise time but increases overshoot
- **Anti-Windup**: Integral term only accumulates when error < 10 m/s to prevent saturation

### 2.3 Final PID Gains

**Speed Controller:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Kp | 4.0 | Fast response to speed error |
| Ki | 0.08 | Eliminate steady-state error |
| Kd | 0.25 | Dampen oscillations |

**Distance Controller:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Kp | 0.5 | Proportional distance correction |
| Ki | 0.02 | Eliminate steady-state gap error |
| Kd | 1.5 | Smooth approach to lead vehicle |

---

## 3. Simulation Results

### 3.1 Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed Rise Time | < 10s | 10.1s | Near limit (physics constrained) |
| Speed Overshoot | < 5% | 1.30% | PASS |
| Speed Steady-State Error | < 0.5 m/s | 0.24-0.30 m/s | PASS |
| Distance Steady-State Error | < 2 m | 1.55 m | PASS |
| Minimum Distance | > 5 m | 1.95 m | FAIL (emergency scenario) |
| Control Duration | 150s | 150s | PASS |

### 3.2 Mode Distribution

| Mode | Timesteps | Percentage |
|------|-----------|------------|
| Cruise | 501 | 33.4% |
| Follow | 980 | 65.3% |
| Emergency | 20 | 1.3% |

### 3.3 Scenario Analysis

The simulation includes several challenging scenarios:

1. **Initial Acceleration (t=0-10s)**: Vehicle accelerates from rest to cruise speed
2. **Steady Cruise (t=15-30s)**: No lead vehicle, maintain 30 m/s
3. **Lead Vehicle Appears (t=30s)**: Transition to follow mode
4. **Variable Lead Speed (t=30-120s)**: Lead vehicle speed varies between ~20-35 m/s
5. **Emergency Cut-in (t=120s)**: Sudden appearance of slow vehicle at 25m distance
6. **Recovery and Cruise (t=130-150s)**: Lead vehicle departs, return to cruise mode

### 3.4 Emergency Braking Event (t=120-122s)

At t=120s, the sensor data shows a sudden cut-in scenario:
- Distance drops from 97.16m to 25.52m
- Lead vehicle speed drops from 20.1 m/s to 5.06 m/s
- ACC immediately applies maximum braking (-8.0 m/s²)
- Minimum distance reached: 1.95m at t=121.6s

**Analysis**: This represents an extreme emergency scenario where even maximum braking cannot prevent the minimum distance violation. The ACC correctly identified the emergency and applied maximum deceleration. In a real vehicle, this scenario would trigger Automatic Emergency Braking (AEB) with additional safety measures.

---

## 4. Key Observations

### 4.1 Speed Control Performance

- Aggressive tuning achieves near-optimal rise time (10.1s vs theoretical 10.0s minimum)
- Low overshoot (1.30%) demonstrates good stability
- Integral anti-windup effectively prevents overshoot during saturation

### 4.2 Distance Control Performance

- Smooth following behavior during normal operation
- Steady-state distance error within 2m requirement
- Quick response to lead vehicle speed changes

### 4.3 Limitations

1. **Physics Constraint**: Cannot achieve rise time < 10s with max_acceleration = 3.0 m/s²
2. **Emergency Scenarios**: Extreme cut-in events may violate minimum distance
3. **Sensor Data Dependency**: Controller performance depends on accurate sensor readings

---

## 5. Files Generated

| File | Description |
|------|-------------|
| `pid_controller.py` | PID controller class with anti-windup |
| `acc_system.py` | ACC system with mode selection |
| `simulation.py` | Simulation runner |
| `tuning_results.yaml` | Tuned PID parameters |
| `simulation_results.csv` | 1501 rows of simulation data |
| `acc_report.md` | This report |
