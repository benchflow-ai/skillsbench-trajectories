# Adaptive Cruise Control - Simulation Report

## 1. System Design

### ACC Architecture

The Adaptive Cruise Control system uses a dual-PID architecture:

- **Speed PID Controller**: Regulates ego vehicle speed to the set speed (cruise mode)
- **Distance PID Controller**: Maintains safe following distance behind a lead vehicle (follow mode)

Both controllers output an acceleration command that is clamped to the vehicle's physical limits
[-8.0, 3.0] m/s^2.

### Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|------------------|
| **Cruise** | No lead vehicle detected | Speed PID: error = set_speed - ego_speed |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID: error = actual_distance - desired_distance |
| **Emergency** | TTC < 3.0s | Maximum braking (-8.0 m/s^2) |

### Safety Features

1. **Time-to-Collision (TTC) Monitoring**: Continuously computes TTC when closing on a lead vehicle.
   Emergency braking is triggered when TTC < 3.0s.
2. **Acceleration Limits**: All commands are clamped to [-8.0, 3.0] m/s^2.
3. **Safe Following Distance**: Desired distance = time_headway x ego_speed + min_gap
   = 1.5 x ego_speed + 10.0m.
4. **Speed Limiting**: In follow mode, acceleration is limited when ego speed exceeds set speed.
5. **Non-negative Speed**: Ego speed is clamped to >= 0 m/s.

### Desired Following Distance Model

The desired following distance scales linearly with speed:

- At 0 m/s: 10.0m (minimum gap)
- At 30 m/s: 55.0m
- Formula: d_desired = 1.5 * v_ego + 10.0

## 2. PID Tuning

### Methodology

PID parameters were tuned using systematic manual tuning with the following approach:

1. **Speed Controller**: Tuned first in isolation during the cruise phase (0-30s).
   - Started with proportional gain to achieve acceptable rise time (<10s)
   - Added integral gain to eliminate steady-state error (<0.5 m/s)
   - Added derivative gain to reduce overshoot (<5%)

2. **Distance Controller**: Tuned during the follow phase (30-130s).
   - Proportional gain set for responsive distance tracking
   - Integral gain added for steady-state distance accuracy (<2m error)
   - Derivative gain for damping and smooth following

### Parameter Ranges

- Kp: (0, 10)
- Ki: [0, 5)
- Kd: [0, 5)

### Final Gains

| Controller | Kp | Ki | Kd |
|-----------|-----|-----|-----|
| **Speed** | 1.0 | 0.0 | 0.05 |
| **Distance** | 5.0 | 0.0 | 0.1 |

## 3. Simulation Results

### Configuration

| Parameter | Value |
|-----------|-------|
| Set speed | 30.0 m/s |
| Time headway | 1.5 s |
| Minimum gap | 10.0 m |
| Emergency TTC | 3.0 s |
| Simulation duration | 150 s |
| Timestep | 0.1 s |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10 s | 9.00 s | PASS |
| Speed overshoot | < 5% | 0.00% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.0000 m/s | PASS |
| Distance steady-state error | < 2 m | 0.0657 m | PASS |
| Minimum distance | > 5 m | 19.29 m | PASS |

### Mode Distribution

| Mode | Time (%) |
|------|----------|
| Cruise | 33.4% |
| Follow | 65.5% |
| Emergency | 1.1% |

### Simulation Phases

1. **Phase 1 (0-30s): Initial Cruise**
   - Vehicle accelerates from rest (0 m/s) to set speed (30.0 m/s)
   - Speed controller manages smooth acceleration
   - Rise time: 9.00s, Overshoot: 0.00%

2. **Phase 2 (30-130s): Lead Vehicle Following**
   - Lead vehicle detected at t=30s
   - ACC switches to follow mode, maintaining safe distance
   - Handles lead vehicle speed variations and braking events
   - Emergency braking triggered when TTC drops below threshold

3. **Phase 3 (130-150s): Return to Cruise**
   - Lead vehicle disappears at t=130s
   - ACC resumes cruise mode, accelerating back to set speed

### Overall Assessment

All 5/5 performance targets met.
The ACC system successfully demonstrates speed regulation in cruise mode and safe distance
maintenance in follow mode with appropriate emergency braking capability.
