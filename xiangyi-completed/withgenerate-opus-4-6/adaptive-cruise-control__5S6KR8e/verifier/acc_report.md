# Adaptive Cruise Control - Simulation Report

## 1. System Design

### Architecture
The ACC system consists of three main components:

1. **PID Controllers** - Two independent PID controllers handle speed control (cruise mode)
   and distance control (follow mode). Each controller computes an acceleration command
   based on the error between the desired and actual value.

2. **Mode Selector** - Determines the operating mode based on sensor inputs:
   - Whether a lead vehicle is detected
   - Time-to-collision (TTC) relative to the emergency threshold

3. **Safety Layer** - Enforces hard constraints on acceleration commands:
   - Acceleration clamped to [-8.0, 3.0] m/s^2
   - Emergency braking when TTC < 3.0s
   - Speed cannot go negative (no reverse)

### Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected | PID speed control to maintain 30.0 m/s |
| **Follow** | Lead vehicle present, TTC >= 3.0s | PID distance control to maintain safe gap |
| **Emergency** | TTC < 3.0s | Maximum deceleration (-8.0 m/s^2) |

### Safety Features
- **Constant Time Headway (CTH) policy**: Desired distance = 1.5s x ego_speed + 10.0m
- **Emergency braking**: Triggered when TTC drops below 3.0s
- **Acceleration limits**: Hard-clamped to vehicle physical limits
- **PID reset on mode transitions**: Prevents integral windup when switching modes

## 2. PID Tuning

### Methodology
PID gains were tuned using a systematic manual approach:

1. **Speed PID**: Tuned first in isolation during the cruise phase (t=0-30s):
   - Started with proportional-only control, increasing Kp until acceptable rise time (<10s)
   - Added integral gain Ki to eliminate steady-state error (<0.5 m/s)
   - Added derivative gain Kd to reduce overshoot (<5%)

2. **Distance PID**: Tuned during the follow phase (t=30-130s):
   - Set Kp to provide reasonable response to distance errors
   - Added Ki for steady-state distance accuracy (<2m error)
   - Added Kd to dampen oscillations and respond to closing rate

### Final Gains

| Controller | Kp | Ki | Kd |
|-----------|-----|-----|-----|
| Speed | 3.0 | 0.01 | 0.1 |
| Distance | 1.0 | 0.1 | 0.5 |

## 3. Simulation Results

### Scenario Description
- **Duration**: 150 seconds
- **Phase 1 (0-30s)**: Cruise mode - accelerate from 0 to 30.0 m/s
- **Phase 2 (30-130s)**: Follow mode - maintain safe distance behind lead vehicle
  - Includes emergency braking scenario around t=120-122s (lead vehicle nearly stops)
- **Phase 3 (130-150s)**: Cruise mode - resume set speed after lead vehicle disappears

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time | < 10s | 9.0s | PASS |
| Speed Overshoot | < 5% | 0.55% | PASS |
| Speed SS Error | < 0.5 m/s | 0.0031 m/s | PASS |
| Distance SS Error | < 2m | 0.3098m | PASS |
| Min Distance | > 5m | 19.24m | PASS |
| Control Duration | 150s | 150s | PASS |

### Key Observations
- The vehicle successfully accelerates from rest to the set speed of 30.0 m/s
  with a rise time of 9.0s.
- Maximum speed reached during cruise: 30.16 m/s
  (overshoot: 0.55%).
- During the follow phase, the ACC maintains a safe distance using the CTH policy.
- The emergency braking scenario around t=120s is handled by the emergency mode,
  applying maximum deceleration when TTC drops below the threshold.
- Minimum TTC observed: 2.10s.
- After the lead vehicle disappears at t=130s, the system smoothly transitions
  back to cruise mode and resumes the set speed.
