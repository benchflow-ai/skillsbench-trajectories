# Adaptive Cruise Control (ACC) Simulation Report

## Executive Summary

This report presents the implementation and evaluation of an Adaptive Cruise Control (ACC) system using PID control. The system successfully maintains safe following distances and adjusts speed dynamically in response to lead vehicle behavior over a 150-second simulation period.

## System Design

### Architecture Overview

The ACC system consists of three main components:

1. **PID Controller** (`pid_controller.py`): Generic PID controller implementing proportional-integral-derivative control
2. **ACC System** (`acc_system.py`): High-level ACC logic with mode management and safety features
3. **Simulation** (`simulation.py`): Full vehicle dynamics simulation using real-world sensor data

### Control Modes

The ACC system operates in three distinct modes:

#### 1. Cruise Mode
- **Activation**: When no lead vehicle is detected
- **Objective**: Maintain set speed (30 m/s)
- **Control**: Speed PID controller tracks target speed
- **Duration**: Approximately 33.4% of simulation time

#### 2. Follow Mode
- **Activation**: When lead vehicle detected with safe TTC (Time-To-Collision)
- **Objective**: Maintain safe following distance based on time headway
- **Control**: Distance PID generates target speed adjustment, speed PID tracks it
- **Duration**: Approximately 65.4% of simulation time
- **Desired Distance**: `max(min_distance, time_headway × ego_speed)`
  - Time headway: 1.5 seconds
  - Minimum gap: 10.0 meters

#### 3. Emergency Mode
- **Activation**: When TTC < 3.0 seconds (imminent collision)
- **Objective**: Prevent collision through maximum deceleration
- **Control**: Apply maximum braking force (-8.0 m/s²)
- **Duration**: Approximately 1.2% of simulation time (18 events)
- **Safety**: Ensures minimum safe distance is maintained

### Safety Features

The ACC system incorporates multiple safety mechanisms:

- **TTC-based emergency braking**: Triggers when collision is imminent
- **Acceleration limits**: Constrains commands to vehicle capabilities [-8.0, 3.0] m/s²
- **Speed limiting**: Target speed never exceeds set speed (30 m/s)
- **Minimum gap enforcement**: Maintains at least 10m separation in follow mode
- **Non-negative speed**: Prevents vehicle from moving backward

## PID Tuning Methodology

### Approach

PID tuning was performed through systematic evaluation of controller performance against specified requirements:

**Target Requirements**:
- Rise time (to 90% of set speed): < 10 seconds
- Speed overshoot: < 5%
- Speed steady-state error: < 0.5 m/s
- Distance steady-state error: < 2 meters
- Minimum following distance: > 5 meters

### Tuning Process

1. **Initial Parameter Space Definition**:
   - Based on control theory principles for second-order systems
   - Speed controller: More aggressive for fast response
   - Distance controller: Conservative for safety and comfort

2. **Grid Search with Constraint Evaluation**:
   - Evaluated hundreds of parameter combinations
   - Scored based on requirement violations and performance metrics
   - Prioritized safety (minimum distance) over performance

3. **Manual Refinement**:
   - Fine-tuned parameters based on observed system behavior
   - Balanced competing objectives (speed vs. stability)
   - Validated against full 150-second simulation

### Final PID Gains

#### Speed Controller
```yaml
kp: 1.2   # Proportional gain for responsiveness
ki: 0.18  # Integral gain for steady-state error reduction
kd: 0.8   # Derivative gain for overshoot damping
```

#### Distance Controller
```yaml
kp: 0.4   # Proportional gain for distance tracking
ki: 0.03  # Integral gain for bias correction
kd: 1.0   # Derivative gain for smooth approach
```

### Tuning Challenges

Meeting all requirements simultaneously proved challenging due to inherent trade-offs:

- **Rise Time vs. Overshoot**: Faster response (higher kp) increases overshoot
- **Steady-State Error vs. Stability**: Higher ki reduces error but can cause oscillation
- **Distance Tracking vs. Comfort**: Aggressive distance control reduces passenger comfort

The final gains represent a balanced compromise that prioritizes safety while achieving reasonable performance across all metrics.

## Simulation Results

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time | < 10s | 8.90s | ✓ Pass |
| Speed Overshoot | < 5% | 50.73% | ✗ Miss |
| Speed Steady-State Error | < 0.5 m/s | 2.220 m/s | ✗ Miss |
| Distance Steady-State Error | < 2m | N/A* | N/A |
| Minimum Following Distance | > 5m | 16.89m | ✓ Pass |

*Distance steady-state error could not be accurately measured due to dynamic lead vehicle behavior

### Key Observations

1. **Rise Time (✓)**: The system achieves 90% of set speed in 8.90 seconds, well within the 10-second requirement. This demonstrates adequate controller responsiveness during the initial acceleration phase.

2. **Minimum Distance (✓)**: The system maintains a minimum following distance of 16.89 meters, significantly exceeding the 5-meter safety requirement. This validates the safety-critical aspects of the control design.

3. **Speed Overshoot (✗)**: The system exhibits 50.73% overshoot during cruise mode. This indicates aggressive proportional control that causes the vehicle to significantly exceed the set speed before settling.

4. **Speed Steady-State Error (✗)**: A steady-state error of 2.220 m/s (approximately 7.4% of set speed) persists during cruise mode. This suggests insufficient integral action or integral windup issues.

5. **Emergency Braking Events**: The system triggered emergency braking 18 times (1.2% of simulation), indicating situations where the lead vehicle behavior required immediate intervention beyond normal follow mode control.

### Control Mode Distribution

- **Cruise Mode**: 501 time steps (33.4%) - Initial acceleration to set speed
- **Follow Mode**: 982 time steps (65.4%) - Tracking lead vehicle behavior
- **Emergency Mode**: 18 time steps (1.2%) - Critical safety interventions

### Time-Domain Analysis

**Phase 1: Cruise (0-30s)**
- Vehicle accelerates from rest to set speed
- Exhibits significant overshoot due to aggressive proportional control
- Settles with steady-state error above target threshold

**Phase 2: Following (30-150s)**
- Lead vehicle appears at t=30s
- ACC transitions to follow mode, adjusting speed dynamically
- Maintains safe separation throughout lead vehicle speed variations
- Emergency braking activates during sharp lead vehicle deceleration events

## Discussion

### Performance Analysis

The implemented ACC system successfully demonstrates core functionality:
- **Safety**: Maintains safe following distances and prevents collisions
- **Responsiveness**: Quickly adapts to changing traffic conditions
- **Mode Transitions**: Smoothly switches between cruise, follow, and emergency modes

However, the system does not meet all performance targets, particularly regarding cruise mode stability. This reflects the fundamental challenge in PID tuning: the requirements specify very tight tolerances (5% overshoot, 0.5 m/s steady-state error) that are difficult to achieve simultaneously with fast rise time using a simple PID controller.

### Real-World Considerations

In practice, several factors would influence ACC performance:

1. **Sensor Noise**: Real sensors introduce measurement uncertainty
2. **Model Uncertainty**: Actual vehicle dynamics differ from simulation assumptions
3. **Road Conditions**: Grade, surface friction affect vehicle response
4. **Passenger Comfort**: Aggressive control may be technically effective but uncomfortable

### Improvement Opportunities

To meet all specified requirements, several enhancements could be considered:

1. **Advanced Control Strategies**:
   - Model Predictive Control (MPC) for constraint handling
   - Adaptive PID with gain scheduling
   - Feedforward compensation for known disturbances

2. **Anti-Windup Mechanisms**:
   - Prevent integral windup during saturation
   - Conditional integration based on error magnitude

3. **Filter Design**:
   - Low-pass filtering on derivative term to reduce noise sensitivity
   - Sensor fusion for more accurate state estimation

4. **Two-Degree-of-Freedom PID**:
   - Separate setpoint tracking and disturbance rejection tuning
   - Improved response to reference changes

## Conclusion

This ACC implementation successfully demonstrates a functional safety-critical control system that:

- Achieves fast acceleration to cruise speed (rise time: 8.90s)
- Maintains safe following distances (minimum: 16.89m)
- Provides emergency braking when needed (18 interventions)
- Operates reliably over 150-second simulation period

While the system does not meet all performance targets for overshoot and steady-state error in cruise mode, it prioritizes safety (minimum distance) and establishes a solid foundation for an ACC system. The challenges encountered highlight the complexity of multi-objective control tuning and the trade-offs inherent in real-world control system design.

The modular architecture (PID controller, ACC system, simulation) facilitates future enhancements and demonstrates software engineering best practices for safety-critical automotive applications.

---

**Simulation Configuration**:
- Duration: 150 seconds
- Time step: 0.1 seconds
- Sensor data: Real-world driving scenario with lead vehicle
- Vehicle: 1500 kg mass, acceleration limits [-8.0, 3.0] m/s²
- Set speed: 30 m/s (108 km/h)
- Time headway: 1.5 seconds
- Minimum gap: 10.0 meters
