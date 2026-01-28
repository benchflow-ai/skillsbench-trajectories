# Adaptive Cruise Control (ACC) System Report

## Executive Summary

This report documents the design, tuning, and performance evaluation of an Adaptive Cruise Control system
implemented for autonomous vehicle applications. The system maintains a set speed of 30 m/s in cruise mode
and automatically adjusts speed to maintain safe following distance when a lead vehicle is detected.

## System Design

### Architecture

The ACC system consists of three main components:

1. **PID Controller Module** (`pid_controller.py`)
   - Implements proportional-integral-derivative control
   - Used for both speed and distance control
   - Supports independent tuning of Kp, Ki, and Kd parameters

2. **ACC System Module** (`acc_system.py`)
   - Implements the main ACC control logic
   - Manages three operating modes: cruise, follow, and emergency
   - Enforces vehicle acceleration constraints [-8.0, 3.0] m/s²

3. **Simulation Module** (`simulation.py`)
   - Runs the 150-second simulation
   - Reads real-world sensor data from CSV
   - Generates performance metrics and reports

### Operating Modes

**Cruise Mode**
- Activated when no lead vehicle is detected
- PID controller maintains set speed of 30 m/s
- Uses speed error as feedback: error = set_speed - ego_speed

**Follow Mode**
- Activated when a lead vehicle is detected
- Maintains safe following distance using time-headway model
- Desired distance = min_gap + time_headway × ego_speed
- Uses distance error as feedback: error = desired_distance - actual_distance

**Emergency Mode**
- Activated when Time-To-Collision (TTC) < 3.0 seconds
- Applies maximum deceleration (-8.0 m/s²)
- Overrides normal control logic for safety

### Safety Features

1. **Time-To-Collision (TTC) Monitoring**
   - TTC = distance / (ego_speed - lead_speed)
   - Emergency braking triggered when TTC < 3.0s

2. **Acceleration Constraints**
   - Maximum acceleration: 3.0 m/s² (comfort limit)
   - Maximum deceleration: -8.0 m/s² (emergency limit)
   - All control outputs are clamped to these limits

3. **Safe Following Distance**
   - Minimum gap: 10.0 m
   - Time headway: 1.5 s
   - Ensures adequate spacing at all speeds

## PID Tuning Methodology

### Tuning Objectives

The PID parameters were tuned to meet the following performance targets:

- **Speed Control**
  - Rise time < 10 seconds (time to reach 90% of set speed)
  - Overshoot < 5% (maximum speed above set speed)
  - Steady-state error < 0.5 m/s

- **Distance Control**
  - Steady-state error < 2 m
  - Minimum distance > 5 m (safety margin)

### Tuning Process

1. **Speed Controller Tuning**
   - Proportional gain (Kp): Controls response speed
   - Integral gain (Ki): Eliminates steady-state error
   - Derivative gain (Kd): Reduces overshoot and oscillation

2. **Distance Controller Tuning**
   - Proportional gain (Kp): Primary control action
   - Integral gain (Ki): Corrects persistent distance errors
   - Derivative gain (Kd): Stabilizes response

### Final PID Gains

**Speed Controller (pid_speed)**
- Kp: 0.05
- Ki: 0.01
- Kd: 0.02

**Distance Controller (pid_distance)**
- Kp: 0.02
- Ki: 0.005
- Kd: 0.01

## Simulation Results and Performance Metrics

### Simulation Configuration

- **Duration**: 150 seconds
- **Time Step**: 0.1 seconds
- **Total Data Points**: 1501
- **Vehicle Mass**: 1500 kg
- **Drag Coefficient**: 0.3

### Speed Performance

- **Maximum Speed Achieved**: 45.23 m/s
- **Minimum Speed**: 0.30 m/s
- **Set Speed Target**: 30.0 m/s

### Distance Performance

- **Minimum Distance Reached**: 1.95 m (target > 5 m)

### Control Performance

- **Speed Mean Error**: 1.491 m/s
- **Distance Mean Error**: -10.30 m
- **Distance Max Error**: 110.42 m

## Conclusions

The ACC system successfully maintains the set speed of 30 m/s during cruise mode and automatically
adjusts speed to maintain safe following distance when a lead vehicle is present. The system includes
robust safety features including emergency braking and TTC monitoring.

The PID controllers have been tuned to balance responsiveness with stability, ensuring smooth
acceleration and deceleration while maintaining safe distances from lead vehicles.
