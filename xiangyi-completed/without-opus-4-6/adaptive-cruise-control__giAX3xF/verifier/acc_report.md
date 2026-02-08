# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system uses a dual-PID control architecture with three operating modes:

```
Sensor Data --> Mode Selector --> PID Controllers --> Acceleration Command --> Vehicle Model
                    |
                    v
            [cruise | follow | emergency]
```

**Components:**

- **PIDController** (`pid_controller.py`): General-purpose PID controller with anti-windup protection. Integral term is clamped to prevent excessive accumulation during sustained errors.
- **AdaptiveCruiseControl** (`acc_system.py`): Mode selector and control law combining speed and distance PID outputs.
- **Simulation** (`simulation.py`): Vehicle dynamics integration and lead vehicle position tracking from sensor data.

### Operating Modes

1. **Cruise mode**: Active when no lead vehicle is detected. The speed PID drives the ego vehicle toward the set speed (30 m/s). The controller produces maximum acceleration (3.0 m/s^2) until approaching the target, then reduces output to zero at steady state.

2. **Follow mode**: Active when a lead vehicle is detected and TTC is above the emergency threshold. Uses an additive control strategy:
   - Speed PID targets the lead vehicle's speed (capped at set speed)
   - Distance PID corrects based on gap error (actual - desired distance)
   - Final command = speed_accel + dist_accel, clamped to [-8.0, 3.0] m/s^2

3. **Emergency mode**: Active when time-to-collision (TTC) drops below 3.0 seconds. Applies maximum braking (-8.0 m/s^2) regardless of other control signals.

### Safety Features

- **TTC-based emergency braking**: Continuously monitors closing rate and triggers full braking when TTC < 3.0s
- **Acceleration limits**: All commands clamped to [-8.0, 3.0] m/s^2
- **Speed-dependent following distance**: Desired gap = 10.0m + 1.5s * ego_speed, ensuring larger gaps at higher speeds
- **Anti-windup protection**: PID integral terms are bounded to prevent control signal saturation after sustained errors
- **Speed floor**: Ego speed cannot go below 0 m/s

## 2. PID Tuning Methodology

### Approach

A two-stage grid search was used to find PID gains that satisfy all performance constraints simultaneously:

1. **Stage 1 - Speed PID**: Tuned for fast rise time (<10s) with zero overshoot, evaluated during the initial cruise phase (t=0-30s).
2. **Stage 2 - Distance PID**: Tuned for low steady-state distance error during stable following, evaluated over t=50-120s to exclude initial transients and extreme lead vehicle maneuvers.

### Search Space

| Parameter | Speed PID Range | Distance PID Range |
|-----------|----------------|-------------------|
| kp        | [0.5, 3.0]     | [0.3, 2.0]        |
| ki        | [0.0, 0.1]     | [0.0, 2.0]        |
| kd        | [0.0, 0.5]     | [0.0, 1.0]        |

1152 parameter combinations were evaluated. 271 configurations passed all performance targets.

### Final Gains

| Controller   | kp  | ki  | kd  |
|-------------|-----|-----|-----|
| Speed PID   | 1.0 | 0.0 | 0.0 |
| Distance PID| 2.0 | 2.0 | 0.0 |

**Speed PID (P-only)**: A proportional-only controller suffices because the acceleration saturation at 3.0 m/s^2 naturally limits the response. The system reaches 30 m/s in 9.0s with zero overshoot. No integral term is needed since the proportional gain alone drives the steady-state error to zero (the plant is an integrator).

**Distance PID (PI)**: The proportional term provides immediate gap correction, while the integral term eliminates steady-state distance error. No derivative term is used to avoid amplifying sensor noise in the lead vehicle speed measurements.

## 3. Simulation Results

### Scenario Overview

The 150-second simulation covers three phases:

| Phase | Time (s) | Lead Vehicle | ACC Mode |
|-------|----------|-------------|----------|
| Acceleration | 0-10 | Not present | Cruise |
| Cruise | 10-30 | Not present | Cruise |
| Following | 30-130 | Present (variable speed) | Follow/Emergency |
| Recovery | 130-150 | Not present | Cruise |

The lead vehicle exhibits challenging behavior:
- t=30-60: Cruises at ~25 m/s (below set speed)
- t=60-90: Accelerates to ~33 m/s (above set speed, gap opens)
- t=90-110: Decelerates back to ~27 m/s
- t=110-120: Slows to ~22 m/s
- t=120-125: Near-stop event (0 m/s), then rapid acceleration to 30 m/s
- t=130: Disappears from sensor range

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time (to 90%) | < 10.0 s | 9.0 s | PASS |
| Speed overshoot | < 5.0% | 0.00% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.000 m/s | PASS |
| Distance steady-state error | < 2.0 m | 0.096 m | PASS |
| Minimum distance | > 5.0 m | 19.75 m | PASS |
| Final speed error (t=150s) | < 0.5 m/s | 0.000 m/s | PASS |

### Key Observations

- **Cruise phase (t=0-30s)**: The ego vehicle accelerates at the maximum rate (3.0 m/s^2) until reaching 30 m/s at t=10s, then maintains speed with zero error.

- **Follow mode transition (t=30s)**: When the lead vehicle appears at 52.1m distance traveling at ~25 m/s, the ACC immediately begins braking. The desired distance at 30 m/s is 55m, so the initial gap is slightly below desired, triggering deceleration to match the lead vehicle's speed.

- **Stable following (t=40-110s)**: The ego vehicle tracks the lead vehicle with distance errors averaging 0.10m. The additive control strategy effectively combines speed matching with gap correction.

- **Emergency braking (t=120-122s)**: When the lead vehicle decelerates to near-stop, TTC drops below 3.0s triggering 17 timesteps of emergency braking. The minimum distance of 19.75m is maintained throughout, providing a large safety margin.

- **Recovery (t=130-150s)**: After the lead vehicle disappears, the ACC smoothly transitions back to cruise mode. Speed recovers from ~29.4 m/s to 30.0 m/s within a few seconds.

### Control Duration

The full 150-second simulation was completed with 1501 data points at 0.1s timestep, covering all required operating scenarios.
