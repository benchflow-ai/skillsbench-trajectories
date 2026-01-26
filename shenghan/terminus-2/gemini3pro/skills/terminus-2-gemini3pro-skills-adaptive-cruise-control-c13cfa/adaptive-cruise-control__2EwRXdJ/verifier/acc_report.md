# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### Architecture
The ACC system is implemented in Python with a modular design:
- **PIDController**: A generic PID class handling the control logic with anti-windup and derivative calculation.
- **AdaptiveCruiseControl**: The main system class that integrates vehicle parameters and switches between control modes.
- **Simulation**: A runner script that integrates sensor data, vehicle physics, and the control system.

### Control Modes
The system operates in three distinct modes:
1. **Cruise Mode**: Active when no lead vehicle is detected. Maintains the set speed (30 m/s) using a speed-based PID controller.
2. **Follow Mode**: Active when a lead vehicle is detected and TTC is safe. Maintains a safe following distance defined by {safe} = v_{ego} * t_{headway} + d_{min}$. Uses a distance-based PID controller.
3. **Emergency Mode**: Active when Time-To-Collision (TTC) drops below 3.0s. Applies maximum deceleration (-8.0 m/s^2) to prevent collisions.

### Safety Features
- **Acceleration Clamping**: Output is strictly limited to [-8.0, 3.0] m/s^2.
- **Emergency Braking**: High-priority override based on TTC.
- **Non-negative Speed**: Physics model prevents reverse motion.

## 2. PID Tuning Methodology

### Methodology
Tuning was performed using a coordinate descent approach via the  script:
1. **Speed Controller**: Tuned to minimize rise time while keeping overshoot < 5% and steady-state error < 0.5 m/s. Tested using a step response from 0 to 30 m/s.
2. **Distance Controller**: Tuned to minimize distance error while ensuring stability. Tested using a scenario where the ego vehicle approaches a lead vehicle.

### Final Gains
Based on the automated tuning results saved in :

**Speed PID**:
- Kp: 5.0
- Ki: 0.0
- Kd: 0.0

**Distance PID**:
- Kp: 1.0
- Ki: 0.0
- Kd: 0.5

## 3. Simulation Results

The simulation was run for 150 seconds using real-world sensor data ().

### Performance Metrics
- **Stability**: The system successfully transitioned between Cruise and Follow modes without instability.
- **Safety**: Emergency braking logic was available to handle critical TTC events.
- **Tracking**: The speed controller achieved the target speed within the rise time constraints during cruise phases.

The detailed time-series data is available in .
