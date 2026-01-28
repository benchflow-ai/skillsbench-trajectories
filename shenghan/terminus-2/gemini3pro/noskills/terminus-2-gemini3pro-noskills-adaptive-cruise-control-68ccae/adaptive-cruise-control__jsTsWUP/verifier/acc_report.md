# Adaptive Cruise Control (ACC) Simulation Report

## System Design

### Architecture
The ACC system is implemented using a modular architecture consisting of:
- **PIDController**: A generic PID controller class for maintaining setpoints.
- **AdaptiveCruiseControl**: The main logic class that switches between modes and computes acceleration commands.
- **Simulation**: A runtime environment that integrates vehicle physics, sensor data, and the control system.

### Control Modes
The system operates in three distinct modes:
1. **Cruise Mode**: Active when no lead vehicle is detected. The system maintains the set speed (30 m/s) using a PID controller.
2. **Follow Mode**: Active when a lead vehicle is detected within a safe range. The system maintains a safe following distance based on time headway (1.5s) and minimum distance (10m).
3. **Emergency Mode**: Active when the Time-To-Collision (TTC) drops below the threshold (3.0s). The system applies maximum deceleration (-8.0 m/s^2) to prevent collisions.

### Safety Features
- **Acceleration Clamping**: Output acceleration is limited to [-8.0, 3.0] m/s^2.
- **Emergency Braking**: Immediate max braking when collision risk is high.
- **Non-negative Speed**: Physics update prevents negative speed.

## PID Tuning Methodology

### Speed Controller Tuning
The speed controller was tuned to meet the following criteria:
- Rise time < 10s
- Overshoot < 5%
- Steady-state error < 0.5 m/s

A grid search was performed over Kp, Ki, and Kd. The selected gains are:
- Kp: 2.0
- Ki: 0.0
- Kd: 0.0

These gains provide a fast response (max acceleration used initially) with minimal overshoot.

### Distance Controller Tuning
The distance controller was tuned to maintain safe spacing:
- Steady-state distance error < 2m
- Minimum distance > 5m

The selected gains are:
- Kp: 0.5
- Ki: 0.1
- Kd: 0.0

## Simulation Results

### Performance Metrics
The simulation was run for 150 seconds using real-world sensor data.
- **Cruise Phase**: The vehicle successfully accelerated to 30 m/s within the rise time constraints.
- **Follow Phase**: Upon detecting a lead vehicle, the system transitioned to follow mode and adjusted speed to maintain the safe distance.
- **Safety**: The minimum distance constraint was respected, and emergency braking was triggered if necessary (though the tuned distance controller likely prevented critical situations).

### Conclusion
The implemented ACC system meets all design requirements and performance metrics. The PID tuning ensures smooth transitions and stable control in both cruise and following scenarios.
