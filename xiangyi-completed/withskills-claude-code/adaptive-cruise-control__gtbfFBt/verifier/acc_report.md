# Adaptive Cruise Control (ACC) Simulation Report

## System Design

### ACC Architecture

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): A generic PID controller with anti-windup
2. **ACC System** (`acc_system.py`): Mode selection and acceleration command generation
3. **Simulation Engine** (`simulation.py`): Vehicle dynamics and state integration

### Operating Modes

The ACC system operates in three modes:

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Maintain set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s, distance >= 10m | Maintain safe following distance |
| **Emergency** | TTC < 3.0s OR distance < 10m | Apply maximum deceleration |

### Safety Features

1. **Time-To-Collision (TTC) Monitoring**: Emergency braking when TTC < 3.0s
2. **Minimum Distance Enforcement**: Emergency braking when distance < 10m
3. **Time Headway Model**: Desired following distance = min_distance + time_headway * ego_speed
4. **Safety Margin Braking**: Progressive braking when approaching minimum distance
5. **Acceleration Limits**: Commands clamped to [-8.0, 3.0] m/s²

### Control Strategy

**Cruise Mode:**
- Speed error = set_speed - ego_speed
- PID controller generates acceleration command

**Follow Mode:**
- Distance error = actual_distance - desired_distance
- Distance PID controller generates base acceleration
- Speed matching term added: 0.5 * (lead_speed - ego_speed)
- Safety margin braking when distance < 2 * min_distance

**Emergency Mode:**
- Apply maximum deceleration (-8.0 m/s²)

## PID Tuning Methodology

### Approach

The PID controllers were tuned iteratively using the Ziegler-Nichols-inspired method with manual refinement:

1. Start with proportional-only control
2. Increase Kp until acceptable rise time achieved
3. Add integral term to eliminate steady-state error
4. Add derivative term to reduce overshoot
5. Implement anti-windup to prevent integral accumulation during saturation

### Anti-Windup Implementation

The PID controller features conditional integration:
- Integration is paused when output is saturated and error would worsen saturation
- Integral term is clamped to ±30 to prevent excessive accumulation

### Final PID Gains

**Speed Controller:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Kp | 2.0 | Fast response to speed error |
| Ki | 0.3 | Eliminate steady-state speed error |
| Kd | 1.5 | Dampen overshoot |

**Distance Controller:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Kp | 0.6 | Responsive gap control |
| Ki | 0.08 | Eliminate steady-state distance error |
| Kd | 1.0 | Smooth distance adjustments |

## Simulation Results

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time (90% of set speed) | < 10s | 9.10s | ✓ Pass |
| Speed Overshoot | < 5% | 0.64% | ✓ Pass |
| Speed Steady-State Error | < 0.5 m/s | 0.38 m/s | ✓ Pass |
| Distance Steady-State Error | < 2m | 1.56m | ✓ Pass |
| Minimum Distance | > 5m | 19.02m | ✓ Pass |

### Scenario Analysis

The 150-second simulation covers several driving scenarios:

1. **Initial Acceleration (0-30s)**: Starting from rest, the ego vehicle accelerates to cruise speed using maximum acceleration (3.0 m/s²), reaching 30 m/s by t ≈ 10s.

2. **First Following Phase (30-60s)**: Lead vehicle appears at ~52m, traveling at ~25 m/s. The ACC smoothly decelerates and establishes a safe following distance.

3. **Speed Variation (60-120s)**: The lead vehicle's speed varies between 20-35 m/s. The ACC adapts its speed to maintain the desired following distance based on the time headway model.

4. **Emergency Braking (120-122s)**: The lead vehicle brakes suddenly from ~20 m/s to near-stop. The ACC detects the critical TTC and applies maximum deceleration, maintaining a safe minimum distance of 19.02m.

5. **Recovery (122-130s)**: Both vehicles accelerate back to cruising speed.

6. **Return to Cruise (130-150s)**: Lead vehicle disappears, and the ACC resumes cruise control at 30 m/s.

### Key Observations

1. **Robust Emergency Response**: The emergency braking scenario at t=120s demonstrated the system's ability to safely respond to sudden lead vehicle deceleration.

2. **Smooth Mode Transitions**: The system transitions smoothly between cruise, follow, and emergency modes without jerky behavior.

3. **Stable Following**: In steady-state following mode, the distance error remains within 2m of the target, indicating effective gap control.

4. **Anti-Windup Effectiveness**: The conditional integration prevents integral windup during the initial acceleration phase, resulting in minimal overshoot (0.64%).

## Configuration Summary

### Vehicle Parameters
- Mass: 1500 kg
- Max Acceleration: 3.0 m/s²
- Max Deceleration: -8.0 m/s²
- Drag Coefficient: 0.3

### ACC Settings
- Set Speed: 30.0 m/s
- Time Headway: 1.5 s
- Minimum Distance: 10.0 m
- Emergency TTC Threshold: 3.0 s

### Simulation Parameters
- Duration: 150 s
- Time Step: 0.1 s
- Total Data Points: 1501

## Conclusion

The implemented ACC system successfully meets all performance targets while providing safe and comfortable vehicle control. The PID-based control architecture with anti-windup provides robust performance across various driving scenarios, including emergency braking situations. The time headway model ensures a speed-dependent following distance that balances safety with traffic efficiency.
