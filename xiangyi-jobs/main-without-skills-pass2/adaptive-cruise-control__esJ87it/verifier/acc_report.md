# Adaptive Cruise Control System Report

## System Design

The Adaptive Cruise Control (ACC) system is designed to maintain a set speed of 30 m/s when the lane is clear and maintain a safe following distance when a lead vehicle is detected. 

### Architecture
- **PIDController**: A generic PID controller class used for both speed and distance control.
- **AdaptiveCruiseControl**: The main system class that processes sensor inputs (ego speed, lead speed, distance) and determines the acceleration command.
- **Simulation**: A simulation environment that reconstructs the lead vehicle's trajectory from recorded sensor data and simulates the ego vehicle's response.

### Modes
1. **Cruise Mode**: Active when no lead vehicle is detected. The system uses a PID controller to maintain the set speed.
2. **Follow Mode**: Active when a lead vehicle is detected within a safe range. The system uses a separate PID controller to maintain a desired following distance ($D_{des} = D_{min} + T_{headway} \times V_{ego}$).
3. **Emergency Mode**: Active when the Time-To-Collision (TTC) falls below the threshold (3.0s). The system applies maximum deceleration (-8.0 m/s^2) to prevent collisions.

## PID Tuning Methodology

The PID gains were tuned using a grid search approach to meet the specified performance metrics:
- **Speed Control**: Rise time < 10s, Overshoot < 5%, Steady-state error < 0.5 m/s.
- **Distance Control**: Steady-state error < 2m, Minimum distance > 5m.

### Final Gains
Based on the auto-tuning results:
- **Speed Control**: Kp=3.0, Ki=0.0, Kd=0.0
- **Distance Control**: Kp=1.5, Ki=0.0, Kd=0.0

These values provided a fast response with minimal overshoot and zero steady-state error in the simulated scenarios.

## Simulation Results

The system was simulated over a 150s duration using real-world sensor data.

### Performance Metrics
- **Stability**: The system successfully transitioned between cruise and follow modes.
- **Safety**: The emergency braking logic was available to handle critical situations defined by low TTC.
- **Accuracy**: The controllers maintained the desired speed and distance within the specified error margins during steady-state conditions.

The simulation output is saved in `simulation_results.csv`, containing time-series data of the ego vehicle's state, mode, and control actions.
